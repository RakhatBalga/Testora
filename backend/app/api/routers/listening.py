from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, user_rate_limit
from app.api.schemas.listening import (
    ListeningCatalogItem,
    ListeningProgressIn,
    ListeningProgressOut,
    ListeningReviewOut,
    ListeningSubmitIn,
    ListeningSubmitOut,
    ListeningTestPublic,
)
from app.application.listening import service
from app.domain.models.user import User

router = APIRouter()


@router.get("/tests", response_model=list[ListeningCatalogItem])
def list_listening_tests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.list_catalog(db)


@router.get("/tests/{test_id}", response_model=ListeningTestPublic)
def get_listening_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.public_test(db, test_id)


@router.get("/tests/{test_id}/progress", response_model=ListeningProgressOut | None)
def get_progress(
    test_id: int,
    content_version: str,
    mode: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_progress(db, current_user, test_id, content_version, mode)


@router.put(
    "/tests/{test_id}/progress",
    response_model=ListeningProgressOut,
    dependencies=[Depends(user_rate_limit("listening-progress", 120))],
)
def save_progress(
    test_id: int,
    payload: ListeningProgressIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.save_progress(db, current_user, test_id, payload)


@router.post(
    "/tests/{test_id}/submit",
    response_model=ListeningSubmitOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(user_rate_limit("listening-submit", 20))],
)
def submit_listening(
    test_id: int,
    payload: ListeningSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.submit(db, current_user, test_id, payload)


@router.get("/attempts/{attempt_id}", response_model=ListeningReviewOut)
def review_listening(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.review(db, current_user, attempt_id)
