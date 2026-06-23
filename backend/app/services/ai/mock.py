import re
from collections import Counter

from app.services.ai.base import Feedback, MistakeItem, WritingGrader, SpeakingGrader

# Small stopword set so vocabulary detectors focus on content words.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "be", "been", "it", "this", "that", "these",
    "those", "as", "at", "by", "from", "we", "i", "you", "they", "he", "she",
    "their", "our", "my", "your", "its", "not", "can", "will", "would", "have",
    "has", "had", "do", "does", "did", "so", "if", "than", "then", "there",
}
# Basic, non-academic words that cap Lexical Resource when overused.
_BASIC_WORDS = {"good", "bad", "very", "thing", "things", "important", "big", "nice", "get", "lot"}


def _round_half(x: float) -> float:
    """Round to the nearest IELTS half-band (0.5 step), clamped to 0-9."""
    x = max(0.0, min(9.0, x))
    return round(x * 2) / 2


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


class MockWritingGrader(WritingGrader):
    """Free heuristic grader. No AI calls — estimates a band from surface features."""

    def grade(self, *, task_type: int, prompt: str, text: str, min_words: int) -> Feedback:
        words = _count_words(text)
        sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
        sentence_count = max(1, len(sentences))
        avg_sentence_len = words / sentence_count
        unique_ratio = (
            len({w.lower() for w in re.findall(r"\b[\w'-]+\b", text)}) / words
            if words
            else 0
        )

        suggestions: list[str] = []

        # Task achievement: driven mostly by hitting the word count.
        if words >= min_words:
            task = 6.5
        elif words >= min_words * 0.8:
            task = 5.5
            suggestions.append(
                f"Write at least {min_words} words — you wrote {words}."
            )
        else:
            task = 4.0
            suggestions.append(
                f"Your answer is too short ({words}/{min_words} words). Develop your ideas further."
            )

        # Coherence: reward a sensible number of paragraphs and sentence lengths.
        paragraphs = [p for p in text.split("\n") if p.strip()]
        if len(paragraphs) >= 3 and 8 <= avg_sentence_len <= 25:
            coherence = 6.5
        elif len(paragraphs) >= 2:
            coherence = 5.5
            suggestions.append("Organise your answer into clear paragraphs (intro, body, conclusion).")
        else:
            coherence = 4.5
            suggestions.append("Split your text into paragraphs to improve structure.")

        # Lexical resource: vocabulary variety.
        if unique_ratio >= 0.55:
            lexical = 6.5
        elif unique_ratio >= 0.4:
            lexical = 5.5
        else:
            lexical = 4.5
            suggestions.append("Try to use a wider range of vocabulary and avoid repetition.")

        # Grammar: rough proxy via sentence-length variety.
        if 10 <= avg_sentence_len <= 22:
            grammar = 6.0
        else:
            grammar = 5.0
            suggestions.append("Vary your sentence length and structure for better flow.")

        criteria = {
            "Task Achievement": _round_half(task),
            "Coherence & Cohesion": _round_half(coherence),
            "Lexical Resource": _round_half(lexical),
            "Grammatical Range & Accuracy": _round_half(grammar),
        }
        overall = _round_half(sum(criteria.values()) / len(criteria))

        if not suggestions:
            suggestions.append("Solid attempt. Keep practising to push past band 6.5.")

        summary = (
            f"Estimated band {overall} based on {words} words across "
            f"{len(paragraphs)} paragraph(s). This is an automatic estimate — "
            f"connect AI grading for detailed, criterion-level feedback."
        )

        mistakes = self._extract_mistakes(
            text=text,
            words=words,
            min_words=min_words,
            paragraphs=paragraphs,
            avg_sentence_len=avg_sentence_len,
        )

        return Feedback(
            band=overall,
            criteria=criteria,
            summary=summary,
            suggestions=suggestions,
            mistakes=mistakes,
        )

    def _extract_mistakes(
        self,
        *,
        text: str,
        words: int,
        min_words: int,
        paragraphs: list[str],
        avg_sentence_len: float,
    ) -> list[MistakeItem]:
        """Deterministic, text-derived mistakes. No AI — surface features only."""
        mistakes: list[MistakeItem] = []
        tokens = [w.lower() for w in re.findall(r"\b[\w'-]+\b", text)]
        counts = Counter(tokens)

        # Task Response — under-length answer.
        if words < min_words:
            mistakes.append(
                MistakeItem(
                    category="task_response",
                    subskill="answer_length",
                    severity=3 if words < min_words * 0.8 else 2,
                    snippet=f"{words} / {min_words} words",
                    correction=f"Develop your ideas to at least {min_words} words.",
                    explanation="An under-length response cannot fully address the task.",
                )
            )

        # Coherence — too few paragraphs.
        if len(paragraphs) < 3:
            mistakes.append(
                MistakeItem(
                    category="coherence",
                    subskill="paragraphing",
                    severity=2,
                    snippet=f"{len(paragraphs)} paragraph(s)",
                    correction="Use a clear intro, body paragraphs, and a conclusion.",
                    explanation="Too few paragraphs weakens organisation.",
                )
            )

        # Coherence — missing signposted conclusion.
        last = paragraphs[-1].lower() if paragraphs else ""
        if not any(p in last for p in ("conclusion", "to conclude", "overall", "in summary")):
            mistakes.append(
                MistakeItem(
                    category="coherence",
                    subskill="weak_conclusion",
                    severity=1,
                    correction="End with a concluding paragraph using a linking phrase.",
                    explanation="No clearly signposted conclusion.",
                )
            )

        # Vocabulary — overused content word.
        for word, c in counts.most_common():
            if word in _STOPWORDS or len(word) <= 2:
                continue
            if c >= 4:
                mistakes.append(
                    MistakeItem(
                        category="vocabulary",
                        subskill="word_repetition",
                        severity=1,
                        snippet=word,
                        correction=f"Use synonyms instead of repeating '{word}' ({c}×).",
                        explanation="Repetition limits Lexical Resource.",
                    )
                )
            break

        # Vocabulary — basic, non-academic words.
        found_basic = [w for w in _BASIC_WORDS if w in counts]
        if found_basic:
            mistakes.append(
                MistakeItem(
                    category="vocabulary",
                    subskill="basic_word",
                    severity=1,
                    snippet=", ".join(sorted(found_basic)[:3]),
                    correction="Replace basic words with academic alternatives.",
                    explanation="Simple word choice caps Lexical Resource.",
                )
            )

        # Grammar — sentence length extremes.
        if avg_sentence_len > 25:
            mistakes.append(
                MistakeItem(
                    category="grammar",
                    subskill="sentence_length",
                    severity=2,
                    correction="Break very long sentences; mix simple and complex forms.",
                    explanation="Overly long sentences hurt grammatical accuracy.",
                )
            )
        elif 0 < avg_sentence_len < 8:
            mistakes.append(
                MistakeItem(
                    category="grammar",
                    subskill="sentence_variety",
                    severity=2,
                    correction="Combine short sentences using complex structures.",
                    explanation="Mostly short, simple sentences limit grammatical range.",
                )
            )

        # Grammar — likely article problems (low article density).
        article_count = counts.get("a", 0) + counts.get("an", 0) + counts.get("the", 0)
        if words and article_count / words < 0.03:
            mistakes.append(
                MistakeItem(
                    category="grammar",
                    subskill="articles",
                    severity=2,
                    correction="Check article usage (a / an / the) before nouns.",
                    explanation="Very low article density often signals missing articles.",
                )
            )

        return mistakes


class MockSpeakingGrader(SpeakingGrader):
    """Free placeholder grader. Audio scoring needs real AI, so this defers."""

    def grade(
        self,
        *,
        part: int,
        questions: list[str],
        audio_path: str,
        transcript: str | None = None,
    ) -> Feedback:
        criteria = {
            "Fluency & Coherence": 0.0,
            "Lexical Resource": 0.0,
            "Grammatical Range & Accuracy": 0.0,
            "Pronunciation": 0.0,
        }
        return Feedback(
            band=0.0,
            criteria=criteria,
            summary=(
                "Your recording was saved. Automatic speaking assessment requires "
                "AI transcription and grading, which is not enabled yet. Connect the "
                "Claude provider to receive a band score and feedback."
            ),
            suggestions=["Speaking is awaiting manual or AI review."],
        )
