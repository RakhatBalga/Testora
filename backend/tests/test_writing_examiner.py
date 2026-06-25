"""Writing assessment engine — validation & calibration suite.

These tests pin the DETERMINISTIC layer that sits between the model and the
stored grade: band snapping, IELTS hard-caps for the failures examiners punish,
the recomputed overall band, and error->mistake mapping. They run without any
network/model call. The band-level fixtures below double as a calibration suite:
each represents an examiner verdict at a target band and asserts the normalized
overall the candidate would actually receive.

Real end-to-end accuracy (does Gemini *itself* land the right band?) must be
checked against the labelled essay fixtures in
`tests/fixtures/writing_calibration.md` with a live key; that can't run in CI.
"""
import pytest

from app.services.ai.schemas import (
    CoachResult,
    Task1Examiner,
    Task2Examiner,
    build_feedback,
    examiner_model,
    normalize_examiner,
)


def _crit(band, note="evidence-based note"):
    return {"band": band, "justification": note}


def _task1(ta, cc, lr, gra, **flags):
    base = {
        "task_achievement": _crit(ta),
        "coherence_cohesion": _crit(cc),
        "lexical_resource": _crit(lr),
        "grammatical_range_accuracy": _crit(gra),
        "errors": [],
    }
    base.update(flags)
    return Task1Examiner.model_validate(base)


def _task2(tr, cc, lr, gra, **flags):
    base = {
        "task_response": _crit(tr),
        "coherence_cohesion": _crit(cc),
        "lexical_resource": _crit(lr),
        "grammatical_range_accuracy": _crit(gra),
        "errors": [],
    }
    base.update(flags)
    return Task2Examiner.model_validate(base)


def _norm1(ex, wc=200, mw=150):
    return normalize_examiner(ex, task_type=1, word_count=wc, min_words=mw)


def _norm2(ex, wc=300, mw=250):
    return normalize_examiner(ex, task_type=2, word_count=wc, min_words=mw)


# ------------------------------- model routing ------------------------------ #

def test_examiner_model_routing():
    assert examiner_model(1) is Task1Examiner
    assert examiner_model(2) is Task2Examiner


def test_criterion_names_differ_by_task():
    assert "Task Achievement" in _norm1(_task1(6, 6, 6, 6))["criteria"]
    assert "Task Response" in _norm2(_task2(6, 6, 6, 6))["criteria"]


# ------------------------------- overall band ------------------------------- #

def test_overall_is_mean_half_up():
    # 7,7,6.5,6.5 -> mean 6.75 -> 7.0 (half-up, not banker's)
    assert _norm2(_task2(7, 7, 6.5, 6.5))["overall"] == 7.0
    # 6,6,6,6 -> 6.0
    assert _norm2(_task2(6, 6, 6, 6))["overall"] == 6.0
    # 6.5,6,6,5.5 -> mean 6.0 -> 6.0
    assert _norm2(_task2(6.5, 6, 6, 5.5))["overall"] == 6.0


def test_overall_not_taken_from_model():
    # Even if every criterion is 9 the overall is recomputed (not inflated input).
    assert _norm2(_task2(9, 9, 9, 9))["overall"] == 9.0


def test_band_snapping_to_half_steps():
    c = _norm2(_task2(6.7, 6.2, 6.0, 6.0))["criteria"]
    assert c["Task Response"] == 6.5   # 6.7 -> 6.5
    assert c["Coherence & Cohesion"] == 6.0  # 6.2 -> 6.0


# --------------------------- Task 1 hard penalties -------------------------- #

def test_task1_missing_overview_caps_task_achievement_at_5():
    n = _norm1(_task1(8, 8, 8, 8, overview_present=False))
    assert n["criteria"]["Task Achievement"] == 5.0


def test_task1_fabricated_data_caps_at_4():
    n = _norm1(_task1(8, 8, 8, 8, fabricated_data=True))
    assert n["criteria"]["Task Achievement"] == 4.0


def test_task1_missing_comparisons_caps_at_5():
    n = _norm1(_task1(7, 7, 7, 7, key_comparisons_present=False))
    assert n["criteria"]["Task Achievement"] == 5.0


def test_task1_fabrication_dominates_other_caps():
    n = _norm1(_task1(8, 8, 8, 8, overview_present=False, fabricated_data=True))
    assert n["criteria"]["Task Achievement"] == 4.0  # lowest cap wins


# --------------------------- Task 2 hard penalties -------------------------- #

def test_task2_off_topic_caps_task_response_at_3():
    n = _norm2(_task2(8, 8, 8, 8, off_topic=True))
    assert n["criteria"]["Task Response"] == 3.0


def test_task2_unclear_position_caps_at_5():
    n = _norm2(_task2(7, 7, 7, 7, position_clear=False))
    assert n["criteria"]["Task Response"] == 5.0


def test_task2_partial_answer_caps_at_5():
    n = _norm2(_task2(7, 7, 7, 7, all_parts_addressed=False))
    assert n["criteria"]["Task Response"] == 5.0


# ------------------------------ under-length -------------------------------- #

def test_task2_underlength_bands():
    assert _norm2(_task2(8, 8, 8, 8), wc=100, mw=250)["criteria"]["Task Response"] == 4.0  # <50%
    assert _norm2(_task2(8, 8, 8, 8), wc=170, mw=250)["criteria"]["Task Response"] == 5.0  # <75%
    assert _norm2(_task2(8, 8, 8, 8), wc=210, mw=250)["criteria"]["Task Response"] == 6.0  # <90%
    # at/above minimum: no automatic cap
    assert _norm2(_task2(8, 8, 8, 8), wc=300, mw=250)["criteria"]["Task Response"] == 8.0


# --------------------------- error -> mistake mapping ----------------------- #

def test_errors_become_mistakes_with_clamped_severity():
    ex = Task2Examiner.model_validate({
        "task_response": _crit(6), "coherence_cohesion": _crit(6),
        "lexical_resource": _crit(6), "grammatical_range_accuracy": _crit(6),
        "errors": [
            {"category": "grammar", "subskill": "articles", "severity": 2,
             "snippet": "in the society", "correction": "in society",
             "explanation": "no article with general nouns"},
            {"category": "vocabulary", "subskill": "repetition", "severity": 1,
             "snippet": "important", "correction": "vary the word"},
        ],
    })
    fb = build_feedback(_norm2(ex), None, task_type=2)
    cats = {m.category for m in fb.mistakes}
    assert cats == {"grammar", "vocabulary"}
    assert all(1 <= m.severity <= 3 for m in fb.mistakes)


def test_identical_correction_errors_are_not_persisted_as_mistakes():
    ex = Task2Examiner.model_validate({
        "task_response": _crit(7), "coherence_cohesion": _crit(7),
        "lexical_resource": _crit(7), "grammatical_range_accuracy": _crit(7),
        "errors": [
            {"category": "grammar", "subskill": "style", "severity": 1,
             "snippet": "This sentence is already correct.",
             "correction": "This sentence is already correct.",
             "explanation": "Optional style note, not a real correction."},
            {"category": "grammar", "subskill": "articles", "severity": 1,
             "snippet": "in the society", "correction": "in society",
             "explanation": "No article with general nouns."},
        ],
    })
    fb = build_feedback(_norm2(ex), None, task_type=2)
    assert len(fb.mistakes) == 1
    assert fb.mistakes[0].subskill == "articles"


def test_punctuation_subskill_is_normalized_from_model_slips():
    ex = Task2Examiner.model_validate({
        "task_response": _crit(7), "coherence_cohesion": _crit(7),
        "lexical_resource": _crit(7), "grammatical_range_accuracy": _crit(7),
        "errors": [
            {"category": "grammar", "subskill": "articles", "severity": 1,
             "snippet": "In the modern world many students",
             "correction": "In the modern world, many students",
             "explanation": "A comma is needed after an introductory phrase."},
        ],
    })
    fb = build_feedback(_norm2(ex), None, task_type=2)
    assert fb.mistakes[0].subskill == "punctuation"


# ----------------------------- feedback assembly ---------------------------- #

def test_build_feedback_with_coaching():
    ex = _task2(6, 6, 6, 5.5)
    coaching = CoachResult.model_validate({
        "strengths": ["clear position"],
        "weaknesses": ["thin support"],
        "priorities": ["Add a concrete example to each body paragraph"],
        "roadmap": [{"target_band": 6.5, "actions": ["develop ideas", "fix article errors"]}],
        "summary": "Develop your examples to move from 6.0 to 6.5.",
    })
    fb = build_feedback(_norm2(ex), coaching, task_type=2)
    assert fb.band == 6.0
    assert fb.strengths == ["clear position"]
    assert fb.roadmap and fb.roadmap[0]["target_band"] == 6.5
    assert "6.5" in fb.summary
    assert fb.criteria_notes["Task Response"]


def test_build_feedback_without_coaching_degrades_gracefully():
    ex = Task2Examiner.model_validate({
        "task_response": _crit(5), "coherence_cohesion": _crit(6),
        "lexical_resource": _crit(6), "grammatical_range_accuracy": _crit(6),
        "errors": [{"category": "grammar", "subskill": "tense", "severity": 2,
                    "snippet": "he go", "correction": "he goes"}],
    })
    fb = build_feedback(_norm2(ex), None, task_type=2)
    assert fb.band == 6.0  # (5+6+6+6)/4 = 5.75 -> 6.0 (half-up)
    assert fb.strengths == [] and fb.roadmap == []
    assert fb.suggestions  # falls back to error corrections
    assert fb.mistakes and fb.mistakes[0].subskill == "tense"


# ------------------------- calibration band fixtures ------------------------ #
# Each fixture is an examiner verdict at a target level; we assert the overall
# the normalization layer would award (the number the student actually sees).

CALIBRATION_T2 = [
    ("band4", _task2(4, 4, 4, 4), 4.0),
    ("band5", _task2(5, 5, 5, 5), 5.0),
    ("band6", _task2(6, 6, 6, 5.5), 6.0),   # mean 5.875 -> 6.0
    ("band7", _task2(7, 7, 6.5, 6.5), 7.0),  # mean 6.75 -> 7.0
    ("band8", _task2(8, 8, 7.5, 8), 8.0),    # mean 7.875 -> 8.0
]

CALIBRATION_T1 = [
    ("band4", _task1(4, 4, 4, 4), 4.0),
    ("band5", _task1(5, 5, 5, 5), 5.0),
    ("band6", _task1(6, 6, 6, 5.5), 6.0),
    ("band7", _task1(7, 7, 6.5, 6.5), 7.0),
    ("band8", _task1(8, 8, 7.5, 8), 8.0),
]


@pytest.mark.parametrize("name,ex,expected", CALIBRATION_T2, ids=[c[0] for c in CALIBRATION_T2])
def test_calibration_task2(name, ex, expected):
    assert _norm2(ex)["overall"] == expected


@pytest.mark.parametrize("name,ex,expected", CALIBRATION_T1, ids=[c[0] for c in CALIBRATION_T1])
def test_calibration_task1(name, ex, expected):
    assert _norm1(ex)["overall"] == expected
