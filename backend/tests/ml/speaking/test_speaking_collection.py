import csv
import io
import traceback

import pytest

from ml.data import read_jsonl
from ml.datasets.speaking.registry import Recording, inspect_recordings, main, worksheet


def registry(tmp_path, count=4):
    rows = []
    for i in range(count):
        (tmp_path / f"{i}.wav").write_bytes(f"synthetic-audio-{i}".encode())
        rows.append(
            Recording(
                sample_id=f"s{i}",
                speaker_id=f"p{i}",
                part=i % 3 + 1,
                task_id=f"t{i}",
                audio_path=f"{i}.wav",
                consent=True,
                consent_record_id=f"consent{i}",
                recorded_at="2026-11-03T10:00:00Z",
                reference_text="private verbatim transcript",
            )
        )
    return rows


def test_worksheet_is_blind_and_has_empty_scores(tmp_path):
    rows = registry(tmp_path)
    payload = worksheet(rows, tmp_path)
    table = list(csv.DictReader(io.StringIO(payload)))
    assert len(table) == 4
    assert table[0]["rater_id"] == table[0]["overall_band"] == ""
    assert len(table[0]["audio_sha256"]) == 64
    assert "speaker_id" not in payload and "reference_text" not in payload
    assert "private verbatim" not in payload and "consent0" not in payload
    assert worksheet(list(reversed(rows)), tmp_path) == payload


@pytest.mark.parametrize("path", ["../secret.wav", "/tmp/a.wav", "C:/a.wav", "=formula.wav", "a\\b.wav"])
def test_registry_rejects_unsafe_paths(tmp_path, path):
    values = registry(tmp_path, 1)[0].model_dump()
    values["audio_path"] = path
    with pytest.raises(ValueError):
        Recording(**values)


@pytest.mark.parametrize(
    "changes",
    [
        dict(part=True),
        dict(part=4),
        dict(consent="true"),
        dict(consent_record_id=None),
        dict(recorded_at="2026-11-03T10:00:00"),
        dict(sample_id="=SUM(1)"),
        dict(reference_text=" "),
    ],
)
def test_registry_rejects_invalid_metadata(tmp_path, changes):
    values = registry(tmp_path, 1)[0].model_dump()
    with pytest.raises(ValueError):
        Recording(**{**values, **changes})


def test_batch_checks_consent_duplicates_and_missing_audio(tmp_path):
    rows = registry(tmp_path)
    for bad in [
        [],
        rows + rows[:1],
        [rows[0].model_copy(update={"consent": False})],
        [rows[0].model_copy(update={"audio_path": "missing.wav"})],
    ]:
        with pytest.raises(ValueError):
            inspect_recordings(bad, tmp_path)
    (tmp_path / "1.wav").write_bytes((tmp_path / "0.wav").read_bytes())
    with pytest.raises(ValueError, match="Duplicate audio"):
        inspect_recordings(rows, tmp_path)


def test_cli_preserves_output_and_hides_invalid_record_payload(tmp_path, capsys):
    rows = registry(tmp_path)
    source, output = tmp_path / "registry.jsonl", tmp_path / "expert.csv"
    source.write_text("\n".join(r.model_dump_json() for r in rows), encoding="utf-8")
    args = [str(source), "--audio-root", str(tmp_path), "--output", str(output)]
    assert main(args) == 0
    before = output.read_bytes()
    with pytest.raises(SystemExit):
        main(args)
    assert output.read_bytes() == before
    source.write_text('{"private": "do-not-print"}', encoding="utf-8")
    try:
        read_jsonl(source, Recording)
    except ValueError:
        assert "do-not-print" not in traceback.format_exc()
    assert "private verbatim" not in capsys.readouterr().out
