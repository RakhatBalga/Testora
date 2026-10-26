"""Writing submission use cases: submit, retry, reconcile.

Quota rules: a submission only costs a free review if the AI was actually
called and succeeded. Pre-check rejections (Band 0) and failed or interrupted
gradings are free.
"""

import logging
import threading
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.application.ai_gate import grading_admission, run_graded_pair
from app.application.mistakes import clear_mistakes, record_mistakes
from app.application.quota import enforce_free_quota, reserve_ai_call
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

# A repeated identical submit inside this window is the same click, not a new essay.
_DUPLICATE_WINDOW = timedelta(minutes=2)
_create_lock = threading.Lock()


def _stored_feedback(feedback) -> dict:
    """Feedback JSON plus the method/provenance record (provider, model, prompt version, caps)."""
    data = feedback.to_dict()
    data["diagnostics"] = feedback.diagnostics()
    return data


def _failure_feedback(summary: str) -> dict:
    return {"band": 0.0, "criteria": {}, "summary": summary, "suggestions": ["Try submitting again."]}


def reconcile_stale_writing(db: Session, user_id: int | None = None) -> int:
    """Mark gradings abandoned by a dead worker as failed so they can be retried."""
    cutoff = utcnow() - timedelta(minutes=settings.grading_stale_minutes)
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
    if rows:
        db.commit()
    return len(rows)


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


def submit_writing(db: Session, user: User, task: WritingTask, text: str) -> WritingSubmission:
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
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return sub

    reconcile_stale_writing(db, user.id)
    enforce_free_quota(db, WritingSubmission, user, settings.FREE_WRITING_SUBMISSIONS, "writing")

    with _create_lock:
        duplicate = (
            db.query(WritingSubmission)
            .filter(
                WritingSubmission.user_id == user.id,
                WritingSubmission.task_id == task.id,
                WritingSubmission.text == text,
                WritingSubmission.status != "failed",
                WritingSubmission.created_at > now - _DUPLICATE_WINDOW,
            )
            .order_by(WritingSubmission.id.desc())
            .first()
        )
        if duplicate is not None:
            if duplicate.status == "pending":
                raise HTTPException(409, "This essay is already being graded.")
            return duplicate
        sub = WritingSubmission(
            user_id=user.id,
            task_id=task.id,
            text=text,
            word_count=precheck.word_count,
            status="pending",
            status_updated_at=now,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
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
