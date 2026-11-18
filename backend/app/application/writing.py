"""Writing submission use cases: submit, retry, reconcile.

Quota rules: a submission only costs a free review if the AI was actually
called and succeeded. Pre-check rejections (Band 0) and failed or interrupted
gradings are free.
"""

import logging
import threading
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.ai_gate import grading_admission, run_graded_pair
from app.application.mistakes import clear_mistakes, record_mistakes
from app.application.quota import (
    enforce_free_quota,
    reconcile_stale_reservations,
    release_resource,
    reserve_ai_call,
)
from app.application.writing_precheck import validate_writing_submission, zero_band_feedback
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure.ai import get_writing_grader
from app.infrastructure.config import settings
from app.infrastructure.time import utcnow

logger = logging.getLogger("testora.writing")

# Shown instead of provider/exception text, which may contain internals.
GRADING_FAILED_SUMMARY = "Automatic grading could not be completed. Your free review was not used; please try again."
INTERRUPTED_SUMMARY = "Grading was interrupted before it finished. Your free review was not used; please retry."

# The same essay sent again this soon after its review finished is a repeated
# click or a retry after a client timeout (the browser gives up after 7 minutes
# while the server keeps grading), not a new essay: it gets the existing review.
_DUPLICATE_WINDOW = timedelta(minutes=10)
_create_lock = threading.Lock()


def _stored_feedback(feedback) -> dict:
    """Feedback JSON plus the method/provenance record (provider, model, prompt version, caps)."""
    data = feedback.to_dict()
    data["diagnostics"] = feedback.diagnostics()
    return data


def _failure_feedback(summary: str) -> dict:
    return {"band": 0.0, "criteria": {}, "summary": summary, "suggestions": ["Try submitting again."]}


def reconcile_stale_writing(db: Session, user_id: int | None = None, *, started_before: datetime | None = None) -> int:
    """Mark gradings abandoned by a dead worker as failed so they can be retried.

    By default a pending row is dead once it is older than the stale window.
    `started_before` replaces that cutoff: the startup sweep passes the boot time
    of this process, because a grading runs inside its request and so cannot
    outlive the process that started it.
    """
    cutoff = started_before or utcnow() - timedelta(minutes=settings.grading_stale_minutes)
    marker = WritingSubmission.status_updated_at
    query = db.query(WritingSubmission).filter(
        WritingSubmission.status == "pending",
        (marker < cutoff) | (marker.is_(None) & (WritingSubmission.created_at < cutoff)),
    )
    if user_id is not None:
        query = query.filter(WritingSubmission.user_id == user_id)
    rows = query.all()
    for row in rows:
        row.status = "failed"
        row.band = None
        row.feedback = _failure_feedback(INTERRUPTED_SUMMARY)
        row.status_updated_at = utcnow()
        # Its grading is dead, so free the retry lock and refund the review now
        # (once) instead of waiting for the reservation's own age check.
        release_resource(db, f"writing:{row.id}")
    # Reservations of other kinds / without a row are swept on their own age; do it
    # here too so a retry never hits a stale lock, even for quota-exempt users.
    released = reconcile_stale_reservations(db, user_id)
    if rows:
        db.commit()
    return len(rows) + released


def get_owned_submission(db: Session, user: User, submission_id: int) -> WritingSubmission:
    reconcile_stale_writing(db, user.id)
    sub = (
        db.query(WritingSubmission)
        .filter(WritingSubmission.id == submission_id, WritingSubmission.user_id == user.id)
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


def list_submissions(db: Session, user: User) -> list[WritingSubmission]:
    reconcile_stale_writing(db, user.id)
    return (
        db.query(WritingSubmission)
        .filter(WritingSubmission.user_id == user.id)
        .order_by(WritingSubmission.created_at.desc())
        .all()
    )


def _find_duplicate(db: Session, user: User, task: WritingTask, text: str, now: datetime) -> WritingSubmission | None:
    """The submission this request repeats, if any.

    A pending one is returned however old it is (it is still being graded, the
    client polls it); a graded one only shortly after its review finished.
    Failed and rejected (Band 0) submissions never match, so they can be resent.
    """
    same_essay = db.query(WritingSubmission).filter(
        WritingSubmission.user_id == user.id,
        WritingSubmission.task_id == task.id,
        WritingSubmission.text == text,
    )
    pending = same_essay.filter(WritingSubmission.status == "pending").order_by(WritingSubmission.id.desc()).first()
    if pending is not None:
        return pending
    finished_at = func.coalesce(WritingSubmission.status_updated_at, WritingSubmission.created_at)
    return (
        same_essay.filter(
            WritingSubmission.status == "graded",
            WritingSubmission.band > 0,
            finished_at > now - _DUPLICATE_WINDOW,
        )
        .order_by(WritingSubmission.id.desc())
        .first()
    )


def find_submission_by_key(db: Session, user_id: int, key: str | None) -> WritingSubmission | None:
    if not key:
        return None
    return (
        db.query(WritingSubmission)
        .filter(WritingSubmission.user_id == user_id, WritingSubmission.submission_key == key)
        .first()
    )


def _insert_submission(db: Session, sub: WritingSubmission) -> tuple[WritingSubmission, bool]:
    """Store a new submission. Returns (row, created); a key that another request
    stored first yields that request's row instead of a second one."""
    user_id, key = sub.user_id, sub.submission_key
    db.add(sub)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = find_submission_by_key(db, user_id, key)
        if existing is None:
            raise
        return existing, False
    db.refresh(sub)
    return sub, True


def submit_writing(
    db: Session, user: User, task: WritingTask, text: str, submission_key: str | None = None
) -> WritingSubmission:
    """Grade an essay.

    Idempotent: a repeated `submission_key` returns the first submission whatever
    its status (pending, graded, failed, rejected) and never charges again.
    Without a key, an identical essay sent again shortly after is matched by text.
    """
    existing = find_submission_by_key(db, user.id, submission_key)
    if existing is not None:
        return existing
    precheck = validate_writing_submission(task_type=task.task_type, text=text, min_words=task.min_words)
    now = utcnow()
    if not precheck.valid:
        # Nothing to grade: answer with the Band-0 explanation without touching
        # the AI or the user's free reviews, and keep it out of mistake memory.
        sub = WritingSubmission(
            user_id=user.id,
            task_id=task.id,
            text=text,
            word_count=precheck.word_count,
            status="graded",
            band=0.0,
            status_updated_at=now,
            feedback=zero_band_feedback(task.task_type, precheck).to_dict(),
            submission_key=submission_key,
        )
        return _insert_submission(db, sub)[0]

    reconcile_stale_writing(db, user.id)

    with _create_lock:
        # Before the quota check: a resubmit of the essay that took the last free
        # review must get that review back, not "no free reviews left".
        duplicate = find_submission_by_key(db, user.id, submission_key) or (
            None if submission_key else _find_duplicate(db, user, task, text, now)
        )
        if duplicate is not None:
            return duplicate
        enforce_free_quota(db, WritingSubmission, user, settings.FREE_WRITING_SUBMISSIONS, "writing")
        sub = WritingSubmission(
            user_id=user.id,
            task_id=task.id,
            text=text,
            word_count=precheck.word_count,
            status="pending",
            status_updated_at=now,
            submission_key=submission_key,
        )
        sub, created = _insert_submission(db, sub)
        if not created:
            return sub
    try:
        return _grade_and_persist(db, user, sub, task)
    except HTTPException:
        # Refused before grading (quota, busy): do not leave a pending ghost row.
        db.rollback()
        if sub.status == "pending" and sub.feedback is None:
            db.delete(sub)
            db.commit()
        raise


def retry_writing(db: Session, user: User, submission_id: int) -> WritingSubmission:
    sub = get_owned_submission(db, user, submission_id)  # also reconciles stale pending rows
    if sub.status != "failed":
        raise HTTPException(409, "Only failed writing submissions can be retried")
    return _grade_and_persist(db, user, sub, sub.task)


def _grade_and_persist(db: Session, user: User, submission: WritingSubmission, task: WritingTask) -> WritingSubmission:
    with grading_admission():
        with reserve_ai_call(
            db,
            user,
            "writing",
            model=WritingSubmission,
            limit=settings.FREE_WRITING_SUBMISSIONS,
            resource=f"writing:{submission.id}",
        ) as reservation:
            db.refresh(submission)
            if submission.status not in ("failed", "pending"):
                raise HTTPException(409, "This submission was already graded")
            submission.status = "pending"
            submission.status_updated_at = utcnow()
            db.add(submission)
            db.commit()
            try:
                result = _perform_grading(db, user, submission, task)
            except BaseException:
                db.rollback()
                submission.status = "failed"
                submission.band = None
                submission.status_updated_at = utcnow()
                db.commit()
                raise
            reservation.success = result.status == "graded" and (result.band or 0) > 0
            return result


def _perform_grading(db: Session, user: User, submission: WritingSubmission, task: WritingTask) -> WritingSubmission:
    precheck = validate_writing_submission(task_type=task.task_type, text=submission.text, min_words=task.min_words)
    submission.word_count = precheck.word_count
    submission.band = None

    improved: str | None = None
    if precheck.valid:
        grader = get_writing_grader()
        # The "Better Version" rewrite is independent of the examiner's output,
        # so it runs concurrently instead of adding its latency on top.
        feedback, improved_result = run_graded_pair(
            grader.grade,
            dict(task_type=task.task_type, prompt=task.prompt, text=submission.text, min_words=task.min_words),
            grader.improve,
            dict(task_type=task.task_type, prompt=task.prompt, text=submission.text),
        )
        if isinstance(improved_result, BaseException):
            logger.warning("Better Version generation failed for user %s task %s", user.id, task.id)
        else:
            improved = improved_result
    else:
        feedback = zero_band_feedback(task.task_type, precheck)

    # A very slow grading can outlive the stale window; if the sweep already failed
    # this row (and refunded its review), the late result must not overwrite it:
    # that would hand out a graded essay for a refunded review. Keep it failed.
    current_status = db.execute(select(WritingSubmission.status).where(WritingSubmission.id == submission.id)).scalar()
    if current_status != "pending":
        logger.warning(
            "Writing grading for submission %s finished after it was reconciled (%s); discarding the late result",
            submission.id,
            current_status,
        )
        db.rollback()
        db.refresh(submission)
        return submission

    db.add(submission)
    db.flush()  # assign submission.id before replacing/recording its mistakes
    clear_mistakes(db, user_id=user.id, submission_id=submission.id, skill="writing")
    if feedback.error:
        # Grading failed: keep the user's text, record no band or mistakes, and
        # never show provider/exception text to the user (log it instead).
        logger.warning("Writing grading failed for user %s task %s: %s", user.id, task.id, feedback.summary)
        feedback.summary = GRADING_FAILED_SUMMARY
        submission.feedback = _stored_feedback(feedback)
        submission.band = None
        submission.status = "failed"
        submission.status_updated_at = utcnow()
        db.commit()
        db.refresh(submission)
        return submission

    submission.feedback = _stored_feedback(feedback) if precheck.valid else feedback.to_dict()
    submission.band = feedback.band
    submission.status = "graded"
    submission.status_updated_at = utcnow()
    if improved:
        submission.improved_text = improved
    if precheck.valid:
        record_mistakes(db, user_id=user.id, submission_id=submission.id, skill="writing", mistakes=feedback.mistakes)
    db.commit()
    db.refresh(submission)
    return submission
