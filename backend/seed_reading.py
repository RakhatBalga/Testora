"""Seed a full IELTS Academic Reading test: 3 passages, 40 questions.

Idempotent for this title — deletes any existing test named the same (and its
sections/questions/attempts via cascade), then inserts a fresh copy. Does NOT
touch listening/writing/speaking data.

Run from backend/:  venv/bin/python seed_reading.py
"""
from app.infrastructure.database import SessionLocal
from app.domain.models.test import Test, Section, Question
from app.domain.models.attempt import Attempt, AnswerRecord

TITLE = "Academic Reading Test 1 (Full)"


# --- Passage 1: paragraphs are numbered with a leading "¶N " marker that the
# frontend parses into numbered paragraphs. Keywords wrapped in **bold** are
# highlighted. ---
P1 = """The Hidden Intelligence of the Octopus

¶1 The octopus has long fascinated marine biologists for a simple reason: it is, by almost any measure, the most intelligent invertebrate on Earth. With a nervous system unlike that of any other animal, the octopus challenges our assumptions about where **intelligence** can arise and what form it must take.

¶2 Unlike vertebrates, whose neurons are concentrated in a central brain, the octopus distributes roughly two-thirds of its neurons across its eight arms. Each arm can, to a remarkable degree, act independently — tasting, touching and even making local decisions without consulting the central brain. Scientists describe this as a form of **distributed cognition**, a model of intelligence radically different from our own.

¶3 In laboratory settings, octopuses have demonstrated abilities once thought to belong only to mammals and birds. They can open jars to reach food, navigate simple mazes, and recognise individual human keepers. Some have been observed using coconut shells as portable shelters — a behaviour that researchers classify as genuine **tool use**.

¶4 Perhaps most striking is the octopus's capacity for camouflage. Within milliseconds it can alter the colour, pattern and even texture of its skin to match its surroundings. This is achieved not through conscious thought alone but through specialised cells called chromatophores, controlled directly by the nervous system. Curiously, octopuses are believed to be colour-blind, which makes the precision of their colour-matching all the more mysterious.

¶5 Yet for all their gifts, octopuses are profoundly solitary and short-lived. Most species survive only one to two years, and they typically die shortly after reproducing. This brief lifespan raises a puzzle: how does such sophisticated intelligence evolve in an animal that has almost no opportunity to learn from others of its kind?"""

P2 = """The Reinvention of the Urban Park

¶1 The public park as we know it is a surprisingly modern invention. For most of human history, green spaces in cities were private — the gardens of palaces and the estates of the wealthy. The idea that a city should provide open, landscaped land for the use of all its citizens did not take hold until the nineteenth century.

¶2 The catalyst was industrialisation. As factories drew vast populations into rapidly growing cities, reformers grew alarmed at the overcrowding, pollution and disease that followed. Parks were promoted not merely as ornaments but as instruments of public health — "the lungs of the city," as one campaigner famously put it.

¶3 New York's Central Park, opened in stages from 1858, became the model that much of the world would later imitate. Its designers deliberately concealed the surrounding city behind dense planting and sunken roads, creating the illusion of open countryside in the heart of the metropolis. The park was, in effect, a vast work of engineering disguised as untouched nature.

¶4 In the twentieth century the purpose of parks shifted again. Playgrounds, sports fields and swimming pools reflected a new emphasis on active recreation rather than quiet contemplation. Critics complained that the serene landscapes of the previous century were being cluttered, but the changes reflected the genuine demands of a broader public.

¶5 Today a third transformation is under way. Faced with climate change, planners increasingly value parks for their environmental services: absorbing rainwater, cooling neighbourhoods and sheltering urban wildlife. The park, once a refuge from the industrial city, has become a tool for making the modern city survivable."""

P3 = """Can Machines Be Creative?

¶1 For decades, creativity was regarded as the last refuge of human uniqueness — the one domain that machines, however powerful, could never enter. Recent advances in artificial intelligence have forced a reconsideration of that comfortable assumption.

¶2 Modern AI systems can now compose music, write poetry and generate images that many observers cannot distinguish from human work. In blind tests, audiences have judged machine-generated compositions to be moving, original and emotionally resonant. If the output is indistinguishable from human creativity, some argue, then the distinction itself may be meaningless.

¶3 Sceptics respond that this is an illusion. A machine, they point out, does not intend to communicate anything; it merely recombines patterns extracted from the millions of human works on which it was trained. What looks like originality, in this view, is sophisticated imitation — a mirror reflecting human creativity back at us rather than a genuine source of it.

¶4 The debate hinges partly on how creativity is defined. If creativity means producing work that is both novel and valuable, then machines may already qualify. If it requires consciousness, intention or lived experience, then current systems fall short, whatever the quality of their output.

¶5 Whatever the philosophical verdict, the practical consequences are already significant. Artists increasingly use AI as a collaborator, generating raw material that humans then select and refine. Rather than replacing human creativity, these tools may be reshaping it — extending what a single person can attempt, while raising uncomfortable questions about authorship and originality."""


def _q(order, text, qtype, correct, options=None, explanation=None, evidence=None):
    return Question(
        order=order,
        text=text,
        question_type=qtype,
        options=options,
        correct_answer=correct if isinstance(correct, list) else [correct],
        explanation=explanation,
        evidence=evidence,  # list of {"paragraph": int, "text": str} spans
    )


def build_test() -> Test:
    test = Test(
        title=TITLE,
        test_type="reading",
        description="Full-length Academic Reading: 3 passages, 40 questions, 60 minutes.",
        duration_minutes=60,
        difficulty="Medium",
    )

    tfng = ["True", "False", "Not Given"]
    ynng = ["Yes", "No", "Not Given"]

    # ---- Passage 1 — Questions 1–13 ----
    s1 = Section(
        order=1,
        title="Passage 1 — The Hidden Intelligence of the Octopus",
        instructions="You should spend about 20 minutes on Questions 1–13.",
        passage=P1,
        questions=[
            _q(1, "The octopus is considered the most intelligent of all invertebrates.",
               "true_false_notgiven", "True", tfng,
               "Paragraph 1 states it is 'the most intelligent invertebrate on Earth'."),
            _q(2, "Most of an octopus's neurons are located in its central brain.",
               "true_false_notgiven", "False", tfng,
               "Paragraph 2: two-thirds of its neurons are distributed across its arms, not the central brain."),
            _q(3, "Octopuses live longer than most other sea creatures.",
               "true_false_notgiven", "Not Given", tfng,
               "Lifespan is discussed (1–2 years) but no comparison with other sea creatures is made."),
            _q(4, "Octopuses can recognise the people who care for them.",
               "true_false_notgiven", "True", tfng,
               "Paragraph 3: they can 'recognise individual human keepers'."),
            _q(5, "Scientists agree on how octopus intelligence evolved.",
               "true_false_notgiven", "Not Given", tfng,
               "Paragraph 5 raises it as a 'puzzle'; whether scientists agree is never stated."),
            _q(6, "The octopus distributes about two-thirds of its neurons across its eight ______.",
               "fill_blank", ["arms", "arm"], None,
               "Paragraph 2: neurons are distributed 'across its eight arms'."),
            _q(7, "Colour-changing skin cells are known as ______.",
               "fill_blank", ["chromatophores", "chromatophore"], None,
               "Paragraph 4 names the cells 'chromatophores'."),
            _q(8, "Researchers regard an octopus's use of coconut shells as a form of ______.",
               "fill_blank", ["tool use", "tool-use"], None,
               "Paragraph 3 classifies this as 'genuine tool use'."),
            _q(9, "Which model of intelligence do scientists use to describe the octopus's arms acting independently?",
               "single_choice", "Distributed cognition",
               ["Central cognition", "Distributed cognition", "Reflexive cognition", "Collective cognition"],
               "Paragraph 2 calls it 'distributed cognition'."),
            _q(10, "What is described as the most striking ability of the octopus?",
               "single_choice", "Its camouflage",
               ["Its tool use", "Its camouflage", "Its maze-solving", "Its jar-opening"],
               "Paragraph 4: 'Perhaps most striking is the octopus's capacity for camouflage.'"),
            _q(11, "According to the passage, octopuses are believed to be unable to perceive ______.",
               "short_answer", ["colour", "color", "colours", "colors"], None,
               "Paragraph 4: 'octopuses are believed to be colour-blind'."),
            _q(12, "Which TWO behaviours have octopuses shown in laboratories?",
               "multiple_choice", ["Opening jars", "Navigating mazes"],
               ["Opening jars", "Building nests", "Navigating mazes", "Hunting in groups"],
               "Paragraph 3 lists opening jars and navigating simple mazes."),
            _q(13, "Most octopus species die shortly after they ______.",
               "short_answer", ["reproduce", "reproducing", "reproduction"], None,
               "Paragraph 5: 'they typically die shortly after reproducing'."),
        ],
    )

    # ---- Passage 2 — Questions 14–26 ----
    headings = [
        "A health remedy for the industrial city",
        "Nature as a feat of engineering",
        "A shift towards active use",
        "Parks as climate infrastructure",
        "The private origins of green space",
        "A decline in public interest",
    ]
    s2 = Section(
        order=2,
        title="Passage 2 — The Reinvention of the Urban Park",
        instructions="You should spend about 20 minutes on Questions 14–26.",
        passage=P2,
        questions=[
            _q(14, "Choose the correct heading for Paragraph 1.",
               "matching", "The private origins of green space", headings,
               "Paragraph 1 explains green spaces were once private."),
            _q(15, "Choose the correct heading for Paragraph 2.",
               "matching", "A health remedy for the industrial city", headings,
               "Paragraph 2 frames parks as instruments of public health."),
            _q(16, "Choose the correct heading for Paragraph 3.",
               "matching", "Nature as a feat of engineering", headings,
               "Paragraph 3 describes Central Park as engineering disguised as nature."),
            _q(17, "Choose the correct heading for Paragraph 4.",
               "matching", "A shift towards active use", headings,
               "Paragraph 4 covers the move to active recreation."),
            _q(18, "Choose the correct heading for Paragraph 5.",
               "matching", "Parks as climate infrastructure", headings,
               "Paragraph 5 values parks for environmental services."),
            _q(19, "The development of public parks began in earnest during which century?",
               "single_choice", "The nineteenth century",
               ["The seventeenth century", "The eighteenth century",
                "The nineteenth century", "The twentieth century"],
               "Paragraph 1: the idea 'did not take hold until the nineteenth century'."),
            _q(20, "What was the main driver behind the creation of public parks?",
               "single_choice", "Industrialisation",
               ["Royal patronage", "Industrialisation", "Tourism", "Religious reform"],
               "Paragraph 2: 'The catalyst was industrialisation.'"),
            _q(21, "Central Park opened in stages from which year?",
               "single_choice", "1858",
               ["1848", "1858", "1868", "1888"],
               "Paragraph 3 dates the opening from 1858."),
            _q(22, "Reformers described parks as the ______ of the city.",
               "fill_blank", ["lungs", "lung"], None,
               "Paragraph 2 quotes 'the lungs of the city'."),
            _q(23, "Central Park's designers hid the surrounding city using dense planting and sunken ______.",
               "fill_blank", ["roads", "road"], None,
               "Paragraph 3: 'dense planting and sunken roads'."),
            _q(24, "In the twentieth century, parks added playgrounds, sports fields and swimming ______.",
               "fill_blank", ["pools", "pool"], None,
               "Paragraph 4 lists 'swimming pools'."),
            _q(25, "Modern planners value parks for absorbing ______.",
               "fill_blank", ["rainwater", "rain water", "water"], None,
               "Paragraph 5: parks help by 'absorbing rainwater'."),
            _q(26, "Which TWO functions do parks serve in the face of climate change?",
               "multiple_choice", ["Cooling neighbourhoods", "Sheltering urban wildlife"],
               ["Generating electricity", "Cooling neighbourhoods",
                "Sheltering urban wildlife", "Producing food"],
               "Paragraph 5 lists cooling neighbourhoods and sheltering urban wildlife."),
        ],
    )

    # ---- Passage 3 — Questions 27–40 ----
    s3 = Section(
        order=3,
        title="Passage 3 — Can Machines Be Creative?",
        instructions="You should spend about 20 minutes on Questions 27–40.",
        passage=P3,
        questions=[
            _q(27, "Creativity was once seen as something machines could never achieve.",
               "true_false_notgiven", "Yes", ynng,
               "Paragraph 1: creativity was 'the one domain that machines ... could never enter'."),
            _q(28, "Audiences can always tell machine-generated music from human music.",
               "true_false_notgiven", "No", ynng,
               "Paragraph 2: in blind tests audiences could not distinguish them."),
            _q(29, "AI systems are more efficient than human artists.",
               "true_false_notgiven", "Not Given", ynng,
               "Efficiency is never compared in the passage."),
            _q(30, "Sceptics believe AI output is a form of imitation.",
               "true_false_notgiven", "Yes", ynng,
               "Paragraph 3: sceptics call it 'sophisticated imitation'."),
            _q(31, "The writer concludes that machines have replaced human creativity.",
               "true_false_notgiven", "No", ynng,
               "Paragraph 5: 'Rather than replacing human creativity ...'"),
            _q(32, "Which paragraph mentions AI being used as a collaborator by artists?",
               "matching", "Paragraph 5", ["Paragraph 2", "Paragraph 3", "Paragraph 4", "Paragraph 5"],
               "Paragraph 5 describes AI as a collaborator generating raw material."),
            _q(33, "Which paragraph defines creativity as producing novel and valuable work?",
               "matching", "Paragraph 4", ["Paragraph 2", "Paragraph 3", "Paragraph 4", "Paragraph 5"],
               "Paragraph 4 gives the 'novel and valuable' definition."),
            _q(34, "Which paragraph compares AI output to a mirror?",
               "matching", "Paragraph 3", ["Paragraph 2", "Paragraph 3", "Paragraph 4", "Paragraph 5"],
               "Paragraph 3 uses the 'mirror' metaphor."),
            _q(35, "Which paragraph reports results from blind listening tests?",
               "matching", "Paragraph 2", ["Paragraph 2", "Paragraph 3", "Paragraph 4", "Paragraph 5"],
               "Paragraph 2 describes the blind tests."),
            _q(36, "According to sceptics, what does a machine lack when producing work?",
               "single_choice", "An intention to communicate",
               ["Access to data", "An intention to communicate",
                "Processing power", "Training examples"],
               "Paragraph 3: a machine 'does not intend to communicate anything'."),
            _q(37, "Which TWO qualities, if required, would mean current AI is not truly creative?",
               "multiple_choice", ["Consciousness", "Lived experience"],
               ["Consciousness", "Speed", "Lived experience", "Memory"],
               "Paragraph 4: if creativity 'requires consciousness, intention or lived experience'."),
            _q(38, "In some tests, listeners judged machine compositions to be moving, original and emotionally ______.",
               "fill_blank", ["resonant"], None,
               "Paragraph 2: 'moving, original and emotionally resonant'."),
            _q(39, "Sceptics say AI recombines patterns taken from human ______.",
               "short_answer", ["works", "work"], None,
               "Paragraph 3: patterns 'extracted from the millions of human works'."),
            _q(40, "The new tools raise uncomfortable questions about authorship and ______.",
               "short_answer", ["originality"], None,
               "Paragraph 5 ends on 'authorship and originality'."),
        ],
    )

    test.sections = [s1, s2, s3]
    return test


def run():
    db = SessionLocal()
    try:
        existing = db.query(Test).filter(Test.title == TITLE).all()
        for t in existing:
            attempt_ids = [a.id for a in db.query(Attempt).filter(Attempt.test_id == t.id).all()]
            if attempt_ids:
                db.query(AnswerRecord).filter(
                    AnswerRecord.attempt_id.in_(attempt_ids)
                ).delete(synchronize_session=False)
                db.query(Attempt).filter(Attempt.test_id == t.id).delete(
                    synchronize_session=False
                )
            db.delete(t)  # cascades to sections + questions
        db.commit()

        test = build_test()
        db.add(test)
        db.commit()
        n_q = sum(len(s.questions) for s in test.sections)
        print(f"Seeded: {test.title} — {len(test.sections)} passages, {n_q} questions.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
