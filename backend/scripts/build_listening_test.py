#!/usr/bin/env python3
"""Build an IELTS-style Listening practice test: synthesize multi-voice audio
(macOS `say`), assemble + loudness-normalize to .m4a, and emit the served
content JSON + an audio manifest.

Every character gets a UNIQUE voice (no two speakers share one). Run on macOS
with ffmpeg installed:

    python scripts/build_listening_test.py

Outputs (relative to backend/):
    static/audio/listening/testora-studio-02.m4a
    content/listening/testora-studio-02.json
    content/listening/testora-studio-02-audio-manifest.json
"""
from __future__ import annotations

import base64
import json
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SLUG = "testora-studio-listening-02"
STEM = "testora-studio-02"
AUDIO_REL = f"/static/audio/listening/{STEM}.m4a"
AUDIO_OUT = BACKEND / "static" / "audio" / "listening" / f"{STEM}.m4a"
CONTENT_OUT = BACKEND / "content" / "listening" / f"{STEM}.json"
MANIFEST_OUT = BACKEND / "content" / "listening" / f"{STEM}-audio-manifest.json"

# --- Unique voice per character (Gemini native TTS, natural human voices). ---
# No two speakers share a voice. Genders spread for realism; voice names are
# Gemini prebuilt voices and are trivially swappable if one sounds off.
TTS_MODEL = "gemini-2.5-flash-preview-tts"
TTS_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{TTS_MODEL}:generateContent"


def _api_key() -> str:
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("GEMINI_API_KEY not found in backend/.env")


API_KEY = _api_key()

VOICES = {
    "Narrator":  {"voice": "Charon",     "accent": "neutral narrator"},      # male, informative
    "Officer":   {"voice": "Kore",       "accent": "British English"},       # female
    "Caller":    {"voice": "Puck",       "accent": "North American English"},# male
    "Guide":     {"voice": "Rasalgethi", "accent": "Indian English"},        # male
    "Tutor":     {"voice": "Gacrux",     "accent": "Irish English"},         # female, mature
    "Tom":       {"voice": "Fenrir",     "accent": "North American English"},# male student
    "Lena":      {"voice": "Leda",       "accent": "North American English"},# female student
    "Lecturer":  {"voice": "Sulafat",    "accent": "South African English"}, # female
}

# ============================ TEST CONTENT ============================
# Each section: narrator lead-in, the dialogue/monologue lines (speaker, text),
# and 10 questions with answers/explanations/evidence.

SECTIONS = [
    {
        "order": 1,
        "title": "Section 1 - Community centre hall hire",
        "instructions": "Questions 1-10. Complete the booking form. Write NO MORE THAN TWO WORDS AND/OR A NUMBER for each answer.",
        "lead_in": "Section 1. You will hear a telephone conversation between a man who wants to hire a hall and a community centre officer. First, you have some time to look at questions 1 to 10.",
        "dialogue": [
            ("Officer", "Good morning, Riverside Community Centre, Diane speaking. How can I help you?"),
            ("Caller", "Hello. I'd like to hire one of your halls for a party, if any are free next month."),
            ("Officer", "Of course. Let me take a few details and start a booking form. Can I have your surname please?"),
            ("Caller", "Yes, it's Hartley."),
            ("Officer", "Could you spell that for me?"),
            ("Caller", "Certainly. H, A, R, T, L, E, Y."),
            ("Officer", "Hartley, thank you. And what kind of event is it?"),
            ("Caller", "It's a retirement party for my father. He's finishing work after forty years."),
            ("Officer", "How lovely. What date were you thinking of?"),
            ("Caller", "The sixth of May, a Saturday."),
            ("Officer", "Let me check. I'm afraid the sixth is already booked for a wedding."),
            ("Caller", "Oh. What about the following Saturday then?"),
            ("Officer", "The sixteenth of May? Yes, that's completely free."),
            ("Caller", "Great, let's say the sixteenth of May."),
            ("Officer", "We have two rooms available that day. The Oak Room holds forty people, and the larger Garden Room holds up to a hundred."),
            ("Caller", "We're expecting about seventy guests, so the Oak Room would be too small."),
            ("Officer", "In that case I'll put you down for the Garden Room. And roughly how many guests did you say?"),
            ("Caller", "Seventy. Maybe a few more, but seventy to be safe."),
            ("Officer", "That's fine. Now, the cost. On weekdays the hall is thirty pounds an hour, but on Saturdays it's forty pounds an hour."),
            ("Caller", "Forty an hour on the Saturday, understood."),
            ("Officer", "There's also a refundable deposit of sixty pounds, which you get back if there's no damage."),
            ("Caller", "No problem. Do you provide any equipment?"),
            ("Officer", "We have a projector available, but most people hiring the Garden Room ask for a microphone, as it's quite a big space."),
            ("Caller", "Yes, we'll definitely need a microphone for the speeches. We won't need the projector."),
            ("Officer", "I'll note down a microphone. One more thing about access: parking is not at the front, it's at the rear of the building."),
            ("Caller", "At the rear, got it."),
            ("Officer", "And finally, a mobile number so I can confirm the booking?"),
            ("Caller", "It's 0, 7, 8, 1, 1, 9, 0, 4, 2, 1, 7."),
            ("Officer", "Let me read that back: 0 7 8 1 1, 9 0 4 2 1 7. Perfect. I'll send a confirmation shortly."),
            ("Caller", "Thank you very much. Goodbye."),
        ],
        "questions": [
            ("Surname:", ["Hartley"], "The caller spells out his surname: H A R T L E Y.", "H, A, R, T, L, E, Y."),
            ("Type of event:", ["retirement party"], "It is a retirement party for the caller's father.", "It's a retirement party for my father."),
            ("Date of event:", ["16 May", "16th May", "the 16th of May", "sixteenth of May"], "The 6th is booked, so they agree on the 16th of May.", "The sixteenth of May? Yes, that's completely free."),
            ("Room booked:", ["Garden Room"], "Seventy guests means the Oak Room is too small, so the Garden Room is chosen.", "I'll put you down for the Garden Room."),
            ("Number of guests:", ["70", "seventy"], "He expects about seventy guests.", "We're expecting about seventy guests."),
            ("Cost on Saturday (per hour): £", ["40", "forty"], "Saturday rate is forty pounds an hour (weekday is thirty).", "on Saturdays it's forty pounds an hour."),
            ("Refundable deposit: £", ["60", "sixty"], "There is a refundable deposit of sixty pounds.", "a refundable deposit of sixty pounds."),
            ("Equipment required:", ["microphone", "a microphone"], "They need a microphone for the speeches, not the projector.", "we'll definitely need a microphone for the speeches."),
            ("Parking located at the:", ["rear"], "Parking is at the rear of the building, not the front.", "parking is not at the front, it's at the rear of the building."),
            ("Contact mobile number:", ["07811 904217", "07811904217"], "He gives his mobile number, read back as 07811 904217.", "0 7 8 1 1, 9 0 4 2 1 7."),
        ],
    },
    {
        "order": 2,
        "title": "Section 2 - Greenfield Country Park",
        "instructions": "Questions 11-15: Choose the correct answer. Questions 16-20: Match each facility to the area where it is located.",
        "lead_in": "Section 2. You will hear a guide giving an introductory talk to a group of visitors at Greenfield Country Park. First, you have some time to look at questions 11 to 20.",
        "dialogue": [
            ("Guide", "Good morning everyone, and welcome to Greenfield Country Park. My name is Sanjay and I'll give you a quick introduction before you explore."),
            ("Guide", "A little history first. People often assume this land was once farmland, but in fact, for most of the nineteenth century it was a working stone quarry. The lake you can see today was the main pit, which slowly filled with water after the quarry closed."),
            ("Guide", "Let's talk about opening times. The park itself is open from dawn until dusk all year round. The visitor centre, however, has shorter hours. In winter it closes at four, but in summer, which is now, it stays open until six in the evening, so you have plenty of time."),
            ("Guide", "A word about dogs, because many of you have brought them. Dogs are welcome across most of the park and can run freely in the woodland. However, near the lake they must be kept on leads at all times, because of the nesting birds."),
            ("Guide", "Now, people enjoy lots of activities here. We have walking trails, fishing, and cycling. But by far the most popular activity, especially with families, is bird watching. The lake attracts dozens of rare species and our hides are busy every weekend."),
            ("Guide", "And some news. We're always improving the park. Last year we resurfaced the car park, and next month we're very excited to be opening a brand new café overlooking the water. So do come back and visit it."),
            ("Guide", "Right, let me tell you where to find things, because the park is large. If you'd like to hire a bicycle, the hire point is down at the Lakeside, next to the boats."),
            ("Guide", "The picnic area is the opposite direction, tucked away in the Woodland, where there's plenty of shade on a hot day like today."),
            ("Guide", "For the best views, climb up to the Hilltop, where you'll find our observation tower. On a clear day you can see for miles."),
            ("Guide", "If you need the toilets, the nearest ones are right here at the North Gate, where you came in."),
            ("Guide", "And finally, for souvenirs and postcards, the gift shop is housed in the beautifully restored Old Mill, just across the bridge. Enjoy your visit!"),
        ],
        "questions": [
            ("In the nineteenth century the site was", ["a quarry"], "The guide says it was a working stone quarry, not farmland.", "for most of the nineteenth century it was a working stone quarry.", ["a farm", "a quarry", "a railway yard"]),
            ("In summer the visitor centre closes at", ["six o'clock"], "In summer it stays open until six in the evening.", "in summer ... it stays open until six in the evening.", ["four o'clock", "five o'clock", "six o'clock"]),
            ("Near the lake, dogs must", ["be kept on leads"], "Near the lake dogs must be kept on leads because of nesting birds.", "near the lake they must be kept on leads at all times.", ["be left at home", "be kept on leads", "run freely"]),
            ("The most popular activity in the park is", ["bird watching"], "The most popular activity is bird watching.", "the most popular activity ... is bird watching.", ["fishing", "cycling", "bird watching"]),
            ("Next month the park will open a new", ["café"], "Next month they are opening a new café overlooking the water.", "next month we're very excited to be opening a brand new café.", ["café", "car park", "boat house"]),
            ("Bicycle hire", ["Lakeside"], "Bicycle hire is at the Lakeside, next to the boats.", "the hire point is down at the Lakeside.", None),
            ("Picnic area", ["Woodland"], "The picnic area is in the Woodland.", "The picnic area ... in the Woodland.", None),
            ("Observation tower", ["Hilltop"], "The observation tower is up at the Hilltop.", "climb up to the Hilltop, where you'll find our observation tower.", None),
            ("Toilets", ["North Gate"], "The nearest toilets are at the North Gate.", "the nearest ones are right here at the North Gate.", None),
            ("Gift shop", ["Old Mill"], "The gift shop is in the Old Mill.", "the gift shop is housed in the ... Old Mill.", None),
        ],
        "match_options": ["North Gate", "Lakeside", "Hilltop", "Woodland", "Old Mill"],
    },
    {
        "order": 3,
        "title": "Section 3 - Geography field-trip report",
        "instructions": "Questions 21-25: Choose the correct answer. Questions 26-30: Decide who will do each task.",
        "lead_in": "Section 3. You will hear two students, Tom and Lena, discussing their geography field-trip report with their tutor. First, you have some time to look at questions 21 to 30.",
        "dialogue": [
            ("Tutor", "Come in, Tom, Lena. So, how did the river field trip go? I've read your draft report."),
            ("Tom", "It went well overall, but honestly the hardest part wasn't the writing. It was collecting the data, because it rained heavily on both days and our equipment kept slipping."),
            ("Lena", "Yes, the weather really slowed us down. The analysis afterwards was actually fine."),
            ("Tutor", "I see. Well, the report reads clearly, but my main suggestion is that you add more graphs. At the moment you describe the numbers in words, and a couple of charts would make the trends much easier to follow."),
            ("Tom", "That's fair. We can turn the tables into bar charts."),
            ("Tutor", "Good. Now, your central finding. What would you say your main conclusion is?"),
            ("Lena", "That the water quality actually improved as we moved downstream, which surprised us, because we expected it to get worse near the town."),
            ("Tutor", "That's a strong conclusion, and worth highlighting. For the next stage, what do you think you need to do?"),
            ("Tom", "I thought we should collect more samples."),
            ("Tutor", "You have enough samples, actually. What's missing is the human side. I'd like you to interview some local residents about how they use the river. That would add real depth."),
            ("Lena", "Okay, interviewing residents, that makes sense."),
            ("Tutor", "And remember the deadline. The full report is due at the end of the month, so don't leave the interviews too late."),
            ("Tom", "End of the month, noted. Should we divide the remaining work?"),
            ("Tutor", "Good idea. Let's agree who does what. Who'll write the introduction?"),
            ("Tom", "I'll do the introduction. I've already started it."),
            ("Lena", "And I'm happy to draw the maps, since I did the GPS work."),
            ("Tutor", "Perfect. Now, someone needs to contact the council for the historical pollution figures."),
            ("Tom", "We could both do that. Lena knows the office and I've got the reference numbers."),
            ("Lena", "Yes, let's contact the council together."),
            ("Tutor", "Fine. And the reference list, that's fiddly. Tom, can you check the references?"),
            ("Tom", "Sure, I'll check all the references."),
            ("Tutor", "Which leaves the presentation slides. Lena?"),
            ("Lena", "Yes, I'll prepare the presentation. I enjoy that part."),
            ("Tutor", "Excellent. That's a clear plan. See me again next week."),
        ],
        "questions": [
            ("According to the students, the most difficult part of the project was", ["collecting the data"], "Tom and Lena agree the hardest part was collecting data in heavy rain.", "It was collecting the data, because it rained heavily.", ["writing the report", "analysing the data", "collecting the data"]),
            ("The tutor's main suggestion is to add more", ["graphs"], "The tutor suggests adding more graphs to show the trends.", "my main suggestion is that you add more graphs.", ["words", "graphs", "samples"]),
            ("The students' main conclusion is that water quality", ["improved downstream"], "Water quality improved downstream, which surprised them.", "the water quality actually improved as we moved downstream.", ["improved downstream", "stayed the same", "got worse near the town"]),
            ("For the next stage, the tutor wants them to", ["interview residents"], "The tutor wants them to interview local residents.", "I'd like you to interview some local residents.", ["collect more samples", "redo the analysis", "interview residents"]),
            ("The full report must be handed in by", ["the end of the month"], "The deadline is the end of the month.", "The full report is due at the end of the month.", ["next week", "the end of the month", "the end of term"]),
            ("Write the introduction", ["Tom"], "Tom will write the introduction.", "I'll do the introduction.", None),
            ("Draw the maps", ["Lena"], "Lena will draw the maps.", "I'm happy to draw the maps.", None),
            ("Contact the council", ["both Tom and Lena"], "Tom and Lena will contact the council together.", "let's contact the council together.", None),
            ("Check the references", ["Tom"], "Tom will check the references.", "I'll check all the references.", None),
            ("Prepare the presentation", ["Lena"], "Lena will prepare the presentation.", "I'll prepare the presentation.", None),
        ],
        "match_options": ["Tom", "Lena", "both Tom and Lena"],
    },
    {
        "order": 4,
        "title": "Section 4 - Lecture on green roofs",
        "instructions": "Questions 31-40. Complete the notes. Write ONE WORD ONLY for each answer.",
        "lead_in": "Section 4. You will hear part of a university lecture about green roofs, that is, roofs covered with plants. First, you have some time to look at questions 31 to 40.",
        "dialogue": [
            ("Lecturer", "Good afternoon. Today we're looking at green roofs, roofs that are deliberately covered with growing plants, and why cities are increasingly adopting them."),
            ("Lecturer", "Although the idea is ancient, the modern green roof movement really began in Germany in the nineteen sixties and seventies. German engineers developed most of the early standards, and the country still has more green roofs than anywhere else."),
            ("Lecturer", "So why build them? The first major benefit is temperature. Cities are much hotter than the countryside, a problem we call the urban heat island. Green roofs absorb less heat than concrete, and so they help to reduce this island effect across a city."),
            ("Lecturer", "Let's look at how one is built, from the bottom up. Directly on the roof deck goes a waterproof layer. Above that, crucially, sits a special membrane, whose job is to stop plant roots from damaging the waterproofing below. Without it, roots would eventually cause leaks."),
            ("Lecturer", "On top of that go a drainage layer, a thin growing medium, and finally the plants. Now, the plants are chosen very carefully. Because the soil is shallow and dries quickly, designers favour succulents, plants that store water in their leaves and so survive long dry periods with almost no maintenance."),
            ("Lecturer", "Beyond cooling, green roofs bring other benefits. When it rains, an ordinary roof sends water straight into the drains all at once. A green roof soaks up much of the rain, which significantly reduces runoff and helps prevent urban flooding."),
            ("Lecturer", "There's an ecological benefit too. In dense cities with few gardens, these roofs create surprising islands of life. They provide a habitat for insects, particularly bees and butterflies, which struggle to find flowers at street level."),
            ("Lecturer", "Of course, there are drawbacks. The most obvious one is money. While they save on energy bills over time, the main disadvantage of a green roof is the high installation cost, which can deter building owners."),
            ("Lecturer", "Maintenance matters as well. Although low, it isn't zero. In particular, the roof must be inspected regularly for leaks, because water damage can be expensive and hard to trace once it spreads."),
            ("Lecturer", "Let me summarise the climate benefits. In summer, the layer of soil and plants insulates the building and keeps the rooms below noticeably cool, cutting air-conditioning use. In winter, the same layer helps keep heat in."),
            ("Lecturer", "Looking ahead, I think the trend is clear. Several cities already offer grants, and I predict that within a decade green roofs will become a legal requirement for many new buildings, just as insulation is today. We'll stop there for now."),
        ],
        "questions": [
            ("The modern green-roof movement began in ____ in the 1960s.", ["Germany"], "The movement began in Germany in the 1960s and 70s.", "the modern green roof movement really began in Germany."),
            ("Green roofs help reduce the urban heat ____ effect.", ["island"], "They reduce the urban heat island effect.", "a problem we call the urban heat island."),
            ("A special ____ stops roots from damaging the waterproofing.", ["membrane"], "A membrane stops roots from damaging the waterproofing.", "sits a special membrane, whose job is to stop plant roots."),
            ("Designers usually choose ____ because they store water and need little care.", ["succulents"], "Succulents store water in their leaves and need little maintenance.", "designers favour succulents, plants that store water in their leaves."),
            ("Green roofs significantly reduce rainwater ____.", ["runoff"], "They reduce runoff and help prevent flooding.", "significantly reduces runoff and helps prevent urban flooding."),
            ("They provide a ____ for insects such as bees.", ["habitat"], "They provide a habitat for insects such as bees.", "They provide a habitat for insects, particularly bees."),
            ("The main disadvantage is the high ____ cost.", ["installation"], "The main disadvantage is the high installation cost.", "the main disadvantage of a green roof is the high installation cost."),
            ("The roof must be checked regularly for ____.", ["leaks"], "The roof must be inspected regularly for leaks.", "the roof must be inspected regularly for leaks."),
            ("In summer, green roofs keep the rooms below ____.", ["cool"], "In summer they keep the rooms below cool.", "keeps the rooms below noticeably cool."),
            ("The lecturer predicts green roofs will become a legal ____.", ["requirement"], "He predicts they will become a legal requirement for new buildings.", "green roofs will become a legal requirement for many new buildings."),
        ],
    },
]


# ============================ AUDIO ENGINE ============================

def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def dur(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def gemini_tts_pcm(text: str, voice: str) -> bytes:
    """Return raw PCM (s16le, 24 kHz, mono) for `text` in the given Gemini voice."""
    body = json.dumps({
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }).encode()
    req = urllib.request.Request(
        TTS_URL, data=body, method="POST",
        headers={"x-goog-api-key": API_KEY, "Content-Type": "application/json"},
    )
    last = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.load(r)
            part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
            return base64.b64decode(part["data"])
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 503) and attempt < 5:
                time.sleep(6 * (attempt + 1))
                continue
            raise
    raise last  # type: ignore[misc]


def say_to_wav(text: str, voice: str, rate: int, out_wav: Path, tmp: Path) -> None:
    """Synthesize `text` via Gemini TTS and write a 44.1 kHz mono wav."""
    pcm = gemini_tts_pcm(text, voice)
    raw = tmp / "seg.pcm"
    raw.write_bytes(pcm)
    run(["ffmpeg", "-y", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(raw),
         "-ar", "44100", "-ac", "1", str(out_wav)])


def silence_wav(seconds: float, out_wav: Path) -> None:
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", f"{seconds:.3f}", "-ar", "44100", "-ac", "1", str(out_wav)])


def cue_wav(out_wav: Path) -> None:
    run(["ffmpeg", "-y", "-f", "lavfi",
         "-i", "sine=frequency=880:duration=0.3:sample_rate=44100",
         "-af", "afade=t=in:st=0:d=0.05,afade=t=out:st=0.25:d=0.05,volume=0.25",
         "-ar", "44100", "-ac", "1", str(out_wav)])


def build() -> None:
    AUDIO_OUT.parent.mkdir(parents=True, exist_ok=True)
    CONTENT_OUT.parent.mkdir(parents=True, exist_ok=True)

    tmp = Path(tempfile.mkdtemp(prefix="listen02_"))
    seg_dir = tmp / "segs"
    seg_dir.mkdir()

    parts: list[Path] = []          # ordered wav segments
    events: list[dict] = []
    clock = 0.0
    idx = 0

    def add(path: Path, kind: str, speaker: str | None = None,
            text: str | None = None, seg_id: str | None = None) -> None:
        nonlocal clock
        d = dur(path)
        ev = {"id": seg_id or f"ev{len(events)}", "kind": kind,
              "start": round(clock, 3), "end": round(clock + d, 3)}
        if speaker:
            ev["speaker"] = speaker
        if text:
            ev["text"] = text
        events.append(ev)
        parts.append(path)
        clock += d

    def speak(speaker: str, text: str, seg_id: str | None = None) -> None:
        nonlocal idx
        idx += 1
        w = seg_dir / f"{idx:04d}.wav"
        v = VOICES[speaker]
        say_to_wav(text, v["voice"], 0, w, tmp)
        add(w, "speech", speaker, text, seg_id)

    def pause(sec: float) -> None:
        nonlocal idx
        idx += 1
        w = seg_dir / f"{idx:04d}_sil.wav"
        silence_wav(sec, w)
        add(w, "silence")

    def cue() -> None:
        nonlocal idx
        idx += 1
        w = seg_dir / f"{idx:04d}_cue.wav"
        cue_wav(w)
        add(w, "cue")

    # --- Intro ---
    speak("Narrator", "This is a Testora Studio I E L T S Listening Practice Test. "
                      "The test will begin in five seconds.", "intro")
    pause(5.0)
    cue()

    sections_out = []
    for sec in SECTIONS:
        speak("Narrator", sec["lead_in"], f"s{sec['order']}-lead")
        pause(4.0)
        cue()
        # body
        passage_lines = []
        for li, (spk, text) in enumerate(sec["dialogue"], 1):
            speak(spk, text, f"s{sec['order']}-{li:02d}")
            passage_lines.append(f"{spk}: {text}")
        pause(3.0)

        # build served questions
        q_objs = []
        base = (sec["order"] - 1) * 10
        for qi, q in enumerate(sec["questions"], 1):
            text, ans, expl, quote = q[0], q[1], q[2], q[3]
            options = q[4] if len(q) > 4 else None
            # decide question_type
            if options is not None:
                qtype = "single_choice"
                opts = options
            elif "match_options" in sec and qi > 5:
                qtype = "matching_information"
                opts = sec["match_options"]
            else:
                qtype = "fill_blank"
                opts = None
            q_objs.append({
                "order": base + qi,
                "text": text,
                "question_type": qtype,
                "options": opts,
                "correct_answer": ans,
                "explanation": expl,
                "evidence": [{"paragraph": 1, "quote": quote}],
                "metadata": {"question": base + qi, "section": sec["order"]},
            })

        sections_out.append({
            "order": sec["order"],
            "title": sec["title"],
            "instructions": sec["instructions"],
            "audio_url": AUDIO_REL,
            "passage": "\n".join(passage_lines),
            "metadata": {"section": sec["order"]},
            "questions": q_objs,
        })

    # --- Assemble audio: concat -> loudnorm -> m4a ---
    concat_list = tmp / "list.txt"
    concat_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts))
    combined = tmp / "combined.wav"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
         "-c", "copy", str(combined)])
    run(["ffmpeg", "-y", "-i", str(combined),
         "-af", "loudnorm=I=-16:TP=-2.5:LRA=7",
         "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "1", str(AUDIO_OUT)])

    total = dur(AUDIO_OUT)

    # Per-section audio offsets so the player shows the right duration and can
    # play each section's slice of the single track (read from section metadata).
    for so in sections_out:
        ev = [e for e in events if e["id"].startswith(f"s{so['order']}-")]
        if ev:
            so["metadata"]["audio_start"] = round(min(e["start"] for e in ev), 3)
            so["metadata"]["audio_end"] = round(max(e["end"] for e in ev), 3)
        so["metadata"]["map_asset"] = None

    # --- Content JSON (served) ---
    content = {"tests": [{
        "title": "Testora Studio Listening Practice Test 02",
        "test_type": "listening",
        "difficulty": "Medium-Hard",
        "description": "Original IELTS-style practice test created by Testora. Four sections, 40 questions, eight distinct voices.",
        "duration_minutes": round(total / 60) + 1,
        "content_version": "1.0.0",
        "metadata": {
            "schema_version": "testora.listening-content.v1",
            "slug": SLUG,
            "published": True,
            "calibration_status": "provisional",
            "authorship": "Original IELTS-style practice test created by Testora.",
            "audio_duration": round(total, 1),
            "voices": VOICES,
        },
        "sections": sections_out,
    }]}
    CONTENT_OUT.write_text(json.dumps(content, ensure_ascii=False, indent=2))

    manifest = {
        "schema_version": "testora.listening-audio-manifest.v1",
        "content_version": "1.0.0",
        "audio_path": f"static/audio/listening/{STEM}.m4a",
        "encoding": {"codec": "AAC", "sample_rate": 44100, "channels": 1, "bitrate": "128k"},
        "loudness_target": {"integrated_lufs": -16, "true_peak_db": -2.5, "lra": 7},
        "duration_seconds": round(total, 1),
        "voices": VOICES,
        "events": events,
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(f"OK  audio={AUDIO_OUT}  ({total:.1f}s)")
    print(f"OK  content={CONTENT_OUT}")
    print(f"OK  manifest={MANIFEST_OUT}  events={len(events)}")
    # uniqueness check
    used = [v["voice"] for v in VOICES.values()]
    assert len(used) == len(set(used)), f"voice collision: {used}"
    print(f"OK  {len(VOICES)} characters, {len(set(used))} unique voices (no collisions)")


if __name__ == "__main__":
    build()
