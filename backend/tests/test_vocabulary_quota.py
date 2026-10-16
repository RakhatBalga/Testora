import asyncio
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application import vocabulary
from app.domain.models.ai_quota import AIQuotaBucket
from app.domain.models.user import User
from app.domain.models.vocabulary import DailyWordQuiz, SavedWord
from app.infrastructure.ai.vocab import MockVocabularyCoach, WordQuiz
from app.infrastructure.config import settings
from app.infrastructure.database import Base


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, "AI_DAILY_ATTEMPTS", 1)
    monkeypatch.setattr(vocabulary, "get_vocabulary_coach", MockVocabularyCoach)
    async def immediate(func, **kwargs):
        return func(**kwargs)
    monkeypatch.setattr(vocabulary, "offload", immediate)
    with Session(engine) as session:
        session.add(User(id=1, username="student", password="hash"))
        session.add(SavedWord(id=1, user_id=1, word="alpha", context="The alpha value is high."))
        session.commit()
        yield session
    engine.dispose()


def test_cached_enrichment_is_free_but_force_uses_daily_budget(db):
    user = db.get(User, 1)
    first = asyncio.run(vocabulary.enrich_word(db, user=user, word_id=1))
    assert first.enrichment
    assert asyncio.run(vocabulary.enrich_word(db, user=user, word_id=1)).enrichment == first.enrichment
    with pytest.raises(HTTPException) as error:
        asyncio.run(vocabulary.enrich_word(db, user=user, word_id=1, force=True))
    assert error.value.status_code == 429
    assert db.query(AIQuotaBucket).one().used == 1


def test_quiz_cache_does_not_call_provider_again(db, monkeypatch):
    user = db.get(User, 1)
    first = asyncio.run(vocabulary.get_daily_quiz(db, user=user, quiz_date=date.today()))
    monkeypatch.setattr(vocabulary, "get_vocabulary_coach", lambda: pytest.fail("Cached quiz called provider"))
    second = asyncio.run(vocabulary.get_daily_quiz(db, user=user, quiz_date=date.today()))
    assert first.id == second.id


def test_failed_quiz_is_not_cached_and_cannot_retry_forever(db, monkeypatch):
    class FailedCoach:
        def generate_quiz(self, **kwargs):
            return WordQuiz(questions=[], error=True)
    monkeypatch.setattr(vocabulary, "get_vocabulary_coach", FailedCoach)
    user = db.get(User, 1)
    for expected in [503, 429]:
        with pytest.raises(HTTPException) as error:
            asyncio.run(vocabulary.get_daily_quiz(db, user=user, quiz_date=date.today()))
        assert error.value.status_code == expected
    assert db.query(DailyWordQuiz).count() == 0
