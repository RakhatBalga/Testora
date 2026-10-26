"""Writing pre-check. The rules live in app.domain.grading (so graders can run
them without importing the application layer); this module re-exports them for
application code and existing imports."""
from app.domain.grading import (  # noqa: F401
    ALPHA_TOKEN_RE,
    COMMON_ENGLISH_WORDS,
    ENGLISH_WORD_RE,
    WORD_CHAR_RE,
    WritingPrecheck,
    count_words,
    validate_writing_submission,
    zero_band_feedback,
)
