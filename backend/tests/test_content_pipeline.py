from types import SimpleNamespace

import import_content
import validate_listening
from app.domain.scoring import grade_attempt, question_type_label


def test_importer_accepts_expanded_ielts_question_types():
    question = import_content._build_question(
        {
            "order": 1,
            "text": "Heading for Paragraph 2",
            "question_type": "matching_headings",
            "options": ["A", "B", "C"],
            "correct_answer": ["B"],
            "explanation": "Paragraph 2 matches heading B.",
        },
        "test 'x', section 1",
        1,
    )

    assert question.question_type == "matching_headings"
    assert question.correct_answer == ["B"]


def test_importer_discovers_nested_content_files(tmp_path, monkeypatch):
    nested = tmp_path / "listening"
    nested.mkdir()
    path = nested / "test-01.json"
    path.write_text('{"tests": []}', encoding="utf-8")
    monkeypatch.setattr(import_content, "CONTENT_DIR", tmp_path)

    assert import_content._collect_paths([]) == [path]


def test_expanded_question_types_score_and_label():
    question = SimpleNamespace(
        id=1,
        text="The writer agrees with the statement.",
        question_type="yes_no_not_given",
        correct_answer=["Yes"],
        explanation="The speaker agrees.",
    )

    graded, score = grade_attempt([question], {1: "yes"})

    assert score == 1
    assert graded[0]["is_correct"] is True
    assert question_type_label("summary_completion") == "Summary Completion"


def _listening_test(evidence_quote: str = "the booking closes on Friday") -> dict:
    sections = []
    order = 1
    for section_order in range(1, 5):
        transcript = f"Speaker: In section {section_order}, {evidence_quote}."
        questions = []
        for _ in range(10):
            questions.append(
                {
                    "order": order,
                    "text": f"Question {order}",
                    "question_type": "fill_blank",
                    "correct_answer": ["Friday"],
                    "explanation": "The transcript states the booking closes on Friday.",
                    "evidence": [{"paragraph": 1, "quote": evidence_quote}],
                }
            )
            order += 1
        sections.append(
            {
                "order": section_order,
                "title": f"Section {section_order}",
                "audio_url": f"/static/audio/listening/s{section_order}.m4a",
                "passage": transcript,
                "questions": questions,
            }
        )
    return {
        "title": "IELTS Listening — Test X",
        "test_type": "listening",
        "sections": sections,
    }


def test_listening_validator_accepts_full_test():
    report = validate_listening.Report()
    validate_listening.validate_test(_listening_test(), "sample.json", report)

    assert report.errors == []
    assert report.questions == 40


def test_listening_validator_rejects_missing_evidence_quote():
    data = _listening_test()
    data["sections"][0]["questions"][0]["evidence"] = [{"paragraph": 1, "quote": "not in transcript"}]
    report = validate_listening.Report()

    validate_listening.validate_test(data, "sample.json", report)

    assert any("evidence quote not found" in error for error in report.errors)
