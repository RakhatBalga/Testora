def _normalize(value: str) -> str:
    return value.strip().lower() if value else ""


def _as_list(value) -> list[str]:
    """Coerce a stored/submitted answer into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _display(value) -> str:
    return ", ".join(_as_list(value))


def _check(question, user_answer) -> bool:
    correct = _as_list(question.correct_answer)
    user = _as_list(user_answer)

    if question.question_type == "multiple_choice":
        return {_normalize(u) for u in user} == {_normalize(c) for c in correct}

    # single answer types (choice / tf-ng / matching / fill_blank / short_answer):
    # the user's single answer must match one of the acceptable answers.
    if not user:
        return False
    return _normalize(user[0]) in {_normalize(c) for c in correct}


# Human labels for the per-question-type result breakdown.
QUESTION_TYPE_LABELS = {
    "single_choice": "Multiple Choice",
    "multiple_choice": "Multiple Answer",
    "true_false_notgiven": "True / False / Not Given",
    "matching": "Matching",
    "fill_blank": "Sentence Completion",
    "short_answer": "Short Answer",
}


def question_type_label(qtype: str) -> str:
    return QUESTION_TYPE_LABELS.get(qtype, qtype.replace("_", " ").title())


def build_breakdown(graded: list[dict]) -> list[dict]:
    """Aggregate graded answers into per-question-type performance stats.

    Returns a list of {question_type, label, correct, total, accuracy} sorted by
    accuracy ascending (weakest type first), so the result screen leads with what
    needs work.
    """
    buckets: dict[str, dict] = {}
    for item in graded:
        qtype = item["question_type"]
        b = buckets.setdefault(qtype, {"correct": 0, "total": 0})
        b["total"] += 1
        if item["is_correct"]:
            b["correct"] += 1

    out = [
        {
            "question_type": qtype,
            "label": question_type_label(qtype),
            "correct": b["correct"],
            "total": b["total"],
            "accuracy": round(b["correct"] / b["total"] * 100) if b["total"] else 0,
        }
        for qtype, b in buckets.items()
    ]
    out.sort(key=lambda x: (x["accuracy"], x["label"]))
    return out


def grade_attempt(questions, answers_map):
    """Compare user answers against the correct ones across all question types.

    questions: list of Question ORM objects.
    answers_map: dict of question_id -> user answer (str or list[str]).

    Returns (graded, score) where graded is a list of dicts ready for the
    AnswerResult schema and score is the number of correct answers.
    """
    graded = []
    score = 0
    for question in questions:
        user_answer = answers_map.get(question.id)
        is_correct = _check(question, user_answer)
        if is_correct:
            score += 1
        graded.append(
            {
                "question_id": question.id,
                "text": question.text,
                "question_type": question.question_type,
                "user_answer": _display(user_answer) or None,
                "correct_answer": _display(question.correct_answer),
                "is_correct": is_correct,
                "explanation": getattr(question, "explanation", None),
            }
        )
    return graded, score
