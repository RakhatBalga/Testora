import json
import pytest
from ml.data import SpeakingSample
from ml.datasets.speaking_readiness import assess, main


def recordings(tmp_path):
    samples = []
    for i in range(4):
        (tmp_path / f"{i}.wav").write_bytes(f"fake-audio-{i}".encode())
        samples.append(
            SpeakingSample(
                sample_id=f"s{i}",
                speaker_id=f"person{i}",
                audio_path=f"{i}.wav",
                reference_text="private spoken sentence",
                expert_band=5 + i * 0.5,
                consent=True,
            )
        )
    return samples


def test_pilot_readiness_is_aggregate_and_does_not_claim_validated_quality(tmp_path):
    samples = recordings(tmp_path)
    result = assess(samples, tmp_path)
    assert result["can_run_pilot"] is True
    assert result["status"] == "pilot_with_warnings"
    assert result["speaker_count"] == 4
    assert "private spoken sentence" not in json.dumps(result)
    assert "person0" not in json.dumps(result)
    assert "0.wav" not in json.dumps(result)


def test_readiness_blocks_missing_audio_and_unusable_reference(tmp_path):
    samples = recordings(tmp_path)
    samples[0] = samples[0].model_copy(update={"audio_path": "missing.wav", "reference_text": "!!!"})
    result = assess(samples, tmp_path)
    assert result["can_run_pilot"] is False
    assert len(result["blockers"]) == 2
    assert assess([], tmp_path)["can_run_pilot"] is False


def test_cli_writes_hashed_report_and_preserves_previous_results(tmp_path, capsys):
    samples = recordings(tmp_path)
    manifest = tmp_path / "samples.jsonl"
    manifest.write_text("\n".join(s.model_dump_json() for s in samples), encoding="utf-8")
    output = tmp_path / "report.json"
    args = [str(manifest), "--audio-root", str(tmp_path), "--output", str(output)]
    assert main(args) == 0
    report = json.loads(output.read_text())
    assert len(report["manifest_sha256"]) == 64
    original = output.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2
    assert output.read_bytes() == original
    assert "private spoken sentence" not in capsys.readouterr().out
