"""Progress Impact engine — Before vs After for a graded submission.

Pure read-time diff between a submission and the previous graded submission of
the same skill. No AI, no new tables: bands + criteria live in the submission's
feedback JSON, mistake counts come from the `mistakes` table. Powers the
"what improved since last time" payoff screen.

Scoped to Writing/Speaking — the only skills with criteria + extracted mistakes.
"""
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.domain.models.writing import WritingSubmission
from app.domain.models.speaking import SpeakingSubmission
from app.domain.models.mistake import Mistake

_MODELS = {"writing": WritingSubmission, "speaking": SpeakingSubmission}

# Mistake category -> human label for the UI.
_CATEGORY_LABELS = {
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
    "coherence": "Coherence & linking",
    "task_response": "Task response",
    "fluency": "Fluency",
    "pronunciation": "Pronunciation",
}


def _label(category: str) -> str:
    return _CATEGORY_LABELS.get(category, category.replace("_", " ").title())


def _get_submission(db: Session, user_id: int, skill: str, submission_id: int):
    model = _MODELS[skill]
    return (
        db.query(model)
        .filter(model.id == submission_id, model.user_id == user_id, model.band.isnot(None))
        .first()
    )


def _previous_submission(db: Session, user_id: int, skill: str, current):
    """Most recent graded submission of this skill strictly before `current`.

    Ordered by (created_at, id) so same-second submissions still resolve to a
    stable predecessor.
    """
    model = _MODELS[skill]
    return (
        db.query(model)
        .filter(
            model.user_id == user_id,
            model.band.isnot(None),
            model.band > 0,
            or_(
                model.created_at < current.created_at,
                and_(model.created_at == current.created_at, model.id < current.id),
            ),
        )
        .order_by(model.created_at.desc(), model.id.desc())
        .first()
    )


def _mistake_counts(db: Session, user_id: int, skill: str, submission_id: int) -> dict[str, int]:
    rows = (
        db.query(Mistake.category, func.count(Mistake.id))
        .filter(
            Mistake.user_id == user_id,
            Mistake.skill == skill,
            Mistake.submission_id == submission_id,
        )
        .group_by(Mistake.category)
        .all()
    )
    return {category: count for category, count in rows}


def _criteria(sub) -> dict[str, float]:
    return (sub.feedback or {}).get("criteria") or {}


def _lowest_criterion(criteria: dict[str, float]) -> str | None:
    scored = {k: v for k, v in criteria.items() if v and v > 0}
    if not scored:
        return None
    return min(scored, key=lambda k: scored[k])


def _diff_criteria(prev: dict[str, float], cur: dict[str, float]) -> list[dict]:
    out: list[dict] = []
    for name, to in cur.items():
        frm = prev.get(name)
        if frm is None or to is None:
            continue
        delta = round(to - frm, 1)
        direction = "up" if delta > 0 else "down" if delta < 0 else "none"
        out.append({"name": name, "from": round(frm, 1), "to": round(to, 1), "delta": delta, "direction": direction})
    # biggest movers first, then alphabetical for stability
    out.sort(key=lambda c: (-abs(c["delta"]), c["name"]))
    return out


def _diff_mistakes(prev: dict[str, int], cur: dict[str, int]) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {"resolved": [], "improved": [], "worsened": [], "new": []}
    for category in set(prev) | set(cur):
        before = prev.get(category, 0)
        after = cur.get(category, 0)
        item = {"category": category, "label": _label(category), "from": before, "to": after}
        if before == 0 and after > 0:
            buckets["new"].append(item)
        elif after == 0 and before > 0:
            buckets["resolved"].append(item)
        elif after < before:
            buckets["improved"].append(item)
        elif after > before:
            buckets["worsened"].append(item)
        # equal & non-zero -> unchanged, omitted
    for key in buckets:
        buckets[key].sort(key=lambda m: (-abs(m["to"] - m["from"]), m["label"]))
    return buckets


def compute_progress_impact(db: Session, user_id: int, skill: str, submission_id: int) -> dict:
    if skill not in _MODELS:
        return {"skill": skill, "supported": False, "has_previous": False}

    current = _get_submission(db, user_id, skill, submission_id)
    if current is None:
        return {"skill": skill, "supported": True, "found": False, "has_previous": False}

    cur_summary = {
        "submission_id": current.id,
        "band": round(current.band, 1) if current.band is not None else None,
        "created_at": current.created_at.isoformat() if current.created_at else None,
    }
    cur_criteria = _criteria(current)

    previous = _previous_submission(db, user_id, skill, current)
    if previous is None:
        return {
            "skill": skill,
            "supported": True,
            "found": True,
            "has_previous": False,
            "current": cur_summary,
            "blocker": {"from": None, "to": _lowest_criterion(cur_criteria), "changed": False},
        }

    prev_criteria = _criteria(previous)
    band_delta = (
        round(current.band - previous.band, 1)
        if current.band is not None and previous.band is not None
        else None
    )
    blocker_from = _lowest_criterion(prev_criteria)
    blocker_to = _lowest_criterion(cur_criteria)

    return {
        "skill": skill,
        "supported": True,
        "found": True,
        "has_previous": True,
        "previous": {
            "submission_id": previous.id,
            "band": round(previous.band, 1) if previous.band is not None else None,
            "created_at": previous.created_at.isoformat() if previous.created_at else None,
        },
        "current": cur_summary,
        "band_delta": band_delta,
        "criteria": _diff_criteria(prev_criteria, cur_criteria),
        "mistakes": _diff_mistakes(
            _mistake_counts(db, user_id, skill, previous.id),
            _mistake_counts(db, user_id, skill, current.id),
        ),
        "blocker": {
            "from": blocker_from,
            "to": blocker_to,
            "changed": bool(blocker_from and blocker_to and blocker_from != blocker_to),
        },
    }
