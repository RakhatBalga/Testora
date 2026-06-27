import re
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.domain.models.attempt import Attempt
from app.domain.models.learning import StudyPlanItem
from app.domain.models.mistake import Mistake
from app.domain.models.test import Test
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure.time import local_today


def week_start(day: date | None = None) -> date:
    day = day or local_today()
    return day - timedelta(days=day.weekday())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _reading_signal(db: Session, user_id: int) -> tuple[dict | None, Attempt | None]:
    attempt = (
        db.query(Attempt)
        .join(Test, Attempt.test_id == Test.id)
        .filter(Attempt.user_id == user_id, Test.test_type == "reading")
        .order_by(Attempt.created_at.desc(), Attempt.id.desc())
        .first()
    )
    items = [item for item in (attempt.breakdown or []) if item.get("total", 0) > 0] if attempt else []
    return (min(items, key=lambda item: item.get("accuracy", 0)) if items else None, attempt)


def _writing_signal(db: Session, user_id: int) -> tuple[str | None, float | None, WritingSubmission | None]:
    submission = (
        db.query(WritingSubmission)
        .filter(
            WritingSubmission.user_id == user_id,
            WritingSubmission.status == "graded",
            WritingSubmission.band.isnot(None),
        )
        .order_by(WritingSubmission.created_at.desc(), WritingSubmission.id.desc())
        .first()
    )
    criteria = (submission.feedback or {}).get("criteria", {}) if submission else {}
    scored = {name: value for name, value in criteria.items() if isinstance(value, (int, float)) and value > 0}
    if not scored:
        return None, None, submission
    criterion = min(scored, key=scored.get)
    return criterion, float(scored[criterion]), submission


def _candidates(db: Session, user: User) -> list[dict]:
    reading_test = db.query(Test).filter(Test.test_type == "reading").order_by(Test.id).first()
    criterion, criterion_band, writing = _writing_signal(db, user.id)
    preferred_task_type = 1 if criterion == "Task Achievement" else 2
    writing_task = (
        db.query(WritingTask)
        .filter(WritingTask.task_type == preferred_task_type)
        .order_by(WritingTask.id)
        .first()
    )
    reading_type, reading = _reading_signal(db, user.id)
    minutes = max(15, min(int(user.daily_study_minutes or 30), 90))
    maintaining = user.current_level is not None and user.current_level >= user.target_band
    tasks: list[dict] = []

    if criterion and writing_task:
        tasks.append({
            "stable_key": f"writing-criterion-{_slug(criterion)}",
            "title": f"{'Reinforce' if maintaining else 'Improve'} {criterion}",
            "reason": (
                f"Your latest Writing score for {criterion} is Band {criterion_band:.1f}; focused practice will help maintain your target level."
                if maintaining
                else f"Your latest Writing score for {criterion} is Band {criterion_band:.1f}, making it the clearest limiter below your Band {user.target_band:.1f} target."
            ),
            "minutes": min(minutes, writing_task.duration_minutes),
            "skill": "writing",
            "action_type": "practice",
            "href": f"/writing/{writing_task.id}",
            "source_type": "writing_criterion",
            "source_ref": str(writing.id),
        })

    if reading_type and reading_test and reading:
        label = reading_type.get("label") or str(reading_type.get("question_type", "questions")).replace("_", " ").title()
        tasks.append({
            "stable_key": f"reading-type-{_slug(str(reading_type.get('question_type', label)))}",
            "title": f"Drill {label}",
            "reason": f"This is your weakest recent Reading question type at {reading_type.get('accuracy', 0):.0f}% accuracy.",
            "minutes": min(minutes, reading_test.duration_minutes),
            "skill": "reading",
            "action_type": "practice",
            "href": f"/reading/{reading_test.id}",
            "source_type": "reading_breakdown",
            "source_ref": str(reading.id),
        })

    recurring = (
        db.query(Mistake)
        .filter(Mistake.user_id == user.id, Mistake.skill == "writing")
        .order_by(Mistake.created_at.desc(), Mistake.id.desc())
        .first()
    )
    if recurring:
        label = (recurring.subskill or recurring.category).replace("_", " ").title()
        tasks.append({
            "stable_key": f"review-writing-{_slug(recurring.subskill or recurring.category)}",
            "title": f"Review {label}",
            "reason": "A recent Writing review flagged this pattern; revisiting it before the next essay reduces repeat errors.",
            "minutes": min(15, minutes),
            "skill": "writing",
            "action_type": "review",
            "href": "/mistakes?skill=writing",
            "source_type": "mistake",
            "source_ref": str(recurring.id),
        })

    if writing_task and not any(task["skill"] == "writing" for task in tasks):
        tasks.append({
            "stable_key": "writing-baseline",
            "title": "Complete a Writing diagnostic task",
            "reason": "A graded essay gives Testora criterion-level evidence for a more precise plan.",
            "minutes": min(minutes, writing_task.duration_minutes),
            "skill": "writing",
            "action_type": "diagnostic" if not writing else "practice",
            "href": f"/writing/{writing_task.id}",
            "source_type": "cold_start",
            "source_ref": str(writing_task.id),
        })
    if reading_test and not any(task["skill"] == "reading" for task in tasks):
        tasks.append({
            "stable_key": "reading-baseline",
            "title": "Complete a Reading practice test",
            "reason": "A Reading result identifies the question types that need the most attention.",
            "minutes": min(minutes, reading_test.duration_minutes),
            "skill": "reading",
            "action_type": "diagnostic" if not reading else "practice",
            "href": f"/reading/{reading_test.id}",
            "source_type": "cold_start",
            "source_ref": str(reading_test.id),
        })

    focus = user.primary_focus or "balanced"
    tasks.sort(key=lambda task: (0 if focus == task["skill"] else 1, task["stable_key"]))
    if user.exam_date:
        days = (user.exam_date - local_today()).days
        if days >= 0:
            for task in tasks:
                task["reason"] += f" Your exam is in {days} day{'s' if days != 1 else ''}."
    return tasks[: max(1, min(user.weekly_study_days or 3, 7))]


def _serialize(item: StudyPlanItem) -> dict:
    return {
        "id": item.id,
        "stable_id": item.stable_key,
        "title": item.title,
        "reason": item.reason,
        "minutes": item.minutes,
        "skill": item.skill,
        "action_type": item.action_type,
        "href": item.href,
        "status": item.status,
        "scheduled_date": item.scheduled_date,
        "source": {"type": item.source_type, "ref": item.source_ref},
    }


def _has_new_results(db: Session, user_id: int, items: list[StudyPlanItem]) -> bool:
    plan_updated = max((item.updated_at or item.created_at) for item in items)
    writing_at = (
        db.query(WritingSubmission.created_at)
        .filter(
            WritingSubmission.user_id == user_id,
            WritingSubmission.status == "graded",
            WritingSubmission.band.isnot(None),
        )
        .order_by(WritingSubmission.created_at.desc())
        .limit(1)
        .scalar()
    )
    reading_at = (
        db.query(Attempt.created_at)
        .join(Test, Attempt.test_id == Test.id)
        .filter(Attempt.user_id == user_id, Test.test_type == "reading")
        .order_by(Attempt.created_at.desc())
        .limit(1)
        .scalar()
    )
    latest_result = max((value for value in (writing_at, reading_at) if value), default=None)
    return bool(latest_result and latest_result > plan_updated)


def get_weekly_plan(db: Session, user: User, recalculate: bool = False) -> dict:
    start = week_start()
    existing = (
        db.query(StudyPlanItem)
        .filter(StudyPlanItem.user_id == user.id, StudyPlanItem.week_start == start)
        .order_by(StudyPlanItem.scheduled_date, StudyPlanItem.id)
        .all()
    )
    if existing and not recalculate and not _has_new_results(db, user.id, existing):
        return _response(existing, start)

    by_key = {item.stable_key: item for item in existing}
    candidates = _candidates(db, user)
    today = local_today()
    first_day = max(start, today)
    available_days = (start + timedelta(days=6) - first_day).days + 1
    candidates = candidates[:available_days]
    generated: list[StudyPlanItem] = []
    for index, candidate in enumerate(candidates):
        scheduled = first_day + timedelta(days=index)
        item = by_key.get(candidate["stable_key"])
        if item is None:
            item = StudyPlanItem(user_id=user.id, week_start=start, status="pending", **candidate)
            db.add(item)
        elif item.status != "completed":
            for key, value in candidate.items():
                setattr(item, key, value)
        item.scheduled_date = scheduled
        generated.append(item)

    keep = {item.stable_key for item in generated}
    for item in existing:
        if item.stable_key not in keep:
            if item.status == "completed":
                generated.append(item)
            else:
                db.delete(item)
    db.commit()
    for item in generated:
        db.refresh(item)
    generated.sort(key=lambda item: (item.scheduled_date, item.id))
    return _response(generated, start)


def _response(items: list[StudyPlanItem], start: date) -> dict:
    completed = sum(item.status == "completed" for item in items)
    return {
        "week_start": start,
        "week_end": start + timedelta(days=6),
        "completed": completed,
        "total": len(items),
        "progress": round(completed / len(items) * 100) if items else 0,
        "items": [_serialize(item) for item in items],
    }


def set_plan_status(db: Session, user_id: int, item_id: int, status: str) -> dict | None:
    item = db.query(StudyPlanItem).filter(StudyPlanItem.id == item_id, StudyPlanItem.user_id == user_id).first()
    if not item:
        return None
    item.status = status
    db.commit()
    db.refresh(item)
    return _serialize(item)
