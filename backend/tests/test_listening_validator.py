import copy
import json
import sys

import pytest
import validate_listening as validator


@pytest.fixture
def package(monkeypatch):
    content = json.loads((validator.CONTENT_DIR / "testora-studio-02.json").read_text(encoding="utf-8"))["tests"][0]
    manifest = json.loads((validator.CONTENT_DIR / "testora-studio-02-audio-manifest.json").read_text(encoding="utf-8"))
    # Unit tests isolate content checks; CI separately runs real ffprobe.
    monkeypatch.setattr(validator, "_probe", lambda path: {
        "duration_seconds": 651.4, "codec": "aac", "sample_rate": 44100,
        "channels": 1, "size_bytes": path.stat().st_size,
    })
    return content, manifest


def check(content, manifest):
    report = validator.Report()
    validator.validate_test(content, "fixture", report)
    validator.validate_current_package(content, manifest, report)
    return report


def test_current_package_has_40_valid_questions_without_fabricated_review(package):
    report = check(*package)
    assert report.errors == []
    assert report.tests == 1
    assert report.questions == 40


@pytest.mark.parametrize("fault", ["quote", "answer", "timing", "version", "transcript", "audio", "question_count"])
def test_detects_content_and_media_regressions(package, fault):
    content, manifest = copy.deepcopy(package)
    if fault == "quote":
        content["sections"][0]["questions"][0]["evidence"][0]["quote"] = "Invented quotation"
    elif fault == "answer":
        content["sections"][1]["questions"][0]["correct_answer"] = ["not an option"]
    elif fault == "timing":
        manifest["events"][1]["end"] += 1
    elif fault == "version":
        manifest["content_version"] = "other"
    elif fault == "transcript":
        next(e for e in manifest["events"] if e["id"] == "s1-01")["text"] = "Different recording"
    elif fault == "audio":
        content["sections"][0]["audio_url"] = "/static/audio/listening/missing.m4a"
    else:
        content["sections"][0]["questions"].pop()
    assert check(content, manifest).errors


def test_empty_pack_fails_cli(tmp_path, monkeypatch, package):
    path = tmp_path / "empty.json"
    path.write_text('{"tests": []}')
    monkeypatch.setattr(sys, "argv", ["validate_listening.py", "--files", str(path), "--no-write-report"])
    assert validator.main() == 1


def test_editorial_gate_still_fails_without_original_blueprint(monkeypatch, package):
    monkeypatch.setattr(sys, "argv", ["validate_listening.py", "--require-editorial", "--no-write-report"])
    assert validator.main() == 1
