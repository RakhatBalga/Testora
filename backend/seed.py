"""Populate the database with sample Reading and Listening tests.

Run from the backend/ folder:  python seed.py
Safe to re-run: it clears existing tests/questions first.
"""
from app.database import SessionLocal
from app.models.test import Test, Question
from app.models.attempt import AnswerRecord, Attempt


def run():
    db = SessionLocal()
    try:
        # clear old data so the script can be re-run
        db.query(AnswerRecord).delete()
        db.query(Attempt).delete()
        db.query(Question).delete()
        db.query(Test).delete()
        db.commit()

        reading = Test(
            title="Reading Practice 1",
            test_type="reading",
            description="Short passage with multiple-choice questions.",
            duration_minutes=20,
            content=(
                "The Great Barrier Reef is the world's largest coral reef system, "
                "located off the coast of Queensland, Australia. It is composed of "
                "over 2,900 individual reefs and 900 islands stretching for over "
                "2,300 kilometres. The reef is home to a wide diversity of marine "
                "life and is the only living structure visible from space."
            ),
        )
        reading.questions = [
            Question(
                text="Where is the Great Barrier Reef located?",
                options=["Brazil", "Australia", "Indonesia", "Mexico"],
                correct_answer="Australia",
                order=1,
            ),
            Question(
                text="How many individual reefs make up the system?",
                options=["Over 900", "Over 1,500", "Over 2,900", "Over 5,000"],
                correct_answer="Over 2,900",
                order=2,
            ),
            Question(
                text="What is special about the reef from space?",
                options=[
                    "It is the brightest object",
                    "It is the only living structure visible",
                    "It cannot be seen",
                    "It looks like an island",
                ],
                correct_answer="It is the only living structure visible",
                order=3,
            ),
        ]

        listening = Test(
            title="Listening Practice 1",
            test_type="listening",
            description="Listen to the audio clip and answer the questions.",
            duration_minutes=15,
            audio_url="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        )
        listening.questions = [
            Question(
                text="What is the speaker's main topic?",
                options=["Travel", "Cooking", "Music", "Science"],
                correct_answer="Music",
                order=1,
            ),
            Question(
                text="How long is the recording?",
                options=["1 minute", "3 minutes", "6 minutes", "10 minutes"],
                correct_answer="6 minutes",
                order=2,
            ),
        ]

        db.add_all([reading, listening])
        db.commit()
        print(f"Seeded: {reading.title}, {listening.title}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
