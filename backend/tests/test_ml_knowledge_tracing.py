import pytest
from ml.data import ResponseRecord
from ml.knowledge_tracing import BKTModel, BKTParameters, fit_bkt


def response(user="u", correct=True, question_type="choice", number=0):
    return ResponseRecord(response_id=f"{user}-{number}", learner_id=user, item_id=str(number),
                          content_version="v1", skill="reading", question_type=question_type,
                          correct=correct, answered_at="2026-10-14T10:00:00Z")


def test_bkt_bayes_update_and_skill_isolation():
    model = BKTModel()
    row = response()
    assert model.probability("u", row.skill_key) == pytest.approx(0.34)
    model.observe(row)
    posterior = 0.2 * 0.9 / 0.34
    assert model.knowledge("u", row.skill_key) == pytest.approx(posterior + (1 - posterior) * 0.1)
    assert model.knowledge("other", row.skill_key) == 0.2
    assert model.knowledge("u", response(question_type="matching").skill_key) == 0.2


def test_fit_distinguishes_defaults_from_calibrated_skills():
    assert not fit_bkt([response()]).fitted_skills
    rows = [response(user, number=i, correct=i % 3 != 0) for user in ("a", "b") for i in range(8)]
    first = fit_bkt(rows)
    assert rows[0].skill_key in first.fitted_skills
    assert first.parameters == fit_bkt(rows).parameters
    assert 0 < first.probability("a", rows[0].skill_key) < 1


def test_bkt_rejects_degenerate_parameters():
    with pytest.raises(ValueError):
        BKTParameters(guess=0.8, slip=0.3)
    with pytest.raises(ValueError):
        BKTParameters(prior=float("nan"))
