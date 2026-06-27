import re

from app.domain.scoring import _as_list, _display, _normalize, build_breakdown


WORD_RE = re.compile(r"[\w]+(?:[-'][\w]+)*", re.UNICODE)


def answer_word_count(value: str) -> int:
    """Count lexical tokens; hyphenated compounds count as one IELTS answer word."""
    return len(WORD_RE.findall(value or ""))


def _is_correct(question, user_answer) -> bool:
    correct = _as_list(question.correct_answer)
    user = _as_list(user_answer)
    if question.question_type == "multiple_choice":
        return {_normalize(item) for item in user} == {_normalize(item) for item in correct}
    if not user:
        return False

    metadata = question.question_metadata or {}
    word_limit = metadata.get("word_limit")
    if word_limit and answer_word_count(user[0]) > int(word_limit):
        return False
    return _normalize(user[0]) in {_normalize(item) for item in correct}


def grade_listening(questions, answers_map):
    graded = []
    score = 0
    for question in questions:
        user_answer = answers_map.get(question.id)
        is_correct = _is_correct(question, user_answer)
        score += int(is_correct)
        graded.append({
            "question_id": question.id,
            "text": question.text,
            "question_type": question.question_type,
            "user_answer": _display(user_answer) or None,
            "correct_answer": _display(question.correct_answer),
            "is_correct": is_correct,
            "explanation": question.explanation,
        })
    return graded, score, build_breakdown(graded)
