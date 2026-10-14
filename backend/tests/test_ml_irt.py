import math
from ml.data import ResponseRecord
from ml.irt import fit_rasch, learner_key


def row(user, item, correct, skill="reading"):
    return ResponseRecord(response_id=f"{user}-{item}-{skill}", learner_id=user, item_id=item,
                          content_version="v1", skill=skill, question_type="choice", correct=correct,
                          answered_at="2026-10-14T10:00:00Z")


def test_rasch_orders_difficulty_and_keeps_extreme_items_finite():
    rows = [row(f"u{i}", item, item == "easy") for i in range(5) for item in ("easy", "hard")]
    model = fit_rasch(rows)
    easy, hard = rows[0].item_key, rows[1].item_key
    assert model.difficulties[easy] < model.difficulties[hard]
    assert model.probability("new", "reading", easy) > model.probability("new", "reading", hard)
    assert all(math.isfinite(v) for v in model.difficulties.values())
    assert model.probability("new", "reading", "unknown") == 0.5


def test_reading_and_listening_abilities_are_separate_and_updates_do_not_refit_items():
    rows = [row("u", "q", True), row("u", "q", False, "listening")]
    model = fit_rasch(rows)
    assert model.abilities[learner_key("u", "reading")] > model.abilities[learner_key("u", "listening")]
    before = model.difficulties.copy()
    old = model.probability("u", "reading", rows[0].item_key)
    model.observe(rows[0])
    assert model.probability("u", "reading", rows[0].item_key) > old
    assert model.difficulties == before
