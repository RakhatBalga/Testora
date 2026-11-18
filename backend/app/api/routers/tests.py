from app.domain.publication import is_published
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.application import catalog
from app.domain.models.user import User
from app.api.schemas.test import TestOut, TestDetail

router = APIRouter()

# Compatibility alias for callers of the former catalog helper.
is_catalog_test = is_published


@router.get("", response_model=List[TestOut])
def list_tests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return catalog.list_published_tests(db)


@router.get("/{test_id}", response_model=TestDetail)
def get_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    test = catalog.get_published_test(db, test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.test_type == "listening":
        # Legacy route remains available for old clients, but review-only data
        # must never be exposed before a submission exists.
        return {
            "id": test.id,
            "title": test.title,
            "test_type": test.test_type,
            "description": test.description,
            "duration_minutes": test.duration_minutes,
            "difficulty": test.difficulty,
            "question_count": sum(len(section.questions) for section in test.sections),
            "sections": [
                {
                    "id": section.id,
                    "order": section.order,
                    "title": section.title,
                    "instructions": section.instructions,
                    "passage": None,
                    "audio_url": section.audio_url,
                    "questions": [
                        {
                            "id": question.id,
                            "text": question.text,
                            "question_type": question.question_type,
                            "options": question.options,
                            "order": question.order,
                            "evidence": None,
                        }
                        for question in section.questions
                    ],
                }
                for section in test.sections
            ],
        }
    if catalog.has_attempt(db, current_user.id, test.id):
        # The review highlights evidence; this user has already seen the answers.
        return test
    # Before the first submission the evidence spans would point at the answers.
    # The result payload (`answers[].evidence`) carries them after submitting.
    detail = TestDetail.model_validate(test)
    for section in detail.sections:
        for question in section.questions:
            question.evidence = None
    return detail
