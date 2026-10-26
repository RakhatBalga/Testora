from app.domain.scoring import answer_word_count, build_breakdown, display_answer, is_correct

__all__ = ["answer_word_count", "grade_listening"]


def grade_listening(questions, answers_map):
    graded = []
    score = 0
    for question in questions:
        user_answer = answers_map.get(question.id)
        correct = is_correct(question, user_answer)
        score += int(correct)
        graded.append(
            {
                "question_id": question.id,
                "text": question.text,
                "question_type": question.question_type,
                "user_answer": display_answer(user_answer) or None,
                "correct_answer": display_answer(question.correct_answer),
                "is_correct": correct,
                "explanation": question.explanation,
            }
        )
    return graded, score, build_breakdown(graded)
