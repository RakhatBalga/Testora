from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.test import Test, Question
from app.models.attempt import Attempt, AnswerRecord
from app.models.user import User
from app.schemas.result import SubmitIn, AttemptResult, AttemptSummary
from app.services.scoring import grade_attempt

router = APIRouter()


@router.post("/submit", response_model=AttemptResult)
def submit_attempt(
    payload: SubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    test = db.query(Test).filter(Test.id == payload.test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    questions = db.query(Question).filter(Question.test_id == test.id).all()
    answers_map = {a.question_id: a.answer for a in payload.answers}

    graded, score = grade_attempt(questions, answers_map)

    attempt = Attempt(
        user_id=current_user.id,
        test_id=test.id,
        score=score,
        total=len(questions),
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
            )
        )
    db.commit()

    return {
        "id": attempt.id,
        "test_id": test.id,
        "test_title": test.title,
        "score": score,
        "total": len(questions),
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
            "score": a.score,
            "total": a.total,
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

    answers = []
    for record in attempt.answers:
        answers.append(
            {
                "question_id": record.question_id,
                "text": record.question.text,
                "user_answer": record.user_answer,
                "correct_answer": record.question.correct_answer,
                "is_correct": record.is_correct,
            }
        )

    return {
        "id": attempt.id,
        "test_id": attempt.test_id,
        "test_title": attempt.test.title,
        "score": attempt.score,
        "total": attempt.total,
        "created_at": attempt.created_at,
        "answers": answers,
    }
