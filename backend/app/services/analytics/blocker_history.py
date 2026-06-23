"""Blocker History engine.

Reconstructs the user's *main blocker* (lowest-scoring criterion across Writing &
Speaking) week by week, from the criteria stored on each graded submission. Lets
the dashboard show "Grammar → Grammar → Grammar → Vocabulary" and call out when
a long-standing blocker is finally dethroned. Pure read-time aggregation, no AI,
no new tables.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.writing import WritingSubmission
from app.models.speaking import SpeakingSubmission


def _events(db: Session, user_id: int) -> list[tuple[datetime, str, dict]]:
    """(created_at, skill, criteria) for every graded W/S submission, oldest first."""
    events: list[tuple[datetime, str, dict]] = []
    for skill, model in (("writing", WritingSubmission), ("speaking", SpeakingSubmission)):
        rows = (
            db.query(model.created_at, model.feedback)
            .filter(model.user_id == user_id, model.band.isnot(None), model.band > 0)
            .all()
        )
        for created_at, feedback in rows:
            criteria = (feedback or {}).get("criteria") or {}
            if created_at and criteria:
                events.append((created_at, skill, criteria))
    events.sort(key=lambda e: e[0])
    return events


def _global_blocker(latest: dict[str, dict]) -> tuple[str, str] | None:
    """Lowest-scoring criterion across all skills' most recent feedback.

    Returns (criterion, skill) or None. Tie-broken by criterion name for stability.
    """
    candidates: list[tuple[float, str, str]] = []
    for skill, criteria in latest.items():
        for name, band in criteria.items():
            if band and band > 0:
                candidates.append((float(band), name, skill))
    if not candidates:
        return None
    candidates.sort(key=lambda c: (c[0], c[1]))
    _, name, skill = candidates[0]
    return name, skill


def _week_label(d: datetime) -> str:
    return f"Wk of {d.strftime('%b %-d')}"


def compute_blocker_history(db: Session, user_id: int) -> dict:
    events = _events(db, user_id)
    if not events:
        return {"has_data": False, "history": [], "note": None}

    # Group events by ISO (year, week); process weeks in order.
    weeks: dict[tuple[int, int], list[tuple[datetime, str, dict]]] = {}
    for created_at, skill, criteria in events:
        iso = created_at.isocalendar()
        weeks.setdefault((iso[0], iso[1]), []).append((created_at, skill, criteria))

    latest: dict[str, dict] = {}
    history: list[dict] = []
    for key in sorted(weeks.keys()):
        week_events = weeks[key]
        for created_at, skill, criteria in week_events:
            latest[skill] = criteria
        blocker = _global_blocker(latest)
        if blocker is None:
            continue
        criterion, skill = blocker
        label = _week_label(min(e[0] for e in week_events))
        changed = bool(history) and history[-1]["blocker"] != criterion
        history.append({"label": label, "blocker": criterion, "skill": skill, "changed": changed})

    # Note for the most recent change, if any.
    note = None
    last_change = next((h for h in reversed(history) if h["changed"]), None)
    if last_change:
        idx = history.index(last_change)
        previous = history[idx - 1]["blocker"]
        note = f"{previous} is no longer your primary limitation — it's now {last_change['blocker']}."

    return {"has_data": True, "history": history, "note": note}
