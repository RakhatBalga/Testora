"""Structured schemas + validation for the Writing assessment engine.

These Pydantic models are both (a) the response schema handed to Gemini's JSON
mode and (b) the validation boundary for what comes back. The normalization
functions then enforce IELTS scoring rules deterministically — independent of
whatever the model returned — so grading can't be inflated by a chatty model:

  * each criterion snapped to a 0.5 step, clamped 0-9;
  * hard caps applied for the failures IELTS punishes (no overview, fabricated
    data, missing comparisons / off-topic, unclear position, partial answer,
    under-length);
  * overall band recomputed as the mean of the four criteria (half-up), never
    taken from the model.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.infrastructure.ai.base import Feedback, MistakeItem
from app.domain.band import round_ielts

# Error categories must match the analytics mistake taxonomy (Writing only).
ErrorCategory = Literal["grammar", "vocabulary", "coherence", "task_response"]

# Canonical display names — keep the "&" forms the analytics/criterion maps use.
COHERENCE = "Coherence & Cohesion"
LEXICAL = "Lexical Resource"
GRAMMAR = "Grammatical Range & Accuracy"
TASK1_FIRST = "Task Achievement"
TASK2_FIRST = "Task Response"


class WritingError(BaseModel):
    category: ErrorCategory
    subskill: str | None = Field(
        None, description="e.g. articles, prepositions, tense, agreement, collocation, "
        "word_choice, repetition, paragraphing, progression, development, support"
    )
    severity: int = Field(1, ge=1, le=3, description="1 minor, 2 recurring, 3 band-limiting")
    snippet: str | None = Field(None, description="the offending text, quoted")
    correction: str | None = Field(None, description="a corrected/improved form")
    explanation: str | None = Field(None, description="why it is an issue, briefly")


class Criterion(BaseModel):
    band: float = Field(..., ge=0, le=9)
    justification: str = ""


class _ExaminerBase(BaseModel):
    coherence_cohesion: Criterion
    lexical_resource: Criterion
    grammatical_range_accuracy: Criterion
    errors: list[WritingError] = Field(default_factory=list)


class Task1Examiner(_ExaminerBase):
    task_achievement: Criterion
    overview_present: bool = True
    key_comparisons_present: bool = True
    data_accuracy_issue: bool = False
    fabricated_data: bool = False


class Task2Examiner(_ExaminerBase):
    task_response: Criterion
    all_parts_addressed: bool = True
    position_clear: bool = True
    off_topic: bool = False


class CoachStep(BaseModel):
    target_band: float = Field(..., ge=0, le=9)
    actions: list[str] = Field(default_factory=list)


class CoachResult(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    priorities: list[str] = Field(default_factory=list)
    roadmap: list[CoachStep] = Field(default_factory=list)
    why_not_higher_band: str = ""
    summary: str = ""


def examiner_model(task_type: int) -> type[BaseModel]:
    return Task1Examiner if task_type == 1 else Task2Examiner


# ----------------------------- normalization ------------------------------- #

def _snap(band: float) -> float:
    """Snap to nearest 0.5 (IELTS half-up) and clamp to 0-9."""
    return round_ielts(band)


def _underlength_cap(word_count: int, min_words: int) -> float | None:
    """The most generous band the task criterion may receive at this length."""
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


def normalize_examiner(result: BaseModel, *, task_type: int, word_count: int, min_words: int) -> dict:
    """Apply IELTS scoring rules deterministically; return a normalized dict.

    Returns: {criteria: {display_name: band}, notes: {display_name: justification},
              overall: float, errors: [WritingError], flags: {...}}.
    """
    coherence = _snap(result.coherence_cohesion.band)
    lexical = _snap(result.lexical_resource.band)
    grammar = _snap(result.grammatical_range_accuracy.band)

    notes: dict[str, str] = {
        COHERENCE: result.coherence_cohesion.justification,
        LEXICAL: result.lexical_resource.justification,
        GRAMMAR: result.grammatical_range_accuracy.justification,
    }
    flags: dict[str, bool] = {}
    caps: list[float] = []
    ul = _underlength_cap(word_count, min_words)
    if ul is not None:
        caps.append(ul)

    if task_type == 1:
        task = _snap(result.task_achievement.band)
        first_name = TASK1_FIRST
        notes[first_name] = result.task_achievement.justification
        flags = {
            "overview_present": result.overview_present,
            "key_comparisons_present": result.key_comparisons_present,
            "data_accuracy_issue": result.data_accuracy_issue,
            "fabricated_data": result.fabricated_data,
        }
        if not result.overview_present:
            caps.append(5.0)
        if not result.key_comparisons_present:
            caps.append(5.0)
        if result.fabricated_data:
            caps.append(4.0)  # fabrication is a severe Task Achievement failure
    else:
        task = _snap(result.task_response.band)
        first_name = TASK2_FIRST
        notes[first_name] = result.task_response.justification
        flags = {
            "all_parts_addressed": result.all_parts_addressed,
            "position_clear": result.position_clear,
            "off_topic": result.off_topic,
        }
        if result.off_topic:
            caps.append(3.0)  # off-topic / memorised content
        if not result.position_clear:
            caps.append(5.0)
        if not result.all_parts_addressed:
            caps.append(5.0)

    if caps:
        task = min(task, min(caps))

    criteria = {
        first_name: task,
        COHERENCE: coherence,
        LEXICAL: lexical,
        GRAMMAR: grammar,
    }
    overall = round_ielts(sum(criteria.values()) / 4)
    return {
        "criteria": criteria,
        "notes": notes,
        "overall": overall,
        "errors": list(result.errors),
        "flags": flags,
    }


def _errors_to_mistakes(errors: list[WritingError]) -> list[MistakeItem]:
    mistakes: list[MistakeItem] = []
    for e in errors:
        snippet = (e.snippet or "").strip()
        correction = (e.correction or "").strip()
        if snippet and correction and snippet == correction:
            continue
        if _is_optional_refinement(e):
            continue
        subskill = _normalize_error_subskill(e)
        category = _normalize_error_category(e.category, subskill)
        mistakes.append(
            MistakeItem(
                category=category,
                subskill=subskill,
                severity=max(1, min(3, e.severity)),
                snippet=e.snippet,
                correction=e.correction,
                explanation=e.explanation,
            )
        )
    return mistakes


def _is_optional_refinement(error: WritingError) -> bool:
    if error.severity > 1:
        return False
    explanation = (error.explanation or "").lower()
    optional_markers = (
        "not strictly incorrect",
        "more concise",
        "more formal",
        "slightly more natural",
        "would be more natural",
        "could be more natural",
        "would also be acceptable",
    )
    return any(marker in explanation for marker in optional_markers)


def _normalize_error_subskill(error: WritingError) -> str | None:
    """Correct common model taxonomy slips before storing Mistake Memory rows."""
    haystack = " ".join(
        p for p in [error.subskill, error.explanation, error.correction] if p
    ).lower()
    if any(word in haystack for word in ("comma", "semicolon", "full stop", "punctuation")):
        return "punctuation"
    return error.subskill


def _normalize_error_category(category: ErrorCategory, subskill: str | None) -> ErrorCategory:
    if subskill in {"word_choice", "collocation", "repetition", "spelling", "word_formation"}:
        return "vocabulary"
    if subskill in {"punctuation", "articles", "prepositions", "tense", "agreement", "sentence_structure"}:
        return "grammar"
    return category


def build_feedback(normalized: dict, coaching: CoachResult | None, *, task_type: int) -> Feedback:
    """Combine normalized examiner output + optional coaching into a Feedback."""
    criteria = normalized["criteria"]
    overall = normalized["overall"]
    notes = normalized["notes"]
    errors = normalized["errors"]
    mistakes = _errors_to_mistakes(errors)

    lowest = min(criteria, key=lambda k: criteria[k])
    if coaching is not None:
        summary = coaching.summary or f"Estimated Band {overall}. Biggest blocker: {lowest}."
        suggestions = coaching.priorities or [n for n in notes.values() if n][:3]
        strengths = coaching.strengths
        weaknesses = coaching.weaknesses
        roadmap = _roadmap_above_current(coaching.roadmap, overall, suggestions)
        why_not_higher = _why_not_higher_band(
            overall=overall,
            explicit=coaching.why_not_higher_band,
            roadmap=roadmap,
            suggestions=suggestions,
            lowest=lowest,
        )
    else:
        # Coach stage unavailable — still return a useful, examiner-grounded result.
        summary = f"Estimated Band {overall}. Your lowest criterion is {lowest} ({criteria[lowest]})."
        suggestions = [m.correction for m in mistakes if m.correction][:3] or [
            f"Focus on {lowest} to lift your band."
        ]
        strengths = []
        weaknesses = []
        roadmap = []
        why_not_higher = _why_not_higher_band(
            overall=overall,
            explicit="",
            roadmap=roadmap,
            suggestions=[f"focus on {lowest}"],
            lowest=lowest,
        )

    return Feedback(
        band=overall,
        criteria=criteria,
        summary=summary,
        suggestions=suggestions,
        mistakes=mistakes,
        criteria_notes=notes,
        strengths=strengths,
        weaknesses=weaknesses,
        roadmap=roadmap,
        why_not_higher_band=why_not_higher,
    )


def _roadmap_above_current(
    steps: list[CoachStep],
    overall: float,
    fallback_actions: list[str],
) -> list[dict]:
    """Keep roadmap targets forward-looking, never equal to the current band."""
    roadmap: list[dict] = []
    seen: set[float] = set()
    for step in steps:
        target = _snap(step.target_band)
        if target <= overall or target in seen:
            continue
        actions = [a.strip() for a in step.actions if a.strip()][:3]
        if not actions:
            continue
        seen.add(target)
        roadmap.append({"target_band": target, "actions": actions})

    if roadmap or overall >= 9.0:
        return sorted(roadmap, key=lambda item: item["target_band"])

    next_band = min(9.0, overall + 0.5)
    actions = [a.strip() for a in fallback_actions if a.strip()][:3]
    if not actions:
        return []
    return [{"target_band": next_band, "actions": actions}]


def _why_not_higher_band(
    *,
    overall: float,
    explicit: str,
    roadmap: list[dict],
    suggestions: list[str],
    lowest: str,
) -> str:
    """Short next-half-band explanation for the result page."""
    if overall >= 9.0:
        return ""
    explicit = explicit.strip()
    if explicit:
        return explicit

    next_band = _snap(overall + 0.5)
    actions: list[str] = []
    if roadmap:
        first = roadmap[0]
        if first.get("target_band") == next_band:
            actions = [str(a) for a in first.get("actions", [])]
    if not actions:
        actions = suggestions
    fragments = [_action_fragment(action) for action in actions if action.strip()][:3]
    if not fragments:
        fragments = [f"focus on {lowest}"]
    return f"To reach {next_band:.1f}, {_join_fragments(fragments)}."


def _action_fragment(action: str) -> str:
    action = action.strip().rstrip(".")
    if not action:
        return action
    return action[:1].lower() + action[1:]


def _join_fragments(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{items[0]}, {items[1]}, and {items[2]}"


_QUOTE_RE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”|`([^`\n]+)`')


def sanitize_coach_evidence(
    coaching: CoachResult,
    *,
    essay: str,
    errors: list[WritingError],
) -> CoachResult:
    """Drop coach items that quote phrases unsupported by the essay/errors."""
    sources = [essay, *[(error.snippet or "") for error in errors]]

    def supported(value: str) -> bool:
        quotes = [
            q.strip()
            for match in _QUOTE_RE.findall(value)
            for q in match
            if q.strip()
        ]
        return all(any(quote in source for source in sources) for quote in quotes)

    def clean_list(items: list[str]) -> list[str]:
        return [item for item in items if supported(item)]

    roadmap: list[CoachStep] = []
    for step in coaching.roadmap:
        actions = clean_list(step.actions)
        if actions:
            roadmap.append(CoachStep(target_band=step.target_band, actions=actions))

    return coaching.model_copy(
        update={
            "strengths": clean_list(coaching.strengths),
            "weaknesses": clean_list(coaching.weaknesses),
            "priorities": clean_list(coaching.priorities),
            "roadmap": roadmap,
            "why_not_higher_band": (
                coaching.why_not_higher_band
                if supported(coaching.why_not_higher_band)
                else ""
            ),
            "summary": coaching.summary if supported(coaching.summary) else "",
        }
    )
