import re

from app.services.ai.base import Feedback, WritingGrader, SpeakingGrader


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

        return Feedback(
            band=overall, criteria=criteria, summary=summary, suggestions=suggestions
        )


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
