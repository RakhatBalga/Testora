"""Seed a full IELTS Listening test: 4 sections, 40 questions.

Idempotent for this title. Uses public SoundHelix MP3s as placeholder audio
(one clip per section) — swap audio_url for real recordings later.

Run from backend/:  venv/bin/python seed_listening.py
"""
from app.database import SessionLocal
from app.models.test import Test, Section, Question
from app.models.attempt import Attempt, AnswerRecord

TITLE = "Listening Test 1 (Full)"

AUDIO = [
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
    "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3",
]


def _q(order, text, qtype, correct, options=None, explanation=None):
    return Question(
        order=order,
        text=text,
        question_type=qtype,
        options=options,
        correct_answer=correct if isinstance(correct, list) else [correct],
        explanation=explanation,
    )


def build_test() -> Test:
    test = Test(
        title=TITLE,
        test_type="listening",
        description="Full-length Listening test: 4 sections, 40 questions, ~30 minutes.",
        duration_minutes=32,
        difficulty="Medium",
    )

    # ---- Section 1 (Q1–10): a phone enquiry — FORM COMPLETION ----
    s1 = Section(
        order=1,
        title="Section 1 — Accommodation enquiry",
        instructions="Questions 1–10. Complete the form below. Write ONE WORD AND/OR A NUMBER for each answer.",
        audio_url=AUDIO[0],
        questions=[
            _q(1, "Caller's surname:", "fill_blank", ["Hampton"], None, "The caller spells out H-A-M-P-T-O-N."),
            _q(2, "Type of accommodation required:", "fill_blank", ["studio", "studio flat"], None, "She asks for a studio flat."),
            _q(3, "Maximum weekly rent (£):", "fill_blank", ["180", "£180"], None, "Her budget is up to £180 a week."),
            _q(4, "Preferred area of the city:", "fill_blank", ["north", "the north"], None, "She prefers the north of the city, near work."),
            _q(5, "Move-in month:", "fill_blank", ["September", "Sept"], None, "She wants to move in in September."),
            _q(6, "Length of let (months):", "fill_blank", ["12", "twelve"], None, "A twelve-month contract is requested."),
            _q(7, "Essential feature:", "fill_blank", ["parking", "car park"], None, "Off-street parking is essential."),
            _q(8, "Pet to be kept:", "fill_blank", ["cat", "a cat"], None, "She mentions she has a cat."),
            _q(9, "Best contact time:", "fill_blank", ["evening", "evenings"], None, "She asks to be called in the evening."),
            _q(10, "Reference number quoted:", "fill_blank", ["472", "C472"], None, "The agent gives reference C472."),
        ],
    )

    # ---- Section 2 (Q11–20): tour of a centre — MAP LABELLING + MULTIPLE CHOICE ----
    map_opts = ["A", "B", "C", "D", "E", "F", "G", "H"]
    s2 = Section(
        order=2,
        title="Section 2 — Visitor centre tour",
        instructions=(
            "Questions 11–15: Label the map. Choose the correct letter A–H for each place. "
            "Questions 16–20: Choose the correct answer."
        ),
        audio_url=AUDIO[1],
        questions=[
            _q(11, "Map: Information desk", "matching", "A", map_opts, "It is just inside the main entrance — A."),
            _q(12, "Map: Café", "matching", "C", map_opts, "The café is past the gift shop on the right — C."),
            _q(13, "Map: Lecture theatre", "matching", "F", map_opts, "The theatre is at the end of the north corridor — F."),
            _q(14, "Map: Toilets", "matching", "D", map_opts, "Toilets are opposite the café — D."),
            _q(15, "Map: Exhibition hall", "matching", "G", map_opts, "The exhibition hall is upstairs — G."),
            _q(16, "The centre first opened to the public in:", "single_choice", "2008",
               ["1998", "2008", "2012"], "The guide says it opened in 2008."),
            _q(17, "Visitors are NOT allowed to:", "single_choice", "touch the exhibits",
               ["take photographs", "touch the exhibits", "bring children"],
               "Photography is fine, but touching exhibits is prohibited."),
            _q(18, "The most popular attraction is the:", "single_choice", "planetarium",
               ["aquarium", "planetarium", "garden"], "The planetarium draws the biggest crowds."),
            _q(19, "Guided tours start every:", "single_choice", "30 minutes",
               ["15 minutes", "30 minutes", "hour"], "Tours leave every half hour."),
            _q(20, "The shop sells mainly:", "single_choice", "books",
               ["books", "clothing", "food"], "The shop specialises in books."),
        ],
    )

    # ---- Section 3 (Q21–30): student discussion — MATCHING + NOTE COMPLETION ----
    people = ["Maria", "Tom", "Both"]
    s3 = Section(
        order=3,
        title="Section 3 — Project tutorial",
        instructions=(
            "Questions 21–25: Who makes each comment? Choose Maria, Tom or Both. "
            "Questions 26–30: Complete the notes. Write NO MORE THAN TWO WORDS."
        ),
        audio_url=AUDIO[2],
        questions=[
            _q(21, "The reading list was too long.", "matching", "Maria", people, "Maria complains about the reading list."),
            _q(22, "The deadline should be extended.", "matching", "Both", people, "Both agree the deadline is tight."),
            _q(23, "More data is needed for the survey.", "matching", "Tom", people, "Tom wants a larger sample."),
            _q(24, "The tutor was very helpful.", "matching", "Maria", people, "Maria praises the tutor."),
            _q(25, "The presentation slides need redesigning.", "matching", "Tom", people, "Tom dislikes the current slides."),
            _q(26, "Project focus: effects of ____ on sleep.", "fill_blank", ["caffeine"], None, "They study caffeine and sleep."),
            _q(27, "Number of participants:", "fill_blank", ["40", "forty"], None, "Forty participants are recruited."),
            _q(28, "Study duration: ____ weeks.", "fill_blank", ["six", "6"], None, "The study runs for six weeks."),
            _q(29, "Main method of recording data:", "fill_blank", ["diary", "diaries", "sleep diary"], None, "Participants keep a sleep diary."),
            _q(30, "Biggest expected problem:", "fill_blank", ["dropout", "drop-out"], None, "They worry about participant dropout."),
        ],
    )

    # ---- Section 4 (Q31–40): lecture — NOTE / SENTENCE COMPLETION ----
    s4 = Section(
        order=4,
        title="Section 4 — Lecture: urban beekeeping",
        instructions="Questions 31–40. Complete the notes. Write ONE WORD ONLY for each answer.",
        audio_url=AUDIO[3],
        questions=[
            _q(31, "Cities can be warmer than the surrounding ____.", "fill_blank", ["countryside", "country"], None, "Urban heat lets bees forage longer."),
            _q(32, "Urban flowers provide a longer ____ season.", "fill_blank", ["flowering", "flower"], None, "Gardens extend the flowering season."),
            _q(33, "A single hive can contain up to 50,000 ____.", "fill_blank", ["bees"], None, "Hives hold tens of thousands of bees."),
            _q(34, "Bees navigate using the position of the ____.", "fill_blank", ["sun"], None, "They orient by the sun."),
            _q(35, "The 'waggle ____' communicates distance to food.", "fill_blank", ["dance"], None, "The waggle dance signals direction and distance."),
            _q(36, "City honey often has a more varied ____.", "fill_blank", ["flavour", "flavor", "taste"], None, "Diverse forage gives varied flavour."),
            _q(37, "The main threat to bees is loss of ____.", "fill_blank", ["habitat"], None, "Habitat loss is the chief threat."),
            _q(38, "Rooftop hives should be sheltered from the ____.", "fill_blank", ["wind"], None, "Wind exposure harms rooftop hives."),
            _q(39, "Beekeepers must inspect hives for ____.", "fill_blank", ["disease", "diseases", "mites"], None, "Regular inspection catches disease."),
            _q(40, "Urban beekeeping can raise public ____ of nature.", "fill_blank", ["awareness"], None, "It boosts public awareness."),
        ],
    )

    test.sections = [s1, s2, s3, s4]
    return test


def run():
    db = SessionLocal()
    try:
        for t in db.query(Test).filter(Test.title == TITLE).all():
            ids = [a.id for a in db.query(Attempt).filter(Attempt.test_id == t.id).all()]
            if ids:
                db.query(AnswerRecord).filter(AnswerRecord.attempt_id.in_(ids)).delete(
                    synchronize_session=False
                )
                db.query(Attempt).filter(Attempt.test_id == t.id).delete(synchronize_session=False)
            db.delete(t)
        db.commit()

        test = build_test()
        db.add(test)
        db.commit()
        n = sum(len(s.questions) for s in test.sections)
        print(f"Seeded: {test.title} — {len(test.sections)} sections, {n} questions.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
