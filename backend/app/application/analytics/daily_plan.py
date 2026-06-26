"""Daily Plan engine — deterministic "what to do today".

Rules over real signals only (no AI, no mock): the named band blocker, the
weakest skill from the band gap, the top recurring mistake, and how long since
the user last practised each skill. Every task carries a `source` naming the
signal that produced it, so the plan is fully explainable and reproducible.
"""
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.time import local_today, to_local_date
from app.domain.models.writing import WritingSubmission
from app.domain.models.speaking import SpeakingSubmission
from app.domain.models.attempt import Attempt
from app.domain.models.test import Test
from app.application.analytics.band_gap import compute_band_gap, generate_blockers, DEFAULT_TARGET
from app.application.analytics.links import practice_href
from app.application.analytics.weakness import compute_weaknesses

# Per-skill effort estimate (minutes) for a single practice task.
_SKILL_MINUTES = {"writing": 40, "speaking": 15, "reading": 20, "listening": 30}
_STALE_DAYS = 3  # a skill untouched this long earns a re-engagement nudge


def _last_activity(db: Session, user_id: int) -> dict[str, datetime | None]:
    """Most recent graded submission datetime per skill (None if never)."""
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


def _task(id_: str, title: str, detail: str, skill: str | None, href: str, source: str, minutes: int) -> dict:
    return {
        "id": id_,
        "title": title,
        "detail": detail,
        "skill": skill,
        "href": href,
        "source": source,
        "estimated_minutes": minutes,
    }


def compute_daily_plan(db: Session, user_id: int, target: float = DEFAULT_TARGET, limit: int = 3) -> dict:
    band_gap = compute_band_gap(db, user_id, target=target)
    today = local_today()

    # Cold start — no graded data yet. Give a concrete first move, not a mock.
    if not band_gap.get("has_data"):
        plan = [
            _task(
                "cold-writing",
                "Complete your first Writing task",
                "I'll estimate your band and find your biggest blocker from it.",
                "writing",
                practice_href("writing"),
                "cold_start",
                _SKILL_MINUTES["writing"],
            ),
            _task(
                "cold-reading",
                "Try a Reading passage",
                "Reading is scored instantly — a fast way to start your band estimate.",
                "reading",
                practice_href("reading"),
                "cold_start",
                _SKILL_MINUTES["reading"],
            ),
        ]
        return {"generated_for": today.isoformat(), "has_data": False, "plan": plan[:limit]}

    blockers = generate_blockers(db, user_id, target=target, limit=1)
    weaknesses = compute_weaknesses(db, user_id, limit=6)
    last = _last_activity(db, user_id)

    plan: list[dict] = []
    used_skills: set[str] = set()

    # 1) Attack the named blocker (highest leverage on band).
    if blockers:
        b = blockers[0]
        skill = b["skill"].lower()
        plan.append(
            _task(
                f"blocker-{skill}",
                f"Practice {b['skill']} — focus on {b['criterion']}",
                b.get("explanation") or f"{b['criterion']} is currently capping your {b['skill']} band.",
                skill,
                b.get("fix_href") or practice_href(skill),
                "blocker",
                _SKILL_MINUTES.get(skill, 20),
            )
        )
        used_skills.add(skill)

    # 2) Lift the weakest skill from the band gap (if not already covered).
    lowest = band_gap.get("lowest_skill")
    if lowest and lowest not in used_skills:
        title_skill = lowest.title()
        plan.append(
            _task(
                f"weakest-{lowest}",
                f"Complete a {title_skill} task",
                f"{title_skill} is your lowest skill (Band {band_gap['per_skill'].get(lowest)}) — the biggest lever to your overall band.",
                lowest,
                practice_href(lowest),
                "band_gap",
                _SKILL_MINUTES.get(lowest, 20),
            )
        )
        used_skills.add(lowest)

    # 3) Review the top recurring mistake (consolidation, low effort).
    recurring = next((w for w in weaknesses if w.get("recurring")), weaknesses[0] if weaknesses else None)
    if recurring and len(plan) < limit:
        plan.append(
            _task(
                f"review-{recurring['skill']}-{recurring['subskill']}",
                f"Review your {recurring['label']} mistakes",
                f"Recurring in {recurring['skill'].title()} — appeared across {recurring['frequency']} recent attempts.",
                recurring["skill"],
                "/analytics",
                "weakness",
                10,
            )
        )

    # 4) Fill remaining slots by re-engaging a stale / never-practised skill.
    if len(plan) < limit:
        stale_candidates: list[tuple[float, str]] = []
        for skill in ("writing", "speaking", "reading", "listening"):
            if skill in used_skills:
                continue
            ts = last.get(skill)
            age = (today - to_local_date(ts)).days if ts else 999
            if age >= _STALE_DAYS:
                stale_candidates.append((age, skill))
        stale_candidates.sort(reverse=True)  # most neglected first
        for _, skill in stale_candidates:
            if len(plan) >= limit:
                break
            ts = last.get(skill)
            detail = (
                f"You haven't practised {skill.title()} in a while — keep all four skills warm."
                if ts
                else f"You haven't tried {skill.title()} yet — get a band estimate for it."
            )
            plan.append(
                _task(
                    f"stale-{skill}",
                    f"Practice {skill.title()}",
                    detail,
                    skill,
                    practice_href(skill),
                    "last_activity",
                    _SKILL_MINUTES.get(skill, 20),
                )
            )
            used_skills.add(skill)

    return {"generated_for": today.isoformat(), "has_data": True, "plan": plan[:limit]}
