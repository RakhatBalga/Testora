"""Reading/Listening attempts: grading persistence shared by both skills."""

import threading
from datetime import timedelta
from typing import Callable

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.band import band_from_raw
from app.domain.models.attempt import AnswerRecord, Attempt
from app.domain.models.test import Question, Section, Test
from app.domain.models.user import User
from app.domain.scoring import build_breakdown, display_answer, grade_attempt
from app.infrastructure.time import utcnow

# A repeated identical submit inside this window is the same click, not a retake.
_DUPLICATE_WINDOW = timedelta(seconds=90)
_save_lock = threading.Lock()


def accuracy(correct: int, total: int) -> int:
    return round(correct / total * 100) if total else 0


def find_attempt_by_key(db: Session, user_id: int, test_id: int, key: str | None) -> Attempt | None:
    if not key:
        return None
    return (
        db.query(Attempt)
        .filter(Attempt.user_id == user_id, Attempt.test_id == test_id, Attempt.submission_key == key)
        .first()
    )


def _find_recent_duplicate(db: Session, user_id: int, test_id: int, answers: dict[int, str | None]):
    recent = (
        db.query(Attempt)
        .filter(
            Attempt.user_id == user_id, Attempt.test_id == test_id, Attempt.created_at > utcnow() - _DUPLICATE_WINDOW
        )
        .order_by(Attempt.id.desc())
        .all()
    )
    for attempt in recent:
        stored = {r.question_id: r.user_answer for r in attempt.answers}
        if stored == answers:
            return attempt
    return None


def save_graded_attempt(
    db: Session,
    user: User,
    test: Test,
    *,
    graded: list[dict],
    score: int,
    total: int,
    breakdown: list[dict],
    review_map: dict[int, bool],
    duration_seconds: int | None,
    content_version: str = "legacy",
    mode: str = "exam",
    submission_key: str | None = None,
    before_commit: Callable[[], None] | None = None,
) -> tuple[Attempt, bool]:
    """Persist an attempt and its answers. Returns (attempt, created).

    Idempotent: a repeated submission key (or, without a key, an identical
    submission seconds later) returns the original attempt instead of creating
    a second one or failing on the unique constraint.
    """
    answers = {item["question_id"]: item["user_answer"] for item in graded}
    with _save_lock:
        existing = find_attempt_by_key(db, user.id, test.id, submission_key) or (
            None if submission_key else _find_recent_duplicate(db, user.id, test.id, answers)
        )
        if existing is not None:
            return existing, False
        attempt = Attempt(
            user_id=user.id,
            test_id=test.id,
            score=score,
            total=total,
            band=band_from_raw(score, total, test.test_type),
            duration_seconds=duration_seconds,
            breakdown=breakdown,
            content_version=content_version,
            mode=mode,
            submission_key=submission_key,
        )
        try:
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
            if before_commit is not None:
                before_commit()
            db.commit()
        except IntegrityError:
            # Same key from another worker won the race: return its attempt.
            db.rollback()
            existing = find_attempt_by_key(db, user.id, test.id, submission_key)
            if existing is None:
                raise
            return existing, False
    db.refresh(attempt)
    return attempt, True


def submit_reading(db: Session, user: User, payload) -> dict:
    test = db.query(Test).filter(Test.id == payload.test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    if test.test_type == "listening" and (test.content_metadata or {}).get("published") is True:
        raise HTTPException(
            status_code=409,
            detail="Use the versioned Listening submission endpoint for this test",
        )
    questions = (
        db.query(Question).join(Section, Question.section_id == Section.id).filter(Section.test_id == test.id).all()
    )
    answers_map = {a.question_id: a.answer for a in payload.answers}
    review_map = {a.question_id: a.marked_for_review for a in payload.answers}

    graded, score = grade_attempt(questions, answers_map)
    attempt, created = save_graded_attempt(
        db,
        user,
        test,
        graded=graded,
        score=score,
        total=len(questions),
        breakdown=build_breakdown(graded),
        review_map=review_map,
        duration_seconds=payload.duration_seconds,
        submission_key=payload.submission_key,
    )
    if not created:
        return attempt_result(attempt)
    for item in graded:
        item["marked_for_review"] = bool(review_map.get(item["question_id"], False))
    return {**_attempt_header(attempt), "answers": graded}


def _attempt_header(attempt: Attempt) -> dict:
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
        "accuracy": accuracy(attempt.score, attempt.total),
        "duration_seconds": attempt.duration_seconds,
        "breakdown": attempt.breakdown or [],
        "created_at": attempt.created_at,
    }


def attempt_result(attempt: Attempt) -> dict:
    answers = [
        {
            "question_id": record.question_id,
            "text": record.question.text,
            "question_type": record.question.question_type,
            "user_answer": record.user_answer,
            "correct_answer": display_answer(record.question.correct_answer),
            "is_correct": record.is_correct,
            "marked_for_review": bool(record.marked_for_review),
            "explanation": record.question.explanation,
        }
        for record in attempt.answers
    ]
    header = _attempt_header(attempt)
    # Older attempts have no stored breakdown: rebuild it from the answers so the
    # result screen is consistent regardless of when the attempt was taken.
    header["breakdown"] = attempt.breakdown or build_breakdown(
        [{"question_type": a["question_type"], "is_correct": a["is_correct"]} for a in answers]
    )
    return {**header, "answers": answers}


def list_attempts(db: Session, user: User) -> list[dict]:
    attempts = db.query(Attempt).filter(Attempt.user_id == user.id).order_by(Attempt.created_at.desc()).all()
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


def get_attempt_result(db: Session, user: User, attempt_id: int) -> dict:
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id, Attempt.user_id == user.id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Attempt not found")
    return attempt_result(attempt)
