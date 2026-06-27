"""Validate the versioned Testora Listening benchmark and its media assembly."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONTENT_DIR = ROOT / "content/listening"
FRONTEND_PUBLIC = ROOT.parent / "frontend/public"
REPORT_PATH = CONTENT_DIR / "testora-studio-01-assembly-report.json"
EXPECTED_INTRO = "This is a Testora Studio Listening Practice Test. The test will begin in five seconds."
AUTHORSHIP = "Original IELTS-style practice test created by Testora."
QUESTION_TYPES = {
    "single_choice", "multiple_choice", "matching", "matching_information",
    "sentence_completion", "summary_completion", "fill_blank", "short_answer",
}
BLUEPRINT_FIELDS = {
    "section", "type", "target_skill", "information_type", "difficulty",
    "answer_location", "evidence_segment", "distractor_mechanism",
    "linguistic_feature", "dependency", "cultural_accessibility", "reviewer_status",
}
CALIBRATION_STATUSES = {"draft", "provisional", "reviewed", "calibrated", "retired"}


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().lower()


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.tests = 0
        self.questions = 0
        self.media: dict = {}

    def err(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def _audio_path(url: str) -> Path:
    prefix = "/static/"
    return ROOT / "static" / url.removeprefix(prefix)


def _probe(path: Path) -> dict:
    output = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=codec_name,sample_rate,channels",
        "-of", "json", str(path),
    ], text=True)
    raw = json.loads(output)
    stream = raw["streams"][0]
    return {
        "duration_seconds": round(float(raw["format"]["duration"]), 3),
        "codec": stream["codec_name"],
        "sample_rate": int(stream["sample_rate"]),
        "channels": int(stream["channels"]),
        "size_bytes": path.stat().st_size,
    }


def _validate_blueprint(data: dict, rep: Report) -> dict[int, dict]:
    if data.get("schema_version") != "testora.listening-blueprint.v1":
        rep.err("blueprint: unsupported schema_version")
    items = data.get("items", [])
    if len(items) != 40:
        rep.err(f"blueprint: expected 40 items, found {len(items)}")
    if data.get("calibration_status") != "provisional":
        rep.err("blueprint: new benchmark must remain provisional before real pretesting")
    if data.get("authorship") != AUTHORSHIP:
        rep.err("blueprint: required original-authorship wording is missing")
    passes = data.get("review_passes", {})
    for name in ("pre_edit", "editorial", "independent_simulation"):
        if passes.get(name, {}).get("status") != "reviewed":
            rep.err(f"blueprint: review pass {name} is not complete")
    by_order = {}
    for item in items:
        number = item.get("question")
        if not isinstance(number, int) or number in by_order:
            rep.err(f"blueprint: invalid or duplicate question {number}")
            continue
        missing = sorted(field for field in BLUEPRINT_FIELDS if not item.get(field))
        if missing:
            rep.err(f"blueprint Q{number}: missing {', '.join(missing)}")
        by_order[number] = item
    if set(by_order) != set(range(1, 41)):
        rep.err("blueprint: question numbers must be exactly 1-40")
    return by_order


def _validate_manifest(manifest: dict, rep: Report) -> None:
    if manifest.get("schema_version") != "testora.listening-audio-manifest.v1":
        rep.err("audio manifest: unsupported schema_version")
    if manifest.get("intro_script") != EXPECTED_INTRO:
        rep.err("audio manifest: intro script is not exact")
    if manifest.get("intro_silence_seconds") != 5.0:
        rep.err("audio manifest: intro silence must be exactly 5.0 seconds")
    events = manifest.get("events", [])
    kinds = [event.get("kind") for event in events[:3]]
    ids = [event.get("id") for event in events[:3]]
    if kinds != ["speech", "silence", "cue"] or ids != ["intro", "intro-silence", "start-cue"]:
        rep.err("audio manifest: expected intro, five-second silence, then neutral cue")
    if len(manifest.get("voices", {})) < 5 or len(manifest.get("voices", {})) > 7:
        rep.err("audio manifest: expected 5-7 stable voice roles")
    accents = {voice.get("accent") for voice in manifest.get("voices", {}).values()}
    if len(accents) < 3:
        rep.err("audio manifest: expected at least three English accent groups")


def validate_test(data: dict, where: str, rep: Report, blueprint: dict[int, dict] | None = None) -> None:
    if data.get("test_type") != "listening":
        return
    rep.tests += 1
    strict = blueprint is not None
    title = data.get("title", where)
    metadata = data.get("metadata", {})
    if strict and metadata.get("schema_version") != "testora.listening-content.v1":
        rep.err(f"{title}: unsupported content schema")
    if strict and metadata.get("authorship") != AUTHORSHIP:
        rep.err(f"{title}: required original-authorship wording is missing")
    status = metadata.get("calibration_status")
    if strict and status not in CALIBRATION_STATUSES:
        rep.err(f"{title}: invalid calibration status {status!r}")
    if strict and status == "calibrated":
        rep.err(f"{title}: cannot be calibrated without real pretest statistics")
    if strict and metadata.get("intro_script") != EXPECTED_INTRO:
        rep.err(f"{title}: intro script is not exact")
    sections = data.get("sections", [])
    if len(sections) != 4:
        rep.err(f"{title}: expected 4 sections, found {len(sections)}")
    seen_orders: set[int] = set()
    urls: set[str] = set()
    for section_index, section in enumerate(sections, 1):
        label = f"{title} / Section {section_index}"
        if section.get("order") != section_index:
            rep.err(f"{label}: sections must be ordered 1-4")
        transcript = section.get("passage", "")
        segments = section.get("metadata", {}).get("transcript_segments", [])
        if strict and (not transcript or not segments):
            rep.err(f"{label}: transcript and timed segments are required")
        segment_ids = {segment.get("id") for segment in segments}
        for segment in segments:
            if not all(key in segment for key in ("id", "speaker", "text", "start", "end")):
                rep.err(f"{label}: malformed transcript segment")
            elif segment["end"] <= segment["start"]:
                rep.err(f"{label}: invalid timestamp for {segment['id']}")
        audio_url = section.get("audio_url")
        if not audio_url:
            rep.err(f"{label}: audio_url is required")
        else:
            urls.add(audio_url)
        if strict and section_index == 2:
            asset = section.get("metadata", {}).get("map_asset")
            if not asset or not (FRONTEND_PUBLIC / asset.lstrip("/")).exists():
                rep.err(f"{label}: original map asset is missing")
        questions = section.get("questions", [])
        if len(questions) != 10:
            rep.err(f"{label}: expected 10 questions, found {len(questions)}")
        for question in questions:
            rep.questions += 1
            order = question.get("order")
            qlabel = f"{title} / Q{order}"
            if order in seen_orders or not isinstance(order, int):
                rep.err(f"{qlabel}: order must be a unique integer")
            seen_orders.add(order)
            if question.get("question_type") not in QUESTION_TYPES:
                rep.err(f"{qlabel}: unsupported question type")
            if not question.get("correct_answer") or not question.get("explanation"):
                rep.err(f"{qlabel}: answer and explanation are required")
            if question.get("question_type") in {"single_choice", "multiple_choice", "matching", "matching_information"} and not question.get("options"):
                rep.err(f"{qlabel}: options are required")
            qmeta = question.get("metadata", {})
            expected = (blueprint or {}).get(order)
            if expected:
                for field in BLUEPRINT_FIELDS:
                    if qmeta.get(field) != expected.get(field):
                        rep.err(f"{qlabel}: metadata field {field} differs from blueprint")
            if strict and question.get("question_type") in {"fill_blank", "sentence_completion", "summary_completion", "short_answer"}:
                limit = qmeta.get("word_limit")
                if not isinstance(limit, int) or not 1 <= limit <= 3:
                    rep.err(f"{qlabel}: completion requires a 1-3 word limit")
            if strict:
                evidence_id = str(qmeta.get("evidence_segment", ""))
                for part in evidence_id.split(":"):
                    if part and part not in segment_ids:
                        rep.err(f"{qlabel}: evidence segment {part} not found")
            for span in question.get("evidence", []):
                quote = span.get("quote", span.get("text", ""))
                if not quote or _norm(quote) not in _norm(transcript):
                    rep.err(f"{qlabel}: evidence quote not found verbatim in transcript")
    if seen_orders != set(range(1, 41)):
        rep.err(f"{title}: question orders must be exactly 1-40")
    if strict and len(urls) != 1:
        rep.err(f"{title}: all sections must reference one versioned master audio file")
    for url in urls if strict else []:
        path = _audio_path(url)
        if not path.exists():
            rep.err(f"{title}: audio file not found: {path}")
            continue
        try:
            media = _probe(path)
        except (OSError, subprocess.CalledProcessError, KeyError, ValueError) as exc:
            rep.err(f"{title}: ffprobe failed: {exc}")
            continue
        rep.media = media
        if media["codec"] != "aac" or media["sample_rate"] != 44100 or media["channels"] != 1:
            rep.err(f"{title}: audio must be AAC mono at 44.1 kHz")
        expected_duration = float(metadata.get("audio_duration", 0))
        if abs(media["duration_seconds"] - expected_duration) > 0.1:
            rep.err(f"{title}: content duration differs from ffprobe")
        if not 480 <= media["duration_seconds"] <= 1800:
            rep.warn(f"{title}: duration is outside the preferred 8-30 minute authored benchmark range")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="+")
    parser.add_argument("--no-write-report", action="store_true")
    args = parser.parse_args()
    rep = Report()
    blueprint_path = CONTENT_DIR / "testora-studio-01-blueprint.json"
    manifest_path = CONTENT_DIR / "testora-studio-01-audio-manifest.json"
    try:
        blueprint_raw = json.loads(blueprint_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Listening validation cannot load assembly metadata: {exc}")
        return 1
    blueprint = _validate_blueprint(blueprint_raw, rep)
    _validate_manifest(manifest, rep)
    files = [Path(path) for path in args.files] if args.files else [CONTENT_DIR / "testora-studio-01.json"]
    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            rep.err(f"{path.name}: cannot read ({exc})")
            continue
        for test in raw.get("tests", []):
            validate_test(test, path.name, rep, blueprint)
    report = {
        "schema_version": "testora.listening-assembly-report.v1",
        "content_version": blueprint_raw.get("content_version"),
        "status": "passed" if not rep.errors else "failed",
        "tests": rep.tests,
        "sections": 4 if rep.tests else 0,
        "questions": rep.questions,
        "blueprint_items": len(blueprint),
        "review_passes": blueprint_raw.get("review_passes"),
        "calibration_status": blueprint_raw.get("calibration_status"),
        "media": rep.media,
        "errors": rep.errors,
        "warnings": rep.warnings,
    }
    if not args.no_write_report:
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print("Listening benchmark validation")
    print(f"  tests/questions : {rep.tests}/{rep.questions}")
    print(f"  blueprint items : {len(blueprint)}")
    if rep.media:
        print(f"  audio           : {rep.media['duration_seconds']}s {rep.media['codec']} {rep.media['sample_rate']}Hz mono")
    for warning in rep.warnings:
        print(f"  warning: {warning}")
    for error in rep.errors:
        print(f"  x {error}")
    print(f"  status          : {report['status']}")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
