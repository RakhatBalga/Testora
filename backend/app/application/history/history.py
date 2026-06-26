"""Unified history — all graded attempts across all four skills.

Returns a flat list of HistoryItem dicts with composite IDs
(e.g. "writing-5", "reading-12") so the router and frontend can
reference any attempt with a single identifier.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.domain.models.writing import WritingSubmission
from app.domain.models.speaking import SpeakingSubmission
from app.domain.models.attempt import Attempt
from app.domain.models.test import Test


def _fmt(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _item(
    skill: str,
    ref_id: int,
    title: str,
    band: float | None,
    score: int | None,
    total: int | None,
    status: str,
    created_at: datetime | None,
    href: str,
) -> dict:
    return {
        "id": f"{skill}-{ref_id}",
        "skill": skill,
        "ref_id": ref_id,
        "title": title,
        "band": round(band, 1) if band is not None else None,
        "score": score,
        "total": total,
        "status": status,
        "created_at": _fmt(created_at),
        "href": href,
    }


def list_history(db: Session, user_id: int, skill: str | None = None) -> list[dict]:
    """Return all attempts for the user, optionally filtered by skill, newest first."""
    items: list[dict] = []

    if not skill or skill == "writing":
        rows = (
            db.query(WritingSubmission)
            .filter(WritingSubmission.user_id == user_id)
            .order_by(WritingSubmission.created_at.desc())
            .all()
        )
        for r in rows:
            title = r.task.title if r.task else f"Writing Task {r.task_id}"
            items.append(
                _item("writing", r.id, title, r.band, None, None, r.status, r.created_at, f"/writing/result/{r.id}")
            )

    if not skill or skill == "speaking":
        rows = (
            db.query(SpeakingSubmission)
            .filter(SpeakingSubmission.user_id == user_id)
            .order_by(SpeakingSubmission.created_at.desc())
            .all()
        )
        for r in rows:
            title = f"Speaking Part {r.task.part}" if r.task else "Speaking"
            status = "graded" if r.band is not None else "pending"
            items.append(
                _item("speaking", r.id, title, r.band, None, None, status, r.created_at, f"/speaking/result/{r.id}")
            )

    for skill_name in ("reading", "listening"):
        if skill and skill != skill_name:
            continue
        rows = (
            db.query(Attempt)
            .join(Test, Attempt.test_id == Test.id)
            .filter(Attempt.user_id == user_id, Test.test_type == skill_name)
            .order_by(Attempt.created_at.desc())
            .all()
        )
        for r in rows:
            title = r.test.title if r.test else f"{skill_name.title()} Test"
            items.append(
                _item(skill_name, r.id, title, r.band, r.score, r.total, "graded", r.created_at, f"/result/{r.id}")
            )

    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return items


def get_history_item(db: Session, user_id: int, item_id: str) -> dict | None:
    """Detailed record for a single history item. item_id = 'writing-5'."""
    parts = item_id.split("-", 1)
    if len(parts) != 2:
        return None
    skill, ref_str = parts
    try:
        ref_id = int(ref_str)
    except ValueError:
        return None

    if skill == "writing":
        r = (
            db.query(WritingSubmission)
            .filter(WritingSubmission.id == ref_id, WritingSubmission.user_id == user_id)
            .first()
        )
        if not r:
            return None
        return {
            "id": item_id,
            "skill": "writing",
            "ref_id": ref_id,
            "title": r.task.title if r.task else f"Writing Task {r.task_id}",
            "band": round(r.band, 1) if r.band is not None else None,
            "score": None,
            "total": None,
            "status": r.status,
            "feedback": r.feedback,
            "created_at": _fmt(r.created_at),
            "href": f"/writing/result/{ref_id}",
        }

    if skill == "speaking":
        r = (
            db.query(SpeakingSubmission)
            .filter(SpeakingSubmission.id == ref_id, SpeakingSubmission.user_id == user_id)
            .first()
        )
        if not r:
            return None
        return {
            "id": item_id,
            "skill": "speaking",
            "ref_id": ref_id,
            "title": f"Speaking Part {r.task.part}" if r.task else "Speaking",
            "band": round(r.band, 1) if r.band is not None else None,
            "score": None,
            "total": None,
            "status": "graded" if r.band is not None else "pending",
            "feedback": r.feedback,
            "created_at": _fmt(r.created_at),
            "href": f"/speaking/result/{ref_id}",
        }

    if skill in ("reading", "listening"):
        r = (
            db.query(Attempt)
            .join(Test, Attempt.test_id == Test.id)
            .filter(Attempt.id == ref_id, Attempt.user_id == user_id, Test.test_type == skill)
            .first()
        )
        if not r:
            return None
        return {
            "id": item_id,
            "skill": skill,
            "ref_id": ref_id,
            "title": r.test.title if r.test else f"{skill.title()} Test",
            "band": round(r.band, 1) if r.band is not None else None,
            "score": r.score,
            "total": r.total,
            "status": "graded",
            "breakdown": r.breakdown,
            "created_at": _fmt(r.created_at),
            "href": f"/result/{ref_id}",
        }

    return None
