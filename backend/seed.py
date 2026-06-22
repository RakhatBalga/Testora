"""Populate the database with sample Reading and Listening tests.

Run from the backend/ folder:  python seed.py
Safe to re-run: it clears existing tests/sections/questions first.
"""
from app.database import SessionLocal
from app.models.test import Test, Section, Question
from app.models.attempt import AnswerRecord, Attempt
from app.models.writing import WritingTask, WritingSubmission
from app.models.speaking import SpeakingTask, SpeakingSubmission


def run():
    db = SessionLocal()
    try:
        # clear old data so the script can be re-run
        db.query(AnswerRecord).delete()
        db.query(Attempt).delete()
        db.query(Question).delete()
        db.query(Section).delete()
        db.query(Test).delete()
        db.query(WritingSubmission).delete()
        db.query(WritingTask).delete()
        db.query(SpeakingSubmission).delete()
        db.query(SpeakingTask).delete()
        db.commit()

        reading = Test(
            title="Academic Reading Practice 1",
            test_type="reading",
            description="One passage with a mix of IELTS question types.",
            duration_minutes=20,
        )
        reading.sections = [
            Section(
                order=1,
                title="Section 1 — The Great Barrier Reef",
                instructions="Read the passage and answer questions 1–5.",
                passage=(
                    "The Great Barrier Reef is the world's largest coral reef system, "
                    "located off the coast of Queensland, Australia. It is composed of "
                    "over 2,900 individual reefs and 900 islands stretching for over "
                    "2,300 kilometres. The reef is home to a wide diversity of marine "
                    "life, including over 1,500 species of fish and 400 types of coral. "
                    "It is the only living structure on Earth visible from space. "
                    "Rising sea temperatures, however, have caused several mass "
                    "bleaching events in recent decades, threatening its survival."
                ),
                questions=[
                    Question(
                        order=1,
                        text="Where is the Great Barrier Reef located?",
                        question_type="single_choice",
                        options=["Brazil", "Australia", "Indonesia", "Mexico"],
                        correct_answer=["Australia"],
                    ),
                    Question(
                        order=2,
                        text="The reef can be seen from space.",
                        question_type="true_false_notgiven",
                        options=["True", "False", "Not Given"],
                        correct_answer=["True"],
                    ),
                    Question(
                        order=3,
                        text="The reef stretches for over ______ kilometres.",
                        question_type="fill_blank",
                        options=None,
                        correct_answer=["2300", "2,300"],
                    ),
                    Question(
                        order=4,
                        text="Which TWO threats or facts are mentioned in the passage?",
                        question_type="multiple_choice",
                        options=[
                            "Rising sea temperatures",
                            "Overfishing",
                            "Mass bleaching events",
                            "Oil spills",
                        ],
                        correct_answer=["Rising sea temperatures", "Mass bleaching events"],
                    ),
                    Question(
                        order=5,
                        text="How many species of fish live in the reef? (write a number)",
                        question_type="short_answer",
                        options=None,
                        correct_answer=["1500", "1,500", "over 1500", "over 1,500"],
                    ),
                ],
            ),
        ]

        listening = Test(
            title="Listening Practice 1",
            test_type="listening",
            description="Listen to the audio clip and answer the questions.",
            duration_minutes=15,
        )
        listening.sections = [
            Section(
                order=1,
                title="Section 1 — Audio clip",
                instructions="Listen and answer questions 1–3.",
                audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
                questions=[
                    Question(
                        order=1,
                        text="What is the main topic of the recording?",
                        question_type="single_choice",
                        options=["Travel", "Cooking", "Music", "Science"],
                        correct_answer=["Music"],
                    ),
                    Question(
                        order=2,
                        text="The recording is a live performance.",
                        question_type="true_false_notgiven",
                        options=["True", "False", "Not Given"],
                        correct_answer=["Not Given"],
                    ),
                    Question(
                        order=3,
                        text="Approximately how long is the recording? (in minutes)",
                        question_type="short_answer",
                        options=None,
                        correct_answer=["6", "six"],
                    ),
                ],
            ),
        ]

        writing_t1 = WritingTask(
            task_type=1,
            title="Writing Task 1 — Bar chart",
            prompt=(
                "The chart below shows the number of international students enrolled "
                "at a university over four years (2019–2022). Summarise the information "
                "by selecting and reporting the main features, and make comparisons "
                "where relevant. Write at least 150 words."
            ),
            image_url=None,
            min_words=150,
            duration_minutes=20,
        )
        writing_t2 = WritingTask(
            task_type=2,
            title="Writing Task 2 — Opinion essay",
            prompt=(
                "Some people believe that technology has made our lives more complex, "
                "while others think it has made life easier. Discuss both views and "
                "give your own opinion. Write at least 250 words."
            ),
            image_url=None,
            min_words=250,
            duration_minutes=40,
        )

        speaking_p1 = SpeakingTask(
            part=1,
            questions=[
                "Where do you live now?",
                "What do you like about your neighbourhood?",
                "Do you prefer studying in the morning or evening?",
            ],
            prep_seconds=15,
            speak_seconds=60,
        )
        speaking_p2 = SpeakingTask(
            part=2,
            questions=[
                "Describe a skill you would like to learn.",
                "You should say what the skill is, why you want to learn it, how you would learn it, and how it could help you in the future.",
            ],
            prep_seconds=60,
            speak_seconds=120,
        )
        speaking_p3 = SpeakingTask(
            part=3,
            questions=[
                "Why do people continue learning new skills as adults?",
                "How has technology changed the way people learn?",
                "Should schools teach more practical life skills?",
            ],
            prep_seconds=20,
            speak_seconds=90,
        )

        db.add_all([
            reading,
            listening,
            writing_t1,
            writing_t2,
            speaking_p1,
            speaking_p2,
            speaking_p3,
        ])
        db.commit()
        print(
            f"Seeded: {reading.title}, {listening.title}, "
            f"{writing_t1.title}, {writing_t2.title}, "
            "Speaking Parts 1-3"
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
