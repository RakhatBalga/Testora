from collections import Counter
from math import sqrt

from sqlalchemy.orm import Session

from app.domain.models.attempt import AnswerRecord, Attempt
from app.domain.models.test import Question, Section


def _point_biserial(values: list[tuple[int, float]]) -> float | None:
    if len(values) < 2:
        return None
    correct = [score for item, score in values if item == 1]
    incorrect = [score for item, score in values if item == 0]
    if not correct or not incorrect:
        return None
    scores = [score for _, score in values]
    mean = sum(scores) / len(scores)
    variance = sum((score - mean) ** 2 for score in scores) / len(scores)
    if variance == 0:
        return None
    p = len(correct) / len(values)
    q = 1 - p
    value = ((sum(correct) / len(correct)) - (sum(incorrect) / len(incorrect))) / sqrt(variance) * sqrt(p * q)
    return round(value, 3)


def item_statistics(db: Session, test_id: int) -> list[dict]:
    """Return observed item statistics without changing editorial calibration status."""
    questions = (
        db.query(Question)
        .join(Section, Question.section_id == Section.id)
        .filter(Section.test_id == test_id)
        .order_by(Question.order)
        .all()
    )
    result = []
    for question in questions:
        rows = (
            db.query(AnswerRecord, Attempt)
            .join(Attempt, AnswerRecord.attempt_id == Attempt.id)
            .filter(AnswerRecord.question_id == question.id)
            .all()
        )
        sample_size = len(rows)
        selections = Counter(record.user_answer or "No answer" for record, _ in rows if not record.is_correct)
        # Corrected item-total correlation avoids correlating an item with itself.
        values = [
            (int(record.is_correct), float(attempt.score - int(record.is_correct)))
            for record, attempt in rows
        ]
        result.append({
            "question_id": question.id,
            "order": question.order,
            "sample_size": sample_size,
            "facility": round(sum(value for value, _ in values) / sample_size, 3) if sample_size else None,
            "point_biserial": _point_biserial(values),
            "distractor_selection": dict(selections.most_common()),
            "status": "observed" if sample_size else "no_data",
        })
    return result
