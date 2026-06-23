"""Attempt Comparison engine — side-by-side diff of any two same-skill attempts.

Writing/Speaking: criteria diff + mistake bucket diff + blocker change.
Reading/Listening: band diff + question-type accuracy diff.

Returns a structured comparison dict; never raises on missing data.
"""
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attempt import Attempt
from app.models.mistake import Mistake
from app.models.speaking import SpeakingSubmission
from app.models.test import Test
from app.models.writing import WritingSubmission

_CATEGORY_LABELS = {
    "grammar": "Grammar",
    "vocabulary": "Vocabulary",
    "coherence": "Coherence & Cohesion",
    "task_response": "Task Response",
    "fluency": "Fluency & Coherence",
    "pronunciation": "Pronunciation",
}


def _label(cat: str) -> str:
    return _CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())


def _parse(item_id: str) -> tuple[str, int] | None:
    parts = item_id.split("-", 1)
    if len(parts) != 2:
        return None
    try:
        return parts[0], int(parts[1])
    except ValueError:
        return None


def _mistake_counts(db: Session, user_id: int, skill: str, ref_id: int) -> dict[str, int]:
    rows = (
        db.query(Mistake.category, func.count(Mistake.id))
        .filter(Mistake.user_id == user_id, Mistake.skill == skill, Mistake.submission_id == ref_id)
        .group_by(Mistake.category)
        .all()
    )
    return {cat: cnt for cat, cnt in rows}


def _diff_criteria(crit_a: dict, crit_b: dict) -> list[dict]:
    out: list[dict] = []
    for name in set(crit_a) | set(crit_b):
        va = crit_a.get(name)
        vb = crit_b.get(name)
        if va is None or vb is None:
            continue
        delta = round(vb - va, 1)
        out.append(
            {
                "name": name,
                "a": round(float(va), 1),
                "b": round(float(vb), 1),
                "delta": delta,
                "direction": "up" if delta > 0 else "down" if delta < 0 else "none",
            }
        )
    out.sort(key=lambda x: (-abs(x["delta"]), x["name"]))
    return out


def _diff_mistakes(mc_a: dict, mc_b: dict) -> dict[str, list[dict]]:
    buckets: dict[str, list[dict]] = {"resolved": [], "improved": [], "worsened": [], "new": []}
    for cat in set(mc_a) | set(mc_b):
        before = mc_a.get(cat, 0)
        after = mc_b.get(cat, 0)
        if before == after:
            continue
        item = {"category": cat, "label": _label(cat), "a": before, "b": after}
        if before == 0:
            buckets["new"].append(item)
        elif after == 0:
            buckets["resolved"].append(item)
        elif after < before:
            buckets["improved"].append(item)
        else:
            buckets["worsened"].append(item)
    return buckets


def _lowest_criterion(crit: dict) -> str | None:
    scored = {k: v for k, v in crit.items() if v and v > 0}
    return min(scored, key=lambda k: scored[k]) if scored else None


def _compare_ws(db: Session, user_id: int, skill: str, id_a: str, row_a, id_b: str, row_b) -> dict:
    crit_a = (row_a.feedback or {}).get("criteria") or {}
    crit_b = (row_b.feedback or {}).get("criteria") or {}

    band_a = round(float(row_a.band), 1) if row_a.band else None
    band_b = round(float(row_b.band), 1) if row_b.band else None
    band_delta = round(band_b - band_a, 1) if band_a is not None and band_b is not None else None

    mc_a = _mistake_counts(db, user_id, skill, row_a.id)
    mc_b = _mistake_counts(db, user_id, skill, row_b.id)

    blocker_a = _lowest_criterion(crit_a)
    blocker_b = _lowest_criterion(crit_b)

    ts_a = row_a.created_at.isoformat() if row_a.created_at else None
    ts_b = row_b.created_at.isoformat() if row_b.created_at else None

    return {
        "skill": skill,
        "a": {
            "id": id_a,
            "ref_id": row_a.id,
            "band": band_a,
            "created_at": ts_a,
            "criteria": {k: round(float(v), 1) for k, v in crit_a.items() if v},
            "summary": (row_a.feedback or {}).get("summary"),
        },
        "b": {
            "id": id_b,
            "ref_id": row_b.id,
            "band": band_b,
            "created_at": ts_b,
            "criteria": {k: round(float(v), 1) for k, v in crit_b.items() if v},
            "summary": (row_b.feedback or {}).get("summary"),
        },
        "band_delta": band_delta,
        "criteria_diff": _diff_criteria(crit_a, crit_b),
        "mistakes": _diff_mistakes(mc_a, mc_b),
        "blocker": {
            "a": blocker_a,
            "b": blocker_b,
            "changed": bool(blocker_a and blocker_b and blocker_a != blocker_b),
        },
    }


def _compare_rl(skill: str, id_a: str, row_a, id_b: str, row_b) -> dict:
    band_a = round(float(row_a.band), 1) if row_a.band else None
    band_b = round(float(row_b.band), 1) if row_b.band else None
    band_delta = round(band_b - band_a, 1) if band_a is not None and band_b is not None else None

    bd_a = {item["question_type"]: item for item in (row_a.breakdown or []) if isinstance(item, dict) and "question_type" in item}
    bd_b = {item["question_type"]: item for item in (row_b.breakdown or []) if isinstance(item, dict) and "question_type" in item}

    qt_diff: list[dict] = []
    for qt in set(bd_a) | set(bd_b):
        ia = bd_a.get(qt, {})
        ib = bd_b.get(qt, {})
        acc_a = ia.get("accuracy")
        acc_b = ib.get("accuracy")
        if acc_a is None or acc_b is None:
            continue
        delta = round(acc_b - acc_a, 1)
        qt_diff.append(
            {
                "question_type": qt,
                "label": ib.get("label") or ia.get("label") or qt,
                "a_accuracy": round(float(acc_a), 1),
                "b_accuracy": round(float(acc_b), 1),
                "a_correct": ia.get("correct"),
                "b_correct": ib.get("correct"),
                "a_total": ia.get("total"),
                "b_total": ib.get("total"),
                "delta": delta,
                "direction": "up" if delta > 0 else "down" if delta < 0 else "none",
            }
        )
    qt_diff.sort(key=lambda x: (-abs(x["delta"]), x["label"]))

    ts_a = row_a.created_at.isoformat() if row_a.created_at else None
    ts_b = row_b.created_at.isoformat() if row_b.created_at else None

    score_a = f"{row_a.score}/{row_a.total}" if row_a.total else None
    score_b = f"{row_b.score}/{row_b.total}" if row_b.total else None

    return {
        "skill": skill,
        "a": {"id": id_a, "ref_id": row_a.id, "band": band_a, "score": score_a, "created_at": ts_a},
        "b": {"id": id_b, "ref_id": row_b.id, "band": band_b, "score": score_b, "created_at": ts_b},
        "band_delta": band_delta,
        "question_type_diff": qt_diff,
    }


def compare_history(db: Session, user_id: int, id_a: str, id_b: str) -> dict:
    p_a = _parse(id_a)
    p_b = _parse(id_b)

    if not p_a or not p_b:
        return {"error": "invalid_id", "message": "IDs must be in format 'skill-number' (e.g. writing-1)"}

    skill_a, ref_a = p_a
    skill_b, ref_b = p_b

    if skill_a != skill_b:
        return {"error": "skill_mismatch", "message": "Both attempts must be the same skill to compare"}

    skill = skill_a

    if skill == "writing":
        row_a = db.query(WritingSubmission).filter(WritingSubmission.id == ref_a, WritingSubmission.user_id == user_id).first()
        row_b = db.query(WritingSubmission).filter(WritingSubmission.id == ref_b, WritingSubmission.user_id == user_id).first()
        if not row_a or not row_b:
            return {"error": "not_found", "message": "One or both writing attempts not found"}
        return _compare_ws(db, user_id, skill, id_a, row_a, id_b, row_b)

    if skill == "speaking":
        row_a = db.query(SpeakingSubmission).filter(SpeakingSubmission.id == ref_a, SpeakingSubmission.user_id == user_id).first()
        row_b = db.query(SpeakingSubmission).filter(SpeakingSubmission.id == ref_b, SpeakingSubmission.user_id == user_id).first()
        if not row_a or not row_b:
            return {"error": "not_found", "message": "One or both speaking attempts not found"}
        return _compare_ws(db, user_id, skill, id_a, row_a, id_b, row_b)

    if skill in ("reading", "listening"):
        row_a = (
            db.query(Attempt)
            .join(Test, Attempt.test_id == Test.id)
            .filter(Attempt.id == ref_a, Attempt.user_id == user_id, Test.test_type == skill)
            .first()
        )
        row_b = (
            db.query(Attempt)
            .join(Test, Attempt.test_id == Test.id)
            .filter(Attempt.id == ref_b, Attempt.user_id == user_id, Test.test_type == skill)
            .first()
        )
        if not row_a or not row_b:
            return {"error": "not_found", "message": f"One or both {skill} attempts not found"}
        return _compare_rl(skill, id_a, row_a, id_b, row_b)

    return {"error": "unsupported_skill", "message": f"Skill '{skill}' cannot be compared"}
