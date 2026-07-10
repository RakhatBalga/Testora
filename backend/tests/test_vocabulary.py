"""Offline (mock) vocabulary coach — the part that must work without an LLM.

Enrichment degrades honestly; the daily quiz still builds real cloze recall
questions from the sentence each word was saved from. No DB is touched.
"""
from app.infrastructure.ai.vocab import MockVocabularyCoach


def test_mock_enrich_degrades_without_crashing():
    coach = MockVocabularyCoach()
    info = coach.enrich_word(
        word="ubiquitous",
        context="Smartphones are ubiquitous now.",
        native_language="Russian",
    )
    assert info.error is False
    assert info.word == "ubiquitous"
    # The example is pulled from the sentence the word was saved from.
    assert "ubiquitous" in info.example.lower()
    payload = info.to_dict()
    assert {"meaning", "synonyms", "alternatives", "translation", "example"} <= set(payload)


def test_mock_quiz_builds_cloze_questions_from_context():
    coach = MockVocabularyCoach()
    words = [
        {"word": "ubiquitous", "context": "Smartphones are ubiquitous in modern life."},
        {"word": "mitigate", "context": "Planting trees can mitigate flooding."},
        {"word": "candid", "context": "She gave a candid answer."},
        {"word": "resilient", "context": "The economy proved resilient."},
    ]
    quiz = coach.generate_quiz(words=words, native_language="Russian", num_questions=4)
    assert quiz.error is False
    assert len(quiz.questions) >= 1
    for q in quiz.questions:
        # The correct option is the saved word, blanked out of its own sentence.
        assert q.options[q.answer_index].lower() == q.word.lower()
        assert "_____" in q.prompt
        assert 2 <= len(q.options) <= 4


def test_mock_quiz_skips_words_without_usable_context():
    coach = MockVocabularyCoach()
    words = [{"word": "serendipity", "context": ""}]
    quiz = coach.generate_quiz(words=words, native_language=None, num_questions=4)
    # No sentence to blank -> no question, but no crash.
    assert quiz.questions == []


def test_mock_quiz_is_deterministic():
    coach = MockVocabularyCoach()
    words = [
        {"word": "alpha", "context": "The alpha value is high."},
        {"word": "beta", "context": "We tested the beta release."},
        {"word": "gamma", "context": "Gamma rays are energetic."},
    ]
    first = coach.generate_quiz(words=words, native_language=None, num_questions=3)
    second = coach.generate_quiz(words=words, native_language=None, num_questions=3)
    assert [(q.word, q.options, q.answer_index) for q in first.questions] == [
        (q.word, q.options, q.answer_index) for q in second.questions
    ]
