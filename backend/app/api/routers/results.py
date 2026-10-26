from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user, user_rate_limit
from app.application import attempts
from app.domain.models.user import User
from app.api.schemas.result import SubmitIn, AttemptResult, AttemptSummary

router = APIRouter()


@router.post(
    "/submit",
    response_model=AttemptResult,
    dependencies=[Depends(user_rate_limit("results-submit", 20))],
)
def submit_attempt(
    payload: SubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return attempts.submit_reading(db, current_user, payload)


@router.get("", response_model=List[AttemptSummary])
def list_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return attempts.list_attempts(db, current_user)


@router.get("/{attempt_id}", response_model=AttemptResult)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return attempts.get_attempt_result(db, current_user, attempt_id)
