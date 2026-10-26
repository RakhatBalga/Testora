"""Explainable offline candidate ranking; does not expose answers or change the API."""

import json
from typing import Literal
from pydantic import Field

from ml.data import Record
from ml.irt import RaschModel
from ml.knowledge_tracing import BKTModel


class Candidate(Record):
    item_id: str = Field(min_length=1)
    content_version: str = Field(min_length=1)
    skill: Literal["reading", "listening"]
    question_type: str = Field(min_length=1)
    # Caller must explicitly confirm that content is available for practice.
    published: bool = False

    @property
    def item_key(self):
        return json.dumps([self.skill, self.content_version, self.item_id])

    @property
    def skill_key(self):
        return json.dumps([self.skill, self.question_type])


def recommend(
    learner_id: str,
    candidates: list[Candidate],
    irt: RaschModel,
    bkt: BKTModel,
    *,
    seen: set[str],
    limit=5,
    target_probability=0.7,
    min_item_support=10,
) -> list[dict]:
    """Prefer weaker skills and achievable challenge; weights are pilot heuristics.

    Only observed-history models may be supplied. Uncalibrated difficulty uses
    a neutral 0.5 prior and is explicitly marked provisional.
    """
    if not 0 < target_probability < 1 or limit < 1 or min_item_support < 1:
        raise ValueError("Invalid ranking settings")
    ranked, included = [], set()
    for item in candidates:
        if not item.published or item.item_key in seen or item.item_key in included:
            continue
        included.add(item.item_key)
        support = irt.item_support.get(item.item_key, 0)
        calibrated = support >= min_item_support
        irt_p = irt.probability(learner_id, item.skill, item.item_key) if calibrated else 0.5
        bkt_p = bkt.probability(learner_id, item.skill_key)
        probability = (irt_p + bkt_p) / 2
        known = (learner_id, item.skill_key) in bkt.mastery
        weakness = 1 - bkt.knowledge(learner_id, item.skill_key)
        score = 0.6 * weakness + 0.4 * (1 - abs(probability - target_probability))
        ranked.append(
            {
                "item_id": item.item_id,
                "content_version": item.content_version,
                "skill": item.skill,
                "question_type": item.question_type,
                "predicted_correct": probability,
                "priority": score,
                "difficulty_support": support,
                "provisional": not calibrated or item.skill_key not in bkt.fitted_skills,
                "reason": (
                    "Practise a less-mastered question type at an achievable difficulty."
                    if known
                    else "Explore this question type; learner history is not available yet."
                ),
            }
        )
    return sorted(ranked, key=lambda r: (-r["priority"], r["skill"], r["item_id"], r["content_version"]))[:limit]
