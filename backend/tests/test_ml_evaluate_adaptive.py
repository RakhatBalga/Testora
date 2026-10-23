from datetime import datetime, timedelta, timezone
import pytest
from ml.data import ResponseRecord
from ml.evaluate_adaptive import evaluate


def synthetic_rows():
    return [ResponseRecord(response_id=f"fake-{i:02}", learner_id=f"fake-{i % 3}", item_id=f"q{i % 7}",
                           content_version="v1", skill="reading", question_type="choice", correct=i % 2 == 0,
                           answered_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i))
            for i in range(20)]


def test_future_labels_cannot_change_current_or_earlier_predictions():
    rows = synthetic_rows()
    before = evaluate(rows, 0.5)
    rows[-1] = rows[-1].model_copy(update={"correct": not rows[-1].correct})
    after = evaluate(rows, 0.5)
    assert before["predictions"][:-1] == after["predictions"][:-1]
    for model in ("error_rate_baseline", "irt", "bkt", "blend"):
        assert before["predictions"][-1][model] == after["predictions"][-1][model]


def test_tied_responses_do_not_leak_and_retries_are_excluded():
    rows = synthetic_rows()
    rows[-1] = rows[-1].model_copy(update={"answered_at": rows[-2].answered_at})
    before = evaluate(rows, 0.5)
    rows[-2] = rows[-2].model_copy(update={"correct": not rows[-2].correct})
    after = evaluate(rows, 0.5)
    for model in ("error_rate_baseline", "irt", "bkt", "blend"):
        assert before["predictions"][-1][model] == after["predictions"][-1][model]
    retry = rows[0].model_copy(update={"response_id": "retry", "answered_at": rows[-1].answered_at})
    assert evaluate(rows + [retry], 0.5)["excluded_repeated_responses"] == 1


def test_evaluator_rejects_unsplittable_data():
    rows = synthetic_rows()
    with pytest.raises(ValueError, match="distinct timestamps"):
        evaluate([r.model_copy(update={"answered_at": rows[0].answered_at}) for r in rows])


def test_conflicting_item_types_rejected_before_training():
    rows = synthetic_rows()
    rows[7] = rows[7].model_copy(update={'question_type': 'gap'})
    with pytest.raises(ValueError, match='Conflicting'):
        evaluate(rows)


def test_per_skill_report_accounts_for_all_heldout_rows():
    rows = synthetic_rows()
    rows[-1] = rows[-1].model_copy(update={'skill': 'listening'})
    report = evaluate(rows)
    assert sum(s['count'] for s in report['by_skill'].values()) == report['test_count']
    assert report['by_skill']['listening']['metrics']['blend']['auc'] is None
    assert evaluate(synthetic_rows())['by_skill']['listening'] == {'count': 0, 'correct': 0, 'incorrect': 0, 'auc_status': 'empty', 'metrics': {}}


def test_cold_start_membership_uses_only_training_history():
    rows = synthetic_rows()
    rows[-1] = rows[-1].model_copy(update={'learner_id': 'new', 'item_id': 'new-question'})
    report = evaluate(rows)
    assert report['predictions'][-1]['new_learner'] is True
    assert report['predictions'][-1]['new_item'] is True
    for group in report['cold_start'].values():
        assert sum(s['count'] for s in group.values()) == report['test_count']


def test_auc_status_explains_single_class_holdout():
    rows = synthetic_rows()
    rows = [r.model_copy(update={'correct': True}) for r in rows]
    held = evaluate(rows)['holdout']
    assert held['auc_status'] == 'single_class'
    assert held['correct'] == held['count']
    assert held['incorrect'] == 0
