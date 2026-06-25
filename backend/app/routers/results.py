from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.test import Test, Section, Question
from app.models.attempt import Attempt, AnswerRecord
from app.models.user import User
from app.schemas.result import SubmitIn, AttemptResult, AttemptSummary
from app.services.scoring import grade_attempt, build_breakdown, _display
from app.services.band import band_from_raw

router = APIRouter()


def _accuracy(correct: int, total: int) -> int:
    return round(correct / total * 100) if total else 0


@router.post("/submit", response_model=AttemptResult)
def submit_attempt(
    payload: SubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    test = db.query(Test).filter(Test.id == payload.test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    questions = (
        db.query(Question)
        .join(Section, Question.section_id == Section.id)
        .filter(Section.test_id == test.id)
        .all()
    )
    answers_map = {a.question_id: a.answer for a in payload.answers}
    review_map = {a.question_id: a.marked_for_review for a in payload.answers}

    graded, score = grade_attempt(questions, answers_map)
    total = len(questions)
    band = band_from_raw(score, total, test.test_type)
    breakdown = build_breakdown(graded)

    attempt = Attempt(
        user_id=current_user.id,
        test_id=test.id,
        score=score,
        total=total,
        band=band,
        duration_seconds=payload.duration_seconds,
        breakdown=breakdown,
    )
    db.add(attempt)
    db.flush()  # assigns attempt.id before we create answer records

    for item in graded:
        db.add(
            AnswerRecord(
                attempt_id=attempt.id,
                question_id=item["question_id"],
                user_answer=item["user_answer"],
                is_correct=item["is_correct"],
                marked_for_review=bool(review_map.get(item["question_id"], False)),
            )
        )
    db.commit()

    for item in graded:
        item["marked_for_review"] = bool(review_map.get(item["question_id"], False))

    return {
        "id": attempt.id,
        "test_id": test.id,
        "test_title": test.title,
        "test_type": test.test_type,
        "score": score,
        "total": total,
        "band": band,
        "correct": score,
        "incorrect": total - score,
        "accuracy": _accuracy(score, total),
        "duration_seconds": payload.duration_seconds,
        "breakdown": breakdown,
        "created_at": attempt.created_at,
        "answers": graded,
    }


@router.get("", response_model=List[AttemptSummary])
def list_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempts = (
        db.query(Attempt)
        .filter(Attempt.user_id == current_user.id)
        .order_by(Attempt.created_at.desc())
        .all()
    )
    return [
        {
            "id": a.id,
            "test_id": a.test_id,
            "test_title": a.test.title,
            "test_type": a.test.test_type,
            "score": a.score,
            "total": a.total,
            "band": a.band,
            "created_at": a.created_at,
        }
        for a in attempts
    ]


@router.get("/{attempt_id}", response_model=AttemptResult)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = (
        db.query(Attempt)
        .filter(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
        .first()
    )
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")

    answers = [
        {
            "question_id": record.question_id,
            "text": record.question.text,
            "question_type": record.question.question_type,
            "user_answer": record.user_answer,
            "correct_answer": _display(record.question.correct_answer),
            "is_correct": record.is_correct,
            "marked_for_review": bool(record.marked_for_review),
            "explanation": record.question.explanation,
        }
        for record in attempt.answers
    ]

    # Older attempts have no stored breakdown — rebuild it from the answers so the
    # result screen is consistent regardless of when the attempt was taken.
    breakdown = attempt.breakdown or build_breakdown(
        [{"question_type": a["question_type"], "is_correct": a["is_correct"]} for a in answers]
    )

    return {
        "id": attempt.id,
        "test_id": attempt.test_id,
        "test_title": attempt.test.title,
        "test_type": attempt.test.test_type,
        "score": attempt.score,
        "total": attempt.total,
        "band": attempt.band,
        "correct": attempt.score,
        "incorrect": attempt.total - attempt.score,
        "accuracy": _accuracy(attempt.score, attempt.total),
        "duration_seconds": attempt.duration_seconds,
        "breakdown": breakdown,
        "created_at": attempt.created_at,
        "answers": answers,
    }
