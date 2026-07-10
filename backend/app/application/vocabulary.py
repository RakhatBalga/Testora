"""Vocabulary builder use-cases: save highlighted words, enrich them (meaning /
synonyms / better alternatives / native translation), opt words into training,
and generate + grade a daily practice quiz.

AI-backed operations (enrich, quiz generation) offload the blocking model call to
the threadpool and cache the result (enrichment on the word row, quiz by date),
so repeat opens never re-call the model. There is no scheduler — "daily" means
on-demand, date-keyed generation, mirroring the weekly study plan.
"""
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models.user import User
from app.domain.models.vocabulary import DailyWordQuiz, SavedWord
from app.infrastructure.ai.concurrency import offload
from app.infrastructure.ai.factory import get_vocabulary_coach

MAX_WORD_LEN = 80
QUIZ_WORD_POOL = 12   # most-recent training words fed to the quiz generator
QUIZ_QUESTIONS = 8

# correct answer advances a word's mastery; a wrong answer pulls it back to learning
_ADVANCE = {"new": "learning", "learning": "mastered", "mastered": "mastered"}


def serialize_word(word: SavedWord) -> dict:
    return {
        "id": word.id,
        "word": word.word,
        "context": word.context,
        "source": word.source,
        "training": word.training,
        "status": word.status,
        "enrichment": word.enrichment,
        "enriched": word.enrichment is not None,
        "created_at": word.created_at.isoformat() if word.created_at else None,
    }


def save_word(
    db: Session,
    *,
    user_id: int,
    word: str,
    context: str | None = None,
    source: str | None = None,
    source_ref: str | None = None,
) -> SavedWord:
    """Save a word, de-duplicated per user. Re-saving an existing word is a no-op
    (but fills in context if it was missing)."""
    clean = " ".join((word or "").split()).strip()[:MAX_WORD_LEN]
    if not clean:
        raise ValueError("word is empty")

    existing = (
        db.query(SavedWord)
        .filter(SavedWord.user_id == user_id, SavedWord.word == clean)
        .first()
    )
    if existing:
        if context and not existing.context:
            existing.context = context
            db.commit()
            db.refresh(existing)
        return existing

    row = SavedWord(
        user_id=user_id, word=clean, context=context, source=source, source_ref=source_ref
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        # Two concurrent saves of the same word raced past the check above.
        db.rollback()
        return (
            db.query(SavedWord)
            .filter(SavedWord.user_id == user_id, SavedWord.word == clean)
            .first()
        )


def list_words(
    db: Session,
    *,
    user_id: int,
    training_only: bool = False,
    page: int = 1,
    page_size: int = 30,
) -> dict:
    q = db.query(SavedWord).filter(SavedWord.user_id == user_id)
    if training_only:
        q = q.filter(SavedWord.training.is_(True))
    total = q.count()
    items = (
        q.order_by(SavedWord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    training_count = (
        db.query(SavedWord)
        .filter(SavedWord.user_id == user_id, SavedWord.training.is_(True))
        .count()
    )
    return {
        "items": [serialize_word(w) for w in items],
        "total": total,
        "training_count": training_count,
        "page": page,
        "page_size": page_size,
    }


def delete_word(db: Session, *, user_id: int, word_id: int) -> bool:
    row = (
        db.query(SavedWord)
        .filter(SavedWord.id == word_id, SavedWord.user_id == user_id)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def set_training(
    db: Session, *, user_id: int, word_id: int, training: bool
) -> SavedWord | None:
    row = (
        db.query(SavedWord)
        .filter(SavedWord.id == word_id, SavedWord.user_id == user_id)
        .first()
    )
    if not row:
        return None
    row.training = training
    if training and row.status == "new":
        row.status = "learning"
    db.commit()
    db.refresh(row)
    return row


async def enrich_word(
    db: Session, *, user: User, word_id: int, force: bool = False
) -> SavedWord | None:
    """Fill in meaning/synonyms/alternatives/translation via the AI coach, cached
    on the row. Returns the (possibly unchanged) word, or None if not found."""
    row = (
        db.query(SavedWord)
        .filter(SavedWord.id == word_id, SavedWord.user_id == user.id)
        .first()
    )
    if not row:
        return None
    if row.enrichment and not force:
        return row

    coach = get_vocabulary_coach()
    info = await offload(
        coach.enrich_word,
        word=row.word,
        context=row.context,
        native_language=user.native_language,
    )
    if not info.error:
        row.enrichment = info.to_dict()
        row.enriched_at = datetime.utcnow()
        db.commit()
        db.refresh(row)
    return row


async def get_daily_quiz(db: Session, *, user: User, quiz_date: date) -> DailyWordQuiz:
    """Return today's quiz, generating and caching it on first open of the day."""
    existing = (
        db.query(DailyWordQuiz)
        .filter(DailyWordQuiz.user_id == user.id, DailyWordQuiz.quiz_date == quiz_date)
        .first()
    )
    if existing:
        return existing

    words = (
        db.query(SavedWord)
        .filter(SavedWord.user_id == user.id, SavedWord.training.is_(True))
        .order_by(SavedWord.created_at.desc())
        .limit(QUIZ_WORD_POOL)
        .all()
    )
    if not words:
        # Nothing explicitly marked for training — fall back to recent saves so the
        # user still gets practice.
        words = (
            db.query(SavedWord)
            .filter(SavedWord.user_id == user.id)
            .order_by(SavedWord.created_at.desc())
            .limit(QUIZ_WORD_POOL)
            .all()
        )

    payload_words = [
        {"word": w.word, "context": w.context, **(w.enrichment or {})} for w in words
    ]
    quiz = await offload(
        get_vocabulary_coach().generate_quiz,
        words=payload_words,
        native_language=user.native_language,
        num_questions=min(QUIZ_QUESTIONS, max(1, len(words))),
    )
    payload = {"questions": [q.to_dict() for q in quiz.questions]}
    row = DailyWordQuiz(
        user_id=user.id, quiz_date=quiz_date, payload=payload, total=len(quiz.questions)
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
        return row
    except IntegrityError:
        db.rollback()
        return (
            db.query(DailyWordQuiz)
            .filter(
                DailyWordQuiz.user_id == user.id, DailyWordQuiz.quiz_date == quiz_date
            )
            .first()
        )


def public_quiz(quiz: DailyWordQuiz) -> dict:
    """Quiz shape sent to the client — correct answers stripped out."""
    questions = (quiz.payload or {}).get("questions", [])
    return {
        "quiz_date": quiz.quiz_date.isoformat() if quiz.quiz_date else None,
        "completed": quiz.completed,
        "score": quiz.score,
        "total": quiz.total if quiz.total is not None else len(questions),
        "questions": [
            {
                "word": q.get("word"),
                "prompt": q.get("prompt"),
                "kind": q.get("kind"),
                "options": q.get("options", []),
            }
            for q in questions
        ],
    }


def grade_daily_quiz(
    db: Session, *, user_id: int, quiz_date: date, answers: list[int | None]
) -> dict | None:
    row = (
        db.query(DailyWordQuiz)
        .filter(DailyWordQuiz.user_id == user_id, DailyWordQuiz.quiz_date == quiz_date)
        .first()
    )
    if not row:
        return None

    questions = (row.payload or {}).get("questions", [])
    results = []
    correct = 0
    for i, q in enumerate(questions):
        chosen = answers[i] if i < len(answers) else None
        is_correct = chosen is not None and chosen == q.get("answer_index")
        if is_correct:
            correct += 1
        results.append(
            {
                "word": q.get("word"),
                "prompt": q.get("prompt"),
                "options": q.get("options", []),
                "answer_index": q.get("answer_index"),
                "your_answer": chosen,
                "correct": is_correct,
                "explanation": q.get("explanation", ""),
            }
        )
        word_row = (
            db.query(SavedWord)
            .filter(SavedWord.user_id == user_id, SavedWord.word == q.get("word"))
            .first()
        )
        if word_row:
            if is_correct:
                word_row.status = _ADVANCE.get(word_row.status, "learning")
            elif word_row.status != "new":
                word_row.status = "learning"

    row.completed = True
    row.score = correct
    row.total = len(questions)
    db.commit()
    return {"score": correct, "total": len(questions), "results": results}
