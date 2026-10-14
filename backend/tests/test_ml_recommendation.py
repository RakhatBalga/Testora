from ml.irt import RaschModel
from ml.knowledge_tracing import BKTModel
from ml.recommendation import Candidate, recommend


def item(identifier, question_type="choice", **kwargs):
    return Candidate(item_id=identifier, content_version="v1", skill="reading",
                     question_type=question_type, **kwargs)


def test_ranking_filters_drafts_seen_and_duplicates():
    seen = item("seen", published=True)
    new = item("new", published=True)
    rows = recommend("u", [item("draft"), seen, new, new], RaschModel(), BKTModel(), seen={seen.item_key})
    assert [r["item_id"] for r in rows] == ["new"]
    assert rows[0]["provisional"] is True
    assert "not available" in rows[0]["reason"]


def test_ranking_prefers_weaker_skill_and_explains_uncertainty():
    weak, strong = item("weak", "matching", published=True), item("strong", published=True)
    bkt = BKTModel(mastery={("u", weak.skill_key): 0.1, ("u", strong.skill_key): 0.9})
    result = recommend("u", [strong, weak], RaschModel(), bkt, seen=set())
    assert result[0]["item_id"] == "weak"
    assert all(0 <= r["predicted_correct"] <= 1 for r in result)
    assert "correct_answer" not in result[0]
