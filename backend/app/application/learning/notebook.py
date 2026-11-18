"""Mistake notebook: Writing mistakes plus wrong Reading/Listening answers.

Writing items come from the `mistakes` table. Their number is bounded by the AI
reviews a user is allowed, and they are de-duplicated against the essay text in
Python. Reading/Listening items come from `answer_records`, which grow with
every free practice test, so they are filtered, counted and cut to the page
in SQL.
"""

from sqlalchemy import String, cast, func, literal_column
from sqlalchemy.orm import Session

from app.application import frontend_routes as routes
from app.domain.scoring import display_answer
from app.domain.models.attempt import AnswerRecord, Attempt
from app.domain.models.learning import MistakeReview
from app.domain.models.mistake import Mistake
from app.domain.models.test import Question, Section, Test
from app.domain.models.writing import WritingSubmission

# A literal, not a bind parameter: PostgreSQL must see the same expression in SELECT and GROUP BY.
_REVIEW_STATUS = func.coalesce(MistakeReview.status, literal_column("'new'"))


def _statuses(db: Session, user_id: int, skill: str) -> dict[tuple[str, int], str]:
    rows = db.query(MistakeReview).filter(MistakeReview.user_id == user_id, MistakeReview.skill == skill).all()
    return {(row.skill, row.source_id): row.status for row in rows}


def _writing_items(db: Session, user_id: int, statuses: dict) -> list[dict]:
    rows = (
        db.query(Mistake, WritingSubmission)
        .join(
            WritingSubmission,
            (WritingSubmission.id == Mistake.submission_id) & (WritingSubmission.user_id == Mistake.user_id),
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
        items.append(
            {
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
                "source_href": routes.result("writing", submission.id),
                "source_title": submission.task.title if submission.task else "Writing result",
                "created_at": mistake.created_at,
            }
        )
    return items


def _wrong_answers(db: Session, user_id: int, skill: str, *entities):
    """Wrong answers of one objective skill, each with its review status."""
    return (
        db.query(*entities)
        .select_from(AnswerRecord)
        .join(Attempt, AnswerRecord.attempt_id == Attempt.id)
        .join(Question, AnswerRecord.question_id == Question.id)
        .join(Section, Question.section_id == Section.id)
        .join(Test, Section.test_id == Test.id)
        .outerjoin(
            MistakeReview,
            (MistakeReview.user_id == user_id)
            & (MistakeReview.skill == skill)
            & (MistakeReview.source_id == AnswerRecord.id),
        )
        .filter(Attempt.user_id == user_id, Test.test_type == skill, AnswerRecord.is_correct.is_(False))
    )


def _answer_counts(db: Session, user_id: int, skill: str) -> dict[str, int]:
    rows = _wrong_answers(db, user_id, skill, _REVIEW_STATUS, func.count(AnswerRecord.id)).group_by(_REVIEW_STATUS)
    return {status: count for status, count in rows.all()}


def _answer_items(db: Session, user_id: int, skill: str, status: str | None, limit: int) -> list[dict]:
    """The first `limit` items of one skill in notebook order.

    The notebook sorts by (created_at, item id) descending and the item id is a
    string ("reading-10" sorts before "reading-9"), so answers of one attempt
    are ordered by their id as text here as well; otherwise the cut could drop
    a row the merged page needs.
    """
    query = _wrong_answers(db, user_id, skill, AnswerRecord, Attempt, Question, Section, Test, _REVIEW_STATUS)
    if status:
        query = query.filter(_REVIEW_STATUS == status)
    rows = query.order_by(Attempt.created_at.desc(), cast(AnswerRecord.id, String).desc()).limit(limit).all()
    items = []
    for record, attempt, question, section, test, review_status in rows:
        category = question.question_type
        if skill == "listening":
            category = (question.question_metadata or {}).get("target_skill", question.question_type)
        items.append(
            {
                "id": f"{skill}-{record.id}",
                "source_id": record.id,
                "skill": skill,
                "status": review_status,
                "category": category,
                "label": category.replace("_", " ").title(),
                "quote": None,
                "user_answer": record.user_answer,
                "correct_answer": display_answer(question.correct_answer),
                "explanation": question.explanation,
                "evidence": [
                    span
                    for span in (question.evidence or [])
                    if isinstance(span, dict)
                    and isinstance(span.get("text"), str)
                    and span["text"] in (section.passage or "")
                ]
                or None,
                "source_href": routes.result(skill, attempt.id),
                "source_title": test.title,
                "created_at": attempt.created_at,
            }
        )
    return items


def list_notebook(
    db: Session,
    user_id: int,
    skill: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    start = (page - 1) * page_size
    needed = start + page_size  # no source can contribute more rows than this to the page
    items = []
    total = 0
    if skill in (None, "writing"):
        writing = _writing_items(db, user_id, _statuses(db, user_id, "writing"))
        if status:
            writing = [item for item in writing if item["status"] == status]
        items.extend(writing)
        total += len(writing)
    for objective in ("reading", "listening"):
        if skill in (None, objective):
            counts = _answer_counts(db, user_id, objective)
            total += counts.get(status, 0) if status else sum(counts.values())
            items.extend(_answer_items(db, user_id, objective, status, needed))
    items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    return {"items": items[start : start + page_size], "total": total, "page": page, "page_size": page_size}


def notebook_summary(db: Session, user_id: int) -> dict:
    """Counts per review status for the dashboard; no notebook items are built for objective skills."""
    counts = {"new": 0, "reviewing": 0, "mastered": 0}
    for item in _writing_items(db, user_id, _statuses(db, user_id, "writing")):
        counts[item["status"]] += 1
    for objective in ("reading", "listening"):
        for status, count in _answer_counts(db, user_id, objective).items():
            counts[status] += count
    return {"total": sum(counts.values()), **counts}


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
