import csv
import io
import json
import traceback

import pytest

from ml.data import SpeakingSample, read_jsonl
from ml.datasets.speaking.labels import assemble, build_bundle, import_ratings, main
from ml.datasets.speaking.readiness import assess
from ml.datasets.speaking.registry import CRITERIA, LABEL_COLUMNS, Recording, inspect_recordings, worksheet


def batch(tmp_path):
    records = []
    for i in range(4):
        (tmp_path / f"{i}.wav").write_bytes(f"synthetic-only-{i}".encode())
        records.append(
            Recording(
                sample_id=f"s{i}",
                speaker_id=f"p{i}",
                part=1,
                task_id="t1",
                audio_path=f"{i}.wav",
                consent=True,
                consent_record_id=f"c{i}",
                recorded_at="2026-11-03T10:00:00Z",
                reference_text="private human transcript",
            )
        )
    rows = list(csv.DictReader(io.StringIO(worksheet(records, tmp_path))))
    for row in rows:
        row.update(rater_id="expert1", overall_band="6.5", **dict.fromkeys(CRITERIA, "6"))
    return records, rows


def csv_text(rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=LABEL_COLUMNS)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def input_files(tmp_path):
    records, rows = batch(tmp_path)
    registry, labels = tmp_path / "registry.jsonl", tmp_path / "expert.csv"
    registry.write_text("\n".join(r.model_dump_json() for r in records), encoding="utf-8")
    labels.write_text(csv_text(rows), encoding="utf-8")
    return registry, labels


def test_bundle_roundtrips_to_existing_pipeline_and_keeps_criterion_provenance(tmp_path):
    registry, labels = input_files(tmp_path)
    output = tmp_path / "bundle"
    metadata = build_bundle(registry, labels, tmp_path, output)
    samples = read_jsonl(output / "samples.jsonl", SpeakingSample)
    assert assess(samples, tmp_path)["can_run_pilot"] is True
    assert all(s.expert_band == 6.5 and s.llm_band is None for s in samples)
    saved = [json.loads(line) for line in (output / "labels.jsonl").read_text().splitlines()]
    assert saved[0]["fluency_coherence"] == 6
    assert saved[0]["rater_id"] == "expert1"
    assert len(saved[0]["recording"]["audio_sha256"]) == 64
    assert metadata["speaker_count"] == 4
    assert "private human transcript" not in (output / "metadata.json").read_text()
    assert "private human transcript" not in (output / "labels.jsonl").read_text()


@pytest.mark.parametrize("value", ["", "6.25", "9.5", "-1", "NaN", "inf", "private@example.test"])
def test_invalid_scores_fail_without_leaking_cell_contents(tmp_path, value):
    records, rows = batch(tmp_path)
    rows[0]["pronunciation"] = value
    try:
        import_ratings(csv_text(rows), inspect_recordings(records, tmp_path))
    except ValueError:
        assert "private@example.test" not in traceback.format_exc()
    else:
        pytest.fail("Invalid score accepted")


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "unknown", "task", "hash", "rater"])
def test_import_requires_exact_recording_set_and_identity(tmp_path, mutation):
    records, rows = batch(tmp_path)
    if mutation == "duplicate":
        rows.append(rows[0])
    elif mutation == "missing":
        rows.pop()
    else:
        key = {"unknown": "sample_id", "task": "task_id", "hash": "audio_sha256", "rater": "rater_id"}[mutation]
        rows[0][key] = "" if mutation == "rater" else "changed"
    with pytest.raises(ValueError):
        import_ratings(csv_text(rows), inspect_recordings(records, tmp_path))


def test_audio_replacement_blocks_import_without_creating_output(tmp_path):
    registry, labels = input_files(tmp_path)
    (tmp_path / "0.wav").write_bytes(b"replacement")
    with pytest.raises(ValueError):
        build_bundle(registry, labels, tmp_path, tmp_path / "bundle")
    assert not (tmp_path / "bundle").exists()


def test_transcript_and_consent_required_at_assembly(tmp_path):
    records, rows = batch(tmp_path)
    ratings = import_ratings(csv_text(rows), inspect_recordings(records, tmp_path))
    for change in [dict(reference_text=None), dict(reference_text="!!!"), dict(consent=False)]:
        bad = [records[0].model_copy(update=change), *records[1:]]
        with pytest.raises(ValueError):
            assemble(bad, ratings)
    with pytest.raises(ValueError):
        assemble(records, ratings + ratings[:1])


def test_cli_does_not_overwrite_previous_bundle_or_print_transcript(tmp_path, capsys):
    registry, labels = input_files(tmp_path)
    output = tmp_path / "bundle"
    args = [str(registry), str(labels), "--audio-root", str(tmp_path), "--output-dir", str(output)]
    assert main(args) == 0
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(SystemExit):
        main(args)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    result = capsys.readouterr()
    assert "private human transcript" not in result.out + result.err


def test_import_accepts_utf8_bom_but_rejects_changed_columns(tmp_path):
    records, rows = batch(tmp_path)
    identities = inspect_recordings(records, tmp_path)
    assert len(import_ratings("\ufeff" + csv_text(rows), identities)) == 4
    with pytest.raises(ValueError):
        import_ratings(csv_text(rows).replace("overall_band", "score", 1), identities)
