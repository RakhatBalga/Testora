"""Deterministic Writing submission pre-checks.

This layer catches responses that should never be sent to an IELTS examiner:
non-English text, empty/gibberish input, and submissions too short to count as
a serious Writing attempt. Gemini can be overly helpful with such inputs, so
these checks return a real Band 0 before any model call is made.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.infrastructure.ai.base import Feedback, MistakeItem
from app.infrastructure.ai.schemas import (
    COHERENCE,
    GRAMMAR,
    LEXICAL,
    TASK1_FIRST,
    TASK2_FIRST,
)

ENGLISH_WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
ALPHA_TOKEN_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)?", re.UNICODE)

COMMON_ENGLISH_WORDS = {
    "a",
    "about",
    "after",
    "all",
    "also",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "but",
    "by",
    "can",
    "children",
    "could",
    "do",
    "for",
    "from",
    "has",
    "have",
    "if",
    "in",
    "is",
    "it",
    "more",
    "not",
    "of",
    "on",
    "or",
    "people",
    "should",
    "society",
    "some",
    "that",
    "the",
    "their",
    "there",
    "these",
    "they",
    "this",
    "to",
    "with",
    "would",
}


@dataclass(frozen=True)
class WritingPrecheck:
    valid: bool
    reason_code: str | None
    message: str | None
    word_count: int
    sentence_count: int


def count_words(text: str) -> int:
    """Count English words, matching the IELTS Writing language requirement."""
    return len(ENGLISH_WORD_RE.findall(text or ""))


def _words(text: str) -> list[str]:
    return [w.lower() for w in ENGLISH_WORD_RE.findall(text or "")]


def _sentence_count(text: str) -> int:
    chunks = re.split(r"[.!?]+|\n+", text or "")
    return sum(1 for chunk in chunks if count_words(chunk) >= 3)


def _ascii_letter_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 1.0
    ascii_letters = [ch for ch in letters if "a" <= ch.lower() <= "z"]
    return len(ascii_letters) / len(letters)


def _looks_non_english(text: str, word_count: int) -> bool:
    alpha_tokens = ALPHA_TOKEN_RE.findall(text or "")
    if not alpha_tokens:
        return False
    english_token_ratio = word_count / len(alpha_tokens)
    return _ascii_letter_ratio(text) < 0.8 or english_token_ratio < 0.7


def _min_attempt_words(task_type: int, min_words: int) -> int:
    if task_type == 1:
        return max(40, int(min_words * 0.25))
    return max(60, int(min_words * 0.25))


def _min_attempt_sentences(task_type: int) -> int:
    return 2 if task_type == 1 else 3


def _looks_like_gibberish(words: list[str]) -> bool:
    if len(words) < 20:
        return False
    unique_ratio = len(set(words)) / len(words)
    vowel_ratio = sum(any(vowel in w for vowel in "aeiou") for w in words) / len(words)
    common_ratio = sum(w in COMMON_ENGLISH_WORDS for w in words) / len(words)
    average_length = sum(len(w) for w in words) / len(words)

    if unique_ratio < 0.15:
        return True
    if vowel_ratio < 0.65:
        return True
    return common_ratio < 0.04 and average_length > 6.5


def validate_writing_submission(
    *, task_type: int, text: str, min_words: int
) -> WritingPrecheck:
    stripped = (text or "").strip()
    word_count = count_words(stripped)
    sentence_count = _sentence_count(stripped)

    if not stripped:
        return WritingPrecheck(
            valid=False,
            reason_code="empty_response",
            message="This submission cannot be assessed because it is empty.",
            word_count=0,
            sentence_count=0,
        )

    if _looks_non_english(stripped, word_count):
        return WritingPrecheck(
            valid=False,
            reason_code="not_english",
            message=(
                "This submission cannot be assessed as IELTS Writing because it "
                "is not written primarily in English."
            ),
            word_count=word_count,
            sentence_count=sentence_count,
        )

    minimum_words = _min_attempt_words(task_type, min_words)
    if word_count < minimum_words:
        return WritingPrecheck(
            valid=False,
            reason_code="too_short",
            message=(
                "This submission is too short to be assessed as a genuine IELTS "
                "Writing response."
            ),
            word_count=word_count,
            sentence_count=sentence_count,
        )

    minimum_sentences = _min_attempt_sentences(task_type)
    if sentence_count < minimum_sentences:
        return WritingPrecheck(
            valid=False,
            reason_code="too_few_sentences",
            message=(
                "This submission needs full sentences and paragraph-level "
                "development before it can be assessed."
            ),
            word_count=word_count,
            sentence_count=sentence_count,
        )

    words = _words(stripped)
    if _looks_like_gibberish(words):
        return WritingPrecheck(
            valid=False,
            reason_code="not_meaningful",
            message=(
                "This submission does not contain enough meaningful English "
                "language to be assessed as IELTS Writing."
            ),
            word_count=word_count,
            sentence_count=sentence_count,
        )

    return WritingPrecheck(
        valid=True,
        reason_code=None,
        message=None,
        word_count=word_count,
        sentence_count=sentence_count,
    )


def zero_band_feedback(task_type: int, precheck: WritingPrecheck) -> Feedback:
    first = TASK1_FIRST if task_type == 1 else TASK2_FIRST
    message = precheck.message or "This submission cannot be assessed as IELTS Writing."
    criteria = {
        first: 0.0,
        COHERENCE: 0.0,
        LEXICAL: 0.0,
        GRAMMAR: 0.0,
    }
    notes = {
        first: message,
        COHERENCE: "No coherent English response was available to assess.",
        LEXICAL: "No assessable English vocabulary was available.",
        GRAMMAR: "No assessable English sentence control was available.",
    }
    return Feedback(
        band=0.0,
        criteria=criteria,
        summary=message,
        suggestions=[
            "Write a complete response in English.",
            "Use full sentences and develop your answer across clear paragraphs.",
            "Submit a genuine IELTS Writing attempt before requesting a band score.",
        ],
        mistakes=[
            MistakeItem(
                category="task_response",
                subskill=precheck.reason_code or "invalid_response",
                severity=3,
                explanation=message,
            )
        ],
        criteria_notes=notes,
        weaknesses=[message],
        actions=[
            "Rewrite the answer in English.",
            "Add enough developed sentences to form a complete IELTS response.",
        ],
    )
