import json
from pathlib import Path

import pytest

pytest.importorskip("sklearn")

from ml.asr import WhisperConfig
from ml.experiments.speaking.run import main, run_experiment
from ml.speech_features import TimedWord, Transcript


def dataset(tmp_path, speakers=6):
    audio = tmp_path / "audio"
    audio.mkdir()
    rows = []
    for speaker in range(speakers):
        for part in range(2):
            name = f"sample-{speaker}-{part}"
            (audio / f"{name}.wav").write_bytes(name.encode())  # explicitly fake audio
            rows.append(
                dict(
                    schema_version="speaking.v1",
                    sample_id=name,
                    speaker_id=f"speaker-{speaker}",
                    audio_path=f"{name}.wav",
                    reference_text="hello world",
                    expert_band=4 + speaker * 0.5,
                    consent=True,
                )
            )
    manifest = tmp_path / "samples.jsonl"
    manifest.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return manifest, audio


class FakeASR:
    def __init__(self, config):
        assert config.allow_download is False

    def transcribe(self, path):
        number = int(path.stem.split("-")[1])
        return Transcript(
            text="hello world",
            duration_seconds=3 + number,
            words=[TimedWord(text="hello", start=0, end=0.4), TimedWord(text="world", start=0.8, end=1.3)],
        )


def run(manifest, audio, output, **kwargs):
    return run_experiment(
        manifest, audio, output, config=WhisperConfig(), dataset_kind="synthetic", engine_factory=FakeASR, **kwargs
    )


def test_pipeline_reports_same_holdout_and_persists_models_without_transcripts(tmp_path):
    manifest, audio = dataset(tmp_path)
    output = tmp_path / "run"
    report = run(manifest, audio, output)
    experiment = report["experiment"]
    assert set(experiment["train_speakers"]).isdisjoint(experiment["test_speakers"])
    assert report["planned_split"] == experiment["split_samples"]
    held = set(experiment["split_samples"]["holdout"])
    for model in ("mean_baseline", "linear_regression", "gradient_boosting"):
        assert {r["sample_id"] for r in experiment["models"][model]["predictions"]} == held
        assert (output / "models" / f"{model}.joblib").is_file()
    assert report["asr"]["corpus_wer"] == 0  # deterministic fake ASR, not real accuracy
    assert experiment["models"]["llm_transcript"]["status"] == "missing_held_out_scores"
    assert json.loads((output / "status.json").read_text())["status"] == "completed"
    for path in output.glob("*.json"):
        text = path.read_text()
        assert "hello world" not in text
        assert str(audio) not in text
    summary = (output / "summary.html").read_text()
    assert "synthetic" in summary and "speaker-" not in summary and "sample-" not in summary


def test_rerun_is_reproducible_and_output_is_never_overwritten(tmp_path):
    manifest, audio = dataset(tmp_path)
    first = run(manifest, audio, tmp_path / "run1")
    # Input ordering does not determine holdout assignment.
    manifest.write_text("\n".join(reversed(manifest.read_text().splitlines())))
    second = run(manifest, audio, tmp_path / "run2")
    assert first["experiment"] == second["experiment"]
    before = (tmp_path / "run1/report.json").read_bytes()
    with pytest.raises(FileExistsError):
        run(manifest, audio, tmp_path / "run1")
    assert (tmp_path / "run1/report.json").read_bytes() == before


def test_preflight_never_constructs_asr(tmp_path):
    manifest, audio = dataset(tmp_path)

    def forbidden(_):
        pytest.fail("ASR must not be loaded in preflight")

    out = tmp_path / "preflight"
    run_experiment(
        manifest,
        audio,
        out,
        config=WhisperConfig(),
        dataset_kind="synthetic",
        check_only=True,
        engine_factory=forbidden,
    )
    assert json.loads((out / "status.json").read_text())["models_trained"] is False
    assert not (out / "models").exists()


@pytest.mark.parametrize("problem", ["consent", "duplicate_audio", "too_few_speakers", "empty_audio", "bad_split"])
def test_invalid_data_fails_before_asr_or_output(tmp_path, problem):
    manifest, audio = dataset(tmp_path, speakers=3 if problem == "too_few_speakers" else 6)
    if problem == "consent":
        rows = [json.loads(line) for line in manifest.read_text().splitlines()]
        rows[0]["consent"] = False
        manifest.write_text("\n".join(json.dumps(r) for r in rows))
    if problem == "duplicate_audio":
        (audio / "sample-1-0.wav").write_bytes((audio / "sample-0-0.wav").read_bytes())
    if problem == "empty_audio":
        (audio / "sample-0-0.wav").write_bytes(b"")
    with pytest.raises(ValueError):
        run(manifest, audio, tmp_path / "invalid", test_size=0.8 if problem == "bad_split" else 0.25)
    assert not (tmp_path / "invalid").exists()


def test_model_failure_marks_partial_run_unusable_and_cli_hides_details(tmp_path, monkeypatch, capsys):
    manifest, audio = dataset(tmp_path)

    def broken(_):
        raise RuntimeError("private transcript and path")

    out = tmp_path / "failed"
    with pytest.raises(RuntimeError):
        run_experiment(manifest, audio, out, config=WhisperConfig(), dataset_kind="synthetic", engine_factory=broken)
    assert json.loads((out / "status.json").read_text())["results_usable"] is False
    import ml.experiments.speaking.run as module

    monkeypatch.setattr(module, "run_experiment", lambda *args, **kwargs: broken(None))
    with pytest.raises(SystemExit) as exc:
        main([str(manifest), "--audio-root", str(audio), "--output-dir", str(out), "--dataset-kind", "synthetic"])
    assert exc.value.code == 2
    assert "private transcript" not in capsys.readouterr().err


def test_changed_audio_during_asr_is_rejected(tmp_path):
    manifest, audio = dataset(tmp_path)

    class MutatingASR(FakeASR):
        def transcribe(self, path):
            result = super().transcribe(path)
            path.write_bytes(path.read_bytes() + b"changed")
            return result

    out = tmp_path / "changed"
    with pytest.raises(ValueError, match="changed"):
        run_experiment(
            manifest, audio, out, config=WhisperConfig(), dataset_kind="synthetic", engine_factory=MutatingASR
        )
    assert not (out / "models").exists()
    assert json.loads((out / "status.json").read_text())["status"] == "failed"


def test_default_private_research_directories_are_excluded_from_docker():
    backend = Path(__file__).resolve().parents[3]
    excluded = set((backend / ".dockerignore").read_text().splitlines())
    assert {"ml/data", "ml/artifacts", "ml/reports"} <= excluded
