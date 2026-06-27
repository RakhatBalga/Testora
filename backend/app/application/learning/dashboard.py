from statistics import mean

from sqlalchemy.orm import Session

from app.domain.band import round_ielts
from app.domain.models.attempt import Attempt
from app.domain.models.test import Test
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission
from app.infrastructure.time import local_today

from .diagnostic import diagnostic_state
from .notebook import notebook_summary
from .study_plan import get_weekly_plan


def _latest_writing(db: Session, user_id: int) -> WritingSubmission | None:
    return (
        db.query(WritingSubmission)
        .filter(
            WritingSubmission.user_id == user_id,
            WritingSubmission.status == "graded",
            WritingSubmission.band.isnot(None),
        )
        .order_by(WritingSubmission.created_at.desc(), WritingSubmission.id.desc())
        .first()
    )


def _latest_reading(db: Session, user_id: int) -> Attempt | None:
    return (
        db.query(Attempt)
        .join(Test, Attempt.test_id == Test.id)
        .filter(Attempt.user_id == user_id, Test.test_type == "reading", Attempt.band.isnot(None))
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .first()
    )


def dashboard_summary(db: Session, user: User) -> dict:
    writing = _latest_writing(db, user.id)
    reading = _latest_reading(db, user.id)
    practice_bands = [float(row.band) for row in (writing, reading) if row and row.band is not None]
    current = user.current_level
    current_source = user.current_level_source
    if current is None and practice_bands:
        current = round_ielts(mean(practice_bands))
        current_source = "recent Writing and Reading practice"

    criteria = (writing.feedback or {}).get("criteria", {}) if writing else {}
    scored = {key: value for key, value in criteria.items() if isinstance(value, (int, float)) and value > 0}
    writing_weakness = None
    if scored:
        key = min(scored, key=scored.get)
        writing_weakness = {"label": key, "value": float(scored[key]), "href": f"/writing/result/{writing.id}"}

    reading_weakness = None
    breakdown = [item for item in (reading.breakdown or []) if item.get("total", 0) > 0] if reading else []
    if breakdown:
        item = min(breakdown, key=lambda row: row.get("accuracy", 0))
        reading_weakness = {
            "label": item.get("label") or str(item.get("question_type", "Questions")).replace("_", " ").title(),
            "value": float(item.get("accuracy", 0)),
            "href": f"/reading/{reading.test_id}?attempt={reading.id}",
        }

    plan = get_weekly_plan(db, user)
    today = local_today()
    todays_items = [item for item in plan["items"] if item["scheduled_date"] <= today and item["status"] == "pending"]
    primary = (todays_items or [None])[0]

    recent = []
    if writing:
        recent.append({
            "id": f"writing-{writing.id}",
            "skill": "writing",
            "title": writing.task.title if writing.task else "Writing",
            "band": writing.band,
            "created_at": writing.created_at,
            "href": f"/writing/result/{writing.id}",
        })
    if reading:
        recent.append({
            "id": f"reading-{reading.id}",
            "skill": "reading",
            "title": reading.test.title if reading.test else "Reading",
            "band": reading.band,
            "created_at": reading.created_at,
            "href": f"/reading/{reading.test_id}?attempt={reading.id}",
        })
    recent.sort(key=lambda row: row["created_at"], reverse=True)

    return {
        "profile": {
            "target_band": user.target_band,
            "current_level": current,
            "current_level_source": current_source,
            "exam_date": user.exam_date,
            "days_to_exam": max(0, (user.exam_date - today).days) if user.exam_date else None,
            "onboarding_completed": bool(user.onboarding_completed),
        },
        "weekly_plan": plan,
        "today": primary,
        "weaknesses": {"writing": writing_weakness, "reading": reading_weakness},
        "recent": recent,
        "mistakes": notebook_summary(db, user.id),
        "diagnostic": diagnostic_state(db, user.id),
    }
