from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.domain.models.attempt import AnswerRecord, Attempt, ListeningProgress
from app.domain.models.test import Test as ContentTest, Section, Question
from app.domain.models.user import User
from app.infrastructure.database import Base
from ml.data import ResponseRecord, read_jsonl
from ml.evaluate_adaptive import evaluate
from ml.export_responses import date_filter, export_records, write_export

SECRET = "synthetic-test-secret-32-bytes-long"
START = datetime(2026, 10, 1)


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(id=17, username="private-name", email="private@example.test", password="private-password")
        session.add(user)
        for i, skill in enumerate(["reading", "listening", "writing"], start=1):
            test = ContentTest(id=i, title="Test", test_type=skill, content_version="current-v2")
            section = Section(id=i, test=test, title="Section")
            question = Question(
                id=i,
                section=section,
                text="private question text",
                correct_answer=["secret answer"],
                question_type="short_answer",
            )
            session.add_all([test, section, question])
            for j in range(3):
                attempt = Attempt(
                    user_id=user.id,
                    test=test,
                    content_version="legacy" if skill == "reading" else "v1",
                    mode="practice" if j == 1 else "exam",
                    created_at=START + timedelta(days=j),
                )
                session.add(attempt)
                session.flush()
                session.add(
                    AnswerRecord(
                        attempt=attempt,
                        question=question,
                        user_answer="private response" if j else None,
                        is_correct=j == 1,
                    )
                )
        session.add(
            ListeningProgress(
                user_id=17, test_id=2, content_version="v1", mode="practice", answers={"2": "unsent answer"}
            )
        )
        session.commit()
        yield session
    engine.dispose()


def test_export_is_read_only_pseudonymous_and_keeps_submission_versions(db):
    statements = []

    def capture(_connection, _cursor, statement, *_args):
        statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", capture)
    records, report = export_records(db, secret=SECRET)
    event.remove(db.bind, "before_cursor_execute", capture)
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    assert len(records) == 6  # No Writing and no unsent Listening progress.
    assert report["legacy_record_count"] == 3
    assert report["records_by_skill"] == {"reading": 3, "listening": 3}
    assert len({record.learner_id for record in records}) == 1
    assert len({record.response_id for record in records}) == 6
    assert records[0].answered_at == START.replace(tzinfo=timezone.utc)
    assert records[0].correct is False  # Unanswered is retained as scored.
    assert {r.content_version for r in records} == {"legacy", "v1"}
    text = "\n".join(r.model_dump_json() for r in records)
    for private in (
        "private-name",
        "private@example.test",
        "private-password",
        "private response",
        "private question text",
        "secret answer",
        "unsent answer",
    ):
        assert private not in text
    assert '"learner_id":"17"' not in text
    assert export_records(db, secret=SECRET)[0] == records
    different = export_records(db, secret="different-synthetic-secret-32-bytes")[0]
    assert different[0].learner_id != records[0].learner_id


def test_filters_are_explicit_and_end_is_exclusive(db):
    records, _ = export_records(
        db,
        secret=SECRET,
        skill="listening",
        mode="practice",
        since=datetime(2026, 10, 2, tzinfo=timezone.utc),
        until=datetime(2026, 10, 3, tzinfo=timezone.utc),
    )
    assert len(records) == 1
    assert records[0].correct is True
    assert len(export_records(db, secret=SECRET, exclude_legacy=True)[0]) == 3
    with pytest.raises(ValueError, match="timezone"):
        export_records(db, secret=SECRET, since=START)
    with pytest.raises(ValueError, match="precede"):
        export_records(
            db, secret=SECRET, since=date_filter("2026-10-03T00:00:00Z"), until=date_filter("2026-10-02T00:00:00Z")
        )
    with pytest.raises(ValueError, match="32"):
        export_records(db, secret="short")


def test_export_roundtrips_into_existing_evaluator_and_keeps_database_unchanged(db, tmp_path):
    # Add independent learners so the first-response dataset can be split.
    for i in range(4):
        user = User(username=f"synthetic-{i}", password="hash")
        db.add(user)
        db.flush()
        attempt = Attempt(user_id=user.id, test_id=2, content_version="v1", created_at=START + timedelta(days=4 + i))
        db.add(attempt)
        db.flush()
        db.add(AnswerRecord(attempt=attempt, question_id=2, is_correct=bool(i % 2)))
    db.commit()
    before = db.execute(select(AnswerRecord.id, AnswerRecord.is_correct)).all()
    records, metadata = export_records(db, secret=SECRET)
    output = tmp_path / "responses.jsonl"
    report = write_export(output, records, metadata)
    loaded = read_jsonl(output, ResponseRecord)
    assert loaded == records
    assert report["dataset_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert json.loads((tmp_path / "responses.jsonl.meta.json").read_text())["record_count"] == 10
    result = evaluate(loaded, train_fraction=0.5)
    assert result["excluded_repeated_responses"] == 4
    assert result["train_count"] + result["test_count"] == 6
    assert db.execute(select(AnswerRecord.id, AnswerRecord.is_correct)).all() == before
    original = output.read_bytes()
    with pytest.raises(FileExistsError):
        write_export(output, records, metadata)
    assert output.read_bytes() == original


def test_empty_export_does_not_create_files(tmp_path):
    output = tmp_path / "empty.jsonl"
    with pytest.raises(ValueError, match="No matching"):
        write_export(output, [], {})
    assert not output.exists()


def test_foreign_question_stops_export(db):
    answer = db.scalars(select(AnswerRecord).order_by(AnswerRecord.id)).first()
    answer.question_id = 2
    db.commit()
    with pytest.raises(ValueError, match="another test"):
        export_records(db, secret=SECRET)


def test_cli_writes_compatible_files_without_printing_secret(db, tmp_path, monkeypatch, capsys):
    from app.infrastructure import database
    from ml.export_responses import main

    output = tmp_path / "cli.jsonl"
    monkeypatch.setenv("ML_EXPORT_KEY", SECRET)
    monkeypatch.setattr(database, "SessionLocal", lambda: db)
    monkeypatch.setattr("sys.argv", ["export_responses", "--output", str(output), "--skill", "listening"])
    main()
    printed = capsys.readouterr().out
    assert SECRET not in printed
    assert json.loads(printed)["record_count"] == 3
    assert all(row.skill == "listening" for row in read_jsonl(output, ResponseRecord))
