"""Provider-agnostic grading core.

Everything here is pure and deterministic: no network, no model, no database.
Every AI provider (Gemini, Claude, Qwen, the rule-based mock) produces a raw
verdict, and the functions below turn it into the grade the student sees:

  * each criterion snapped to a 0.5 step and clamped to 0-9; NaN/inf rejected;
  * the overall band recomputed as the mean of the criteria (IELTS half-up),
    never taken from the model;
  * hard caps for the failures IELTS punishes. Where a cap can be checked in
    code (word count, overview wording, topic overlap, instructions addressed
    to the examiner) the code decides, so the model cannot switch the cap off
    by reporting a flag;
  * mistake snippets kept only if they appear verbatim in the essay (FR-6).

What stays model-judged: the four criterion bands themselves, and the Task 1
"key comparisons / data accuracy / fabrication" and Task 2 "all parts addressed
/ clear position" findings. Those can only lower a band, never raise it.

The Writing pre-check (empty, non-English, too short, gibberish) also lives
here so graders can run it without importing the application layer.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Iterable

from app.domain.band import round_ielts

# --------------------------------------------------------------------------- #
# Result types
# --------------------------------------------------------------------------- #


@dataclass
class MistakeItem:
    """An atomic mistake extracted during grading. Persisted to the `mistakes`
    table so analytics can aggregate weaknesses across attempts (no AI at read time)."""

    category: str          # e.g. grammar | vocabulary | coherence | task_response | fluency ...
    subskill: str | None   # e.g. articles | word_repetition | paragraphing | answer_length
    severity: int = 1      # 1 (minor) .. 3 (band-limiting)
    snippet: str | None = None
    correction: str | None = None
    explanation: str | None = None


@dataclass
class Feedback:
    """Result of grading a Writing or Speaking submission."""

    band: float
    criteria: dict[str, float]  # criterion name -> band (0-9)
    summary: str
    suggestions: list[str] = field(default_factory=list)
    mistakes: list[MistakeItem] = field(default_factory=list)
    # Per-criterion examiner justification (criterion name -> 1-2 sentence note).
    criteria_notes: dict[str, str] = field(default_factory=dict)
    # Coaching extras (populated by the two-stage Writing engine; empty otherwise).
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    roadmap: list[dict] = field(default_factory=list)  # [{target_band, actions[]}]
    why_not_higher_band: str = ""
    # True when grading could not be completed (AI error/timeout/malformed
    # output). The caller must NOT persist this as a real Band-0 grade.
    error: bool = False
    # Provenance: which method produced this grade. Not part of to_dict() yet;
    # use diagnostics() to log or persist it.
    prompt_version: str = ""
    provider: str = ""
    model: str = ""
    # Examiner findings and the caps that fired, so a low band can be told
    # apart from a cap (E1 cap-case hit rate).
    flags: dict[str, bool] = field(default_factory=dict)
    caps_applied: list[str] = field(default_factory=list)
    # Model-reported mistake snippets dropped because they are not in the essay.
    unverified_snippets: int = 0

    def to_dict(self) -> dict:
        # Mistakes are persisted separately (mistakes table), not in the stored
        # feedback JSON. The extra coaching keys are additive and backward
        # compatible — older consumers read band/criteria/summary/suggestions.
        data = {
            "band": self.band,
            "criteria": self.criteria,
            "summary": self.summary,
            "suggestions": self.suggestions,
        }
        if self.criteria_notes:
            data["criteria_notes"] = self.criteria_notes
        if self.strengths:
            data["strengths"] = self.strengths
        if self.weaknesses:
            data["weaknesses"] = self.weaknesses
        if self.actions:
            data["actions"] = self.actions
        if self.roadmap:
            data["roadmap"] = self.roadmap
        if self.why_not_higher_band:
            data["why_not_higher_band"] = self.why_not_higher_band
        return data

    def diagnostics(self) -> dict:
        """Method/provenance record for logs, calibration runs and persistence."""
        return {
            "prompt_version": self.prompt_version,
            "provider": self.provider,
            "model": self.model,
            "flags": dict(self.flags),
            "caps_applied": list(self.caps_applied),
            "unverified_snippets": self.unverified_snippets,
            "error": self.error,
        }


# --------------------------------------------------------------------------- #
# Criterion names (keep the "&" forms the analytics/criterion maps use)
# --------------------------------------------------------------------------- #
COHERENCE = "Coherence & Cohesion"
LEXICAL = "Lexical Resource"
GRAMMAR = "Grammatical Range & Accuracy"
TASK1_FIRST = "Task Achievement"
TASK2_FIRST = "Task Response"

FLUENCY = "Fluency & Coherence"
PRONUNCIATION = "Pronunciation"
SPEAKING_CRITERIA = (FLUENCY, LEXICAL, GRAMMAR, PRONUNCIATION)


def writing_criteria(task_type: int) -> tuple[str, str, str, str]:
    first = TASK1_FIRST if task_type == 1 else TASK2_FIRST
    return (first, COHERENCE, LEXICAL, GRAMMAR)


# --------------------------------------------------------------------------- #
# Band arithmetic
# --------------------------------------------------------------------------- #


class InvalidBand(ValueError):
    """A band that is not a finite number (NaN, inf, text, None)."""


def snap_band(value) -> float:
    """Snap to the nearest 0.5 (IELTS half-up) and clamp to 0-9.

    Rejects NaN/inf and non-numbers instead of storing them.
    """
    if isinstance(value, bool):
        raise InvalidBand(f"band must be a number, got {value!r}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise InvalidBand(f"band must be a number, got {value!r}") from exc
    if not math.isfinite(number):
        raise InvalidBand(f"band must be finite, got {value!r}")
    return round_ielts(number)


def overall_band(criteria: dict[str, float]) -> float:
    """Mean of the criteria, rounded half-up to 0.5. Never from the model."""
    if not criteria:
        return 0.0
    return round_ielts(sum(criteria.values()) / len(criteria))


def underlength_cap(word_count: int, min_words: int) -> float | None:
    """The most generous band the task criterion may receive at this length.

    The ratios are a Testora design choice; the public descriptors penalise
    under-length within TR/TA but publish no ratios.
    """
    if min_words <= 0 or word_count >= min_words:
        return None
    ratio = word_count / min_words
    if ratio < 0.5:
        return 4.0
    if ratio < 0.75:
        return 5.0
    if ratio < 0.9:
        return 6.0
    return None  # 90-100% of minimum: no automatic cap, examiner decides


# --------------------------------------------------------------------------- #
# Deterministic checks (code decides; model flags cannot switch these off)
# --------------------------------------------------------------------------- #

_OVERVIEW_RE = re.compile(
    r"\b(overall|in general|generally|in summary|to sum up|summari[sz]e|in short|"
    r"in brief|broadly|at a glance|on the whole|"
    r"it is (clear|evident|apparent|obvious|noticeable)|"
    r"(can|could) be (seen|observed|noticed)|clearly|evidently|"
    r"(main|key|general|overall) (trends?|features?|patterns?|changes?|differences?)|"
    r"most (striking|notable|noticeable|significant|obvious)|stands? out)\b",
    re.IGNORECASE,
)


def overview_detected(text: str) -> bool:
    """Task 1: does the script contain any typical overview signal?

    Deliberately broad so a real overview is almost never missed; it only
    catches scripts that are pure detail with no summarising statement.
    """
    return bool(_OVERVIEW_RE.search(text or ""))


# Phrases addressed to the grader rather than to the task. Narrow on purpose:
# a genuine IELTS essay never needs them.
_INJECTION_PATTERNS = [
    re.compile(
        r"\b(ignore|disregard|forget|override)\s+(all\s+)?(the\s+|your\s+|any\s+|of\s+the\s+)?"
        r"(previous|prior|above|earlier|preceding|original)\s+(instructions?|rules|prompts?|guidelines)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(ignore|disregard|forget|override)\s+(all\s+|any\s+)?(the\s+|your\s+)?(rubric|system prompt|"
        r"band descriptors|examiner instructions|(marking|scoring|grading) (rules|criteria|scheme))\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(give|award|assign|grade|mark|rate)\s+(me|this|the|my)\b[^.\n]{0,40}\bband\s*\d",
        re.IGNORECASE,
    ),
    re.compile(r"\bband\s*9(\.0)?\s+(on|for|in)\s+(all|every|each)\b", re.IGNORECASE),
    re.compile(r"^\s*(system|assistant|developer)\s*(note|message|prompt|override)?\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(
        r"\b(off_topic|overview_present|position_clear|all_parts_addressed|"
        r"key_comparisons_present|fabricated_data|response_schema)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\byou are (now )?(an?|the) (ielts )?(examiner|grader|assistant|language model)\b", re.IGNORECASE),
    re.compile(r"</?\s*candidate[_ ]response|<<<\s*end", re.IGNORECASE),
]


def injection_suspected(text: str) -> bool:
    """True when the essay contains instructions aimed at the grader."""
    return any(p.search(text or "") for p in _INJECTION_PATTERNS)


_TOPIC_STOPWORDS = {
    "about", "above", "after", "agree", "against", "although", "answer", "argue",
    "argued", "because", "before", "being", "believe", "below", "between", "both",
    "cause", "causes", "could", "describe", "disadvantages", "advantages", "discuss",
    "disagree", "effect", "effects", "either", "example", "examples", "experience",
    "extent", "factors", "following", "given", "important", "include", "issue",
    "knowledge", "least", "measures", "might", "opinion", "other", "others",
    "outweigh", "people", "positive", "negative", "problem", "problems", "provide",
    "reasons", "relevant", "should", "solutions", "solve", "solved", "some", "summarise",
    "summarize", "their", "there", "these", "thing", "things", "think", "those",
    "today", "views", "where", "whether", "which", "while", "would", "write",
    "words", "information", "making", "comparisons", "selecting", "reporting",
    "features", "main", "development", "developments", "nowadays", "society",
    "world", "many", "much", "more", "most", "what", "when", "your", "own",
}


def _content_stems(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", (text or "").lower())
    return {w[:5] for w in words if len(w) >= 5 and w not in _TOPIC_STOPWORDS}


def topic_overlap(prompt: str, text: str) -> int | None:
    """How many content-word stems of the task prompt the essay reuses.

    None when the prompt is too short to judge (fewer than 3 content words).
    """
    prompt_stems = _content_stems(prompt)
    if len(prompt_stems) < 3:
        return None
    return len(prompt_stems & _content_stems(text))


# --------------------------------------------------------------------------- #
# Writing normalisation
# --------------------------------------------------------------------------- #

INJECTION_CAP = 5.0


@dataclass
class WritingVerdict:
    """A provider's raw Writing verdict, before any rule is applied."""

    task_type: int
    bands: dict[str, float]           # criterion display name -> raw model band
    notes: dict[str, str] = field(default_factory=dict)
    # Model-reported findings. Task 1: overview_present, key_comparisons_present,
    # data_accuracy_issue, fabricated_data. Task 2: all_parts_addressed,
    # position_clear, off_topic.
    flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class NormalizedWriting:
    criteria: dict[str, float]
    notes: dict[str, str]
    overall: float
    flags: dict[str, bool]
    caps_applied: list[str]


def normalize_writing(
    verdict: WritingVerdict,
    *,
    word_count: int,
    min_words: int,
    text: str | None = None,
    prompt: str | None = None,
) -> NormalizedWriting:
    """Apply IELTS scoring rules deterministically.

    `text` / `prompt` enable the code-side checks (overview wording, topic
    overlap, injection). Without them only model flags and length are used.
    """
    names = writing_criteria(verdict.task_type)
    first = names[0]
    criteria = {name: snap_band(verdict.bands[name]) for name in names}
    flags = dict(verdict.flags)
    caps: list[tuple[str, float]] = []

    ul = underlength_cap(word_count, min_words)
    if ul is not None:
        caps.append(("under_length", ul))

    if verdict.task_type == 1:
        if text is not None:
            flags["overview_detected"] = overview_detected(text)
        if not flags.get("overview_present", True) or flags.get("overview_detected") is False:
            caps.append(("no_overview", 5.0))
        if not flags.get("key_comparisons_present", True):
            caps.append(("no_key_comparisons", 5.0))
        if flags.get("fabricated_data", False):
            caps.append(("fabricated_data", 4.0))  # severe Task Achievement failure
    else:
        if text is not None and prompt is not None:
            overlap = topic_overlap(prompt, text)
            if overlap is not None:
                flags["topic_overlap_none"] = overlap == 0
        if flags.get("off_topic", False) or flags.get("topic_overlap_none", False):
            caps.append(("off_topic", 3.0))  # off-topic / memorised content
        if not flags.get("position_clear", True):
            caps.append(("unclear_position", 5.0))
        if not flags.get("all_parts_addressed", True):
            caps.append(("partial_answer", 5.0))

    fired: list[str] = []
    for reason, cap in caps:
        if criteria[first] > cap:
            fired.append(reason)
    if caps:
        criteria[first] = min(criteria[first], min(cap for _, cap in caps))

    # Instructions addressed to the grader: the model's scores are not
    # trustworthy, so every criterion is bounded and the result is flagged.
    if text is not None:
        flags["injection_suspected"] = injection_suspected(text)
        if flags["injection_suspected"]:
            if any(v > INJECTION_CAP for v in criteria.values()):
                fired.append("injection_suspected")
            criteria = {k: min(v, INJECTION_CAP) for k, v in criteria.items()}

    notes = {name: verdict.notes.get(name, "") for name in names}
    return NormalizedWriting(
        criteria=criteria,
        notes=notes,
        overall=overall_band(criteria),
        flags=flags,
        caps_applied=fired,
    )


# --------------------------------------------------------------------------- #
# Speaking normalisation
# --------------------------------------------------------------------------- #


def normalize_speaking(bands: dict[str, float], *, transcript: str | None = None) -> tuple[dict[str, float], float, dict[str, bool]]:
    """Snap/clamp the four Speaking criteria and recompute the overall.

    Returns (criteria, overall, flags). Missing criteria raise KeyError so a
    partial model answer is a failed grading, not a silent mean of three.
    """
    criteria = {name: snap_band(bands[name]) for name in SPEAKING_CRITERIA}
    flags: dict[str, bool] = {}
    if transcript is not None:
        flags["injection_suspected"] = injection_suspected(transcript)
        if flags["injection_suspected"]:
            criteria = {k: min(v, INJECTION_CAP) for k, v in criteria.items()}
    return criteria, overall_band(criteria), flags


# --------------------------------------------------------------------------- #
# Snippet verification (FR-6)
# --------------------------------------------------------------------------- #

_QUOTE_CHARS = str.maketrans({
    "‘": "'", "’": "'", "‛": "'", "′": "'",
    "“": '"', "”": '"', "‟": '"',
    "–": "-", "—": "-", " ": " ",
})
_ELLIPSIS_RE = re.compile(r"\s*(?:\.\.\.|…)\s*")


def normalize_for_match(text: str) -> str:
    """Lower-case, unify quotes/dashes, collapse whitespace."""
    return " ".join((text or "").translate(_QUOTE_CHARS).lower().split())


def snippet_in_text(snippet: str | None, text: str) -> bool:
    """True if `snippet` occurs verbatim in `text` (whitespace/case-insensitive).

    Surrounding quotes are ignored. An ellipsis splits the snippet into parts
    that must all occur, in order.
    """
    if not snippet or not snippet.strip():
        return False
    haystack = normalize_for_match(text)
    parts = [
        normalize_for_match(p).strip(" \"'`")
        for p in _ELLIPSIS_RE.split(snippet.translate(_QUOTE_CHARS))
    ]
    parts = [p for p in parts if p]
    if not parts:
        return False
    position = 0
    for part in parts:
        found = haystack.find(part, position)
        if found < 0:
            # Models often add or drop final punctuation; retry without it.
            trimmed = part.rstrip(".,;:!?")
            found = haystack.find(trimmed, position) if trimmed else -1
            if found < 0:
                return False
            part = trimmed
        position = found + len(part)
    return True


def verify_mistakes(mistakes: Iterable[MistakeItem], text: str | None) -> tuple[list[MistakeItem], int]:
    """Keep mistakes whose snippet is in the essay; return (kept, dropped).

    Mistakes without a snippet (e.g. a paragraphing issue) are kept. With no
    text to check against (audio-only Speaking) snippets are cleared instead,
    because they cannot be verified.
    """
    kept: list[MistakeItem] = []
    dropped = 0
    for m in mistakes:
        if not (m.snippet or "").strip():
            kept.append(m)
        elif text is None:
            kept.append(MistakeItem(
                category=m.category, subskill=m.subskill, severity=m.severity,
                snippet=None, correction=m.correction, explanation=m.explanation,
            ))
        elif snippet_in_text(m.snippet, text):
            kept.append(m)
        else:
            dropped += 1
    return kept, dropped


# --------------------------------------------------------------------------- #
# Failure feedback
# --------------------------------------------------------------------------- #

GRADING_FAILED_MESSAGE = (
    "Automatic grading could not be completed. Your answer was saved; "
    "please try again in a few minutes."
)


def grading_error_feedback(
    *,
    provider: str = "",
    model: str = "",
    prompt_version: str = "",
    message: str = GRADING_FAILED_MESSAGE,
) -> Feedback:
    """Failed-grading feedback. Never carries internal error text."""
    return Feedback(
        band=0.0,
        criteria={},
        summary=message,
        suggestions=["Try submitting again in a few minutes."],
        error=True,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
    )


# --------------------------------------------------------------------------- #
# Writing pre-check (pure rules; mirrors application/writing_precheck.py)
# --------------------------------------------------------------------------- #

ENGLISH_WORD_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)?")
ALPHA_TOKEN_RE = re.compile(r"[^\W\d_]+(?:[-'][^\W\d_]+)?", re.UNICODE)
# A single ASCII letter or digit — used to decide whether a whitespace-separated
# token counts as a word. ASCII (not \w) so punctuation like "—" and non-English
# scripts (e.g. Cyrillic) don't inflate the count of an English Writing task,
# while numbers written as figures still count.
WORD_CHAR_RE = re.compile(r"[A-Za-z0-9]")

COMMON_ENGLISH_WORDS = {
    "a", "about", "after", "all", "also", "an", "and", "are", "as", "at", "be",
    "because", "been", "but", "by", "can", "children", "could", "do", "for",
    "from", "has", "have", "if", "in", "is", "it", "more", "not", "of", "on",
    "or", "people", "should", "society", "some", "that", "the", "their", "there",
    "these", "they", "this", "to", "with", "would",
}


@dataclass(frozen=True)
class WritingPrecheck:
    valid: bool
    reason_code: str | None
    message: str | None
    word_count: int
    sentence_count: int


def count_words(text: str) -> int:
    """Count words the way an IELTS examiner does: whitespace-separated tokens
    that contain at least one letter or digit. Numbers written as figures,
    hyphenated words, and contractions each count as a single word, so this
    matches the live counter shown to the candidate while they write."""
    return sum(1 for token in (text or "").split() if WORD_CHAR_RE.search(token))


def _english_word_count(text: str) -> int:
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


def _looks_non_english(text: str, english_word_count: int) -> bool:
    alpha_tokens = ALPHA_TOKEN_RE.findall(text or "")
    if not alpha_tokens:
        return False
    english_token_ratio = english_word_count / len(alpha_tokens)
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


def validate_writing_submission(*, task_type: int, text: str, min_words: int) -> WritingPrecheck:
    stripped = (text or "").strip()
    word_count = count_words(stripped)
    sentence_count = _sentence_count(stripped)

    def invalid(code: str, message: str, words: int = word_count, sentences: int = sentence_count):
        return WritingPrecheck(False, code, message, words, sentences)

    if not stripped:
        return invalid("empty_response", "This submission cannot be assessed because it is empty.", 0, 0)
    if _looks_non_english(stripped, _english_word_count(stripped)):
        return invalid(
            "not_english",
            "This submission cannot be assessed as IELTS Writing because it "
            "is not written primarily in English.",
        )
    if word_count < _min_attempt_words(task_type, min_words):
        return invalid(
            "too_short",
            "This submission is too short to be assessed as a genuine IELTS "
            "Writing response.",
        )
    if sentence_count < _min_attempt_sentences(task_type):
        return invalid(
            "too_few_sentences",
            "This submission needs full sentences and paragraph-level "
            "development before it can be assessed.",
        )
    if _looks_like_gibberish(_words(stripped)):
        return invalid(
            "not_meaningful",
            "This submission does not contain enough meaningful English "
            "language to be assessed as IELTS Writing.",
        )
    return WritingPrecheck(True, None, None, word_count, sentence_count)


def zero_band_feedback(task_type: int, precheck: WritingPrecheck) -> Feedback:
    first = TASK1_FIRST if task_type == 1 else TASK2_FIRST
    message = precheck.message or "This submission cannot be assessed as IELTS Writing."
    criteria = {first: 0.0, COHERENCE: 0.0, LEXICAL: 0.0, GRAMMAR: 0.0}
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
