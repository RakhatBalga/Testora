from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)

from app.infrastructure.database import Base


class SavedWord(Base):
    """A word or short phrase the user saved (e.g. highlighted while reading).

    Enrichment (meaning, synonyms, better alternatives, native-language
    translation) is produced on demand by the vocabulary AI coach and cached on
    the row, so the word card and the daily quiz never re-call the model for the
    same word. `training=True` opts the word into the daily practice pool.
    """

    __tablename__ = "saved_words"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    word = Column(String, nullable=False)        # display form (trimmed)
    context = Column(Text, nullable=True)        # sentence/snippet it came from
    source = Column(String, nullable=True)       # reading | writing | manual | ...
    source_ref = Column(String, nullable=True)   # free-form origin id (e.g. section/test)

    # Cached enrichment produced by the vocabulary coach:
    # {meaning, part_of_speech, synonyms[], alternatives[], translation, example}
    enrichment = Column(JSON, nullable=True)
    enriched_at = Column(DateTime, nullable=True)

    # "I want to practice this word" — included in the daily quiz pool when true.
    training = Column(Boolean, nullable=False, default=False)
    # new | learning | mastered — nudged as the user answers daily quizzes.
    status = Column(String, nullable=False, default="new")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "word", name="uq_saved_word_user_word"),
        Index("ix_saved_words_user_created", "user_id", "created_at"),
        Index("ix_saved_words_user_training", "user_id", "training"),
    )


class DailyWordQuiz(Base):
    """A quiz the vocabulary coach generated for one user on one day.

    Cached by (user, date): there is no scheduler, so generation is on-demand and
    date-keyed (mirroring the weekly study plan) — opening the practice page again
    on the same day reuses one generation. `payload` holds the full quiz including
    correct answers; the API strips answers before sending to the client and
    grades submissions server-side.
    """

    __tablename__ = "daily_word_quizzes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_date = Column(Date, nullable=False)

    payload = Column(JSON, nullable=False)       # {"questions": [...]}
    completed = Column(Boolean, nullable=False, default=False)
    score = Column(Integer, nullable=True)       # correct count, once submitted
    total = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "quiz_date", name="uq_daily_word_quiz_user_date"),
    )
