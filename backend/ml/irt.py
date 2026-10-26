"""Regularized Rasch 1PL pilot: P(correct) = sigmoid(ability - difficulty).

L2 priors anchor the otherwise translation-invariant scale and keep extreme
response patterns finite. This is penalized joint fitting, not conditional MLE.
"""

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field

from ml.data import ResponseRecord


def sigmoid(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp = math.exp(value)
    return exp / (1 + exp)


def learner_key(learner_id: str, skill: str) -> str:
    return json.dumps([learner_id, skill])


@dataclass
class RaschModel:
    abilities: dict[str, float] = field(default_factory=dict)
    difficulties: dict[str, float] = field(default_factory=dict)
    item_support: dict[str, int] = field(default_factory=dict)
    regularization: float = 1.0
    iterations: int = 0

    def probability(self, learner_id: str, skill: str, item_key: str) -> float:
        theta = self.abilities.get(learner_key(learner_id, skill), 0.0)
        return sigmoid(theta - self.difficulties.get(item_key, 0.0))

    def observe(self, record: ResponseRecord, learning_rate: float = 0.2) -> None:
        """Update ability after prediction; keep calibrated item difficulty frozen."""
        if not math.isfinite(learning_rate) or not 0 < learning_rate <= 1:
            raise ValueError("learning_rate must be in (0, 1]")
        key = learner_key(record.learner_id, record.skill)
        error = float(record.correct) - self.probability(record.learner_id, record.skill, record.item_key)
        self.abilities[key] = max(-6, min(6, self.abilities.get(key, 0.0) + learning_rate * error))


def fit_rasch(records: list[ResponseRecord], *, regularization=1.0, iterations=100) -> RaschModel:
    if not records or not math.isfinite(regularization) or regularization <= 0 or iterations < 1:
        raise ValueError("Nonempty responses, positive regularization and iterations required")
    users, items = defaultdict(list), defaultdict(list)
    for row in records:
        key = learner_key(row.learner_id, row.skill)
        users[key].append(row)
        items[row.item_key].append(row)
    model = RaschModel(
        abilities=dict.fromkeys(users, 0.0),
        difficulties=dict.fromkeys(items, 0.0),
        item_support={key: len(rows) for key, rows in items.items()},
        regularization=regularization,
    )
    for iteration in range(iterations):
        change = 0.0
        for key, rows in users.items():
            theta = model.abilities[key]
            probabilities = [sigmoid(theta - model.difficulties[r.item_key]) for r in rows]
            gradient = sum(float(r.correct) - p for r, p in zip(rows, probabilities)) - regularization * theta
            curvature = sum(p * (1 - p) for p in probabilities) + regularization
            step = max(-1, min(1, gradient / curvature))
            model.abilities[key] = theta + step
            change = max(change, abs(step))
        for key, rows in items.items():
            difficulty = model.difficulties[key]
            probabilities = [sigmoid(model.abilities[learner_key(r.learner_id, r.skill)] - difficulty) for r in rows]
            gradient = sum(p - float(r.correct) for r, p in zip(rows, probabilities)) - regularization * difficulty
            curvature = sum(p * (1 - p) for p in probabilities) + regularization
            step = max(-1, min(1, gradient / curvature))
            model.difficulties[key] = difficulty + step
            change = max(change, abs(step))
        model.iterations = iteration + 1
        if change < 1e-6:
            break
    return model
