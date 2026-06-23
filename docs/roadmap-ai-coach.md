# Testora — AI IELTS Coach Roadmap

> Goal: evolve Testora from an "IELTS practice app" into an **AI IELTS coach** that grades
> Writing/Speaking, shows band scores, explains mistakes, remembers weak spots, tells the
> student *why their score isn't growing*, and hands them a personal plan — at a price a
> student in KZ/CIS/MENA can afford instead of a private tutor.

---

## 0. Reality check (read this first)

The product brief lists the stack as **Supabase + Gemini + Vercel**. The repo today is:

| Layer | Brief says | Repo actually is |
|---|---|---|
| Frontend | Next.js + TS | ✅ Next.js 16 + TS (App Router) |
| Backend | Supabase | ❌ **FastAPI (Python) + SQLAlchemy + Alembic** |
| DB | Supabase Postgres | ✅ Postgres — but accessed via SQLAlchemy, not Supabase client |
| AI | Gemini | ✅ `google-genai` installed; `services/ai/` has mock/claude/gemini behind a factory |
| Hosting | Vercel | Frontend can go on Vercel; **FastAPI cannot** (needs a Python host: Railway/Render/Fly) |

**Decision you must make once (it shapes everything below):**

- **Option A — keep FastAPI.** All "API logic" below = FastAPI routers. DB = your existing
  Postgres + Alembic migrations. You host the API on Railway/Render. This roadmap is written
  primarily for Option A because it's what you already have working.
- **Option B — migrate to Supabase.** You'd drop FastAPI, move auth to Supabase Auth, put
  business logic in Edge Functions / Next.js route handlers, and use RLS. Cleaner for a solo
  dev and Vercel-native, but it's a **2–3 week migration** that builds zero user-facing value.

> My recommendation: **stay on Option A for the beta.** Don't migrate mid-roadmap. The table
> designs below are plain Postgres DDL — they work as Alembic migrations *and* as Supabase
> tables verbatim, so you keep the option open. Every AI feature already has a home in
> `services/ai/` — lean on that, don't scatter Gemini calls across the codebase.

A second hard truth: **the moat is not "we call Gemini."** Anyone can. The moat is
**mistake memory + band-gap analysis + "why your score isn't improving"** — the longitudinal
data you accumulate per user. Build the data capture early even if the UI is ugly, because
that history is what you can't fake later.

Legend: Impact **H/M/L** · Difficulty **Easy/Med/Hard** · Stage **Now/Beta/Launch/Later** · **Free/Premium**

---

## 1. Must-have before first serious beta

These make the core loop (practice → graded → told what to fix → come back) actually work.
Without them you have a demo, not a coach.

### 1.1 Structured IELTS rubric breakdown (Writing + Speaking)
- **What:** every Writing/Speaking grade returns the 4 official criteria with a per-criterion
  band + 1–2 line justification, not just one overall number.
  - Writing: Task Response/Achievement, Coherence & Cohesion, Lexical Resource, Grammar Range & Accuracy.
  - Speaking: Fluency & Coherence, Lexical Resource, Grammar Range & Accuracy, Pronunciation.
- **Why:** the overall band is useless for improvement; students need to know *which* criterion
  is dragging them. This is the foundation every other coaching feature reads from.
- **Impact:** H · **Difficulty:** Med · **Stage:** Now · **Free**
- **DB:** you already store `writing_submissions.feedback JSON`. Formalize the shape:
  `feedback = { overall, criteria: { task_response: {band, comment}, ... }, errors: [...] }`.
  Add the same `feedback JSON` + `band` to a new `speaking_submissions` rubric (speaking model exists).
- **Frontend:** `RubricBreakdown.tsx` (4 bars + comments), reused in Writing result & Speaking result.
- **Backend:** tighten the Gemini prompt in `services/ai/` to return strict JSON per criterion;
  validate with a Pydantic schema so a malformed model response can't crash the result page.
- **Risks:** Gemini returns prose instead of JSON → enforce `response_mime_type=application/json`
  + schema + a repair/fallback path. Band inflation → calibrate with a few anchor essays in the prompt.

### 1.2 Mistake memory (the core differentiator)
- **What:** every graded attempt extracts atomic mistakes tagged by category
  (grammar, vocabulary, coherence, task response, pronunciation, fluency, reading-q-type,
  listening-q-type). Store them per user. Aggregate into "You make 40% of your Writing Task 2
  mistakes in Coherence."
- **Why:** this is the product. It's what a tutor does and an app usually doesn't. It powers
  band-gap analysis, quests, study plan, and the "why no improvement" page.
- **Impact:** H · **Difficulty:** Hard · **Stage:** Beta · **Free** (deep history → Premium later)
- **DB:** `mistakes` table (see §8). One row per detected mistake with `category`, `skill`,
  `subskill`, `severity`, `snippet`, `correction`, `submission_id`, `created_at`.
- **Frontend:** none required for capture; surfaces in §1.4, §5, §6 later.
- **Backend:** grading pipeline writes mistakes in the same call that returns the rubric
  (don't make a second AI call — extract errors in the same JSON).
- **Risks:** category drift (the model invents categories) → constrain to a fixed enum in the
  prompt and reject unknown tags. Volume → cap mistakes per submission (e.g. top 15 by severity).

### 1.3 Diagnostic test / onboarding
- **What:** first-run flow capturing target band, exam date, daily study minutes, self-rated
  weak skills, **plus** one short auto-graded writing prompt + a few reading/listening items to
  produce an *estimated current band* instead of relying on self-report.
- **Why:** you can't build a study plan or band-gap without a starting point and a deadline.
  It also massively improves activation (user feels the product "gets" them in minute one).
- **Impact:** H · **Difficulty:** Med · **Stage:** Beta · **Free**
- **DB:** `profiles` (target_band, exam_date, daily_minutes, native_language, country),
  `goals`, and a `diagnostic_results` row.
- **Frontend:** extend the existing 3-step register onboarding into a post-signup diagnostic
  (`/onboarding/diagnostic`). Reuse the step/progress UI you already built.
- **Backend:** `POST /onboarding`, reuses the Writing grader for the diagnostic essay.
- **Risks:** too long → people drop. Keep ≤8 min. Make the essay skippable with a "self-estimate" fallback.

### 1.4 Band gap analysis
- **What:** dashboard module: current estimated band → target band, per skill, with the 2–3
  concrete things to fix to close each gap (pulled from mistake memory + rubric weak criteria).
- **Why:** turns scattered feedback into a single "here's your path" view. High motivational payoff.
- **Impact:** H · **Difficulty:** Med · **Stage:** Beta · **Free**
- **DB:** computed from `goals` + `mistakes` + latest bands; optionally cache in `band_estimates`.
- **Frontend:** `BandGap.tsx` (current vs target gauge + ranked fix-list per skill).
- **Backend:** `GET /analytics/band-gap` — aggregates mistakes by category, maps weak criteria → actions.
- **Risks:** estimated band noisy with little data → show confidence ("based on 3 attempts").

### 1.5 Speaking feedback by criteria + recording history
- **What:** Speaking attempts graded on the 4 criteria with answer-length and a model "improved
  answer." Every attempt saved so the user can replay/compare. (Audio storage = Premium; transcript+score = Free.)
- **Why:** Speaking is the hardest to self-assess and where tutors are most expensive — biggest value-per-feature.
- **Impact:** H · **Difficulty:** Hard · **Stage:** Beta · **Free** (audio retention Premium)
- **DB:** `speaking_submissions` (extend existing) with `transcript`, `feedback JSON`, `audio_url NULL`.
- **Frontend:** `SpeakingResult.tsx` + `SpeakingHistory.tsx` (list, play if audio kept, compare two attempts).
- **Backend:** transcribe (Gemini supports audio) → grade → store. Gate audio persistence by plan.
- **Risks:** transcription cost/latency, audio storage cost/privacy (see §9 storage + consent).

> **Beta exit bar:** a new user can onboard, do a Writing + Speaking task, get a rubric breakdown,
> see their band gap, and see at least one "your top mistake category" insight. That's a coach.

---

## 2. Must-have before public launch

Polish + the things press/word-of-mouth will judge you on.

### 2.1 Real IELTS exam interface (Reading & Listening)
- **What:** authentic test UI — countdown timer, question navigator, passage-left/questions-right,
  answer sheet, flag-for-review, submit + "you have N unanswered" guard, auto-submit on timeout.
- **Why:** this is table stakes for "IELTS prep" credibility and the #1 thing Reading/Listening
  users expect. Currently missing — it's your biggest content gap.
- **Impact:** H · **Difficulty:** Hard · **Stage:** Launch · **Free**
- **DB:** reuse `tests/sections/questions`; add `mock_tests` + `mock_attempts` for full timed runs.
- **Frontend:** `/mock-tests/[id]/run` with `ExamTimer`, `QuestionNavigator`, `PassagePane`,
  `AnswerSheet`, `ReviewModal`. (Your Mock Tests listing page already exists as a shell.)
- **Backend:** `POST /mock-attempts/start|answer|submit`; server-side timer authority (don't trust client clock).
- **Risks:** content authoring is the real cost (writing/licensing passages), not the UI. Plan content sourcing now.

### 2.2 Personal study plan
- **What:** generates a weekly plan + daily tasks from target band, exam date, weak skills, and
  available minutes. Adapts as mistakes/bands change.
- **Why:** converts insight into a habit. The "tutor would tell me what to do today" feeling.
- **Impact:** H · **Difficulty:** Hard · **Stage:** Launch · **Free** (advanced adaptivity → Premium)
- **DB:** `study_plans`, `study_tasks` (date, skill, type, target, status).
- **Frontend:** `/plan` (week view + today's tasks), dashboard "Today" widget.
- **Backend:** `POST /plan/generate` (rule-based first, Gemini-assisted later), nightly job to roll the plan forward.
- **Risks:** over-engineering the scheduler. **Start rule-based** (templates by gap + days-left), not ML.

### 2.3 Vocabulary weakness tracker
- **What:** detects repeated basic words ("good", "very", "important"), suggests academic
  upgrades, tracks vocabulary growth over time; feeds the Lexical Resource criterion.
- **Why:** Lexical Resource is a common ceiling at band 6→7; cheap, concrete wins.
- **Impact:** M · **Difficulty:** Med · **Stage:** Launch · **Free**
- **DB:** `vocab_items` (word, status: learning/known/weak), `vocab_flags` (overused word → suggestion, submission_id).
- **Frontend:** extend the existing `/vocabulary` page with "overused words" + suggestions; inline highlights in Writing result.
- **Backend:** lexical analysis step in the Writing pipeline (frequency + level lookup), no extra AI call needed for detection.
- **Risks:** false positives ("good" is fine sometimes) → suggest, never penalize automatically.

### 2.4 Exam countdown + on-track status
- **What:** dashboard shows "23 days to your exam — on track / behind" based on plan completion vs required pace.
- **Why:** urgency + accountability; cheap retention lever.
- **Impact:** M · **Difficulty:** Easy · **Stage:** Beta · **Free**
- **DB:** `goals.exam_date` (already planned).
- **Frontend:** `ExamCountdown.tsx` dashboard widget (you already mocked a streak/goal strip — reuse).
- **Backend:** pure computation; no new endpoint if profile is already loaded.
- **Risks:** "behind" must motivate, not shame → positive framing + a "catch-up plan" CTA.

### 2.5 "Why my score isn't improving?" page
- **What:** a single page that names the 2–3 real blockers (top mistake categories, a criterion
  stuck for N attempts, plateaued band) and gives 3 concrete next actions.
- **Why:** this is the emotional core of the value prop and the most *shareable* insight. It's
  what makes people say "this app actually told me the truth."
- **Impact:** H · **Difficulty:** Med · **Stage:** Launch · **Free**
- **DB:** reads `mistakes`, `band_estimates`, attempt history. No new tables.
- **Frontend:** `/insights/why` — narrative + evidence + action buttons (→ quests/plan).
- **Backend:** `GET /insights/why` aggregation; optional Gemini pass to phrase it empathetically.
- **Risks:** needs ≥~5 attempts of data to be credible → gate with an empty state until enough history.

### 2.6 Localized explanations (RU now, KZ later)
- **What:** mistake explanations available in Russian, tuned to common L1-Russian/Kazakh errors
  (articles, prepositions, word order, aspect). Toggle in settings.
- **Why:** **your wedge.** Global apps explain in English; your audience often can't fully parse
  English grammar explanations. RU/KZ explanations are a genuine differentiator for KZ/CIS/MENA.
- **Impact:** H · **Difficulty:** Med · **Stage:** Beta · **Free**
- **DB:** `profiles.explanation_language` ('en'|'ru'|'kk'); cache `mistakes.explanation_localized`.
- **Frontend:** language toggle on result/insight pages (you already have an EN/RU/KZ switcher in nav — wire it).
- **Backend:** Gemini prompt switch by language; cache translations to control cost.
- **Risks:** translation cost per mistake → cache aggressively; KZ quality lower → ship RU first, KZ behind a flag.

---

## 3. Premium features (monetization)

> Pricing reality for this audience: target **~$3–8/month** or a one-time exam-prep pack.
> Tutors cost $10–30/hour here — you win on price. **Free must be genuinely useful** (one
> Writing + one Speaking grade/day, full rubric, basic mistake memory) or the funnel dies.
> Gate *depth and volume*, not the core "is it any good" experience.

### 3.1 Essay rewrite to Band 7 / Band 8
- **What:** original essay → corrected version → upgraded Band 7 → upgraded Band 8, with a diff
  and an explanation of *what changed and why* per criterion.
- **Why:** the single most "wow" paid feature — students see exactly what a higher band looks like
  for *their* essay. Strong willingness to pay.
- **Impact:** H · **Difficulty:** Med · **Stage:** Beta(build)/Launch(gate) · **Premium**
- **DB:** `essay_rewrites` (submission_id, corrected, band7, band8, explanation JSON).
- **Frontend:** `RewriteTabs.tsx` (Original | Corrected | Band 7 | Band 8) + diff highlighting.
- **Backend:** dedicated Gemini call; expensive → Premium + per-day cap even for Premium.
- **Risks:** token cost (long essays ×4 versions) → cache, and stream output.

### 3.2 Speaking audio retention + progress comparison
- **What:** keep audio long-term, compare any two attempts side by side, track fluency/pronunciation trend.
- **Free tier:** transcript + score kept; audio deleted after 24h. **Premium:** audio kept + compare.
- **Impact:** M · **Difficulty:** Med · **Stage:** Launch · **Premium**
- **DB:** `speaking_submissions.audio_url`, `audio_expires_at`.
- **Risks:** storage cost & privacy/consent (voice = personal data) → explicit consent + retention policy.

### 3.3 Emergency mode / 14-day IELTS sprint
- **What:** a fixed high-intensity plan for users with an exam <2–3 weeks out — daily
  high-impact Writing + Speaking tasks, ruthless prioritization of the biggest band levers.
- **Why:** high urgency = high willingness to pay *right now*. Natural paywall moment.
- **Impact:** M · **Difficulty:** Med · **Stage:** Launch · **Premium**
- **DB:** reuse `study_plans` with `mode='sprint'`.
- **Frontend:** `/sprint` focused mode (stripped UI, one task at a time).
- **Risks:** promising a band jump in 14 days → never guarantee outcomes; frame as "maximize what's possible."

### 3.4 Unlimited grading + full history + advanced analytics
- **What:** remove daily caps, full mistake history & trends, all rewrite bands, all localized explanations.
- **Impact:** H (it's the core paywall) · **Difficulty:** Easy (it's gating) · **Stage:** Launch · **Premium**
- **DB:** `subscriptions` (plan, status, current_period_end), `usage_counters` (daily quotas).
- **Risks:** quota logic must be server-side and abuse-resistant.

> **Payments:** for KZ/CIS, Stripe coverage is patchy. Plan for a local processor (Kaspi, CloudPayments,
> YooKassa) abstracted behind one `PaymentProvider` interface. Don't hardcode Stripe.

---

## 4. Viral growth features

### 4.1 Free Writing checker without registration (top of funnel)
- **What:** paste an essay on the landing page → instant short feedback (overall band + one weak
  criterion + 1 sample fix). Full rubric/rewrite/history requires sign-up.
- **Why:** lowest-friction proof of value; the natural hook for ads/SEO/Telegram. This should be
  the **#1 acquisition surface.**
- **Impact:** H · **Difficulty:** Med · **Stage:** Beta · **Free (lead-gen)**
- **DB:** `anon_checks` (ip/fingerprint, count) for rate-limiting; optional email capture.
- **Frontend:** landing `<FreeChecker/>` + teaser result with a "Sign up for the full report" wall.
- **Backend:** `POST /public/quick-check` — heavily rate-limited, abuse-protected, cheap model/short output.
- **Risks:** **abuse/cost** (free Gemini calls to anonymous users) → strict rate limits, length cap,
  captcha/Turnstile, and a cheaper/shorter prompt than the logged-in grader.

### 4.2 Shareable score report
- **What:** a beautiful, public, link-shareable report card (band + rubric + improvement),
  PDF download later. Watermarked with Testora branding.
- **Why:** students *love* sharing scores; every share is a branded impression. Cheap viral loop.
- **Impact:** M · **Difficulty:** Med · **Stage:** Launch · **Free**
- **DB:** `score_reports` (public_slug, snapshot JSON, visibility).
- **Frontend:** `/r/[slug]` public OG-optimized page (dynamic OG image), share buttons.
- **Backend:** snapshot at share-time (immutable); `GET /r/[slug]`.
- **Risks:** privacy (don't leak full essay unless opted in) + fake/edited reports → snapshot + watermark.

### 4.3 Referral system
- **What:** invite link → both sides get extra checks / Premium days when invitee completes a task.
- **Why:** cheapest paid-feeling growth for a budget audience; rewards align with usage.
- **Impact:** M · **Difficulty:** Med · **Stage:** Launch · **Free→Premium reward**
- **DB:** `referrals` (referrer_id, invitee_id, status, reward_granted).
- **Frontend:** `/invite` + dashboard widget.
- **Backend:** attribution on signup, anti-fraud (one reward per verified, active invitee).
- **Risks:** self-referral/fraud → require the invitee to actually complete a graded task before reward.

---

## 5. Retention features

### 5.1 Streaks (keep it simple)
- **What:** daily-practice streak + 3/7/14-day milestones. One number on the dashboard. No leagues, no XP economy.
- **Why:** proven habit lever; you already display a streak — just make it real.
- **Impact:** M · **Difficulty:** Easy · **Stage:** Beta · **Free**
- **DB:** `streaks` (current, longest, last_active_date) or derive from `activity_log`.
- **Risks:** punishing breaks too hard → offer one "freeze"/grace day.

### 5.2 Weak-skill quests
- **What:** 1–3 daily tasks generated from mistake memory: "Fix Task Response today",
  "Do 5 Speaking Part 2 answers", "Rewrite one Coherence-weak paragraph."
- **Why:** turns analysis into a concrete daily action; the engine of the daily loop.
- **Impact:** H · **Difficulty:** Med · **Stage:** Launch · **Free**
- **DB:** `quests` (date, type, target_category, status, reward).
- **Frontend:** dashboard "Today's quests" + completion animation.
- **Backend:** `GET /quests/today` generated from top weak categories + plan.
- **Risks:** repetitive quests → rotate categories, cap repeats.

### 5.3 Progress trends & comparison
- **What:** band trajectory per skill over time, attempt-vs-attempt comparison (Speaking & Writing).
- **Why:** seeing the line go up is the reward that brings people back.
- **Impact:** M · **Difficulty:** Med · **Stage:** Launch · **Free** (deep history Premium)
- **DB:** `band_estimates` time series (already partly visualized in your Analytics page).
- **Risks:** noisy with little data → smooth + show trend only after a few points.

---

## 6. Features for later

| Feature | Note | Stage |
|---|---|---|
| Telegram bot mini-version | Send essay → quick band → link to full report. Great for this audience, but build only after the web quick-check + report API exist (the bot just calls them). | Later · Free→funnel |
| KZ-language explanations | Ship after RU is validated and translation quality is acceptable. | Later · Free |
| PDF export of score report | After the web report card works; use a render service. | Later · Premium |
| Adaptive/ML study plan | Only after rule-based plan + enough data. Don't start here. | Later · Premium |
| Teacher/B2B dashboard (schools, agencies) | Real revenue path in KZ/CIS, but a different product surface — after consumer beta. | Later |
| Listening/Reading auto-item-generation via AI | Powerful for content scale, but needs heavy QA. | Later |

---

## 7. Features to NOT build now

- **SAT / TOEFL / Duolingo English Test / GRE** — explicitly out. Don't dilute the IELTS focus or the data model.
- **Native mobile app** — the web app (responsive + later a PWA) covers it. A mobile app is months of work for no new value pre-PMF.
- **Full social network / community / forums** — moderation + cold-start problem; not your moat. (A leaderboard is enough social proof — keep it secondary, as you already have.)
- **Live human tutoring / marketplace** — opposite of your "without an expensive tutor" thesis and an ops nightmare.
- **Supabase migration mid-roadmap** — zero user value; revisit only if FastAPI hosting becomes a real pain.
- **Your own LLM / fine-tuning** — Gemini + good prompts + calibration is enough until you have thousands of graded essays.
- **Gamified XP economy / coins / avatars** — streaks + quests are enough; don't build a game.

---

## 8. Postgres / Supabase table structure

> Plain Postgres DDL. Use as Alembic migrations (Option A) or paste into Supabase SQL editor
> (Option B). `feedback`/snapshot columns are `jsonb`. Existing tables: `users`, `tests`,
> `sections`, `questions`, `attempts`, `writing_tasks`, `writing_submissions`, speaking tables.

```sql
-- Profile & goals -----------------------------------------------------------
create table profiles (
  user_id            bigint primary key references users(id) on delete cascade,
  first_name         text,
  native_language    text,            -- 'ru' | 'kk' | 'en' | ...
  country            text,
  explanation_language text default 'en',  -- 'en' | 'ru' | 'kk'
  daily_minutes      int default 30,
  created_at         timestamptz default now()
);

create table goals (
  id            bigserial primary key,
  user_id       bigint references users(id) on delete cascade,
  target_band   numeric(2,1) not null,    -- 6.5, 7.0 ...
  current_band  numeric(2,1),             -- estimated
  exam_date     date,
  created_at    timestamptz default now()
);

-- Diagnostic ----------------------------------------------------------------
create table diagnostic_results (
  id              bigserial primary key,
  user_id         bigint references users(id) on delete cascade,
  estimated_band  numeric(2,1),
  per_skill       jsonb,   -- {listening, reading, writing, speaking}
  weak_skills     text[],
  created_at      timestamptz default now()
);

-- Mistake memory (the moat) -------------------------------------------------
create table mistakes (
  id            bigserial primary key,
  user_id       bigint references users(id) on delete cascade,
  skill         text not null,        -- writing|speaking|reading|listening
  category      text not null,        -- grammar|vocabulary|coherence|task_response|
                                       -- pronunciation|fluency|reading_qtype|listening_qtype
  subskill      text,                 -- e.g. 'articles', 'subject_verb_agreement'
  severity      int default 1,        -- 1..3
  snippet       text,                 -- the offending text
  correction    text,
  explanation        text,
  explanation_localized jsonb,        -- {ru: "...", kk: "..."}
  submission_id bigint,               -- polymorphic ref (writing/speaking/mock)
  submission_type text,
  created_at    timestamptz default now()
);
create index on mistakes (user_id, category);
create index on mistakes (user_id, created_at);

-- Band estimates time series ------------------------------------------------
create table band_estimates (
  id          bigserial primary key,
  user_id     bigint references users(id) on delete cascade,
  skill       text not null,          -- or 'overall'
  band        numeric(2,1) not null,
  source      text,                   -- diagnostic|writing|speaking|mock
  created_at  timestamptz default now()
);

-- Study plan ----------------------------------------------------------------
create table study_plans (
  id          bigserial primary key,
  user_id     bigint references users(id) on delete cascade,
  mode        text default 'standard',  -- standard|sprint
  start_date  date,
  end_date    date,
  created_at  timestamptz default now()
);
create table study_tasks (
  id          bigserial primary key,
  plan_id     bigint references study_plans(id) on delete cascade,
  user_id     bigint references users(id) on delete cascade,
  due_date    date not null,
  skill       text,
  type        text,                   -- practice|rewrite|speaking|vocab|mock
  target      text,                   -- human label
  status      text default 'pending', -- pending|done|skipped
  created_at  timestamptz default now()
);

-- Quests & streaks ----------------------------------------------------------
create table quests (
  id          bigserial primary key,
  user_id     bigint references users(id) on delete cascade,
  date        date not null,
  type        text,
  target_category text,
  status      text default 'pending',
  created_at  timestamptz default now()
);
create table streaks (
  user_id        bigint primary key references users(id) on delete cascade,
  current_streak int default 0,
  longest_streak int default 0,
  last_active    date,
  freezes_left   int default 1
);
create table activity_log (
  id        bigserial primary key,
  user_id   bigint references users(id) on delete cascade,
  kind      text,            -- writing|speaking|mock|vocab|quest
  ref_id    bigint,
  created_at timestamptz default now()
);

-- Vocabulary ----------------------------------------------------------------
create table vocab_items (
  id        bigserial primary key,
  user_id   bigint references users(id) on delete cascade,
  word      text not null,
  status    text default 'learning',  -- learning|known|weak
  topic     text,
  updated_at timestamptz default now(),
  unique (user_id, word)
);
create table vocab_flags (
  id            bigserial primary key,
  user_id       bigint references users(id) on delete cascade,
  overused_word text,
  suggestion    text,
  submission_id bigint,
  created_at    timestamptz default now()
);

-- Essay rewrites (Premium) --------------------------------------------------
create table essay_rewrites (
  id            bigserial primary key,
  submission_id bigint references writing_submissions(id) on delete cascade,
  user_id       bigint references users(id) on delete cascade,
  corrected     text,
  band7         text,
  band8         text,
  explanation   jsonb,
  created_at    timestamptz default now()
);

-- Mock tests (real exam interface) ------------------------------------------
create table mock_tests (
  id          bigserial primary key,
  title       text,
  test_type   text,           -- academic
  duration_min int,
  expected_band numeric(2,1)
);
create table mock_attempts (
  id          bigserial primary key,
  user_id     bigint references users(id) on delete cascade,
  mock_test_id bigint references mock_tests(id),
  status      text default 'in_progress',  -- in_progress|submitted|expired
  answers     jsonb,          -- {question_id: answer}
  flagged     jsonb,          -- [question_id, ...]
  started_at  timestamptz default now(),
  expires_at  timestamptz,    -- server-authoritative timer
  submitted_at timestamptz,
  result      jsonb
);

-- Growth & monetization -----------------------------------------------------
create table score_reports (
  id          bigserial primary key,
  user_id     bigint references users(id) on delete cascade,
  public_slug text unique,
  snapshot    jsonb,          -- immutable copy at share time
  visibility  text default 'unlisted',
  created_at  timestamptz default now()
);
create table referrals (
  id            bigserial primary key,
  referrer_id   bigint references users(id) on delete cascade,
  invitee_id    bigint references users(id),
  code          text unique,
  status        text default 'pending',  -- pending|qualified|rewarded
  created_at    timestamptz default now()
);
create table subscriptions (
  user_id            bigint primary key references users(id) on delete cascade,
  plan               text default 'free',     -- free|premium
  status             text default 'active',
  current_period_end timestamptz,
  provider           text,                     -- kaspi|cloudpayments|stripe
  created_at         timestamptz default now()
);
create table usage_counters (
  user_id   bigint references users(id) on delete cascade,
  day       date,
  kind      text,            -- writing_grade|speaking_grade|rewrite|quick_check
  count     int default 0,
  primary key (user_id, day, kind)
);
create table anon_checks (
  id          bigserial primary key,
  fingerprint text,          -- ip+ua hash
  day         date,
  count       int default 0,
  email       text
);
```

---

## 9. Suggested Next.js folder structure

> App Router. Keep features vertical (a feature owns its components/hooks/types). API calls go
> through one typed `lib/api/*` layer (today that's your FastAPI client; if you ever move to
> Supabase only this layer changes).

```
frontend/src/
  app/
    (marketing)/                 # public, no app chrome
      page.tsx                   # landing + FreeChecker
      r/[slug]/page.tsx          # public shareable score report (OG image)
    (auth)/
      login/ register/ onboarding/diagnostic/
    (app)/                       # authenticated shell (nav + container)
      dashboard/page.tsx
      practice/[skill]/...
      writing/  speaking/
      mock-tests/[id]/run/page.tsx   # real exam interface
      plan/  quests/  vocabulary/  analytics/
      insights/why/page.tsx
      sprint/                    # premium emergency mode
      settings/  billing/
    admin/                       # gated admin panel
  components/
    ui/                          # Button, Card, Badge, Input, Modal, Progress...
    dashboard/                   # widgets (band gap, countdown, streak, quests)
    writing/   speaking/         # RubricBreakdown, RewriteTabs, SpeakingHistory
    exam/                        # ExamTimer, QuestionNavigator, PassagePane, AnswerSheet
    growth/                      # FreeChecker, ShareReport, ReferralWidget
  lib/
    api/                         # typed clients: writing.ts, speaking.ts, plan.ts, mistakes.ts
    auth.tsx
    rubric.ts                    # shared IELTS criteria types/labels
    format.ts
  hooks/                         # useRequireAuth, usePlan, useStreak, useQuota
  types/                         # shared TS types mirroring backend schemas
```

Backend (FastAPI, Option A) mirrors features:
```
backend/app/
  routers/   onboarding.py  plan.py  mistakes.py  insights.py  quests.py
             mock_tests.py  rewrites.py  growth.py (public quick-check, referrals)  billing.py
  services/
    ai/      base|factory|gemini|claude|mock  (+ prompts/ for each task)
    grading/ writing.py  speaking.py  mistakes.py  (extraction + rubric)
    plan/    generator.py (rule-based first)
    analytics/ band_gap.py  why.py
  models/    (one per table above)
  schemas/   (Pydantic in/out, incl. strict rubric JSON schema)
```

---

## 10. 30-day implementation plan

> Solo dev, ~realistic pace. Each week ends on something demoable. Commit per feature; deploy weekly.

**Week 1 — Make grading a coach, not a number.**
- Day 1–2: Lock the rubric JSON schema (Pydantic) + Gemini `response_mime_type=json`; validate/repair.
- Day 3–4: `RubricBreakdown.tsx`; wire into Writing result (real Gemini, calibrated). (§1.1)
- Day 5: `mistakes` table + extract mistakes in the same grading call; start writing rows. (§1.2)
- Day 6–7: Speaking grading on 4 criteria + transcript; save attempts (no audio yet). (§1.5)

**Week 2 — Onboarding + the "truth" features.**
- Day 8–9: `profiles`/`goals`/`diagnostic_results` + `/onboarding/diagnostic` (reuse step UI). (§1.3)
- Day 10–11: Band gap analysis endpoint + `BandGap.tsx` on dashboard. (§1.4)
- Day 12: Exam countdown widget. (§2.4)
- Day 13–14: "Why isn't my score improving?" page from mistake aggregates. (§2.5)
- **Beta exit bar hit here.**

**Week 3 — Habit loop + acquisition hook.**
- Day 15–16: Streaks (real) + activity_log. (§5.1)
- Day 17–18: Weak-skill quests from top mistake categories. (§5.2)
- Day 19–20: RU localized explanations (cache). (§2.6)
- Day 21: Free Writing checker on landing (rate-limited). (§4.1)

**Week 4 — Monetizable wow + growth + launch prep.**
- Day 22–24: Essay rewrite Band 7/8 (Premium-gated, capped). (§3.1)
- Day 25–26: Shareable score report `/r/[slug]` + OG image. (§4.2)
- Day 27–28: Subscriptions + usage_counters + server-side quota gating (payment provider stub). (§3.4)
- Day 29: Rule-based study plan v1 (today's tasks widget). (§2.2 lite)
- Day 30: Polish, empty states, error handling, deploy; instrument analytics.

> Deliberately **after day 30:** full real-exam Reading/Listening UI (§2.1) — it's the biggest
> chunk and gated on content authoring; run it as its own 2-week track in parallel with content sourcing.

---

## 11. Priority order (most → least important)

1. **Rubric breakdown** (Writing+Speaking) — everything reads from it. (§1.1)
2. **Mistake memory** — the moat; start capturing immediately. (§1.2)
3. **Diagnostic onboarding** — gives every other feature a baseline + deadline. (§1.3)
4. **Band gap analysis** — turns data into direction. (§1.4)
5. **Speaking feedback by criteria + history** — highest value-per-feature. (§1.5)
6. **"Why isn't my score improving?"** — emotional core + shareable. (§2.5)
7. **Weak-skill quests** — converts insight into the daily loop. (§5.2)
8. **Streaks** — cheap retention. (§5.1)
9. **Free Writing checker (no signup)** — top of funnel / acquisition. (§4.1)
10. **RU localized explanations** — your wedge for KZ/CIS/MENA. (§2.6)
11. **Essay rewrite Band 7/8** — first real paywall wow. (§3.1)
12. **Subscriptions + quotas** — turn it on once there's something worth paying for. (§3.4)
13. **Personal study plan (rule-based)** — habit + structure. (§2.2)
14. **Shareable score report** — viral loop. (§4.2)
15. **Exam countdown** — easy urgency. (§2.4)
16. **Vocabulary weakness tracker** — concrete band-6→7 wins. (§2.3)
17. **Real exam Reading/Listening interface** — credibility, but heavy + content-bound. (§2.1)
18. **Referral system** — growth once retention works. (§4.3)
19. **Emergency 14-day sprint** — premium urgency pack. (§3.3)
20. **Telegram bot / KZ explanations / PDF export** — later, reuse existing APIs. (§6)

---

### One-line strategic summary
Build the **grading → mistake memory → band gap → "why" → quests** spine first; that's the coach
no competitor in your market has. Wrap it in a **free no-signup essay check** for growth and an
**essay-rewrite + unlimited** paywall for revenue. Stay on FastAPI+Postgres. Don't touch Supabase,
mobile, community, or other exams until you have product-market fit on IELTS.
