from types import SimpleNamespace

import pytest

from app.domain.scoring import _check, build_breakdown, grade_attempt


def question(question_type: str, correct_answer, question_id: int = 1):
    return SimpleNamespace(
        id=question_id,
        text="Question",
        question_type=question_type,
        correct_answer=correct_answer,
        explanation="Evidence-based explanation.",
    )


@pytest.mark.parametrize(
    ("question_type", "correct", "submitted"),
    [
        ("true_false_notgiven", ["TRUE"], " true "),
        ("yes_no_not_given", ["YES"], "yes"),
        ("matching_headings", ["iv"], "IV"),
        ("matching_information", ["B"], "b"),
        ("sentence_completion", ["solar power"], " Solar Power "),
        ("summary_completion", ["declined"], "DECLINED"),
        ("short_answer", ["three years", "3 years"], "3 YEARS"),
        ("single_choice", ["C"], "c"),
    ],
)
def test_reading_single_answer_types_normalize_case_and_whitespace(question_type, correct, submitted):
    assert _check(question(question_type, correct), submitted) is True


def test_multiple_choice_requires_the_complete_set_in_any_order():
    item = question("multiple_choice", ["A", "C"])

    assert _check(item, [" c ", "a"]) is True
    assert _check(item, ["A"]) is False
    assert _check(item, ["A", "B", "C"]) is False


@pytest.mark.parametrize(
    ("question_type", "correct", "submitted"),
    [
        ("yes_no_not_given", ["YES"], "TRUE"),
        ("yes_no_not_given", ["NO"], "FALSE"),
        ("true_false_notgiven", ["TRUE"], "YES"),
        ("true_false_notgiven", ["FALSE"], "NO"),
    ],
)
def test_yes_no_and_true_false_are_not_interchangeable(question_type, correct, submitted):
    assert _check(question(question_type, correct), submitted) is False


def test_grade_attempt_keeps_explanations_and_builds_weakest_first_breakdown():
    questions = [
        question("short_answer", ["solar"], 1),
        question("short_answer", ["wind"], 2),
        question("matching_headings", ["i"], 3),
    ]

    graded, score = grade_attempt(questions, {1: "wrong", 2: "wind", 3: "i"})
    breakdown = build_breakdown(graded)

    assert score == 2
    assert graded[0]["explanation"] == "Evidence-based explanation."
    assert breakdown[0]["question_type"] == "short_answer"
    assert breakdown[0]["accuracy"] == 50
