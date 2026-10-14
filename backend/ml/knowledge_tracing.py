"""No-forgetting Bayesian Knowledge Tracing, separately per question type."""
import math
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import product

from ml.data import ResponseRecord


@dataclass(frozen=True)
class BKTParameters:
    prior: float = 0.2
    learn: float = 0.1
    guess: float = 0.2
    slip: float = 0.1

    def __post_init__(self):
        if any(not math.isfinite(v) or not 0 < v < 1 for v in (self.prior, self.learn, self.guess, self.slip)):
            raise ValueError("BKT parameters must be inside (0, 1)")
        if self.guess + self.slip >= 1:
            raise ValueError("Guess plus slip must be less than one")


@dataclass
class BKTModel:
    parameters: dict[str, BKTParameters] = field(default_factory=dict)
    mastery: dict[tuple[str, str], float] = field(default_factory=dict)
    fitted_skills: set[str] = field(default_factory=set)

    def knowledge(self, learner_id: str, skill_key: str) -> float:
        params = self.parameters.get(skill_key, BKTParameters())
        return self.mastery.get((learner_id, skill_key), params.prior)

    def probability(self, learner_id: str, skill_key: str) -> float:
        params = self.parameters.get(skill_key, BKTParameters())
        mastery = self.knowledge(learner_id, skill_key)
        return mastery * (1 - params.slip) + (1 - mastery) * params.guess

    def observe(self, record: ResponseRecord) -> None:
        params = self.parameters.get(record.skill_key, BKTParameters())
        prior = self.knowledge(record.learner_id, record.skill_key)
        probability = self.probability(record.learner_id, record.skill_key)
        posterior = (prior * (1 - params.slip) / probability if record.correct
                     else prior * params.slip / (1 - probability))
        self.mastery[(record.learner_id, record.skill_key)] = posterior + (1 - posterior) * params.learn


def fit_bkt(records: list[ResponseRecord], *, min_responses=10) -> BKTModel:
    """Coarse train-only likelihood search; defaults for unsupported skills.

    The caller owns the train/test boundary. No holdout labels may be supplied.
    This pilot grid is not an EM implementation or a tuned production model.
    """
    if min_responses < 1:
        raise ValueError("min_responses must be positive")
    ordered = sorted(records, key=lambda r: (r.answered_at, r.response_id))
    groups = defaultdict(list)
    for row in ordered:
        groups[row.skill_key].append(row)
    model = BKTModel()
    candidates = [BKTParameters(*values) for values in product((0.2, 0.5, 0.8), (0.05, 0.15), (0.1, 0.25), (0.05, 0.15))]
    for skill, rows in groups.items():
        if len(rows) < min_responses or len({r.learner_id for r in rows}) < 2:
            model.parameters[skill] = BKTParameters()
            continue
        best_loss = math.inf
        for params in candidates:
            trial = BKTModel(parameters={skill: params})
            loss = 0.0
            for row in rows:
                p = trial.probability(row.learner_id, skill)
                loss -= math.log(max(1e-12, p if row.correct else 1 - p))
                trial.observe(row)
            if loss < best_loss:
                best_loss = loss
                model.parameters[skill] = params
        model.fitted_skills.add(skill)
    for row in ordered:
        model.observe(row)
    return model
