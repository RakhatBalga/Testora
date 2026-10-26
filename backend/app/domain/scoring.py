import re
import unicodedata

_QUOTES = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u2013": "-",
        "\u2014": "-",
    }
)
_EDGE_PUNCT = " .,;:!?\"'`()[]"
_SPACES_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[\w]+(?:[-'][\w]+)*", re.UNICODE)


def normalize_answer(value: str) -> str:
    """Canonical form for comparing answers.

    Case, surrounding whitespace/punctuation, repeated spaces and curly vs
    straight quotes never decide whether an answer is right.
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).translate(_QUOTES).lower()
    return _SPACES_RE.sub(" ", text).strip(_EDGE_PUNCT).strip()


def as_list(value) -> list[str]:
    """Coerce a stored/submitted answer into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def display_answer(value) -> str:
    return ", ".join(as_list(value))


def answer_word_count(value: str) -> int:
    """Count lexical tokens; hyphenated compounds count as one IELTS answer word."""
    return len(_WORD_RE.findall(value or ""))


def is_correct(question, user_answer) -> bool:
    """Shared answer check for Reading and Listening questions."""
    correct = as_list(question.correct_answer)
    user = as_list(user_answer)

    if question.question_type == "multiple_choice":
        return {normalize_answer(u) for u in user} == {normalize_answer(c) for c in correct}

    # single answer types (choice / tf-ng / yn-ng / matching / completion):
    # the user's single answer must match one of the acceptable answers.
    if not user:
        return False
    word_limit = (getattr(question, "question_metadata", None) or {}).get("word_limit")
    if word_limit and answer_word_count(user[0]) > int(word_limit):
        return False
    return normalize_answer(user[0]) in {normalize_answer(c) for c in correct}


# Human labels for the per-question-type result breakdown.
QUESTION_TYPE_LABELS = {
    "single_choice": "Multiple Choice",
    "multiple_choice": "Multiple Answer",
    "true_false_notgiven": "True / False / Not Given",
    "yes_no_not_given": "Yes / No / Not Given",
    "matching": "Matching",
    "matching_headings": "Matching Headings",
    "matching_information": "Matching Information",
    "sentence_completion": "Sentence Completion",
    "summary_completion": "Summary Completion",
    "fill_blank": "Completion",
    "short_answer": "Short Answer",
}


def question_type_label(qtype: str) -> str:
    return QUESTION_TYPE_LABELS.get(qtype, qtype.replace("_", " ").title())


def build_breakdown(graded: list[dict]) -> list[dict]:
    """Aggregate graded answers into per-question-type performance stats.

    Returns a list of {question_type, label, correct, total, accuracy} sorted by
    accuracy ascending (weakest type first), so the result screen leads with what
    needs work.
    """
    buckets: dict[str, dict] = {}
    for item in graded:
        qtype = item["question_type"]
        b = buckets.setdefault(qtype, {"correct": 0, "total": 0})
        b["total"] += 1
        if item["is_correct"]:
            b["correct"] += 1

    out = [
        {
            "question_type": qtype,
            "label": question_type_label(qtype),
            "correct": b["correct"],
            "total": b["total"],
            "accuracy": round(b["correct"] / b["total"] * 100) if b["total"] else 0,
        }
        for qtype, b in buckets.items()
    ]
    out.sort(key=lambda x: (x["accuracy"], x["label"]))
    return out


def grade_attempt(questions, answers_map):
    """Compare user answers against the correct ones across all question types.

    questions: list of Question ORM objects.
    answers_map: dict of question_id -> user answer (str or list[str]).

    Returns (graded, score) where graded is a list of dicts ready for the
    AnswerResult schema and score is the number of correct answers.
    """
    graded = []
    score = 0
    for question in questions:
        user_answer = answers_map.get(question.id)
        correct_now = is_correct(question, user_answer)
        if correct_now:
            score += 1
        graded.append(
            {
                "question_id": question.id,
                "text": question.text,
                "question_type": question.question_type,
                "user_answer": display_answer(user_answer) or None,
                "correct_answer": display_answer(question.correct_answer),
                "is_correct": correct_now,
                "explanation": getattr(question, "explanation", None),
            }
        )
    return graded, score
