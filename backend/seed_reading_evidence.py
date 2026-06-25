"""Populate evidence spans on the full Reading test (Reading Review highlighting).

Maps each question (by its global 1-based order across the test) to one or more
{paragraph, text} spans whose `text` appears verbatim in that section's passage.
`paragraph` is relative to the section (¶1..¶5). Questions that are genuinely
Not Given have NO evidence (None) — that absence is itself the lesson.

Runs in place (does NOT delete attempts). Run from backend/:
    venv/bin/python seed_reading_evidence.py
"""
from app.database import SessionLocal
from app.models.test import Test, Section, Question

TITLE = "Academic Reading Test 1 (Full)"

# global_question_number -> list of {paragraph, text} (paragraph relative to section)
EVIDENCE: dict[int, list[dict]] = {
    # Passage 1 — Octopus
    1: [{"paragraph": 1, "text": "the most intelligent invertebrate on Earth"}],
    2: [{"paragraph": 2, "text": "distributes roughly two-thirds of its neurons across its eight arms"}],
    # 3 — Not Given (no evidence)
    4: [{"paragraph": 3, "text": "recognise individual human keepers"}],
    # 5 — Not Given (no evidence)
    6: [{"paragraph": 2, "text": "across its eight arms"}],
    7: [{"paragraph": 4, "text": "specialised cells called chromatophores"}],
    8: [{"paragraph": 3, "text": "using coconut shells as portable shelters"}],
    9: [{"paragraph": 2, "text": "a form of distributed cognition"}],
    10: [{"paragraph": 4, "text": "the octopus's capacity for camouflage"}],
    11: [{"paragraph": 4, "text": "believed to be colour-blind"}],
    12: [{"paragraph": 3, "text": "open jars to reach food, navigate simple mazes"}],
    13: [{"paragraph": 5, "text": "die shortly after reproducing"}],
    # Passage 2 — Urban Park
    14: [{"paragraph": 1, "text": "green spaces in cities were private"}],
    15: [{"paragraph": 2, "text": "instruments of public health"}],
    16: [{"paragraph": 3, "text": "a vast work of engineering disguised as untouched nature"}],
    17: [{"paragraph": 4, "text": "a new emphasis on active recreation"}],
    18: [{"paragraph": 5, "text": "value parks for their environmental services"}],
    19: [{"paragraph": 1, "text": "did not take hold until the nineteenth century"}],
    20: [{"paragraph": 2, "text": "The catalyst was industrialisation"}],
    21: [{"paragraph": 3, "text": "opened in stages from 1858"}],
    22: [{"paragraph": 2, "text": "the lungs of the city"}],
    23: [{"paragraph": 3, "text": "dense planting and sunken roads"}],
    24: [{"paragraph": 4, "text": "Playgrounds, sports fields and swimming pools"}],
    25: [{"paragraph": 5, "text": "absorbing rainwater"}],
    26: [{"paragraph": 5, "text": "cooling neighbourhoods and sheltering urban wildlife"}],
    # Passage 3 — Machines Creative
    27: [{"paragraph": 1, "text": "could never enter"}],
    28: [{"paragraph": 2, "text": "many observers cannot distinguish from human work"}],
    # 29 — Not Given (no evidence)
    30: [{"paragraph": 3, "text": "sophisticated imitation"}],
    31: [{"paragraph": 5, "text": "Rather than replacing human creativity"}],
    32: [{"paragraph": 5, "text": "use AI as a collaborator"}],
    33: [{"paragraph": 4, "text": "both novel and valuable"}],
    34: [{"paragraph": 3, "text": "a mirror reflecting human creativity"}],
    35: [{"paragraph": 2, "text": "In blind tests"}],
    36: [{"paragraph": 3, "text": "does not intend to communicate anything"}],
    37: [{"paragraph": 4, "text": "requires consciousness, intention or lived experience"}],
    38: [{"paragraph": 2, "text": "moving, original and emotionally resonant"}],
    39: [{"paragraph": 3, "text": "the millions of human works"}],
    40: [{"paragraph": 5, "text": "authorship and originality"}],
}


def run():
    db = SessionLocal()
    try:
        test = db.query(Test).filter(Test.title == TITLE).first()
        if not test:
            print(f"Test not found: {TITLE!r}. Run seed_reading.py first.")
            return

        questions = (
            db.query(Question)
            .join(Section, Question.section_id == Section.id)
            .filter(Section.test_id == test.id)
            .order_by(Section.order, Question.order)
            .all()
        )

        updated = 0
        for idx, q in enumerate(questions, start=1):
            spans = EVIDENCE.get(idx)
            if spans is not None:
                q.evidence = spans
                updated += 1
        db.commit()
        print(f"Updated evidence on {updated}/{len(questions)} questions for {test.title}.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
