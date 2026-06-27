"""Build the Testora Studio Listening 01 content pack and reproducible master audio.

Run from backend/: python scripts/generate_listening_benchmark.py
Use --content-only when macOS `say` or ffmpeg is unavailable.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT_PATH = ROOT / "content/listening/testora-studio-01-blueprint.json"
CONTENT_PATH = ROOT / "content/listening/testora-studio-01.json"
MANIFEST_PATH = ROOT / "content/listening/testora-studio-01-audio-manifest.json"
AUDIO_PATH = ROOT / "static/audio/listening/testora-studio-01.m4a"
INTRO = "This is a Testora Studio Listening Practice Test. The test will begin in five seconds."
AUTHORSHIP = "Original IELTS-style practice test created by Testora."


VOICES = {
    "Narrator": {"voice": "Daniel", "accent": "British English", "rate": 150},
    "Maya": {"voice": "Karen", "accent": "Australian English", "rate": 157},
    "Naomi": {"voice": "Samantha", "accent": "North American English", "rate": 155},
    "Mina": {"voice": "Karen", "accent": "Australian English", "rate": 158},
    "Lucas": {"voice": "Daniel", "accent": "British English", "rate": 154},
    "Dr Okafor": {"voice": "Tessa", "accent": "South African English", "rate": 151},
    "Lecturer": {"voice": "Moira", "accent": "Irish English", "rate": 150},
}


def seg(id_: str, speaker: str, text: str) -> dict:
    return {"id": id_, "speaker": speaker, "text": text}


SECTIONS = [
    {
        "order": 1,
        "title": "Section 1 - Repair workshop booking",
        "instructions": "Questions 1-10. Complete the booking form. Write NO MORE THAN TWO WORDS AND/OR A NUMBER for each answer.",
        "segments": [
            seg("s1-01", "Maya", "Good afternoon, Harbour Repair Workshop. Maya speaking. How can I help?"),
            seg("s1-02", "Naomi", "Hello. I would like to book a place on the beginners' bicycle maintenance session."),
            seg("s1-03", "Maya", "Certainly. Can I take your surname? Patel, that's P A T E L."),
            seg("s1-04", "Naomi", "Yes, that's right. I saw two dates online, but I was not sure which still had spaces."),
            seg("s1-05", "Maya", "The page briefly showed the seventeenth of July, but that session is now reserved for a school group."),
            seg("s1-06", "Maya", "The public beginners' session is on the eighteenth of July, and there are three places left."),
            seg("s1-07", "Naomi", "Perfect. I finish work at five thirty, so I hope it is not too early."),
            seg("s1-08", "Maya", "You will be fine. The workshop starts at six thirty and the doors remain open until six twenty-five."),
            seg("s1-09", "Naomi", "Do I need to bring tools? I have a small pump, but nothing for removing a wheel."),
            seg("s1-10", "Maya", "We provide all the tools, and an apron is included as well."),
            seg("s1-11", "Maya", "You only need to bring gloves. Ordinary gardening ones are suitable."),
            seg("s1-12", "Naomi", "Good. What does the session cost?"),
            seg("s1-13", "Maya", "It is forty-two pounds, including replacement cables to practise with. There is no separate deposit."),
            seg("s1-14", "Naomi", "I was planning to drive. Is there parking behind the workshop?"),
            seg("s1-15", "Maya", "There are only two spaces and both are needed for staff vans. The train station is a long walk."),
            seg("s1-16", "Naomi", "In that case I will take the bus. Route twelve stops across the road, doesn't it?"),
            seg("s1-17", "Maya", "It does. The main doors will be locked by then because the shop closes at six."),
            seg("s1-18", "Maya", "Use the side entrance, beside the blue loading bay. We will put a workshop sign there."),
            seg("s1-19", "Naomi", "Could you text me if anything changes?"),
            seg("s1-20", "Maya", "Of course. I have zero seven nine two zero, six zero seven nine, from your online enquiry."),
            seg("s1-21", "Naomi", "The last four digits should be six zero seven four, not six zero seven nine."),
            seg("s1-22", "Maya", "Thanks, I have corrected that. We also invite people to bring one damaged object for the recycling demonstration."),
            seg("s1-23", "Maya", "A steel or aluminium part is useful, but please bring aluminium if you have a choice because it is easier to cut safely."),
            seg("s1-24", "Naomi", "I have an old aluminium bottle cage. That should work."),
            seg("s1-25", "Maya", "Yes. I will email the booking confirmation today. If you need to cancel, reply to that email at least twenty-four hours beforehand."),
        ],
    },
    {
        "order": 2,
        "title": "Section 2 - Coast discovery centre",
        "instructions": "Questions 11-15. Label the map. Choose the correct letter A-H. Questions 16-20. Choose the correct answer A, B, or C.",
        "map_asset": "/listening/testora-studio-01-map.svg",
        "segments": [
            seg("s2-01", "Lucas", "Welcome to Northhaven Coast Discovery Centre. Before you explore, I will describe the site using the map on your screen."),
            seg("s2-02", "Lucas", "You are standing at the entrance at the bottom of the map. The main path runs straight towards the shore."),
            seg("s2-03", "Lucas", "Reception is on the right as you enter, but you do not need to go there if you already have a ticket."),
            seg("s2-04", "Lucas", "The ticket kiosk is immediately on your left, at point B, before the path reaches the first junction."),
            seg("s2-05", "Lucas", "Continue to the wooden footbridge. Just after crossing it, a narrow path turns right towards the reed beds."),
            seg("s2-06", "Lucas", "Follow that narrow path to point D, where you will find the bird hide."),
            seg("s2-07", "Lucas", "Back on the main path, the education garden is beside the pond."),
            seg("s2-08", "Lucas", "The picnic shelter is opposite the garden at point F, not beside the pond as an older leaflet suggests."),
            seg("s2-09", "Lucas", "For the kayak launch, keep going until the main path bends left around the laboratory."),
            seg("s2-10", "Lucas", "Take the short path on the seaward side of that bend. The kayak point is H, close to the beach."),
            seg("s2-11", "Lucas", "The toilets are not in the laboratory. Walk past the laboratory and the outdoor showers."),
            seg("s2-12", "Lucas", "They are at point G, at the end of the paved path, just before the dunes."),
            seg("s2-13", "Lucas", "Now, a few suggestions for planning your visit."),
            seg("s2-14", "Lucas", "Families often head directly to the beach, while the short film is popular when people are tired."),
            seg("s2-15", "Lucas", "For younger children, however, begin at the touch pool. A guide is always there to help them handle the animals gently."),
            seg("s2-16", "Lucas", "The seal talk normally starts at two o'clock on weekdays."),
            seg("s2-17", "Lucas", "Today the rescue team is returning late from a survey, so the talk cannot begin at its usual time."),
            seg("s2-18", "Lucas", "It has been moved to two thirty. The feeding demonstration will follow at three."),
            seg("s2-19", "Lucas", "You may photograph wildlife and use binoculars throughout the site."),
            seg("s2-20", "Lucas", "Please do not feed the birds, even with food bought in our cafe, because it changes their natural behaviour."),
            seg("s2-21", "Lucas", "Our outdoor programme changes with the weather."),
            seg("s2-22", "Lucas", "Light rain does not stop the shore walk, and in heavy rain we use the covered observation deck."),
            seg("s2-23", "Lucas", "Strong wind is different: the shore path closes, and the activity moves into the indoor laboratory."),
            seg("s2-24", "Lucas", "Entry to the centre is free. You may see a suggested donation at reception."),
            seg("s2-25", "Lucas", "That donation pays for fuel and maintenance for the small rescue boat, rather than the exhibits inside the centre."),
        ],
    },
    {
        "order": 3,
        "title": "Section 3 - Student food-waste study",
        "instructions": "Questions 21-25. Match each statement with the correct speaker. Questions 26-27. Choose the correct answer. Questions 28-30. Complete the notes. Write ONE WORD AND/OR A NUMBER.",
        "segments": [
            seg("s3-01", "Dr Okafor", "Let's review your proposed study of food waste in the campus dining hall. What have you decided so far?"),
            seg("s3-02", "Mina", "We first planned to compare all three dining halls, but that would give us too much data for a six-week project."),
            seg("s3-03", "Lucas", "I still think two sites would make the results stronger."),
            seg("s3-04", "Mina", "I would rather study one hall properly. A shallow comparison would not tell the catering team what to change."),
            seg("s3-05", "Dr Okafor", "A single site is acceptable if you explain the limitation."),
            seg("s3-06", "Lucas", "My concern is that students may behave differently when they notice us measuring what they leave."),
            seg("s3-07", "Mina", "We could put the scales behind the tray-return screen, so nobody sees the measurements."),
            seg("s3-08", "Lucas", "That solves part of it, and I agree that we should avoid questioning people while they eat."),
            seg("s3-09", "Lucas", "But I still want short interviews afterwards, because the weights alone cannot explain why food was left."),
            seg("s3-10", "Mina", "I offered to conduct the interviews because I wrote the draft questions."),
            seg("s3-11", "Lucas", "You also know the weighing equipment. I have used interview software before and can code the responses faster."),
            seg("s3-12", "Mina", "Fair point. You take the interviews, then, and I will manage the measurements instead."),
            seg("s3-13", "Dr Okafor", "Good. Make sure your categories separate food that was unpopular from portions that were simply too large."),
            seg("s3-14", "Mina", "Portion size matters because the same serving is given to everyone."),
            seg("s3-15", "Dr Okafor", "Exactly. That is the strongest reason to record meal type as well as total weight; soup and bread cannot be compared as if they were identical."),
            seg("s3-16", "Lucas", "Should our title be 'How much food do students waste'?"),
            seg("s3-17", "Dr Okafor", "That only describes quantity, while your interviews investigate motives."),
            seg("s3-18", "Dr Okafor", "Frame the main focus as the causes of edible food waste. The total weight becomes supporting evidence."),
            seg("s3-19", "Mina", "For the method, we could ask diners to estimate how much they left."),
            seg("s3-20", "Lucas", "Self-reported estimates are unreliable. Photographs might be better, although classifying them would take time."),
            seg("s3-21", "Dr Okafor", "Use direct observation of returned plates, supported by weighing. Save interviews for explaining the patterns."),
            seg("s3-22", "Mina", "We tested the observation sheet with twelve diners yesterday."),
            seg("s3-23", "Dr Okafor", "For the main study, collect data from sixty diners across lunch and dinner. Twelve is only enough for the pilot."),
            seg("s3-24", "Lucas", "I can clean the spreadsheet and send it to you on Wednesday."),
            seg("s3-25", "Dr Okafor", "Wednesday was the date in your old plan, before the dining hall changed its menu cycle."),
            seg("s3-26", "Dr Okafor", "Send the final data on Thursday instead, after you have captured the vegetarian menu."),
            seg("s3-27", "Mina", "And our final assessment is a written report, correct?"),
            seg("s3-28", "Dr Okafor", "The report is for the catering manager. For this module, your assessed output is a poster, which you will present in week eight."),
        ],
    },
    {
        "order": 4,
        "title": "Section 4 - Introduction to soundscape ecology",
        "instructions": "Questions 31-35. Complete the sentences. Write ONE WORD ONLY. Questions 36-40. Choose the correct answer A, B, or C.",
        "segments": [
            seg("s4-01", "Lecturer", "Today we will look at soundscape ecology, a field that treats environmental sound as data rather than background."),
            seg("s4-02", "Lecturer", "A soundscape contains biological sounds, physical sounds such as wind and water, and sounds created by people."),
            seg("s4-03", "Lecturer", "The key idea is not merely to list those sounds, but to study the relationships between living things and their environment through sound."),
            seg("s4-04", "Lecturer", "Animal calls perform several ecological functions."),
            seg("s4-05", "Lecturer", "They can attract mates, warn of predators, coordinate a group, or defend territories."),
            seg("s4-06", "Lecturer", "A recording therefore tells us more than whether a place seems pleasant to a human listener."),
            seg("s4-07", "Lecturer", "When analysing a recording, loudness describes the strength of a sound."),
            seg("s4-08", "Lecturer", "Frequency, by contrast, helps distinguish a low engine hum from a high insect call."),
            seg("s4-09", "Lecturer", "Researchers often display both time and frequency as a coloured image."),
            seg("s4-10", "Lecturer", "This image is called a spectrogram. It can reveal repeated calls that are difficult to notice by ear."),
            seg("s4-11", "Lecturer", "One short recording can confirm that a species called at a particular moment, but long-term monitoring is more powerful."),
            seg("s4-12", "Lecturer", "If recorders sample the same locations over months or years, researchers can compare seasonal patterns."),
            seg("s4-13", "Lecturer", "Repeated detections may also provide an indicator of abundance, although they are not a direct count of individual animals."),
            seg("s4-14", "Lecturer", "Human noise is one reason those comparisons require care."),
            seg("s4-15", "Lecturer", "A road does not necessarily cause birds to leave the entire area."),
            seg("s4-16", "Lecturer", "Traffic may instead mask their calls, making communication and detection more difficult even when the birds remain present."),
            seg("s4-17", "Lecturer", "A good monitoring design reduces avoidable differences between samples."),
            seg("s4-18", "Lecturer", "Recording whenever a researcher happens to be free would mix dawn, midday, and evening soundscapes."),
            seg("s4-19", "Lecturer", "Recording at the same time each day makes samples more comparable and separates daily cycles from longer changes."),
            seg("s4-20", "Lecturer", "Interpretation must also remain cautious."),
            seg("s4-21", "Lecturer", "Suppose a frog appears in Monday's recording but not Tuesday's."),
            seg("s4-22", "Lecturer", "We should say it was not recorded on Tuesday, not that it was absent. Wind or another sound may have hidden its call."),
            seg("s4-23", "Lecturer", "Consider a small city park monitored beside a road."),
            seg("s4-24", "Lecturer", "The weekday recordings contain steady traffic from the morning commute."),
            seg("s4-25", "Lecturer", "At the same hour on weekends, traffic falls and more short bird calls can be detected. That pattern may reflect reduced masking, not an instant rise in bird numbers."),
            seg("s4-26", "Lecturer", "Finally, sound recordings are valuable because they can be stored and checked again by different analysts."),
            seg("s4-27", "Lecturer", "They can reveal ecological change across time, but microphones do not explain every cause."),
            seg("s4-28", "Lecturer", "The strongest conclusion is therefore that acoustic evidence is a repeatable measure which must be interpreted alongside habitat, weather, and human activity."),
        ],
    },
]


def question(order, text, qtype, answers, evidence, explanation, options=None, word_limit=None):
    return {
        "order": order,
        "text": text,
        "question_type": qtype,
        "options": options,
        "correct_answer": answers,
        "explanation": explanation,
        "evidence": [{"paragraph": 1, "quote": evidence}],
        "word_limit": word_limit,
    }


QUESTIONS = [
    question(1, "Surname:", "fill_blank", ["Patel"], "Patel, that's P A T E L", "The coordinator confirms the surname Patel.", word_limit=1),
    question(2, "Session date:", "fill_blank", ["18 July", "eighteenth of July"], "public beginners' session is on the eighteenth of July", "The seventeenth is corrected; the public session is on 18 July.", word_limit=3),
    question(3, "Start time:", "fill_blank", ["6:30", "6.30", "six thirty"], "workshop starts at six thirty", "The workshop begins at 6:30.", word_limit=2),
    question(4, "Item to bring:", "fill_blank", ["gloves"], "only need to bring gloves", "Tools and an apron are provided; gloves are required.", word_limit=1),
    question(5, "Fee: £", "fill_blank", ["42", "forty-two"], "It is forty-two pounds", "The total fee is forty-two pounds.", word_limit=1),
    question(6, "Transport:", "fill_blank", ["bus", "the bus"], "I will take the bus", "The caller rejects driving and decides to take the bus.", word_limit=2),
    question(7, "Entrance to use:", "fill_blank", ["side entrance", "the side entrance"], "Use the side entrance", "The main doors are closed, so attendees use the side entrance.", word_limit=3),
    question(8, "Last four phone digits:", "fill_blank", ["6074"], "six zero seven four", "The caller corrects the final four digits to 6074.", word_limit=1),
    question(9, "Material to bring if possible:", "fill_blank", ["aluminium", "aluminum"], "please bring aluminium", "Aluminium is preferred because it is easier to cut safely.", word_limit=1),
    question(10, "To cancel, reply by:", "fill_blank", ["email"], "reply to that email", "Cancellation is made by replying to the confirmation email.", word_limit=1),

    question(11, "Ticket kiosk", "matching_information", ["B"], "ticket kiosk is immediately on your left, at point B", "The kiosk is marked B on the map.", options=list("ABCDEFGH")),
    question(12, "Bird hide", "matching_information", ["D"], "point D, where you will find the bird hide", "The bird hide is at D.", options=list("ABCDEFGH")),
    question(13, "Picnic shelter", "matching_information", ["F"], "picnic shelter is opposite the garden at point F", "The picnic shelter is at F.", options=list("ABCDEFGH")),
    question(14, "Kayak point", "matching_information", ["H"], "kayak point is H", "The kayak launch is at H near the beach.", options=list("ABCDEFGH")),
    question(15, "Toilets", "matching_information", ["G"], "They are at point G", "The toilets are at G beyond the laboratory and showers.", options=list("ABCDEFGH")),
    question(16, "Where should families with younger children begin?", "single_choice", ["At the touch pool"], "begin at the touch pool", "A guide at the touch pool can help younger children.", options=["At the beach", "At the touch pool", "In the film room"]),
    question(17, "What time is today's seal talk?", "single_choice", ["2:30"], "moved to two thirty", "The usual 2:00 talk is moved to 2:30 today.", options=["2:00", "2:30", "3:00"]),
    question(18, "What must visitors not do?", "single_choice", ["Feed the birds"], "do not feed the birds", "Feeding birds is prohibited because it changes their behaviour.", options=["Photograph wildlife", "Use binoculars", "Feed the birds"]),
    question(19, "What happens when there is strong wind?", "single_choice", ["Activities move to the indoor laboratory"], "activity moves into the indoor laboratory", "Strong wind closes the shore path and moves the activity indoors.", options=["The centre closes", "Activities use the covered deck", "Activities move to the indoor laboratory"]),
    question(20, "What does the suggested donation support?", "single_choice", ["The rescue boat"], "pays for fuel and maintenance for the small rescue boat", "Donations fund fuel and maintenance for the rescue boat.", options=["The rescue boat", "The indoor exhibits", "The cafe"]),

    question(21, "A detailed study of one site is preferable.", "matching_information", ["A Mina"], "I would rather study one hall properly", "Mina argues for studying one hall in depth.", options=["A Mina", "B Lucas", "C Dr Okafor"]),
    question(22, "Being observed may change participants' behaviour.", "matching_information", ["B Lucas"], "students may behave differently when they notice us", "Lucas raises the concern about observation effects.", options=["A Mina", "B Lucas", "C Dr Okafor"]),
    question(23, "Interviews are still needed to explain the measurements.", "matching_information", ["B Lucas"], "weights alone cannot explain why food was left", "Lucas supports interviews because weights do not reveal motives.", options=["A Mina", "B Lucas", "C Dr Okafor"]),
    question(24, "The original division of work should be changed.", "matching_information", ["A Mina"], "You take the interviews, then, and I will manage the measurements", "Mina agrees to swap the assigned tasks.", options=["A Mina", "B Lucas", "C Dr Okafor"]),
    question(25, "Meal type must be recorded to make comparisons meaningful.", "matching_information", ["C Dr Okafor"], "strongest reason to record meal type", "Dr Okafor explains why meal type is essential.", options=["A Mina", "B Lucas", "C Dr Okafor"]),
    question(26, "What should be the main focus of the study?", "single_choice", ["The causes of edible food waste"], "main focus as the causes of edible food waste", "The tutor narrows the study to causes, with weight as supporting evidence.", options=["Differences between dining halls", "The total weight of all waste", "The causes of edible food waste"]),
    question(27, "Which main data-collection method does the tutor recommend?", "single_choice", ["Direct observation"], "Use direct observation of returned plates", "Direct observation, supported by weighing, is the main method.", options=["Self-reported estimates", "Direct observation", "Photographs only"]),
    question(28, "Main study sample: ____ diners", "fill_blank", ["60", "sixty"], "collect data from sixty diners", "The full study needs sixty diners; twelve was the pilot.", word_limit=1),
    question(29, "Final data deadline:", "fill_blank", ["Thursday"], "final data on Thursday", "The old Wednesday deadline is changed to Thursday.", word_limit=1),
    question(30, "Assessed output:", "fill_blank", ["poster", "a poster"], "assessed output is a poster", "The module assesses a poster, while the manager receives a report.", word_limit=2),

    question(31, "Soundscape ecology studies ____ between living things and their environment.", "sentence_completion", ["relationships"], "study the relationships between living things and their environment", "The field studies relationships through sound.", word_limit=1),
    question(32, "Some animal calls are used to defend ____.", "sentence_completion", ["territories"], "defend territories", "Defending territories is one function of animal calls.", word_limit=1),
    question(33, "____ helps distinguish a low engine sound from a high insect call.", "sentence_completion", ["frequency"], "Frequency, by contrast, helps distinguish", "Frequency differentiates low and high sounds.", word_limit=1),
    question(34, "A visual display of time and frequency is a ____.", "sentence_completion", ["spectrogram"], "image is called a spectrogram", "The visual display is called a spectrogram.", word_limit=1),
    question(35, "Repeated detections can indicate a species' ____.", "sentence_completion", ["abundance"], "indicator of abundance", "Repeated long-term detections may indicate abundance.", word_limit=1),
    question(36, "How can traffic noise affect birds that remain in an area?", "single_choice", ["It can mask their calls"], "Traffic may instead mask their calls", "Noise can mask calls and hinder communication or detection.", options=["It can mask their calls", "It makes their calls lower", "It stops them defending territory"]),
    question(37, "Why should recordings be made at the same time each day?", "single_choice", ["To make samples more comparable"], "makes samples more comparable", "A consistent time reduces variation caused by daily cycles.", options=["To use fewer recorders", "To make samples more comparable", "To avoid recording insects"]),
    question(38, "What should a researcher conclude when a species is not heard?", "single_choice", ["It was not recorded in that sample"], "say it was not recorded", "Non-detection does not prove absence.", options=["It left the area", "It was silent all day", "It was not recorded in that sample"]),
    question(39, "Why were more bird calls detected at weekends in the park example?", "single_choice", ["There may have been less traffic masking"], "pattern may reflect reduced masking", "Reduced traffic masking may reveal calls that weekday noise covers.", options=["There may have been less traffic masking", "Bird numbers immediately increased", "Recordings were made later"]),
    question(40, "What is the lecturer's main conclusion about acoustic evidence?", "single_choice", ["It is repeatable but needs contextual interpretation"], "repeatable measure which must be interpreted alongside", "Recordings are repeatable evidence but need habitat, weather, and activity context.", options=["It explains the causes of every change", "It is repeatable but needs contextual interpretation", "It is useful only with direct animal counts"]),
]


def _run(*args: str) -> None:
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _duration(path: Path) -> float:
    output = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], text=True)
    return round(float(output.strip()), 3)


def _write_content(timeline: dict[str, dict], duration: float) -> dict:
    blueprint = json.loads(BLUEPRINT_PATH.read_text(encoding="utf-8"))
    by_order = {item["question"]: item for item in blueprint["items"]}
    questions = []
    for raw in QUESTIONS:
        item = dict(raw)
        word_limit = item.pop("word_limit")
        blueprint_item = by_order[item["order"]]
        item["metadata"] = {**blueprint_item, "word_limit": word_limit}
        questions.append(item)

    sections = []
    for section in SECTIONS:
        section_questions = [q for q in questions if (q["order"] - 1) // 10 + 1 == section["order"]]
        timed = []
        for segment in section["segments"]:
            stamp = timeline.get(segment["id"], {"start": 0, "end": 0})
            timed.append({**segment, **stamp})
        section_start = min((item["start"] for item in timed), default=0)
        section_end = max((item["end"] for item in timed), default=0)
        sections.append({
            "order": section["order"],
            "title": section["title"],
            "instructions": section["instructions"],
            "audio_url": "/static/audio/listening/testora-studio-01.m4a",
            "passage": "\n".join(f"{item['speaker']}: {item['text']}" for item in section["segments"]),
            "metadata": {
                "audio_start": section_start,
                "audio_end": section_end,
                "map_asset": section.get("map_asset"),
                "transcript_segments": timed,
            },
            "questions": section_questions,
        })

    pack = {"tests": [{
        "title": "Testora Studio Listening Practice Test 01",
        "test_type": "listening",
        "difficulty": "Medium-Hard",
        "description": AUTHORSHIP,
        "duration_minutes": max(1, round(duration / 60)),
        "content_version": blueprint["content_version"],
        "metadata": {
            "schema_version": "testora.listening-content.v1",
            "slug": blueprint["test_slug"],
            "published": True,
            "calibration_status": blueprint["calibration_status"],
            "authorship": AUTHORSHIP,
            "intro_script": INTRO,
            "intro_notice": "The recording opens with a test identification, followed by exactly five seconds of silence and a neutral cue.",
            "audio_duration": duration,
            "voices": VOICES,
            "review_passes": blueprint["review_passes"],
        },
        "sections": sections,
    }]}
    CONTENT_PATH.write_text(json.dumps(pack, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return pack


def build_audio() -> tuple[dict[str, dict], float, list[dict]]:
    for command in ("say", "ffmpeg", "ffprobe"):
        if not shutil.which(command):
            raise RuntimeError(f"Required command not found: {command}")
    AUDIO_PATH.parent.mkdir(parents=True, exist_ok=True)
    timeline: dict[str, dict] = {}
    events: list[dict] = []
    current = 0.0
    with tempfile.TemporaryDirectory(prefix="testora-listening-") as raw_tmp:
        tmp = Path(raw_tmp)
        silence = tmp / "silence.wav"
        gap = tmp / "gap.wav"
        cue = tmp / "cue.wav"
        _run("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "5.000", str(silence))
        _run("ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.320", str(gap))
        _run("ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=880:duration=0.300:sample_rate=44100", "-af", "volume=0.12,afade=t=in:d=0.03,afade=t=out:st=0.22:d=0.08", str(cue))

        clips: list[Path] = []

        def add_speech(event_id: str, speaker: str, text: str) -> None:
            nonlocal current
            settings = VOICES[speaker]
            aiff = tmp / f"{event_id}.aiff"
            wav = tmp / f"{event_id}.wav"
            _run("say", "-v", settings["voice"], "-r", str(settings["rate"]), "-o", str(aiff), text)
            _run("ffmpeg", "-y", "-i", str(aiff), "-ar", "44100", "-ac", "1", str(wav))
            duration = _duration(wav)
            start = round(current, 3)
            current = round(current + duration, 3)
            clips.append(wav)
            events.append({"id": event_id, "kind": "speech", "speaker": speaker, "text": text, "start": start, "end": current})
            if event_id.startswith("s") and "-" in event_id:
                timeline[event_id] = {"start": start, "end": current}

        def add_clip(event_id: str, kind: str, path: Path, declared_duration: float | None = None) -> None:
            nonlocal current
            duration = declared_duration if declared_duration is not None else _duration(path)
            start = round(current, 3)
            current = round(current + duration, 3)
            clips.append(path)
            events.append({"id": event_id, "kind": kind, "start": start, "end": current, "duration": duration})

        add_speech("intro", "Narrator", INTRO)
        add_clip("intro-silence", "silence", silence, 5.0)
        add_clip("start-cue", "cue", cue)
        for section in SECTIONS:
            add_speech(f"section-{section['order']}-cue", "Narrator", f"Section {['One', 'Two', 'Three', 'Four'][section['order'] - 1]}.")
            add_clip(f"section-{section['order']}-lead", "silence", gap, 0.32)
            for index, segment in enumerate(section["segments"]):
                add_speech(segment["id"], segment["speaker"], segment["text"])
                if index < len(section["segments"]) - 1:
                    add_clip(f"{segment['id']}-gap", "silence", gap, 0.32)
            if section["order"] < 4:
                add_clip(f"section-{section['order']}-transition", "cue", cue)

        concat = tmp / "concat.txt"
        concat.write_text("".join(f"file '{path.as_posix()}'\n" for path in clips), encoding="utf-8")
        master_wav = tmp / "master.wav"
        _run("ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(master_wav))
        total = _duration(master_wav)
        fade_start = max(0, total - 0.12)
        _run(
            "ffmpeg", "-y", "-i", str(master_wav),
            "-af", f"loudnorm=I=-16:LRA=7:TP=-2.5,afade=t=in:st=0:d=0.08,afade=t=out:st={fade_start}:d=0.12",
            "-ar", "44100", "-ac", "1", "-c:a", "aac", "-b:a", "128k", str(AUDIO_PATH),
        )
    return timeline, _duration(AUDIO_PATH), events


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--content-only", action="store_true")
    args = parser.parse_args()
    if args.content_only:
        pack = _write_content({}, 0)
        print(f"wrote {CONTENT_PATH} ({len(pack['tests'][0]['sections'])} sections)")
        return 0

    timeline, duration, events = build_audio()
    _write_content(timeline, duration)
    manifest = {
        "schema_version": "testora.listening-audio-manifest.v1",
        "content_version": "1.0.0",
        "audio_path": str(AUDIO_PATH.relative_to(ROOT)),
        "intro_script": INTRO,
        "intro_silence_seconds": 5.0,
        "neutral_cue": "880 Hz sine, 300 ms, faded",
        "encoding": {"codec": "AAC", "sample_rate": 44100, "channels": 1, "bitrate": "128k"},
        "loudness_target": {"integrated_lufs": -16, "true_peak_db": -2.5, "lra": 7},
        "duration_seconds": duration,
        "voices": VOICES,
        "events": events,
        "editorial_sources": [
            "https://www.nps.gov/yell/learn/nature/soundscape.htm",
            "https://www.nps.gov/lewi/learn/nature/soundscape.htm",
            "https://www.nps.gov/ever/learn/nature/soundscape.htm"
        ],
        "source_note": "Section 4 uses general factual background from public National Park Service educational pages; all wording, examples, questions, and audio are original Testora content."
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"wrote {AUDIO_PATH} ({duration:.1f}s)")
    print(f"wrote {CONTENT_PATH}")
    print(f"wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
