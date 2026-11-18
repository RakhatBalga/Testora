"""Unified history — all graded attempts across all four skills.

Returns a flat list of HistoryItem dicts with composite IDs
(e.g. "writing-5", "reading-12") so the router and frontend can
reference any attempt with a single identifier.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.application import frontend_routes as routes
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


def _ordered(query, model, sort: str, limit: int | None):
    """One source in the requested order, cut to the rows a page can need.

    The tie-breaks (newest first, then highest id) are the ones `_sort` applies
    after the merge, so the first `limit` rows of every source always contain
    the first `limit` rows of the merged list.
    """
    newest = (model.created_at.desc().nulls_last(), model.id.desc())
    if sort == "oldest":
        order = (model.created_at.asc().nulls_first(), model.id.desc())
    elif sort == "highest":
        order = (model.band.is_(None), model.band.desc(), *newest)
    elif sort == "lowest":
        order = (model.band.is_(None), model.band.asc(), *newest)
    else:
        order = newest
    query = query.order_by(*order)
    return (query.limit(limit) if limit is not None else query).all()


def _sources(db: Session, user_id: int, skill: str | None) -> list[tuple[str, type, object]]:
    """(skill, model, base query) for every table that feeds the history."""
    sources: list[tuple[str, type, object]] = []
    if not skill or skill == "writing":
        sources.append(
            ("writing", WritingSubmission, db.query(WritingSubmission).filter(WritingSubmission.user_id == user_id))
        )
    if not skill or skill == "speaking":
        sources.append(
            ("speaking", SpeakingSubmission, db.query(SpeakingSubmission).filter(SpeakingSubmission.user_id == user_id))
        )
    for skill_name in ("reading", "listening"):
        if skill and skill != skill_name:
            continue
        query = (
            db.query(Attempt)
            .join(Test, Attempt.test_id == Test.id)
            .filter(Attempt.user_id == user_id, Test.test_type == skill_name)
        )
        sources.append((skill_name, Attempt, query))
    return sources


def _to_item(skill: str, r) -> dict:
    if skill == "writing":
        title = r.task.title if r.task else f"Writing Task {r.task_id}"
        return _item("writing", r.id, title, r.band, None, None, r.status, r.created_at, routes.result("writing", r.id))
    if skill == "speaking":
        title = f"Speaking Part {r.task.part}" if r.task else "Speaking"
        status = "graded" if r.band is not None else "pending"
        return _item("speaking", r.id, title, r.band, None, None, status, r.created_at, routes.result("speaking", r.id))
    title = r.test.title if r.test else f"{skill.title()} Test"
    return _item(skill, r.id, title, r.band, r.score, r.total, "graded", r.created_at, routes.result(skill, r.id))


def _sort(items: list[dict], sort: str) -> None:
    """Order the merged list. Stable sorts, so every order falls back to newest
    first, then to the source order (writing, speaking, reading, listening)."""
    items.sort(key=lambda x: x["created_at"] or "", reverse=True)
    if sort == "oldest":
        items.sort(key=lambda x: x["created_at"] or "")
    elif sort == "highest":
        items.sort(key=lambda x: (x["band"] is None, -(x["band"] or 0)))
    elif sort == "lowest":
        items.sort(key=lambda x: (x["band"] is None, x["band"] or 0))


def list_history(
    db: Session, user_id: int, skill: str | None = None, sort: str = "newest", limit: int | None = None
) -> list[dict]:
    """Attempts of the user in `sort` order, optionally filtered by skill.

    With `limit`, each table is read only up to `limit` rows (in SQL) before the
    merge, so a page costs the same however long the history is.
    """
    items: list[dict] = []
    for skill_name, model, query in _sources(db, user_id, skill):
        rows = _ordered(query, model, sort, limit)
        # Canonical newest-first order inside a source, whatever SQL order fetched it.
        rows.sort(key=lambda r: ((r.created_at.isoformat() if r.created_at else ""), r.id), reverse=True)
        items.extend(_to_item(skill_name, r) for r in rows)
    _sort(items, sort)
    return items[:limit] if limit is not None else items


def history_page(db: Session, user_id: int, skill: str | None, sort: str, page: int, page_size: int) -> dict:
    total = sum(query.count() for _, _, query in _sources(db, user_id, skill))
    start = (page - 1) * page_size
    items = list_history(db, user_id, skill=skill, sort=sort, limit=start + page_size) if start < total else []
    return {"items": items[start:], "total": total, "page": page, "page_size": page_size}


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
            "href": routes.result("writing", ref_id),
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
            "href": routes.result("speaking", ref_id),
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
            "href": routes.result(skill, ref_id),
        }

    return None
