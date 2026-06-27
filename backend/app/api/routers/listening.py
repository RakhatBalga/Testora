from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.schemas.listening import (
    ListeningCatalogItem,
    ListeningProgressIn,
    ListeningProgressOut,
    ListeningReviewOut,
    ListeningSubmitIn,
    ListeningSubmitOut,
    ListeningTestPublic,
)
from app.domain.band import band_from_raw
from app.domain.listening_scoring import grade_listening
from app.domain.models.attempt import AnswerRecord, Attempt, ListeningProgress
from app.domain.models.test import Question, Section, Test
from app.domain.models.user import User
from app.domain.scoring import _display


router = APIRouter()
PUBLIC_SCHEMA = "testora.listening-public.v1"
AUTHORSHIP = "Original IELTS-style practice test created by Testora."


def _metadata(test: Test) -> dict:
    return test.content_metadata or {}


def _is_published(test: Test) -> bool:
    meta = _metadata(test)
    return test.test_type == "listening" and meta.get("published", False) is True


def _catalog_item(test: Test, question_count: int) -> dict:
    meta = _metadata(test)
    return {
        "id": test.id,
        "title": test.title,
        "description": test.description,
        "duration_minutes": test.duration_minutes,
        "difficulty": test.difficulty,
        "question_count": question_count,
        "content_version": test.content_version,
        "calibration_status": meta.get("calibration_status", "draft"),
        "authorship": meta.get("authorship", AUTHORSHIP),
    }


def _public_test(test: Test) -> dict:
    count = sum(len(section.questions) for section in test.sections)
    result = _catalog_item(test, count)
    result.update({
        "schema_version": PUBLIC_SCHEMA,
        "intro_notice": _metadata(test).get("intro_notice", "Audio begins after a five-second pause."),
        "sections": [],
    })
    for section in test.sections:
        section_meta = section.section_metadata or {}
        result["sections"].append({
            "id": section.id,
            "order": section.order,
            "title": section.title,
            "instructions": section.instructions,
            "audio_url": section.audio_url,
            "audio_start": float(section_meta.get("audio_start", 0)),
            "audio_end": float(section_meta.get("audio_end", 0)),
            "map_asset": section_meta.get("map_asset"),
            "questions": [
                {
                    "id": q.id,
                    "order": q.order,
                    "text": q.text,
                    "question_type": q.question_type,
                    "options": q.options,
                    "word_limit": (q.question_metadata or {}).get("word_limit"),
                }
                for q in section.questions
            ],
        })
    return result


def _get_published_test(db: Session, test_id: int) -> Test:
    test = db.query(Test).filter(Test.id == test_id).first()
    if not test or not _is_published(test):
        raise HTTPException(status_code=404, detail="Listening test not found")
    return test


def _submit_response(attempt: Attempt) -> dict:
    return {
        "schema_version": "testora.listening-submit.v1",
        "attempt_id": attempt.id,
        "test_id": attempt.test_id,
        "content_version": attempt.content_version,
        "mode": attempt.mode,
        "score": attempt.score,
        "total": attempt.total,
        "band": attempt.band,
        "accuracy": round(attempt.score / attempt.total * 100) if attempt.total else 0,
        "breakdown": attempt.breakdown or [],
        "created_at": attempt.created_at,
    }


@router.get("/tests", response_model=list[ListeningCatalogItem])
def list_listening_tests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    counts = dict(
        db.query(Section.test_id, func.count(Question.id))
        .join(Question, Question.section_id == Section.id)
        .group_by(Section.test_id)
        .all()
    )
    tests = [test for test in db.query(Test).order_by(Test.id).all() if _is_published(test)]
    return [_catalog_item(test, counts.get(test.id, 0)) for test in tests]


@router.get("/tests/{test_id}", response_model=ListeningTestPublic)
def get_listening_test(
    test_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _public_test(_get_published_test(db, test_id))


@router.get("/tests/{test_id}/progress", response_model=ListeningProgressOut | None)
def get_progress(
    test_id: int,
    content_version: str,
    mode: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_published_test(db, test_id)
    if mode not in {"exam", "practice"}:
        raise HTTPException(status_code=422, detail="Unsupported mode")
    return (
        db.query(ListeningProgress)
        .filter(
            ListeningProgress.user_id == current_user.id,
            ListeningProgress.test_id == test_id,
            ListeningProgress.content_version == content_version,
            ListeningProgress.mode == mode,
        )
        .first()
    )


@router.put("/tests/{test_id}/progress", response_model=ListeningProgressOut)
def save_progress(
    test_id: int,
    payload: ListeningProgressIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    test = _get_published_test(db, test_id)
    if payload.content_version != test.content_version:
        raise HTTPException(status_code=409, detail="Content version changed; restart this test")
    row = (
        db.query(ListeningProgress)
        .filter(
            ListeningProgress.user_id == current_user.id,
            ListeningProgress.test_id == test_id,
            ListeningProgress.content_version == payload.content_version,
            ListeningProgress.mode == payload.mode,
        )
        .first()
    )
    if row is None:
        row = ListeningProgress(
            user_id=current_user.id,
            test_id=test_id,
            content_version=payload.content_version,
            mode=payload.mode,
        )
        db.add(row)
    row.answers = payload.answers
    row.current_section = payload.current_section
    row.audio_position = payload.audio_position
    row.max_audio_position = max(payload.max_audio_position, payload.audio_position)
    row.status = "in_progress"
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


@router.post("/tests/{test_id}/submit", response_model=ListeningSubmitOut, status_code=status.HTTP_201_CREATED)
def submit_listening(
    test_id: int,
    payload: ListeningSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    test = _get_published_test(db, test_id)
    if payload.content_version != test.content_version:
        raise HTTPException(status_code=409, detail="Content version changed; restart this test")
    existing = (
        db.query(Attempt)
        .filter(
            Attempt.user_id == current_user.id,
            Attempt.test_id == test_id,
            Attempt.submission_key == payload.submission_key,
        )
        .first()
    )
    if existing:
        return _submit_response(existing)

    questions = [question for section in test.sections for question in section.questions]
    valid_ids = {question.id for question in questions}
    submitted_ids = [answer.question_id for answer in payload.answers]
    if len(submitted_ids) != len(set(submitted_ids)) or not set(submitted_ids).issubset(valid_ids):
        raise HTTPException(status_code=422, detail="Answers contain duplicate or foreign question IDs")
    answers_map = {answer.question_id: answer.answer for answer in payload.answers}
    review_map = {answer.question_id: answer.marked_for_review for answer in payload.answers}
    graded, score, breakdown = grade_listening(questions, answers_map)
    attempt = Attempt(
        user_id=current_user.id,
        test_id=test.id,
        score=score,
        total=len(questions),
        band=band_from_raw(score, len(questions), "listening"),
        duration_seconds=payload.duration_seconds,
        breakdown=breakdown,
        content_version=test.content_version,
        mode=payload.mode,
        submission_key=payload.submission_key,
    )
    db.add(attempt)
    db.flush()
    for item in graded:
        db.add(AnswerRecord(
            attempt_id=attempt.id,
            question_id=item["question_id"],
            user_answer=item["user_answer"],
            is_correct=item["is_correct"],
            marked_for_review=bool(review_map.get(item["question_id"], False)),
        ))
    db.query(ListeningProgress).filter(
        ListeningProgress.user_id == current_user.id,
        ListeningProgress.test_id == test_id,
        ListeningProgress.content_version == test.content_version,
        ListeningProgress.mode == payload.mode,
    ).update({"status": "submitted"}, synchronize_session=False)
    db.commit()
    db.refresh(attempt)
    return _submit_response(attempt)


def _evidence(question: Question, section: Section) -> list[dict]:
    meta = question.question_metadata or {}
    wanted = str(meta.get("evidence_segment", "")).split(":")
    segments = (section.section_metadata or {}).get("transcript_segments", [])
    selected = [segment for segment in segments if segment.get("id") in wanted]
    if selected:
        return [{
            "segment_id": segment.get("id"),
            "start": segment.get("start"),
            "end": segment.get("end"),
            "quote": segment.get("text", ""),
        } for segment in selected]
    return [{"segment_id": None, "start": None, "end": None, "quote": span.get("text", "")}
            for span in (question.evidence or [])]


@router.get("/attempts/{attempt_id}", response_model=ListeningReviewOut)
def review_listening(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = db.query(Attempt).filter(Attempt.id == attempt_id, Attempt.user_id == current_user.id).first()
    if not attempt or attempt.test.test_type != "listening":
        raise HTTPException(status_code=404, detail="Listening attempt not found")
    section_by_question = {
        question.id: section
        for section in attempt.test.sections
        for question in section.questions
    }
    base = _submit_response(attempt)
    base.update({
        "schema_version": "testora.listening-review.v1",
        "test_title": attempt.test.title,
        "duration_seconds": attempt.duration_seconds,
        "sections": [{
            "id": section.id,
            "order": section.order,
            "title": section.title,
            "transcript_segments": (section.section_metadata or {}).get("transcript_segments", []),
        } for section in attempt.test.sections],
        "answers": [],
    })
    records = sorted(attempt.answers, key=lambda record: record.question.order)
    for record in records:
        question = record.question
        section = section_by_question[question.id]
        base["answers"].append({
            "question_id": question.id,
            "order": question.order,
            "section_order": section.order,
            "text": question.text,
            "question_type": question.question_type,
            "user_answer": record.user_answer,
            "correct_answer": _display(question.correct_answer),
            "is_correct": record.is_correct,
            "explanation": question.explanation,
            "target_skill": (question.question_metadata or {}).get("target_skill"),
            "evidence": _evidence(question, section),
        })
    return base
