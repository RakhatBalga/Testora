"""Practice Recommendation Engine.

Deterministic — no AI. Pulls from five ranked signals:
  1. Main blocker (lowest criterion in Writing/Speaking)
  2. Largest band-gap skill (lowest overall band)
  3. Most recurring mistake (highest frequency across recent attempts)
  4. Weakest question type (lowest accuracy in Reading/Listening breakdown)
  5. Longest inactive skill

Every recommendation carries a `reason` — the exact signal that triggered it.
"""
from collections import defaultdict
from datetime import datetime
from statistics import mean

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.attempt import Attempt
from app.domain.models.test import Test
from app.domain.models.writing import WritingSubmission
from app.domain.models.speaking import SpeakingSubmission
from app.application.analytics.band_gap import compute_band_gap, generate_blockers, DEFAULT_TARGET
from app.application.analytics.links import practice_href
from app.application.analytics.weakness import compute_recurring_mistakes

_SKILL_MINUTES = {"writing": 40, "speaking": 15, "reading": 20, "listening": 30}

_IMPACT = {
    "blocker": "High",
    "band_gap": "High",
    "recurring_mistake": "Medium",
    "question_type": "Medium",
    "inactivity": "Low",
    "cold_start": "High",
}


def _rec(
    id_: str,
    title: str,
    reason: str,
    source: str,
    skill: str | None,
    priority: int,
    href: str,
) -> dict:
    return {
        "id": id_,
        "title": title,
        "reason": reason,
        "source": source,
        "skill": skill,
        "priority": priority,
        "estimated_impact": _IMPACT.get(source, "Medium"),
        "href": href,
        "estimated_minutes": _SKILL_MINUTES.get(skill or "", 20),
    }


def _last_activity(db: Session, user_id: int) -> dict[str, datetime | None]:
    out: dict[str, datetime | None] = {}
    out["writing"] = (
        db.query(func.max(WritingSubmission.created_at))
        .filter(WritingSubmission.user_id == user_id)
        .scalar()
    )
    out["speaking"] = (
        db.query(func.max(SpeakingSubmission.created_at))
        .filter(SpeakingSubmission.user_id == user_id)
        .scalar()
    )
    for skill in ("reading", "listening"):
        out[skill] = (
            db.query(func.max(Attempt.created_at))
            .join(Test, Attempt.test_id == Test.id)
            .filter(Attempt.user_id == user_id, Test.test_type == skill)
            .scalar()
        )
    return out


def _weakest_question_type(db: Session, user_id: int) -> dict | None:
    """Lowest-accuracy question type across recent Reading/Listening attempts."""
    attempts = (
        db.query(Attempt)
        .join(Test, Attempt.test_id == Test.id)
        .filter(
            Attempt.user_id == user_id,
            Attempt.breakdown.isnot(None),
            Test.test_type.in_(["reading", "listening"]),
        )
        .order_by(Attempt.created_at.desc())
        .limit(10)
        .all()
    )
    if not attempts:
        return None

    per_type: dict[tuple, list[float]] = defaultdict(list)
    label_map: dict[tuple, str] = {}
    skill_map: dict[tuple, str] = {}

    for attempt in attempts:
        test_type = attempt.test.test_type if attempt.test else None
        if not test_type or not attempt.breakdown:
            continue
        for item in attempt.breakdown:
            if not isinstance(item, dict):
                continue
            qt = item.get("question_type")
            label = item.get("label") or qt
            if qt and item.get("total", 0) > 0:
                key = (test_type, qt)
                per_type[key].append(float(item.get("accuracy", 0)))
                label_map[key] = str(label)
                skill_map[key] = test_type

    if not per_type:
        return None

    avg_accuracy = {k: mean(v) for k, v in per_type.items() if v}
    weakest_key = min(avg_accuracy, key=lambda k: avg_accuracy[k])

    return {
        "skill": skill_map[weakest_key],
        "question_type": weakest_key[1],
        "label": label_map[weakest_key],
        "accuracy": round(avg_accuracy[weakest_key], 1),
    }


def compute_recommendations(
    db: Session,
    user_id: int,
    target: float = DEFAULT_TARGET,
    limit: int = 5,
) -> list[dict]:
    band_gap = compute_band_gap(db, user_id, target=target)
    recs: list[dict] = []
    seen_skills: set[str] = set()
    priority = 1

    # Cold start — no graded data at all.
    if not band_gap.get("has_data"):
        return [
            _rec(
                "cold-writing",
                "Complete your first Writing task",
                "No band estimate yet. Writing gives the richest signal — band and four criteria at once.",
                "cold_start",
                "writing",
                1,
                practice_href("writing"),
            ),
            _rec(
                "cold-reading",
                "Try a Reading passage",
                "Reading is scored instantly — a fast way to get your first band estimate.",
                "cold_start",
                "reading",
                2,
                practice_href("reading"),
            ),
        ][:limit]

    # ── 1. Main blocker ───────────────────────────────────────────────────────
    blockers = generate_blockers(db, user_id, target=target, limit=1)
    if blockers:
        b = blockers[0]
        skill = b["skill"].lower()
        recs.append(
            _rec(
                f"blocker-{skill}-{b['criterion'].replace(' ', '-').lower()}",
                f"Practice {b['skill']} — focus on {b['criterion']}",
                b.get("explanation")
                or f"{b['criterion']} is capping your {b['skill']} band at {b['band_cap']}.",
                "blocker",
                skill,
                priority,
                b.get("fix_href") or practice_href(skill),
            )
        )
        seen_skills.add(skill)
        priority += 1

    # ── 2. Largest band-gap skill ─────────────────────────────────────────────
    lowest_skill = band_gap.get("lowest_skill")
    if lowest_skill and lowest_skill not in seen_skills:
        band_val = band_gap["per_skill"].get(lowest_skill)
        gap = round(target - band_val, 1) if band_val is not None else None
        reason = (
            f"{lowest_skill.title()} is your lowest skill at Band {band_val} — {gap:+.1f} from your target of {target}."
            if band_val is not None and gap is not None
            else f"{lowest_skill.title()} is your lowest-scoring skill."
        )
        recs.append(
            _rec(
                f"band-gap-{lowest_skill}",
                f"Complete a {lowest_skill.title()} task",
                reason,
                "band_gap",
                lowest_skill,
                priority,
                practice_href(lowest_skill),
            )
        )
        seen_skills.add(lowest_skill)
        priority += 1

    # ── 3. Most recurring mistake ─────────────────────────────────────────────
    recurring = compute_recurring_mistakes(db, user_id, limit=1)
    if recurring and len(recs) < limit:
        r = recurring[0]
        skill = r["skill"]
        recs.append(
            _rec(
                f"recurring-{skill}-{r['subskill']}",
                f"Review {r['label']} in {skill.title()}",
                r["message"],
                "recurring_mistake",
                skill,
                priority,
                "/analytics",
            )
        )
        priority += 1

    # ── 4. Weakest question type ──────────────────────────────────────────────
    if len(recs) < limit:
        weakest_qt = _weakest_question_type(db, user_id)
        if weakest_qt:
            skill = weakest_qt["skill"]
            recs.append(
                _rec(
                    f"qt-{skill}-{weakest_qt['question_type']}",
                    f"Drill {weakest_qt['label']}",
                    f"Accuracy is {weakest_qt['accuracy']:.0f}%, currently your weakest {skill.title()} question type.",
                    "question_type",
                    skill,
                    priority,
                    practice_href(skill),
                )
            )
            seen_skills.add(skill)
            priority += 1

    # ── 5. Longest inactive skill ─────────────────────────────────────────────
    if len(recs) < limit:
        last = _last_activity(db, user_id)
        today = datetime.utcnow().date()
        stale: list[tuple[int, str]] = []
        for skill in ("writing", "speaking", "reading", "listening"):
            if skill in seen_skills:
                continue
            ts = last.get(skill)
            age = (today - ts.date()).days if ts else 999
            stale.append((age, skill))
        stale.sort(reverse=True)
        for age, skill in stale:
            if len(recs) >= limit:
                break
            if age >= 3:
                ts_str = f"{age} day{'s' if age != 1 else ''} ago" if age < 999 else "never"
                recs.append(
                    _rec(
                        f"inactive-{skill}",
                        f"Practice {skill.title()}",
                        f"Last practised {ts_str} — all four skills need regular practice for a balanced band.",
                        "inactivity",
                        skill,
                        priority,
                        practice_href(skill),
                    )
                )
                priority += 1

    return recs[:limit]
