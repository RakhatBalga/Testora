from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.schemas.vocabulary import QuizSubmitIn, SaveWordIn, TrainingIn
from app.application import vocabulary as vocab
from app.domain.models.user import User
from app.infrastructure.config import settings

router = APIRouter()


def _today() -> date:
    """Today in the app timezone (users are in CIS/MENA, not UTC)."""
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()


@router.post("/words", status_code=status.HTTP_201_CREATED)
def save_word(
    payload: SaveWordIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        row = vocab.save_word(
            db,
            user_id=current_user.id,
            word=payload.word,
            context=payload.context,
            source=payload.source,
            source_ref=payload.source_ref,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="Word cannot be empty")
    return vocab.serialize_word(row)


@router.get("/words")
def list_words(
    training: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return vocab.list_words(
        db,
        user_id=current_user.id,
        training_only=training,
        page=page,
        page_size=page_size,
    )


@router.delete("/words/{word_id}")
def delete_word(
    word_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not vocab.delete_word(db, user_id=current_user.id, word_id=word_id):
        raise HTTPException(status_code=404, detail="Word not found")
    return {"deleted": word_id}


@router.post("/words/{word_id}/enrich")
async def enrich_word(
    word_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = await vocab.enrich_word(db, user=current_user, word_id=word_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Word not found")
    return vocab.serialize_word(row)


@router.patch("/words/{word_id}/training")
def set_training(
    word_id: int,
    payload: TrainingIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = vocab.set_training(
        db, user_id=current_user.id, word_id=word_id, training=payload.training
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Word not found")
    return vocab.serialize_word(row)


@router.get("/daily-quiz")
async def daily_quiz(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    quiz = await vocab.get_daily_quiz(db, user=current_user, quiz_date=_today())
    return vocab.public_quiz(quiz)


@router.post("/daily-quiz/submit")
def submit_daily_quiz(
    payload: QuizSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = vocab.grade_daily_quiz(
        db, user_id=current_user.id, quiz_date=_today(), answers=payload.answers
    )
    if result is None:
        raise HTTPException(status_code=404, detail="No quiz has been generated for today")
    return result
