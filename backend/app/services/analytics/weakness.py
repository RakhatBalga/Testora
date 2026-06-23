"""Weakness aggregation engine.

Pure aggregation over the `mistakes` table. No AI. Recent mistakes weigh more
(exponential recency decay, 14-day half-life); scores are normalised by how many
attempts could have surfaced the mistake (opportunities).
"""
from collections import defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.mistake import Mistake
from app.services.analytics.sources import opportunities, recent_submission_ids

HALF_LIFE_DAYS = 14
RECURRING_MIN_OCCURRENCES = 3
RECURRING_WINDOW = 8

# How a skill's attempts are named in user-facing recurring copy.
_ATTEMPT_NOUN = {
    "writing": "essays",
    "speaking": "attempts",
    "reading": "attempts",
    "listening": "attempts",
}


def recency_decay(age_days: float) -> float:
    """0.5 at one half-life, 0.25 at two, ... Recent mistakes matter more."""
    return 0.5 ** (max(0.0, age_days) / HALF_LIFE_DAYS)


def _humanize(subskill: str | None, category: str) -> str:
    label = (subskill or category).replace("_", " ").strip()
    return label.title() if label else category.title()


def compute_weaknesses(db: Session, user_id: int, limit: int = 6) -> list[dict]:
    """Top weaknesses by score = squash( sum(severity * recency_decay) / opportunities )."""
    mistakes = db.query(Mistake).filter(Mistake.user_id == user_id).all()
    if not mistakes:
        return []

    opp = opportunities(db, user_id)
    now = datetime.utcnow()

    groups: dict[tuple, list[Mistake]] = defaultdict(list)
    for m in mistakes:
        groups[(m.skill, m.category, m.subskill or m.category)].append(m)

    results: list[dict] = []
    for (skill, category, subskill), items in groups.items():
        denom = max(1, opp.get(skill, 1))
        weighted = sum(
            i.severity * recency_decay((now - (i.created_at or now)).total_seconds() / 86400)
            for i in items
        )
        intensity = weighted / denom
        # squash to [0, 1): intensity 1 -> 0.50, 2 -> 0.75, 3 -> 0.875
        score = round(1 - 0.5 ** intensity, 2)
        frequency = len({i.submission_id for i in items if i.submission_id is not None})

        results.append(
            {
                "skill": skill,
                "category": category,
                "subskill": subskill,
                "label": _humanize(subskill, category),
                "score": score,
                "frequency": frequency or len(items),
                "avg_severity": round(sum(i.severity for i in items) / len(items), 1),
                "recurring": frequency >= RECURRING_MIN_OCCURRENCES,
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]


def compute_recurring_mistakes(db: Session, user_id: int, limit: int = 6) -> list[dict]:
    """Patterns like "Articles in 6 of the last 8 essays"."""
    out: list[dict] = []

    for skill in ("writing", "speaking", "reading", "listening"):
        recent_ids = recent_submission_ids(db, user_id, skill, RECURRING_WINDOW)
        if not recent_ids:
            continue
        window = len(recent_ids)

        rows = (
            db.query(Mistake)
            .filter(
                Mistake.user_id == user_id,
                Mistake.skill == skill,
                Mistake.submission_id.in_(recent_ids),
            )
            .all()
        )

        per_subskill: dict[tuple, set] = defaultdict(set)
        for m in rows:
            per_subskill[(m.category, m.subskill or m.category)].add(m.submission_id)

        for (category, subskill), subs in per_subskill.items():
            occurrences = len(subs)
            if occurrences < RECURRING_MIN_OCCURRENCES:
                continue
            label = _humanize(subskill, category)
            noun = _ATTEMPT_NOUN.get(skill, "attempts")
            out.append(
                {
                    "skill": skill,
                    "category": category,
                    "subskill": subskill,
                    "label": label,
                    "occurrences": occurrences,
                    "window": window,
                    "message": f"{label} in {occurrences} of the last {window} {noun}.",
                }
            )

    out.sort(key=lambda r: (r["occurrences"] / r["window"]), reverse=True)
    return out[:limit]
