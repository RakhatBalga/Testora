"""Core coach math: recency decay, recurring window, band gap, streak, timezone."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.analytics import streak as streak_module
from app.application.analytics.band_gap import compute_band_gap
from app.application.analytics.streak import compute_streak
from app.application.analytics.weakness import (
    HALF_LIFE_DAYS,
    compute_recurring_mistakes,
    compute_weaknesses,
    recency_decay,
)
from app.domain.band import band_from_raw, round_ielts
from app.domain.models.attempt import Attempt
from app.domain.models.mistake import Mistake
from app.domain.models.test import Test as ContentTest
from app.domain.models.user import User
from app.domain.models.writing import WritingSubmission, WritingTask
from app.infrastructure import time as time_module
from app.infrastructure.config import settings
from app.infrastructure.database import Base
from app.infrastructure.time import local_today, to_local_date, utcnow


@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    user = User(username="student", password="hashed")
    task = WritingTask(task_type=2, title="Essay", prompt="Discuss.", min_words=250, duration_minutes=40)
    session.add_all([user, task])
    session.commit()
    session.info["user_id"] = user.id
    session.info["task_id"] = task.id
    try:
        yield session
    finally:
        session.close()


def _essay(db, *, age_days=0.0, band=6.5, status="graded"):
    sub = WritingSubmission(
        user_id=db.info["user_id"], task_id=db.info["task_id"], text="x", word_count=1,
        status=status, band=band, created_at=utcnow() - timedelta(days=age_days),
    )
    db.add(sub)
    db.commit()
    return sub


def _mistake(db, sub, subskill="articles", age_days=0.0):
    db.add(Mistake(user_id=db.info["user_id"], submission_id=sub.id, skill="writing", category="grammar",
                   subskill=subskill, severity=2, created_at=utcnow() - timedelta(days=age_days)))
    db.commit()


def test_recency_decay_halves_every_fourteen_days():
    assert HALF_LIFE_DAYS == 14
    assert recency_decay(0) == 1.0
    assert recency_decay(14) == pytest.approx(0.5)
    assert recency_decay(28) == pytest.approx(0.25)
    assert recency_decay(-3) == 1.0  # clock skew never boosts a mistake


def test_old_mistake_scores_lower_than_fresh_one(db):
    old = _essay(db, age_days=28)
    fresh = _essay(db, age_days=0)
    _mistake(db, old, "articles", age_days=28)
    _mistake(db, fresh, "spelling", age_days=0)
    scores = {w["subskill"]: w["score"] for w in compute_weaknesses(db, db.info["user_id"])}
    assert scores["spelling"] > scores["articles"]


def test_recurring_needs_three_of_the_recent_window(db):
    # Articles in 3 old essays, then 8 clean recent essays: not recurring any more.
    for age in (200, 190, 180):
        _mistake(db, _essay(db, age_days=age), age_days=age)
    for age in range(8):
        _essay(db, age_days=age)
    weak = compute_weaknesses(db, db.info["user_id"])[0]
    assert weak["frequency"] == 3          # all-time count is still reported
    assert weak["recent_frequency"] == 0
    assert weak["recurring"] is False
    assert compute_recurring_mistakes(db, db.info["user_id"]) == []


def test_recurring_flag_matches_recurring_mistakes_widget(db):
    for age in (3, 2, 1):
        _mistake(db, _essay(db, age_days=age), age_days=age)
    weak = compute_weaknesses(db, db.info["user_id"])[0]
    assert weak["recurring"] is True and weak["recent_frequency"] == 3
    assert [r["subskill"] for r in compute_recurring_mistakes(db, db.info["user_id"])] == ["articles"]


def test_failed_and_pending_essays_are_not_opportunities(db):
    _essay(db, status="failed", band=None)
    _essay(db, status="pending", band=None)
    _essay(db, band=0.0)  # pre-check rejection
    sub = _essay(db)
    _mistake(db, sub)
    from app.application.analytics.sources import opportunities

    assert opportunities(db, db.info["user_id"])["writing"] == 1


def test_band_gap_rounds_half_up_and_handles_no_data(db):
    empty = compute_band_gap(db, db.info["user_id"], target=7.5)
    assert empty == {"current": None, "target": 7.5, "gap": None, "per_skill": {},
                     "lowest_skill": None, "has_data": False}
    _essay(db, band=6.5)
    listening = ContentTest(title="L", test_type="listening", duration_minutes=30)
    db.add(listening)
    db.commit()
    db.add(Attempt(user_id=db.info["user_id"], test_id=listening.id, score=30, total=40, band=6.0))
    db.commit()
    gap = compute_band_gap(db, db.info["user_id"], target=7.5)
    assert gap["current"] == 6.5  # mean 6.25 -> 6.5, not banker's 6.0
    assert gap["gap"] == 1.0 and gap["lowest_skill"] == "listening"


def test_raw_score_to_band_rounds_half_up():
    # 9/16 -> 22.5 of 40 -> 23 -> Band 6.0 (banker's rounding gave 22 -> 5.5)
    assert band_from_raw(9, 16, "reading") == 6.0
    assert band_from_raw(0, 0, "reading") == 0.0
    assert round_ielts(7.25) == 7.5


def test_streak_ignores_failed_and_counts_local_days(db, monkeypatch):
    monkeypatch.setattr(settings, "APP_TIMEZONE", "Asia/Almaty")
    fixed_now = datetime(2026, 10, 10, 20, 0, tzinfo=timezone.utc)  # 01:00 on the 11th in Almaty

    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now.astimezone(tz) if tz else fixed_now

    monkeypatch.setattr(time_module, "datetime", _Clock)
    assert local_today().isoformat() == "2026-10-11"
    # 21:00 UTC on the 10th is already the 11th in Almaty (UTC+5).
    assert to_local_date(datetime(2026, 10, 10, 21, 0)).isoformat() == "2026-10-11"

    def at(day, hour):
        return datetime(2026, 10, day, hour, 0)

    for created, band, status in [(at(9, 10), 6.5, "graded"), (at(10, 10), 6.5, "graded"),
                                  (at(10, 21), 6.5, "graded"),   # = the 11th locally
                                  (at(8, 10), None, "failed")]:  # failed: does not extend the streak
        db.add(WritingSubmission(user_id=db.info["user_id"], task_id=db.info["task_id"], text="x",
                                 word_count=1, status=status, band=band, created_at=created))
    db.commit()
    result = compute_streak(db, db.info["user_id"])
    assert result == {"current_streak": 3, "active_today": True}
    assert streak_module  # module imported for the patched helpers
