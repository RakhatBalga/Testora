# Testora — AI Coach Redesign & Product Review

> Companion to `roadmap-ai-coach.md`. That doc is the feature catalogue. This doc is the
> **opinionated product review**: what's wrong today, how the dashboard must change, and the
> exact logic for mistake memory, band-gap, and study plans. Written to be argued with, not flattered.

---

## 0. The brutal part (read even if you skip the rest)

**You are building a Duolingo-skinned practice app and calling it a coach.** The current
dashboard shows streaks, a leaderboard, weekly-hour goals, generic skill % bars, and a
made-up "68% to target" number. None of those answer the only two questions a coach exists to answer:

1. **Why is this user stuck below their target band?**
2. **What should they do in the next 30 minutes to fix it?**

Everything that doesn't serve those two questions is decoration. Most of your current dashboard is decoration.

**Five hard truths:**

1. **Band-estimate credibility is existential, not a feature.** If your AI says "Band 6.5" and the
   user's real exam is 7.0 (or 6.0), they never trust the product again and they tell their friends
   it's wrong. Calibration + showing confidence is the difference between a coach and a toy. This is
   the single biggest risk in the whole product, and right now you have no calibration story.

2. **The feedback loop doesn't exist yet.** You have grading. A coach needs the *loop*:
   grade → extract mistakes → name the blocker → assign today's fix → re-grade → **show the band move**.
   Without "show the band move," users can't feel progress and they churn. That loop is the product.

3. **Speaking is your highest value and your highest risk.** It's where tutors are most expensive
   (so most worth replacing) — but LLM **pronunciation** scoring is genuinely weak and easy to call
   out as fake. Grade Fluency/Lexis/Grammar confidently from transcript; be humble and qualitative
   on Pronunciation until you can validate it. Don't fake a pronunciation sub-band you can't defend.

4. **Mock tests are a content problem, not a UI problem.** The exam interface is a week of work.
   Sourcing/authoring enough *good* Reading/Listening tests is the real cost and the real moat-killer
   if you get it wrong. Don't build an item-authoring CMS; get 3–4 solid full tests first.

5. **Your vocabulary page and leaderboard are premature.** A standalone vocabulary tracker
   disconnected from the user's *own* writing mistakes is a flashcard app — not coaching. The
   leaderboard has a cold-start problem and rewards the wrong thing (activity, not improvement).

**Wasted effort / distractions to stop:** leaderboard, weekly-hours goal, the four generic skill
progress bars, the "% to target" vanity number, any XP/coins gamification, a vocabulary page that
isn't fed by real mistakes. Re-spend that surface area on blockers + today's task.

---

## 1. Repositioning: from "IELTS tools" to "AI Coach"

A tools app says: *"Here are Writing, Speaking, Reading, Listening. Go practice."*
A coach says: *"Here's why you're at 6.5, here's the one thing holding you back, do this today."*

The mental model shift:

| Tools app (now) | AI Coach (target) |
|---|---|
| Sections you choose between | One recommended next action |
| "You practiced 6.5h this week" | "Your Task Response is blocking Band 7" |
| Generic progress bars | Band-per-skill + the binding constraint |
| Streaks/leaderboard as hero | Blockers + today's plan as hero |
| Grade → number | Grade → mistake → blocker → fix → re-grade → movement |

The product is the **loop**, surfaced through the dashboard. Everything else is a supporting screen.

---

## 2. Dashboard redesign (the center of the product)

The dashboard must answer Q1 (what's blocking me) and Q2 (what do I do today) **above the fold**.

### Proposed layout (top → bottom)

1. **Coach line (hero).** One sentence, generated:
   *"Rakhat, you're at an estimated **6.5**, target **7.5**. The main thing holding you back is
   **Grammar Range in Writing** — it's stuck at 6.0 across your last 4 essays."* + a **single primary
   CTA: "Start today's task →"**. This is the most important pixel in the product.

2. **Band gap strip.** Current estimated band · Target band · Gap remaining · Exam countdown
   ("23 days left — on track / behind"). Four numbers, honest, confidence-tagged.

3. **What's blocking you (top 3 blockers).** Ranked. Each: skill + criterion + plain-language reason
   + "this is capping you at Band X" + a fix CTA. This is Q1, made concrete.

4. **Today's plan (2–3 tasks).** Generated from blockers + plan + available time. Each task is one
   click into the real practice flow. This is Q2.

5. **Recent movement.** Not "recent activity" — **what changed**: "Coherence 6.0 → 6.5 (last 2 essays)",
   "Speaking fluency improving", "Reading T/F/NG accuracy dropped — revisit." Wins *and* regressions.

6. **Band trajectory.** A single line chart: estimated overall band over time, with target line.
   The "line goes up" reward. (You already built a band-history chart — repurpose it here.)

### Keep / Change / Remove verdicts

| Component (today) | Verdict | Why |
|---|---|---|
| Current/Target band | **ADD** | The whole premise. Wasn't there as an *estimate vs target*. |
| Exam countdown + on-track | **ADD** | Urgency + accountability; cheap, high-impact. |
| "What's blocking you" | **ADD (hero)** | This is Q1. The reason the product exists. |
| "Today's task" CTA | **ADD (hero)** | This is Q2. One action beats ten choices. |
| Skill progress bars (generic %) | **CHANGE** | Replace 0–100% with **band per skill** + the blocking criterion. A % with no band is meaningless for IELTS. |
| Weekly-hours goal | **REMOVE / demote** | Hours studied ≠ band improvement. Replace with "tasks that move your band this week." Measuring input, not outcome. |
| Streak | **KEEP, shrink** | Real habit lever, but a *secondary* chip, never the centerpiece. Add 1 grace/freeze day. |
| Leaderboard | **REMOVE from dashboard** | Vanity, cold-start, rewards activity not improvement. At most a buried optional page later. |
| "68% to target" number | **REMOVE** | Fabricated. Replace with concrete gap + named blockers. Fake precision destroys trust. |
| Recent activity (log) | **CHANGE** | From "what you did" → "what improved/regressed." Coaches talk about change, not logs. |

> Net: the dashboard goes from "look how active you are" to "here's your diagnosis and your prescription for today."

---

## 3. Mistake Memory System

The asset competitors can't copy: a longitudinal record of *this user's* recurring errors.

### 3.1 What to store
One row per atomic mistake, captured **in the same AI call that grades the attempt** (no second call):

- `skill` (writing|speaking|reading|listening)
- `category` — Writing: grammar, vocabulary, coherence, task_response · Speaking: fluency,
  grammar, vocabulary, pronunciation · Reading: question_type, timing · Listening: question_type, listening_weakness
- `subskill` — e.g. `articles`, `subject_verb_agreement`, `linking_devices`, `paraphrasing`,
  `TFNG`, `matching_headings`, `map_labelling`
- `severity` (1–3 — does it actually cost band, or is it cosmetic)
- `snippet` (the offending text/answer), `correction`, `explanation` (+ localized RU/KZ)
- `submission_id` + `submission_type`, `created_at`

(Table DDL is in `roadmap-ai-coach.md` §8 `mistakes`.)

### 3.2 How to calculate a weakness (the scoring logic)
Don't just count. A weakness score per (skill, category) should weight **frequency × severity ×
recency**, normalized against how often that category *could* occur:

```
weakness_score(category) =
    Σ over mistakes in category of ( severity × recency_decay(age) )
    ────────────────────────────────────────────────────────────────
                 attempts_that_could_show_this_category

recency_decay(age_days) = 0.5 ^ (age_days / HALF_LIFE)   # HALF_LIFE ≈ 14 days
```

- **Recency decay** so fixed problems fade and the coach reflects *current* weakness, not history.
- **Normalize by opportunity** so categories that simply appear more often don't always "win."
- Surface as a **percentage of current mistakes**: "Coherence = 38% of your Writing mistakes (last 30 days)."
- Flag **recurring** when the same `subskill` appears in ≥N attempts → "You've made article errors in 5 of your last 6 essays."

### 3.3 How users see it
- **Dashboard:** top 3 weaknesses only (don't overwhelm).
- **Mistakes page:** a heatmap (skill × category, color = weakness_score) + "Your top recurring mistakes" list,
  each expandable to real examples from *their* work + the fix.
- **In-context:** inline highlights on the Writing/Speaking result page (the mistake where it happened).

### 3.4 Example analytics view
```
WRITING — last 30 days (8 essays)
  Task Response   ██████████░░  blocking Band 7.0   ← binding constraint
  Coherence       ███████░░░░░  38% of mistakes
  Grammar         █████░░░░░░░  recurring: articles (6/8 essays)
  Lexical         ███░░░░░░░░░  improving ↑

Top recurring mistake: missing/incorrect articles → seen in 6 of 8 essays
Coach: "Fix articles and tighten Task Response — together that's your path to 7.0."
```

---

## 4. Band Gap Analysis

### 4.1 The IELTS math that makes this tractable
- **Overall band = average of the 4 skills, rounded to nearest 0.5.** So the cheapest +0.5 overall
  usually comes from lifting your **lowest** skill, not your favorite one.
- **Within Writing/Speaking**, the band is roughly the average of the 4 criteria, but the **lowest
  criterion drags hardest**. So the "blocker" = the criterion furthest below target band.

This means band-gap isn't fuzzy AI vibes — it's arithmetic over your stored criteria sub-bands.

### 4.2 Scoring logic
```
overall_estimate = round_to_half( mean(skill_bands) )
binding_skill    = argmin(skill_bands)                 # cheapest place to gain
for the weakest skill:
    binding_criterion = argmin(criterion_bands)        # the named blocker
gap = target_band - overall_estimate
required_lift_per_skill = how many skills need +0.5/+1.0 to round up to target
```

### 4.3 User-facing interface
A simple, honest panel:
- Current **6.5** → Target **7.5** → Gap **1.0**
- "To reach 7.5 you need two skills up +0.5. Cheapest path: **Writing 6.0→6.5** and **Speaking 6.5→7.0**."
- Per blocker, concrete and specific (not "improve grammar"):
  - *"Grammar Range is blocking Band 7 in Writing — you rely on simple sentences; you need consistent complex structures."*
  - *"Short Speaking Part 2 answers are blocking Band 7 — you average 45s; aim for the full ~2 min."*
  - *"Weak Task Response is capping Writing at 6.5 — you don't fully address all parts of the prompt."*

### 4.4 Coach recommendations
Each blocker maps to a **canned-but-personalized action** → feeds the study plan and quests.
Blocker → recommended task type → estimated band impact ("fixing this is worth ~+0.5 in Writing").

---

## 5. Personal Study Plan

### 5.1 Inputs → outputs
Inputs: current per-skill bands, target band, exam date, weak categories (from §3), daily minutes.
Outputs: today's tasks, this week's plan, skill prioritization, and a sprint mode when the exam is close.

### 5.2 Scheduling logic (rule-based first — do NOT start with ML)
1. **Rank skills by leverage:** lowest band first (cheapest path to a higher overall, per §4.1).
2. **Within a skill, target the binding criterion** and its top recurring subskills.
3. **Allocate daily minutes** across 1–3 tasks; bias to the highest-leverage blocker but rotate so it
   isn't the same task daily (boredom kills retention).
4. **Respect the deadline:** `days_left = exam_date - today`.
   - Lots of time → balanced, foundational.
   - `days_left < 21` → **Sprint mode**: drop foundational work, only high-impact Writing+Speaking
     drills on the binding constraints; Reading/Listening reduced to timed mock practice.
5. **Always end the day with one gradeable task** so mistake memory keeps updating.

### 5.3 Adaptive updates
- Re-rank after **every graded attempt** (a fixed weakness drops; a new one may surface).
- If a criterion improves to target, retire its tasks and promote the next blocker.
- Nightly job rolls the plan forward; missed tasks get re-queued (not silently dropped), capped so the
  user isn't buried under a backlog (show "behind by 2 tasks — catch up?" not 14 angry red items).

### 5.4 Exam-countdown behavior
Dashboard shows days left + on-track status (planned vs completed pace). "Behind" must offer a
**catch-up plan** CTA, never just shame. As the date nears, the plan auto-tightens toward Sprint.

---

## 6. Mock Test Strategy (MVP)

### 6.1 Reading & Listening — what to actually build
- **Content first, small:** 3–4 full Academic Reading + 3–4 Listening tests, authored or licensed.
  Quality > quantity. This is the bottleneck — start sourcing now, in parallel with the UI.
- **Interface:** timer (server-authoritative), question navigator, passage-left/questions-right
  (Reading) or audio player with one-play discipline (Listening), answer sheet, flag-for-review,
  submit with "N unanswered" guard, auto-submit on timeout.
- **Scoring is easy here:** Reading/Listening answers are objective → instant raw score → band via
  the standard raw→band conversion table. No AI needed for scoring (only for the *analysis*).

### 6.2 Result analysis (this is the coaching part)
- Raw score + band.
- **Per-question-type accuracy:** "T/F/NG 40%, Matching Headings 50%, MCQ 80%" → feeds mistake memory.
- **Timing analysis:** where did they slow down / run out of time (Listening: which section; Reading:
  did they not finish passage 3). Timing is a top-3 real reason people underperform.
- Mistake breakdown by question type → "Your weakness is Matching Headings — here's the technique."

### 6.3 Before Beta vs after launch
- **Before Beta:** the *single-section* timed practice + per-question-type analytics (cheap, high value).
- **Before Public Launch:** the full 4-section timed simulation + raw→band + the analysis above.
- **After launch:** more test content, AI-assisted item generation (with heavy human QA), adaptive difficulty.

---

## 7. Monetization (priced around IELTS outcomes, not SaaS tiers)

### 7.1 The principle
**Sell the cure, not the diagnosis.** The free tier should make the *pain* vivid (show the gap and
the blockers). The paywall unlocks the *relief* (the fixes, the plan, unlimited grading, the rewrite).
A student who's seen "Task Response is blocking your 7.0" will pay to fix it.

### 7.2 Tiers

**Free — "See where you stand"**
- Full diagnostic + estimated band + band gap + top blockers (the pain, fully visible).
- Limited grading: e.g. 2 Writing + 2 Speaking gradings / week, with rubric breakdown.
- Basic mistake memory (top weakness only), basic study plan (today's task only).
- *Goal: prove the band estimate is credible and the diagnosis is sharp.*

**Coach — the core paid plan (~$6–9/mo, or a one-time "until exam date" pass)**
- Unlimited Writing/Speaking grading.
- Full mistake memory + trends + "why your score isn't improving."
- Full adaptive study plan + weak-skill quests.
- Essay rewrite to Band 7/8.
- Full mock tests + analytics.
- RU/KZ explanations.

**Sprint / Premium — urgency pack (sold when exam < 3 weeks, premium add-on or top tier)**
- 14-day emergency plan, daily high-impact Writing+Speaking.
- Speaking audio retention + attempt comparison.
- Priority grading / longer rewrites.

### 7.3 KZ/CIS/MENA pricing reality
- **Regional / PPP pricing.** $7/mo is not universally "cheap" here — price in local currency and at
  local affordability. The pitch is **"a tutor is $10–30/hour; Testora is the price of one lesson per month."**
- **Students think in exam cycles, not subscriptions.** Offer a **one-time "exam pass"** (e.g. access
  until your exam date) alongside monthly — it converts better than forcing a recurring sub.
- **Payments:** Stripe coverage is patchy here. Abstract a `PaymentProvider` and plan for **Kaspi /
  CloudPayments / YooKassa**. Don't hardcode Stripe; it'll block your whole market.

### 7.4 Conversion & retention levers
- **Conversion:** the free diagnostic → "here's your gap and blockers" → paywall on "here's your plan
  to close it." Free no-signup essay check on the landing page as the top of funnel.
- **Retention:** the daily loop (today's task → re-grade → visible band movement) + exam countdown +
  streak. Retention is the *loop working*, not gamification bolted on.

---

## 8. Brutally honest roadmap

Impact **H/M/L** · Complexity **Easy/Med/Hard** · Priority = build order.

### 8.1 Must build immediately (the spine — without this there is no coach)
| Feature | Impact | Complexity | Priority |
|---|---|---|---|
| Calibrated rubric grading (4 criteria + overall band, strict JSON, anchor-calibrated) | H | Med | 1 |
| Mistake capture in the grading call (mistake memory data) | H | Med | 2 |
| Band estimate + confidence (per skill + overall) | H | Med | 3 |
| Dashboard spine: blocker line + band gap + today's task CTA | H | Med | 4 |

### 8.2 Must build before Beta
| Feature | Impact | Complexity | Priority |
|---|---|---|---|
| Diagnostic onboarding (target, exam date, minutes, est. band) | H | Med | 5 |
| Band gap analysis (binding skill + criterion) | H | Med | 6 |
| Speaking feedback by criteria + history | H | Hard | 7 |
| "Why isn't my score improving?" page | H | Med | 8 |
| Study plan v1 (rule-based) + today's tasks | H | Med | 9 |
| Weak-skill quests + real streak | M | Med | 10 |

### 8.3 Must build before Public Launch
| Feature | Impact | Complexity | Priority |
|---|---|---|---|
| Real Reading/Listening exam interface + 3–4 real tests + raw→band + analytics | H | Hard | 11 |
| Payments + plan gating + usage quotas (regional provider) | H | Med | 12 |
| Essay rewrite Band 7/8 (paywall wow) | H | Med | 13 |
| RU localized explanations | H | Med | 14 |
| Free no-signup essay checker (acquisition) | H | Med | 15 |
| Shareable score report (viral) | M | Med | 16 |

### 8.4 Nice to have later
Referral system · Telegram bot (reuses the quick-check API) · KZ explanations · PDF export ·
Adaptive/ML study plan · Vocabulary upgrades tied to real mistakes · B2B/teacher dashboard.

### 8.5 Do NOT build yet
SAT/TOEFL/DET/GRE · native mobile app · community/forum · Supabase migration · leaderboard expansion ·
XP/coins economy · **precise AI pronunciation sub-band scoring** (validate first; keep it qualitative) ·
AI mock-test item generation at scale (QA cost too high pre-PMF).

---

## 9. The one-paragraph verdict
Stop building tools and build the loop: **calibrated grade → mistakes → named blocker → today's fix →
re-grade → visible band movement**, with the **dashboard as the diagnosis-and-prescription screen**.
Rip the streak/leaderboard/weekly-hours/vanity-% theatre off the dashboard. Treat band-estimate
calibration as existential. Sell the *cure* (plan + fixes + unlimited) and give away the *diagnosis*
(gap + blockers). Price for KZ/CIS reality with an exam-pass option and local payment rails. Don't
touch other exams, mobile, community, or Supabase until IELTS has product-market fit.
