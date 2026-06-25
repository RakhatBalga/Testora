"""Gold-standard IELTS Academic Reading test — the reference template.

100% original passages (written from scratch, not adapted from any source).
3 passages · 13 + 13 + 14 = 40 questions · realistic question-type mix.
Every question carries an explanation and verbatim evidence span(s) so the
Reading Review UI can highlight the supporting sentence automatically.

Also removes the legacy "Academic Reading Practice 1" demo from the library.

Idempotent for this title. Run from backend/:
    venv/bin/python seed_reading_gold.py
"""
from app.database import SessionLocal
from app.models.test import Test, Section, Question
from app.models.attempt import Attempt, AnswerRecord

TITLE = "IELTS Academic Reading — Test A"
LEGACY_TITLE = "Academic Reading Practice 1"

# --------------------------------------------------------------------------- #
# Passages. "¶N " marks a numbered paragraph; **text** is highlighted.
# --------------------------------------------------------------------------- #

P1 = """The Return of the Beaver

¶1 For centuries the European beaver was among the most intensively hunted animals on the continent. Its dense, waterproof fur was made into hats and coats, its meat was eaten, and a secretion from its scent glands, known as castoreum, was valued by apothecaries as a medicine. So relentless was the trade that by the beginning of the twentieth century the species had been pushed to the brink of extinction. No more than a few thousand animals survived, in scattered pockets of Norway, Germany, France and Russia. For several generations the wild beaver effectively vanished from daily life, and it came to be remembered, if at all, as a creature of folklore rather than of the living countryside.

¶2 That picture has changed with remarkable speed. Since the middle of the twentieth century, conservationists have deliberately released beavers into rivers and wetlands across Europe, and in some regions the animals have spread back on their own. Biologists greet this return with particular enthusiasm because the beaver is a keystone species — one whose presence or absence determines the character of an entire ecosystem. **Few animals reshape their surroundings as profoundly as the beaver.** Where it settles, the landscape itself begins to change.

¶3 The agent of that change is the dam. Working mainly at night, a family of beavers will drag branches, pile up stones and pack mud into the gaps until a stream is blocked. Behind the barrier a pond forms, the current slows, and fine sediment sinks to the bottom. A single well-maintained dam may, over several seasons, generate a patchwork of pools, side channels and saturated ground. Such wetlands teem with life. Insects, amphibians and fish move in quickly, wading birds arrive to feed, and water-loving plants spread across the margins, so that a once-monotonous stretch of river becomes one of the richest habitats in the region.

¶4 These engineered wetlands also perform tasks that human infrastructure achieves only at great expense. Because a chain of ponds holds back large volumes of water, it functions as a natural reservoir, storing moisture during dry periods and releasing it gradually. When storms arrive, the same ponds soak up the surge and slow its passage downstream, so that communities lower down the valley are less likely to flood. Scientists monitoring reintroduced colonies have also recorded cleaner water leaving beaver sites, because the sediment trapped behind each dam carries with it fertilisers and pollutants that would otherwise reach the river.

¶5 Yet the beaver's return has not been universally welcomed. Where ponds spread onto farmland, fields may be waterlogged and crops spoiled, and orchards can be gnawed down in a night. In a number of countries the animal has become the focus of a genuine conflict of interest, pitting conservation bodies, who regard it as a cheap and self-operating tool for river restoration, against farmers and foresters, who must absorb the immediate losses. Reconciling these competing claims has become one of the most demanding aspects of any reintroduction scheme, and most programmes now devote considerable effort to compensating or assisting affected landowners.

¶6 Advocates contend that the case for the beaver only strengthens as the climate becomes less predictable. With droughts and floods expected to grow more severe, an animal that can store water and even out the flow of rivers offers a form of natural insurance. A valley populated by beaver ponds is, in a sense, buffered against weather extremes. Recognising this, several water utilities have started to finance beaver schemes, having calculated that the animals can deliver, almost for nothing, services that would otherwise demand costly dams and pipelines.

¶7 The recovery of the beaver, then, is not simply a heart-warming tale of a species saved. It shows how the restoration of one animal can ripple outward until it remakes an entire landscape. Whether the beaver comes to be seen as an ally or a nuisance will depend, in the end, not on the animal but on how far people are prepared to share their rivers with a fellow engineer."""

P2 = """Why We Forget

¶1 Forgetting has a bad reputation. We treat it as a malfunction — proof that the mind is failing us — and we speak of memories "fading" or "slipping away" as though they were objects that gradually wear out. For much of the twentieth century, psychologists shared this intuition. The earliest laboratory studies, conducted by Hermann Ebbinghaus in the 1880s, traced a steep "forgetting curve" along which freshly learned material was lost, and the dominant assumption was that memories simply decay with the passage of time, like ink left in sunlight.

¶2 Later researchers were not convinced that time alone was responsible. They pointed out that two people can let the same amount of time pass and yet remember very different amounts, depending on what they do in the interval. This observation gave rise to interference theory, which holds that memories are lost not because they decay but because they compete. New learning can obscure older memories, and older memories can make new ones harder to acquire. On this view, forgetting is less like fading ink than like a crowded noticeboard, where fresh notices cover and obscure those pinned up earlier.

¶3 More recently, scientists have begun to argue that forgetting is not a defect at all but a feature — an active process the brain has evolved to perform. A mind that retained every detail of every experience would be overwhelmed by useless information and unable to see the wider pattern. By discarding the trivial and the outdated, forgetting allows us to generalise, to recognise what matters, and to keep our picture of the world reasonably current. Far from being a weakness, the ability to let go of unimportant memories may be essential to thinking clearly.

¶4 If forgetting is partly under the brain's control, it follows that the way we study can influence what we keep. One of the most robust findings in modern memory research is the "testing effect": the discovery that trying to recall information strengthens it far more effectively than simply reading it again. Every act of successful retrieval appears to reinforce the route to a memory, making it easier to reach in future. Paradoxically, then, the effort to remember something we have nearly forgotten can do more good than the comfortable rereading of something we already know well.

¶5 Sleep plays its own quiet part. During the hours after learning, and especially during deep sleep, the brain appears to replay and reorganise the day's experiences, transferring selected memories into more stable, long-term storage. Material reviewed shortly before sleep is often retained better than material learned earlier in the day, and students who sacrifice sleep in order to study late into the night may undermine the very consolidation they are trying to achieve.

¶6 These findings carry clear lessons for education. They suggest that cramming, though it may produce a brief sense of mastery, is among the least efficient ways to learn, and that information is better revisited at spaced intervals, tested rather than merely reread, and followed by adequate rest. None of this comes naturally; the methods that feel most productive in the moment are frequently the least durable. Understanding why we forget, it turns out, is the first step towards remembering more."""

P3 = """Bringing Languages Back to Life

¶1 Of the roughly seven thousand languages spoken today, linguists estimate that nearly half may fall silent before the end of the century. When the last fluent speaker of a language dies, a unique way of describing the world — its stories, its humour, its categories of thought — is usually lost with them. For a long time this process was regarded as irreversible: a language without speakers was, like an extinct species, simply gone. In recent decades, however, a growing number of communities have set out to challenge that assumption, attempting to revive tongues that had been declared dead or dying.

¶2 The example most often cited is Hebrew. For nearly two thousand years it survived chiefly as a language of religious texts, rarely used in everyday conversation; today it is the mother tongue of millions. Yet specialists caution that Hebrew was never truly extinct, since it remained in continuous written and liturgical use, and that the political circumstances surrounding its revival were highly unusual. For this reason, Dr Elena Marsh, a linguist who studies endangered languages, warns that Hebrew should be treated as an inspiring exception rather than a model that other communities can expect to follow.

¶3 More typical are the smaller revivals now under way from Cornwall to Hawaii. Cornish, whose last traditional speakers died in the eighteenth and nineteenth centuries, has been reconstructed from written records and is once again being taught to children. In Hawaii, immersion schools have produced a new generation of young speakers after the language had dwindled to a few hundred elderly ones. These efforts are frequently celebrated, but they also raise a difficult question: is a language pieced together from documents, and shaped by the first language of its new speakers, really the same language that was lost?

¶4 On this point experts disagree. Professor Tomas Reuel argues that a revived language is inevitably a new creation — its pronunciation, vocabulary and rhythm bear the imprint of the dominant language its speakers grew up with, so that what is reborn is, strictly speaking, a descendant rather than a resurrection. Dr Aiko Tanaka takes a different view. She maintains that all living languages change constantly, and that the differences between a revived language and its historical form are no greater than those that separate any language from its own past; to dismiss a revived tongue as inauthentic, she argues, is to apply a standard we apply to no other.

¶5 Technology has altered what is possible. Archived recordings allow learners to hear the voices of speakers long dead, while smartphone applications, online dictionaries and social-media groups let scattered enthusiasts practise together without sharing a town, or even a continent. A community that once depended on a single ageing speaker can now draw on a permanent digital archive. Such tools cannot, by themselves, create fluent speakers — that still requires the slow work of daily use — but they remove many of the practical obstacles that doomed earlier efforts.

¶6 Behind these debates lies a deeper question about what languages are for. If their only purpose were efficient communication, the effort poured into reviving a tongue spoken by a few thousand people would be hard to justify. But a language is also a marker of identity and a link to ancestors, and for many communities its return is a source of pride that has little to do with practicality. A revived language need not be identical to the one that was lost in order to matter. What counts, in the end, is that a community has reclaimed something it feared was gone for good — and, in doing so, has insisted that its past still has a place in its future."""


def _q(order, text, qtype, correct, options=None, explanation=None, evidence=None):
    return Question(
        order=order,
        text=text,
        question_type=qtype,
        options=options,
        correct_answer=correct if isinstance(correct, list) else [correct],
        explanation=explanation,
        evidence=evidence,
    )


def _ev(paragraph, text):
    return [{"paragraph": paragraph, "text": text}]


def build_test() -> Test:
    test = Test(
        title=TITLE,
        test_type="reading",
        description="Original full-length Academic Reading test: 3 passages, 40 questions, 60 minutes.",
        duration_minutes=60,
        difficulty="Medium",
    )

    tfng = ["True", "False", "Not Given"]
    ynng = ["Yes", "No", "Not Given"]
    p1_paras = [f"Paragraph {i}" for i in range(1, 8)]

    # =================== PASSAGE 1 — Questions 1–13 =================== #
    s1 = Section(
        order=1,
        title="Passage 1 — The Return of the Beaver",
        instructions="You should spend about 20 minutes on Questions 1–13.",
        passage=P1,
        questions=[
            # Q1–6 True / False / Not Given
            _q(1, "Beaver fur was used to make items of clothing.", "true_false_notgiven", "True", tfng,
               "Paragraph 1 says the fur 'was made into hats and coats' — both items of clothing — so the statement agrees with the text.",
               _ev(1, "made into hats and coats")),
            _q(2, "By 1900 the European beaver had become completely extinct in the wild.", "true_false_notgiven", "False", tfng,
               "The statement claims total extinction, but Paragraph 1 says only that the species was pushed 'to the brink of extinction' and that 'a few thousand animals survived'. Surviving animals contradict 'completely extinct'.",
               _ev(1, "No more than a few thousand animals survived")),
            _q(3, "In some areas beavers have returned without being released by people.", "true_false_notgiven", "True", tfng,
               "Paragraph 2 states that 'in some regions the animals have spread back on their own', which matches returning without human release.",
               _ev(2, "the animals have spread back on their own")),
            _q(4, "Beavers carry out most of their building work during daylight hours.", "true_false_notgiven", "False", tfng,
               "Paragraph 3 says beavers work 'mainly at night', which contradicts the claim that they build during daylight.",
               _ev(3, "Working mainly at night")),
            _q(5, "Water leaving beaver sites has been measured as cleaner.", "true_false_notgiven", "True", tfng,
               "Paragraph 4 reports that scientists 'recorded cleaner water leaving beaver sites', directly supporting the statement.",
               _ev(4, "cleaner water leaving beaver sites")),
            _q(6, "Most reintroduction programmes take no account of farmers' concerns.", "true_false_notgiven", "False", tfng,
               "The statement says concerns are ignored, but Paragraph 5 says most programmes 'devote considerable effort to compensating or assisting affected landowners' — the opposite.",
               _ev(5, "compensating or assisting affected landowners")),
            # Q7–9 Sentence completion (ONE WORD ONLY)
            _q(7, "The medicinal secretion taken from the beaver's scent glands was called ______.", "fill_blank",
               ["castoreum"], None,
               "Paragraph 1 names the secretion: it was 'known as castoreum' and valued as a medicine.",
               _ev(1, "known as castoreum")),
            _q(8, "When the current behind a dam slows, fine ______ sinks to the bottom of the pond.", "fill_blank",
               ["sediment"], None,
               "Paragraph 3 explains that once the current slows, 'fine sediment sinks to the bottom'.",
               _ev(3, "fine sediment sinks to the bottom")),
            _q(9, "A chain of beaver ponds works as a natural ______, storing water in dry periods.", "fill_blank",
               ["reservoir"], None,
               "Paragraph 4 says the ponds function 'as a natural reservoir, storing moisture during dry periods'.",
               _ev(4, "functions as a natural reservoir")),
            # Q10–13 Matching information (which paragraph contains…)
            _q(10, "a description of disagreement between conservationists and landowners", "matching",
               "Paragraph 5", p1_paras,
               "Paragraph 5 describes 'a genuine conflict of interest' between conservation bodies and farmers/foresters.",
               _ev(5, "a genuine conflict of interest")),
            _q(11, "examples of wildlife that move into beaver wetlands", "matching",
               "Paragraph 3", p1_paras,
               "Paragraph 3 lists the creatures that colonise the wetland: 'Insects, amphibians and fish move in quickly'.",
               _ev(3, "Insects, amphibians and fish move in quickly")),
            _q(12, "a reference to companies paying for beaver projects", "matching",
               "Paragraph 6", p1_paras,
               "Paragraph 6 notes that 'several water utilities have started to finance beaver schemes'.",
               _ev(6, "several water utilities have started to finance beaver schemes")),
            _q(13, "a statement that the beaver was once thought of as belonging to folklore", "matching",
               "Paragraph 1", p1_paras,
               "Paragraph 1 says the animal was remembered 'as a creature of folklore rather than of the living countryside'.",
               _ev(1, "as a creature of folklore")),
        ],
    )

    # =================== PASSAGE 2 — Questions 14–26 =================== #
    headings = [
        "The traditional belief that memory simply wears away",  # ¶1
        "Memories that compete rather than fade",                # ¶2
        "A useful process the brain performs on purpose",        # ¶3
        "How recall outperforms rereading",                      # ¶4
        "The contribution of rest to lasting memory",            # ¶5
        "Practical advice for learners",                         # ¶6
        "The danger of remembering everything",                  # distractor
        "Why eyewitnesses make mistakes",                        # distractor
    ]
    s2 = Section(
        order=2,
        title="Passage 2 — Why We Forget",
        instructions=(
            "You should spend about 20 minutes on Questions 14–26. "
            "Questions 14–19: choose the correct heading for each paragraph."
        ),
        passage=P2,
        questions=[
            # Q14–19 Matching headings
            _q(14, "Heading for Paragraph 1", "matching", headings[0], headings,
               "Paragraph 1's main idea is the old assumption that 'memories simply decay with the passage of time'; Ebbinghaus is only the supporting example.",
               _ev(1, "memories simply decay with the passage of time")),
            _q(15, "Heading for Paragraph 2", "matching", headings[1], headings,
               "Paragraph 2 introduces interference theory: memories are lost 'not because they decay but because they compete'.",
               _ev(2, "not because they decay but because they compete")),
            _q(16, "Heading for Paragraph 3", "matching", headings[2], headings,
               "Paragraph 3 argues that forgetting 'is not a defect at all but a feature' — a deliberate, useful brain process.",
               _ev(3, "not a defect at all but a feature")),
            _q(17, "Heading for Paragraph 4", "matching", headings[3], headings,
               "Paragraph 4 is about the testing effect: recall 'strengthens it far more effectively than simply reading it again'.",
               _ev(4, "strengthens it far more effectively than simply reading it again")),
            _q(18, "Heading for Paragraph 5", "matching", headings[4], headings,
               "Paragraph 5 explains how sleep transfers memories 'into more stable, long-term storage'.",
               _ev(5, "more stable, long-term storage")),
            _q(19, "Heading for Paragraph 6", "matching", headings[5], headings,
               "Paragraph 6 opens by stating these findings 'carry clear lessons for education' and gives study advice.",
               _ev(6, "carry clear lessons for education")),
            # Q20–23 Multiple choice
            _q(20, "Ebbinghaus's early research suggested that memories", "single_choice",
               "decline steadily over time",
               ["compete with one another", "decline steadily over time",
                "improve when tested", "depend on sleep"],
               "Paragraph 1 links his 'forgetting curve' to the idea that 'memories simply decay with the passage of time' — a steady decline.",
               _ev(1, "memories simply decay with the passage of time")),
            _q(21, "Interference theory explains forgetting as the result of", "single_choice",
               "memories obscuring one another",
               ["the simple passage of time", "a lack of sleep",
                "memories obscuring one another", "damage to brain cells"],
               "Paragraph 2 compares memory to a noticeboard where new notices 'cover and obscure those pinned up earlier' — memories competing.",
               _ev(2, "fresh notices cover and obscure those pinned up earlier")),
            _q(22, "According to the passage, the 'testing effect' shows that", "single_choice",
               "attempting to recall information strengthens it",
               ["tests mainly cause anxiety", "rereading is better than testing",
                "attempting to recall information strengthens it", "tests measure intelligence"],
               "Paragraph 4 defines it as the discovery that 'trying to recall information strengthens it' more than rereading.",
               _ev(4, "trying to recall information strengthens it far more effectively than simply reading it again")),
            _q(23, "What does the passage say about studying late into the night?", "single_choice",
               "It may harm the consolidation of memories",
               ["It reliably improves recall", "It may harm the consolidation of memories",
                "It is recommended before exams", "It has no measurable effect"],
               "Paragraph 5 warns that students who lose sleep 'may undermine the very consolidation they are trying to achieve'.",
               _ev(5, "may undermine the very consolidation")),
            # Q24–26 Summary completion (ONE WORD ONLY)
            _q(24, "Cramming produces only a brief sense of ______ and is inefficient.", "fill_blank",
               ["mastery"], None,
               "Paragraph 6 says cramming 'may produce a brief sense of mastery' yet is among the least efficient methods.",
               _ev(6, "a brief sense of mastery")),
            _q(25, "Material should instead be revisited at spaced ______.", "fill_blank",
               ["intervals"], None,
               "Paragraph 6 advises that information 'is better revisited at spaced intervals'.",
               _ev(6, "revisited at spaced intervals")),
            _q(26, "Study should be tested rather than reread, and followed by adequate ______.", "fill_blank",
               ["rest"], None,
               "Paragraph 6 ends the recommendation with material 'followed by adequate rest'.",
               _ev(6, "followed by adequate rest")),
        ],
    )

    # =================== PASSAGE 3 — Questions 27–40 =================== #
    people = ["Dr Elena Marsh", "Professor Tomas Reuel", "Dr Aiko Tanaka"]
    s3 = Section(
        order=3,
        title="Passage 3 — Bringing Languages Back to Life",
        instructions=(
            "You should spend about 20 minutes on Questions 27–40. "
            "Questions 27–32: do the statements agree with the writer's views?"
        ),
        passage=P3,
        questions=[
            # Q27–32 Yes / No / Not Given (writer's views)
            _q(27, "Around half of the world's languages may disappear during this century.", "true_false_notgiven", "Yes", ynng,
               "Paragraph 1 states linguists estimate 'nearly half may fall silent before the end of the century', agreeing with the writer.",
               _ev(1, "nearly half may fall silent before the end of the century")),
            _q(28, "The death of a language usually means losing a distinct way of seeing the world.", "true_false_notgiven", "Yes", ynng,
               "Paragraph 1 says that when the last speaker dies, 'a unique way of describing the world … is usually lost with them'.",
               _ev(1, "a unique way of describing the world")),
            _q(29, "Hebrew is a reliable model that other communities can expect to follow.", "true_false_notgiven", "No", ynng,
               "Dr Marsh, whose view the writer reports, warns Hebrew should be seen 'as an inspiring exception rather than a model' — contradicting the statement.",
               _ev(2, "an inspiring exception rather than a model")),
            _q(30, "Cornish currently has more speakers than Hawaiian.", "true_false_notgiven", "Not Given", ynng,
               "Paragraph 3 discusses both revivals but never compares their numbers of speakers, so this cannot be confirmed or denied.",
               None),
            _q(31, "Technology on its own is enough to create fluent speakers.", "true_false_notgiven", "No", ynng,
               "Paragraph 5 states such tools 'cannot, by themselves, create fluent speakers', which contradicts the statement.",
               _ev(5, "cannot, by themselves, create fluent speakers")),
            _q(32, "The writer believes a revived language must be identical to the original to be worthwhile.", "true_false_notgiven", "No", ynng,
               "In Paragraph 6 the writer states a revived language 'need not be identical to the one that was lost in order to matter' — the opposite of the statement.",
               _ev(6, "need not be identical to the one that was lost in order to matter")),
            # Q33–36 Multiple choice
            _q(33, "Specialists regard Hebrew as unusual mainly because", "single_choice",
               "it stayed in continuous written and religious use",
               ["it never had a written form", "it stayed in continuous written and religious use",
                "it was always widely spoken", "it was simple to learn"],
               "Paragraph 2 explains Hebrew 'was never truly extinct, since it remained in continuous written and liturgical use'.",
               _ev(2, "it remained in continuous written and liturgical use")),
            _q(34, "Cornish was brought back mainly through", "single_choice",
               "reconstruction from written records",
               ["recordings of native speakers", "immersion schools",
                "reconstruction from written records", "an official government order"],
               "Paragraph 3 says Cornish 'has been reconstructed from written records'. (Immersion schools describe Hawaii, not Cornish.)",
               _ev(3, "reconstructed from written records")),
            _q(35, "According to the writer, what can technology do for language revival?", "single_choice",
               "remove many practical obstacles",
               ["guarantee fluency", "remove many practical obstacles",
                "replace daily use of the language", "preserve endangered species"],
               "Paragraph 5 says the tools 'remove many of the practical obstacles that doomed earlier efforts', while stopping short of guaranteeing fluency.",
               _ev(5, "they remove many of the practical obstacles")),
            _q(36, "In the final paragraph the writer suggests reviving a language is valuable chiefly as", "single_choice",
               "an expression of identity and pride",
               ["a commercial opportunity", "a means of efficient communication",
                "an expression of identity and pride", "a purely scientific experiment"],
               "Paragraph 6 argues a language is 'a marker of identity and a link to ancestors' and a 'source of pride', outweighing pure practicality.",
               _ev(6, "a marker of identity and a link to ancestors")),
            # Q37–39 Matching features (attribute each view to a person)
            _q(37, "A revived language is really a new descendant rather than a true resurrection.", "matching",
               "Professor Tomas Reuel", people,
               "Paragraph 4: Professor Reuel argues a revived language is 'a descendant rather than a resurrection'.",
               _ev(4, "a descendant rather than a resurrection")),
            _q(38, "Hebrew should be treated as an exceptional case, not a general model.", "matching",
               "Dr Elena Marsh", people,
               "Paragraph 2: Dr Marsh warns Hebrew is 'an inspiring exception rather than a model'.",
               _ev(2, "an inspiring exception rather than a model")),
            _q(39, "Calling a revived language inauthentic applies a standard used for no other language.", "matching",
               "Dr Aiko Tanaka", people,
               "Paragraph 4: Dr Tanaka argues that to dismiss a revived tongue as inauthentic 'is to apply a standard we apply to no other'.",
               _ev(4, "a standard we apply to no other")),
            # Q40 Short answer (NO MORE THAN TWO WORDS)
            _q(40, "What kind of archive can a community now use instead of relying on a single ageing speaker?", "short_answer",
               ["digital archive", "a digital archive", "permanent digital archive"], None,
               "Paragraph 5 says a community 'can now draw on a permanent digital archive' rather than one ageing speaker.",
               _ev(5, "a permanent digital archive")),
        ],
    )

    test.sections = [s1, s2, s3]
    return test


def _delete_by_title(db, title):
    for t in db.query(Test).filter(Test.title == title).all():
        ids = [a.id for a in db.query(Attempt).filter(Attempt.test_id == t.id).all()]
        if ids:
            db.query(AnswerRecord).filter(AnswerRecord.attempt_id.in_(ids)).delete(
                synchronize_session=False
            )
            db.query(Attempt).filter(Attempt.test_id == t.id).delete(synchronize_session=False)
        db.delete(t)


def run():
    db = SessionLocal()
    try:
        _delete_by_title(db, TITLE)        # idempotent re-seed
        _delete_by_title(db, LEGACY_TITLE)  # remove the old demo from the library
        db.commit()

        test = build_test()
        db.add(test)
        db.commit()
        n = sum(len(s.questions) for s in test.sections)
        print(f"Seeded: {test.title} — {len(test.sections)} passages, {n} questions.")
        print(f"Removed legacy test: {LEGACY_TITLE!r}.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
