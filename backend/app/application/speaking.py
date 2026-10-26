"""Speaking submission use case: store the recording, grade it, keep mistakes."""

import logging
import os
import tempfile
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ai_gate import grading_admission, run_graded
from app.application.mistakes import record_mistakes
from app.application.quota import enforce_free_quota, reconcile_stale_reservations, reserve_ai_call
from app.domain.models.speaking import SpeakingSubmission, SpeakingTask
from app.domain.models.user import User
from app.infrastructure.ai import get_speaking_grader
from app.infrastructure.config import settings
from app.infrastructure.storage import get_storage, storage_for_key
from app.infrastructure.storage.sniff import sniff_audio
from app.infrastructure.time import utcnow

logger = logging.getLogger("testora.speaking")

_SUFFIX = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/flac": ".flac",
}


def speaking_enabled() -> bool:
    return settings.SPEAKING_ENABLED and settings.FREE_SPEAKING_SUBMISSIONS != 0


def require_speaking_enabled() -> None:
    if not speaking_enabled():
        raise HTTPException(
            status_code=403,
            detail={
                "code": "speaking_disabled",
                "message": "Speaking assessment is not available yet.",
            },
        )


def task_questions(task: SpeakingTask) -> list[str]:
    return [str(q) for q in task.questions or []]


def detect_audio_type(data: bytes) -> str:
    content_type = sniff_audio(data[:16])
    if content_type is None:
        raise HTTPException(status_code=415, detail="Unsupported audio format. Use WebM, OGG, MP3, WAV or M4A.")
    return content_type


GRADING_FAILED_SUMMARY = "Automatic grading could not be completed. Please try again."
INTERRUPTED_SUMMARY = "Grading was interrupted before it finished. Your free review was not used; please try again."


def _failure_feedback(summary: str) -> dict:
    return {"band": 0.0, "criteria": {}, "summary": summary, "suggestions": ["Try recording your answer again."]}


def reconcile_stale_speaking(db: Session, user_id: int | None = None) -> int:
    """Give recordings whose grading died a visible failed state (no band, error feedback).

    A speaking row is created before the grader runs, so a killed worker or an
    exception leaves band and feedback both empty forever. The matching
    reservation is expired (and the review refunded) by the same sweep.
    """
    cutoff = utcnow() - timedelta(minutes=settings.grading_stale_minutes)
    query = db.query(SpeakingSubmission).filter(
        SpeakingSubmission.band.is_(None),
        SpeakingSubmission.feedback.is_(None),
        SpeakingSubmission.created_at < cutoff,
    )
    if user_id is not None:
        query = query.filter(SpeakingSubmission.user_id == user_id)
    rows = query.all()
    for row in rows:
        row.feedback = _failure_feedback(INTERRUPTED_SUMMARY)
    if rows:
        db.commit()
    return len(rows) + reconcile_stale_reservations(db, user_id)


def _mark_failed(db: Session, key: str) -> None:
    """An exception ended grading: the recording stays, but not as a silent blank row."""
    row = db.query(SpeakingSubmission).filter(SpeakingSubmission.audio_url == key).first()
    if row is not None and row.feedback is None and row.band is None:
        row.feedback = _failure_feedback(GRADING_FAILED_SUMMARY)
        db.commit()


def submit_speaking(db: Session, user: User, task: SpeakingTask, audio: bytes) -> SpeakingSubmission:
    require_speaking_enabled()
    content_type = detect_audio_type(audio)
    enforce_free_quota(db, SpeakingSubmission, user, settings.FREE_SPEAKING_SUBMISSIONS, "speaking")

    storage = get_storage()
    key = None
    with grading_admission():
        try:
            with reserve_ai_call(
                db, user, "speaking", model=SpeakingSubmission, limit=settings.FREE_SPEAKING_SUBMISSIONS
            ) as reservation:
                key = storage.save(db, kind="speaking_audio", owner_id=user.id, data=audio, content_type=content_type)
                submission = SpeakingSubmission(user_id=user.id, task_id=task.id, audio_url=key, transcript=None)
                db.add(submission)
                db.commit()
                feedback = _grade_audio(task, audio, content_type)
                # The sweep may have failed this row while a very slow grading ran
                # (and refunded the review): do not resurrect it with a free band.
                late = db.execute(
                    select(SpeakingSubmission.feedback).where(SpeakingSubmission.id == submission.id)
                ).scalar()
                if late is not None:
                    logger.warning("Speaking grading for submission %s finished after reconciliation", submission.id)
                    db.rollback()
                    db.refresh(submission)
                    return submission
                reservation.success = not feedback.error
                if feedback.error:
                    # Keep the recording, but never store a bogus band or mistakes.
                    logger.warning(
                        "Speaking grading failed for user %s task %s: %s", user.id, task.id, feedback.summary
                    )
                    feedback.summary = "Automatic grading could not be completed. Please try again."
                    submission.feedback = {**feedback.to_dict(), "diagnostics": feedback.diagnostics()}
                    submission.band = None
                    db.commit()
                    db.refresh(submission)
                    return submission
                submission.feedback = {**feedback.to_dict(), "diagnostics": feedback.diagnostics()}
                submission.band = feedback.band
                db.flush()  # assign submission.id before recording its mistakes
                record_mistakes(
                    db, user_id=user.id, submission_id=submission.id, skill="speaking", mistakes=feedback.mistakes
                )
                db.commit()
                db.refresh(submission)
                return submission
        except BaseException:
            # Keep recordings that belong to a persisted submission; drop rejected uploads.
            if key is not None:
                if _submission_persisted(db, key):
                    _mark_failed(db, key)
                else:
                    storage_for_key(key).delete(db, key)
                    db.commit()
            raise


def _submission_persisted(db: Session, key: str) -> bool:
    return db.query(SpeakingSubmission.id).filter(SpeakingSubmission.audio_url == key).first() is not None


def _grade_audio(task: SpeakingTask, audio: bytes, content_type: str):
    """The grader reads a file path, so hand it a short-lived temp copy."""
    handle, path = tempfile.mkstemp(suffix=_SUFFIX.get(content_type, ".webm"))
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(audio)
        grader = get_speaking_grader()
        return run_graded(
            grader.grade, part=task.part, questions=task_questions(task), audio_path=path, transcript=None
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
