from datetime import datetime, timedelta, timezone
import json

import pytest

from ml.data import ResponseRecord
from ml.datasets.readiness import assess, inspect_file, main
from ml.datasets.split import temporal_split
from ml.evaluate_adaptive import evaluate


def rows():
    return [ResponseRecord(response_id=f"r{i:03}", learner_id=f"u{i % 4}",
        item_id=f"q{i}", content_version="v1", skill="reading" if i % 2 else "listening",
        question_type="short_answer", correct=bool((i // 2) % 2),
        answered_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=i))
        for i in range(24)]


def test_report_matches_actual_experiment_split():
    records = rows()
    report = assess(records)
    experiment = evaluate(records)
    assert report["can_run_auc_comparison"]
    assert report["status"] == "pilot_with_warnings"
    assert report["split"]["cutoff"] == experiment["cutoff"]
    assert report["split"]["train"]["responses"] == experiment["train_count"]
    assert report["split"]["holdout"]["responses"] == experiment["test_count"]
    assert report["raw"]["learners"] == 4
    assert report["by_skill"]["reading"]["responses"] == 12
    assert all(row["holdout_auc_available"] for row in report["by_skill"].values())
    assert any("neutral IRT" in warning for warning in report["warnings"])


@pytest.mark.parametrize("records", [[], rows()[:3], [r.model_copy(update={"answered_at": rows()[0].answered_at}) for r in rows()]])
def test_empty_small_and_simultaneous_datasets_are_blocked(records):
    report = assess(records)
    assert report["status"] == "blocked"
    assert not report["can_run_auc_comparison"]


def test_duplicates_are_blocked_and_repeated_attempts_are_excluded():
    records = rows()
    assert assess(records + [records[0]])["duplicate_response_ids"] == 1
    assert assess(records + [records[0]])["status"] == "blocked"
    repeated = records[0].model_copy(update={"response_id": "retry", "answered_at": records[-1].answered_at})
    report = assess(records + [repeated])
    assert report["excluded_repeats"] == 1
    assert report["first_responses"]["responses"] == 24
    assert report["split"] == assess(records)["split"]


def test_holdout_with_one_class_blocks_auc():
    records = rows()
    records[18:] = [r.model_copy(update={"correct": True}) for r in records[18:]]
    report = assess(records)
    assert report["status"] == "blocked"
    assert not report["split"]["auc_available"]


def test_support_is_measured_only_in_training_data():
    records = rows()
    records = [r.model_copy(update={"question_type": "matching"}) if i >= 18 else r for i, r in enumerate(records)]
    report = assess(records)
    for group in report["question_types"]:
        if group["question_type"] == "matching":
            assert group["train"]["responses"] == 0
            assert not group["meets_bkt_fit_threshold"]
            assert group["first_responses"]["responses"] == 3


def test_legacy_and_missing_skill_are_visible():
    records = [r.model_copy(update={"skill": "reading", "content_version": "legacy"}) for r in rows()]
    report = assess(records)
    assert report["legacy_responses"] == 24
    assert any("Legacy" in text for text in report["warnings"])
    assert report["by_skill"]["listening"]["responses"] == 0
    assert any("No listening data" in text for text in report["warnings"])


def test_support_threshold_uses_distinct_learners_first_responses():
    records = [r.model_copy(update={"learner_id": f"u{i}", "item_id": "shared", "skill": "reading"}) for i, r in enumerate(rows())]
    report = assess(records)
    assert report["items"][0]["meets_pilot_support"]
    assert report["items"][0]["train"]["responses"] == 18
    assert report["question_types"][0]["meets_bkt_fit_threshold"]


def test_conflicting_item_types_block_and_versions_are_distinct():
    records = rows()
    records[2] = records[2].model_copy(update={"item_id": records[0].item_id, "question_type": "matching"})
    assert assess(records)["status"] == "blocked"
    records[2] = records[2].model_copy(update={"content_version": "v2"})
    assert assess(records)["can_run_auc_comparison"]


def test_invalid_lines_are_reported_without_echoing_raw_content(tmp_path):
    source = tmp_path / "responses.jsonl"
    source.write_text(rows()[0].model_dump_json() + '\n{"private":"do-not-echo"}\n', encoding="utf-8")
    report = inspect_file(source)
    assert report["invalid_lines"] == [2]
    assert report["status"] == "blocked"
    assert "do-not-echo" not in json.dumps(report)


def test_cli_writes_report_and_never_overwrites_input(tmp_path, monkeypatch, capsys):
    source = tmp_path / "responses.jsonl"
    source.write_text("".join(r.model_dump_json() + "\n" for r in rows()), encoding="utf-8")
    original = source.read_bytes()
    output = tmp_path / "reports" / "readiness.json"
    monkeypatch.setattr("sys.argv", ["readiness", str(source), "--output", str(output)])
    assert main() == 0
    assert json.loads(output.read_text())["raw"]["responses"] == 24
    assert source.read_bytes() == original
    monkeypatch.setattr("sys.argv", ["readiness", str(source), "--output", str(source)])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
    assert source.read_bytes() == original
    capsys.readouterr()


def test_invalid_split_rejected_and_ties_never_cross_split():
    with pytest.raises(ValueError):
        assess(rows(), train_fraction=1)
    records = rows()
    records[17] = records[17].model_copy(update={"answered_at": records[18].answered_at})
    train, test, cutoff = temporal_split(records, 0.75)
    assert all(r.answered_at < cutoff for r in train)
    assert all(r.answered_at >= cutoff for r in test)
