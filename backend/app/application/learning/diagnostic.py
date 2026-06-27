from datetime import datetime
from statistics import mean

from sqlalchemy.orm import Session

from app.domain.band import round_ielts
from app.domain.models.attempt import Attempt
from app.domain.models.learning import DiagnosticSession
from app.domain.models.test import Test
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask


def _content(db: Session) -> dict:
    writing = db.query(WritingTask).order_by(WritingTask.task_type.desc(), WritingTask.id).first()
    reading = db.query(Test).filter(Test.test_type == "reading").order_by(Test.id).first()
    return {
        "writing_task_id": writing.id if writing else None,
        "reading_test_id": reading.id if reading else None,
    }


def _serialize(session: DiagnosticSession | None, db: Session) -> dict:
    base = {
        "id": None,
        "status": "not_started",
        "skills": [],
        "writing_submission_id": None,
        "reading_attempt_id": None,
        "provisional_level": None,
        "started_at": None,
        "completed_at": None,
    }
    if session:
        base.update(
            id=session.id,
            status=session.status,
            skills=session.skills or [],
            writing_submission_id=session.writing_submission_id,
            reading_attempt_id=session.reading_attempt_id,
            provisional_level=session.provisional_level,
            started_at=session.started_at,
            completed_at=session.completed_at,
        )
    base.update(_content(db))
    return base


def diagnostic_state(db: Session, user_id: int) -> dict:
    session = (
        db.query(DiagnosticSession)
        .filter(DiagnosticSession.user_id == user_id)
        .order_by(DiagnosticSession.started_at.desc(), DiagnosticSession.id.desc())
        .first()
    )
    return _serialize(session, db)


def start_diagnostic(db: Session, user_id: int, skills: list[str]) -> dict:
    session = DiagnosticSession(user_id=user_id, status="in_progress", skills=skills)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _serialize(session, db)


def refresh_diagnostic(db: Session, user_id: int) -> dict | None:
    session = (
        db.query(DiagnosticSession)
        .filter(DiagnosticSession.user_id == user_id, DiagnosticSession.status == "in_progress")
        .order_by(DiagnosticSession.started_at.desc(), DiagnosticSession.id.desc())
        .first()
    )
    if not session:
        return None

    bands: list[float] = []
    if "writing" in session.skills:
        submission = (
            db.query(WritingSubmission)
            .filter(
                WritingSubmission.user_id == user_id,
                WritingSubmission.status == "graded",
                WritingSubmission.band.isnot(None),
                WritingSubmission.created_at >= session.started_at,
            )
            .order_by(WritingSubmission.created_at.desc(), WritingSubmission.id.desc())
            .first()
        )
        if submission:
            session.writing_submission_id = submission.id
            bands.append(float(submission.band))

    if "reading" in session.skills:
        attempt = (
            db.query(Attempt)
            .join(Test, Attempt.test_id == Test.id)
            .filter(
                Attempt.user_id == user_id,
                Test.test_type == "reading",
                Attempt.band.isnot(None),
                Attempt.created_at >= session.started_at,
            )
            .order_by(Attempt.created_at.desc(), Attempt.id.desc())
            .first()
        )
        if attempt:
            session.reading_attempt_id = attempt.id
            bands.append(float(attempt.band))

    completed = all(
        session.writing_submission_id if skill == "writing" else session.reading_attempt_id
        for skill in session.skills
    )
    if completed and bands:
        session.status = "completed"
        session.provisional_level = max(4.0, min(8.5, round_ielts(mean(bands))))
        session.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return _serialize(session, db)


def accept_diagnostic_level(db: Session, user: User) -> dict | None:
    session = (
        db.query(DiagnosticSession)
        .filter(
            DiagnosticSession.user_id == user.id,
            DiagnosticSession.status == "completed",
            DiagnosticSession.provisional_level.isnot(None),
        )
        .order_by(DiagnosticSession.completed_at.desc(), DiagnosticSession.id.desc())
        .first()
    )
    if not session:
        return None
    user.current_level = session.provisional_level
    user.current_level_source = "diagnostic"
    user.target_band = max(user.target_band, session.provisional_level)
    db.add(user)
    db.commit()
    return _serialize(session, db)
