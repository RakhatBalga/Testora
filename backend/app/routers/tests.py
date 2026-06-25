from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.test import Test, Section, Question
from app.models.user import User
from app.schemas.test import TestOut, TestDetail

router = APIRouter()


@router.get("", response_model=List[TestOut])
def list_tests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # One grouped query for question counts, so the library can show "N questions"
    # without an N+1 fetch of every test's sections.
    counts = dict(
        db.query(Section.test_id, func.count(Question.id))
        .join(Question, Question.section_id == Section.id)
        .group_by(Section.test_id)
        .all()
    )
    tests = db.query(Test).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "test_type": t.test_type,
            "description": t.description,
            "duration_minutes": t.duration_minutes,
            "difficulty": t.difficulty,
            "question_count": counts.get(t.id, 0),
        }
        for t in tests
    ]


@router.get("/{test_id}", response_model=TestDetail)
def get_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test
