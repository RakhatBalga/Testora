def _normalize(value: str) -> str:
    return value.strip().lower() if value else ""


def grade_attempt(questions, answers_map):
    """Compare user answers against the correct ones.

    questions: list of Question ORM objects.
    answers_map: dict of question_id -> user answer string.

    Returns (graded, score) where graded is a list of dicts ready for the
    AnswerResult schema and score is the number of correct answers.
    """
    graded = []
    score = 0
    for question in questions:
        user_answer = answers_map.get(question.id)
        is_correct = _normalize(user_answer) == _normalize(question.correct_answer)
        if is_correct:
            score += 1
        graded.append(
            {
                "question_id": question.id,
                "text": question.text,
                "user_answer": user_answer,
                "correct_answer": question.correct_answer,
                "is_correct": is_correct,
            }
        )
    return graded, score
