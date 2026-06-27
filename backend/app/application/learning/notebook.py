from sqlalchemy.orm import Session

from app.domain.models.attempt import AnswerRecord, Attempt
from app.domain.models.learning import MistakeReview
from app.domain.models.mistake import Mistake
from app.domain.models.test import Question, Section, Test
from app.domain.models.writing import WritingSubmission


def _statuses(db: Session, user_id: int) -> dict[tuple[str, int], str]:
    rows = db.query(MistakeReview).filter(MistakeReview.user_id == user_id).all()
    return {(row.skill, row.source_id): row.status for row in rows}


def _writing_items(db: Session, user_id: int, statuses: dict) -> list[dict]:
    rows = (
        db.query(Mistake, WritingSubmission)
        .join(
            WritingSubmission,
            (WritingSubmission.id == Mistake.submission_id)
            & (WritingSubmission.user_id == Mistake.user_id),
        )
        .filter(Mistake.user_id == user_id, Mistake.skill == "writing")
        .order_by(Mistake.created_at.desc(), Mistake.id.desc())
        .all()
    )
    items = []
    seen: set[tuple] = set()
    for mistake, submission in rows:
        quote = (mistake.snippet or "").strip()
        if quote and quote not in submission.text:
            quote = ""
        dedupe_key = (submission.id, mistake.category, mistake.subskill, quote, mistake.correction)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        items.append({
            "id": f"writing-{mistake.id}",
            "source_id": mistake.id,
            "skill": "writing",
            "status": statuses.get(("writing", mistake.id), "new"),
            "category": mistake.category,
            "label": (mistake.subskill or mistake.category).replace("_", " ").title(),
            "quote": quote or None,
            "user_answer": None,
            "correct_answer": mistake.correction,
            "explanation": mistake.explanation,
            "evidence": None,
            "source_href": f"/writing/result/{submission.id}",
            "source_title": submission.task.title if submission.task else "Writing result",
            "created_at": mistake.created_at,
        })
    return items


def _display_answer(value) -> str:
    values = value if isinstance(value, list) else [value]
    return ", ".join(str(item) for item in values if item is not None)


def _reading_items(db: Session, user_id: int, statuses: dict) -> list[dict]:
    rows = (
        db.query(AnswerRecord, Attempt, Question, Section, Test)
        .join(Attempt, AnswerRecord.attempt_id == Attempt.id)
        .join(Question, AnswerRecord.question_id == Question.id)
        .join(Section, Question.section_id == Section.id)
        .join(Test, Section.test_id == Test.id)
        .filter(Attempt.user_id == user_id, Test.test_type == "reading", AnswerRecord.is_correct.is_(False))
        .order_by(Attempt.created_at.desc(), AnswerRecord.id.desc())
        .all()
    )
    return [
        {
            "id": f"reading-{record.id}",
            "source_id": record.id,
            "skill": "reading",
            "status": statuses.get(("reading", record.id), "new"),
            "category": question.question_type,
            "label": question.question_type.replace("_", " ").title(),
            "quote": None,
            "user_answer": record.user_answer,
            "correct_answer": _display_answer(question.correct_answer),
            "explanation": question.explanation,
            "evidence": [
                span
                for span in (question.evidence or [])
                if isinstance(span, dict)
                and isinstance(span.get("text"), str)
                and span["text"] in (section.passage or "")
            ] or None,
            "source_href": f"/reading/{attempt.test_id}?attempt={attempt.id}",
            "source_title": test.title,
            "created_at": attempt.created_at,
        }
        for record, attempt, question, section, test in rows
    ]


def _listening_items(db: Session, user_id: int, statuses: dict) -> list[dict]:
    rows = (
        db.query(AnswerRecord, Attempt, Question, Section, Test)
        .join(Attempt, AnswerRecord.attempt_id == Attempt.id)
        .join(Question, AnswerRecord.question_id == Question.id)
        .join(Section, Question.section_id == Section.id)
        .join(Test, Section.test_id == Test.id)
        .filter(Attempt.user_id == user_id, Test.test_type == "listening", AnswerRecord.is_correct.is_(False))
        .order_by(Attempt.created_at.desc(), AnswerRecord.id.desc())
        .all()
    )
    return [
        {
            "id": f"listening-{record.id}",
            "source_id": record.id,
            "skill": "listening",
            "status": statuses.get(("listening", record.id), "new"),
            "category": (question.question_metadata or {}).get("target_skill", question.question_type),
            "label": (question.question_metadata or {}).get("target_skill", question.question_type).replace("_", " ").title(),
            "quote": None,
            "user_answer": record.user_answer,
            "correct_answer": _display_answer(question.correct_answer),
            "explanation": question.explanation,
            "evidence": [
                span for span in (question.evidence or [])
                if isinstance(span, dict) and isinstance(span.get("text"), str)
                and span["text"] in (section.passage or "")
            ] or None,
            "source_href": f"/listening/result/{attempt.id}",
            "source_title": test.title,
            "created_at": attempt.created_at,
        }
        for record, attempt, question, section, test in rows
    ]


def list_notebook(
    db: Session,
    user_id: int,
    skill: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    statuses = _statuses(db, user_id)
    items = []
    if skill in (None, "writing"):
        items.extend(_writing_items(db, user_id, statuses))
    if skill in (None, "reading"):
        items.extend(_reading_items(db, user_id, statuses))
    if skill in (None, "listening"):
        items.extend(_listening_items(db, user_id, statuses))
    if status:
        items = [item for item in items if item["status"] == status]
    items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start : start + page_size], "total": total, "page": page, "page_size": page_size}


def notebook_summary(db: Session, user_id: int) -> dict:
    result = list_notebook(db, user_id, page_size=100000)
    counts = {"new": 0, "reviewing": 0, "mastered": 0}
    for item in result["items"]:
        counts[item["status"]] += 1
    return {"total": result["total"], **counts}


def set_mistake_status(db: Session, user_id: int, skill: str, source_id: int, status: str) -> bool:
    if skill == "writing":
        owned = (
            db.query(Mistake)
            .filter(Mistake.id == source_id, Mistake.user_id == user_id, Mistake.skill == "writing")
            .first()
        )
    else:
        test_type = "listening" if skill == "listening" else "reading"
        owned = (
            db.query(AnswerRecord)
            .join(Attempt, AnswerRecord.attempt_id == Attempt.id)
            .join(Question, AnswerRecord.question_id == Question.id)
            .join(Section, Question.section_id == Section.id)
            .join(Test, Section.test_id == Test.id)
            .filter(
                AnswerRecord.id == source_id,
                Attempt.user_id == user_id,
                Test.test_type == test_type,
                AnswerRecord.is_correct.is_(False),
            )
            .first()
        )
    if not owned:
        return False
    row = (
        db.query(MistakeReview)
        .filter(
            MistakeReview.user_id == user_id,
            MistakeReview.skill == skill,
            MistakeReview.source_id == source_id,
        )
        .first()
    )
    if row is None:
        row = MistakeReview(user_id=user_id, skill=skill, source_id=source_id)
        db.add(row)
    row.status = status
    db.commit()
    return True
