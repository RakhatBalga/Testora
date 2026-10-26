"""Hand-built text features for the classical-ML Writing baseline (pure Python).

FEATURE_VERSION must change whenever a feature's definition changes, because
saved models record it. These are surface features: they measure length, range
and fluency proxies, not whether the argument answers the prompt.
"""
import math
import re

FEATURE_VERSION = "writing-features.v1"

LINKERS = {
    "however", "therefore", "furthermore", "moreover", "consequently", "nevertheless",
    "nonetheless", "meanwhile", "additionally", "similarly", "conversely", "thus", "hence",
    "firstly", "secondly", "finally", "although", "whereas", "despite", "while",
}
LINKER_PHRASES = ("in contrast", "on the other hand", "for instance", "for example",
                  "as a result", "in conclusion", "in addition", "to conclude", "in particular")
SUBORDINATORS = {"because", "although", "though", "while", "whereas", "since", "unless",
                 "whether", "which", "who", "whose", "if", "when", "once", "before", "after"}

FEATURE_NAMES = (
    "task_type", "log_words", "n_sentences", "mean_sentence_len", "sd_sentence_len",
    "n_paragraphs", "ttr_root", "mattr_50", "mean_word_len", "long_word_ratio",
    "linker_rate", "subordinator_rate", "comma_rate",
    "err_lower_i", "err_no_capital", "err_no_space_after_punct", "err_repeat_word",
    "err_article_an", "err_letter_run", "err_double_space",
)


def _words(text):
    return re.findall(r"[A-Za-z']+", text)


def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _mattr(words, window=50):
    if len(words) < window:
        return len(set(words)) / len(words) if words else 0.0
    total = 0.0
    count = len(words) - window + 1
    for i in range(count):
        total += len(set(words[i:i + window])) / window
    return total / count


def extract(text: str, task_type: int = 2) -> dict[str, float]:
    words = _words(text)
    lower = [w.lower() for w in words]
    n = max(1, len(words))
    sentences = _sentences(text)
    lengths = [len(_words(s)) for s in sentences] or [0]
    mean_len = sum(lengths) / len(lengths)
    sd_len = math.sqrt(sum((x - mean_len) ** 2 for x in lengths) / len(lengths))
    paragraphs = [p for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    low_text = text.lower()
    linker_count = sum(w in LINKERS for w in lower) + sum(low_text.count(p) for p in LINKER_PHRASES)
    per100 = 100.0 / n
    return {
        "task_type": float(task_type),
        "log_words": math.log(n),
        "n_sentences": float(len(sentences)),
        "mean_sentence_len": mean_len,
        "sd_sentence_len": sd_len,
        "n_paragraphs": float(len(paragraphs)),
        "ttr_root": len(set(lower)) / math.sqrt(n),
        "mattr_50": _mattr(lower),
        "mean_word_len": sum(len(w) for w in words) / n,
        "long_word_ratio": sum(len(w) >= 7 for w in words) / n,
        "linker_rate": linker_count * per100,
        "subordinator_rate": sum(w in SUBORDINATORS for w in lower) * per100,
        "comma_rate": text.count(",") * per100,
        # Error-rate proxies (per 100 words). No dictionary or grammar checker is
        # used, so spelling and agreement errors are NOT measured.
        "err_lower_i": len(re.findall(r"(?<![A-Za-z'])i(?![A-Za-z'])", text)) * per100,
        "err_no_capital": sum(1 for s in sentences if s[0].isalpha() and s[0].islower()) * per100,
        "err_no_space_after_punct": len(re.findall(r"[a-z][,.;:][A-Za-z]", text)) * per100,
        "err_repeat_word": sum(a == b for a, b in zip(lower, lower[1:])) * per100,
        "err_article_an": (len(re.findall(r"\ba\s+[aeiou]\w+", low_text))
                           + len(re.findall(r"\ban\s+[bcdfgjklmnpqrstvwxz]\w+", low_text))) * per100,
        "err_letter_run": len(re.findall(r"([a-z])\1{2,}", low_text)) * per100,
        "err_double_space": len(re.findall(r"[^\s] {2,}[^\s]", text)) * per100,
    }


def vector(text: str, task_type: int = 2) -> list[float]:
    f = extract(text, task_type)
    return [f[name] for name in FEATURE_NAMES]


# Module-level (picklable) transformers for the sklearn pipelines in ml.train_writing.
# X is a sequence of (task_type, text) pairs.
def dense_matrix(X):
    import numpy as np
    return np.array([vector(text, task) for task, text in X], dtype=float)


def texts_of(X):
    return [text for _, text in X]
