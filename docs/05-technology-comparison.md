# 5. Comparison of Technology Alternatives

## 5.1 Requirements that drive the choices

Every decision below is judged against the same project requirements (R1–R6). They come from Testora's core loop and from how the project is run.

| ID | Requirement | Where it comes from |
|---|---|---|
| R1 | **Python ML ecosystem**: the speaking pipeline (Whisper ASR, fluency features, regressors) and adaptive models (Rasch/IRT, knowledge tracing) must run next to the API | ML research modules (`backend/ml/`) |
| R2 | **Concurrent long I/O**: one grading is an LLM call lasting several seconds; slow gradings must not block other requests | Writing/Speaking grading |
| R3 | **Relational data with history and analytics**: users → attempts → submissions → criterion scores → mistakes; trends over time, quotas, regrade comparison | Weakness model, progress, band change |
| R4 | **Low budget**: near-zero fixed cost while user numbers are small | Student project; target users are budget-limited |
| R5 | **Small team (2 developers)**: little ops work, one main language per tier, fast iteration | Team size |
| R6 | **Simple, repeatable deployment**: deploy on git push, versioned DB migrations, CI | Live product at testora.studio |

Each table rates alternatives as **++** (strong fit), **+** (adequate), **–** (weak) or **– –** (poor) against the requirements above.

## 5.2 Decision 1: Backend framework

| Criterion | **FastAPI (Python)** | Django REST Framework (Python) | Node.js (Express / NestJS) |
|---|---|---|---|
| Same language as ML code (R1) | ++ | ++ | – – (ML would need a second Python service) |
| Async handlers for LLM calls (R2) | ++ native `async def` | – async views come from the third-party package *adrf* [T1] | ++ event loop by design |
| Request/response validation | ++ Pydantic; the same models validate LLM JSON | + serializers | + needs Zod/class-validator |
| Auto API docs | ++ OpenAPI generated | + via add-ons | + via add-ons (NestJS Swagger) |
| Built-in admin / batteries | – | ++ admin, auth, ORM | – (Express) / + (NestJS) |
| Weight for a small team (R5) | ++ small, explicit | + larger conventions to learn | + but adds a 3rd stack (TS backend + Python ML) |

**Chosen: FastAPI.**
- **ML in the same language (R1).** Testora's ML (faster-whisper, scikit-learn, IRT) is Python, so a Python backend can load these models directly.
- **Grading does not block other requests (R2).** Handlers are `async`. The SDK calls to the LLM provider are blocking, so they run in a thread pool behind a semaphore (`app/infrastructure/ai/concurrency.py`). A slow grading never blocks fast endpoints, and the semaphore caps parallel LLM calls for cost and quota safety.
- **Pydantic validates both API traffic and LLM replies.** Each grader validates the model's JSON with `model_validate_json`.
- **Why not Django REST Framework.** Its admin is attractive, but async support is not first-class.
- **Why not Node.js.** The ML code would have to move to a separate service.

## 5.3 Decision 2: Database

| Criterion | **PostgreSQL** | MongoDB | MySQL / SQLite |
|---|---|---|---|
| Relational model with joins (R3) | ++ | – document model, joins via `$lookup` | ++ / + |
| Semi-structured LLM feedback | ++ JSONB | ++ native documents | + JSON type (MySQL) / – (SQLite) |
| Analytics over time (window functions, aggregates) (R3) | ++ | + aggregation pipeline | + / – |
| Transactions (AI quota reservation, regrade) | ++ | + multi-document transactions | ++ / + (single writer) |
| Managed free tier with no expiry (R4) | ++ Neon Free [T2] | + Atlas free tier | + / n.a. (file DB) |
| Migrations with SQLAlchemy + Alembic (R6) | ++ | – (no Alembic) | ++ / + |

**Chosen: PostgreSQL (Neon).**
- **The data is relational (R3).** It needs joins across users, attempts, criterion scores and mistakes, plus time-ordered queries for the weakness model and progress charts.
- **Quota reservations need transactions.** An AI grade is reserved before the LLM call and released if the call fails.
- **LLM feedback fits in JSONB.** This keeps document-style flexibility without giving up relational integrity.
- **SQLite was rejected for production.** It is a single-writer file database and does not suit a managed, stateless container host.
- **MySQL would work.** It has no advantage that outweighs PostgreSQL's JSONB and the team's existing PostgreSQL tooling.

## 5.4 Decision 3: Frontend framework

| Criterion | **Next.js 16 (App Router)** | React SPA (Vite) | Vue 3 / Nuxt |
|---|---|---|---|
| SEO and fast first load for public pages | ++ server rendering / static generation | – client-only by default | ++ (Nuxt SSR) |
| File-based routing, layouts | ++ | – needs React Router | ++ |
| Ecosystem used (Recharts, Framer Motion, lucide) | ++ React | ++ React | – different libraries |
| TypeScript support | ++ | ++ | ++ |
| Hosting integration (R6) | ++ Vercel native | + any static host | + |
| Learning cost for the team (R5) | + (React known; App Router concepts new) | ++ simplest | – new framework |

**Chosen: Next.js + TypeScript + Tailwind v4.**
- **Search visibility for public pages.** Landing and marketing pages must be indexable for a worldwide audience, which needs server rendering. A Vite SPA cannot do this without extra work.
- **The React ecosystem is already in use.** Recharts powers the band charts. Nuxt would mean learning a new framework without a functional gain.
- **Less glue code (R5, R6).** Next.js has built-in routing and deploys to Vercel with no configuration.

## 5.5 Decision 4: LLM provider for grading

| Criterion | **Google Gemini (2.5 Flash)** | Anthropic Claude (Sonnet) | OpenAI GPT | Self-hosted open model |
|---|---|---|---|---|
| Structured JSON output (schema) | ++ `response_schema` / JSON mode [T3] | ++ schema-constrained outputs [T4] | ++ Structured Outputs [T5] | + depends on serving stack |
| Native audio input (Speaking) | ++ audio input priced separately [T6] | – text/image only; needs separate ASR | + audio-capable models exist | – needs separate ASR |
| Cost (R4) | ++ free tier for development, low-cost Flash tier [T6] | – higher per-token tier | + | – GPU hosting is a fixed cost, even when idle |
| Latency per grading | + seconds | + seconds | + seconds | depends on GPU |
| Rubric-grading quality | + (validated with our calibration script) | ++ strong writing analysis | ++ | – smaller models are weaker on rubric scoring |
| Ops burden (R5) | ++ API | ++ API | ++ API | – – serving, scaling, updates |

Exact per-token prices change often and are not quoted here. See the providers' official pricing pages [T6][T7][T8].

**Chosen: Gemini in production, behind a provider-independent layer.**
- **Abstraction layer.** The code defines `WritingGrader` / `SpeakingGrader` interfaces (`app/infrastructure/ai/base.py`) with three implementations: `mock`, `claude` and `gemini`. A factory selects one with the `AI_PROVIDER` environment variable (`factory.py`). If the key is missing, the factory falls back to `mock`, and startup validation refuses to launch production on the mock grader.
- **Why Gemini wins for Testora:**
  1. It accepts the **recorded audio directly**, so one call can grade Speaking, including Pronunciation and Fluency, without a separate ASR service.
  2. It enforces a JSON schema, which the backend then validates again with Pydantic.
  3. Its free and low-cost tiers fit R4.
- **Claude** is fully implemented as an alternative and can be switched on with one variable.
- **Self-hosting** was rejected for now because of GPU cost and ops load (R4, R5).
- **Not locked in.** The abstraction lets us switch providers if prices or quality change, and the calibration script (Section 4, C8) can re-check score agreement before any switch.

## 5.6 Decision 5: Component interaction

| Criterion | **REST / JSON over HTTPS** | GraphQL | gRPC |
|---|---|---|---|
| Browser support | ++ native `fetch` | ++ with client library | – needs gRPC-Web proxy |
| Fit to the domain (resource-oriented: tests, attempts, submissions) | ++ | + | + |
| Tooling with FastAPI | ++ OpenAPI generated automatically | + extra library (e.g. Strawberry) | + extra codegen |
| File upload (Speaking audio) | ++ multipart | – needs a spec extension | + streaming |
| HTTP caching, simplicity for a small team (R5) | ++ | – single endpoint, harder caching | – binary, harder to debug |
| Payload efficiency | + | ++ client picks fields | ++ protobuf |

**Chosen: REST/JSON.**
- **Simple, resource-shaped interactions.** Typical calls are "submit essay", "get attempt" and "list history". The frontend is the only client, so GraphQL's flexible querying brings little benefit.
- **Native browser support.** gRPC would need a proxy in front of the browser.
- **Fits FastAPI and audio upload.** REST maps directly onto FastAPI routers, gives free OpenAPI documentation, and handles audio upload with standard multipart forms.
- **Authentication** uses JWT bearer tokens and Google OAuth with PKCE, all over HTTPS.

## 5.7 Decision 6: Speech recognition (Speaking research pipeline)

| Criterion | **Whisper, local (faster-whisper)** | Cloud STT (Google / Azure) |
|---|---|---|
| Cost (R4) | ++ open source, MIT licence [T9]; compute only | – billed per audio minute |
| Word timestamps for fluency features (speech rate, pauses) | ++ | ++ |
| Accuracy on non-native English | + (varies by model size) | + |
| Data privacy (learner recordings) | ++ audio stays on our machine | – sent to a third party |
| Ops / hardware | – CPU is slow for large models; GPU preferred [T9] | ++ managed |

**Chosen for research: local Whisper (faster-whisper).**
- **Why local Whisper.** It is free, keeps learner audio private and gives the word timings the fluency features need (`backend/ml/asr.py`, `speech_features.py`).
- **Kept out of the production image.** It ships in an optional `requirements-asr.txt`, so the production image stays small. Production Speaking currently relies on Gemini's native audio input (Decision 4).
- **Cloud STT** stays an option if a dedicated, low-latency transcription service is needed later.

## 5.8 Decision 7: Hosting

| Criterion | **Vercel + Render + Neon** | Single VPS + Docker Compose | Managed cloud (AWS / GCP) |
|---|---|---|---|
| Fixed cost at low traffic (R4) | ++ free tiers [T2][T10][T11] | + small fixed monthly fee | – free credits expire; complex billing |
| Deploy on git push (R6) | ++ built in | – self-built CI/CD | + after setup |
| Ops burden: TLS, OS patches, backups (R5) | ++ managed | – – all manual | + managed, but many services to configure |
| Cold starts / limits | – Render Free sleeps after 15 min idle (≈1 min wake-up) [T10]; Neon Free suspends after 5 min [T2]; Vercel Hobby is non-commercial only [T11] | ++ always on | ++ |
| Scaling path | + upgrade each service separately | – manual | ++ |
| Vendor lock-in | + Docker image and standard Postgres are portable | ++ | – proprietary services |

**Chosen: Vercel (frontend) + Render (Docker backend) + Neon (PostgreSQL).**
- **Fits budget and team (R4, R5, R6).** Each tier has a free plan, deploys from GitHub, and handles TLS and patching. GitHub Actions runs tests before deploy.
- **Neon for the database.** Render's free PostgreSQL expires 30 days after creation [T10], while Neon's free tier does not expire [T2].
- **Portability is kept.** The backend is a standard Docker image (`render.yaml`, `backend/Dockerfile`), so moving to a VPS or a cloud provider later is cheap.
- **Known trade-offs:**
  - Cold starts on the free backend and database tiers.
  - The Vercel Hobby plan is restricted to non-commercial use [T11], so a paid tier must be adopted before Testora charges users.
- **Lesson learned.** An earlier single-droplet setup was abandoned in favour of managed tiers to reduce ops work.

## 5.9 Summary of decisions

| Decision | Chosen | Main reasons (requirements) |
|---|---|---|
| Backend | FastAPI | Python ML (R1), async + threadpool for LLM calls (R2), Pydantic validation |
| Database | PostgreSQL on Neon | Relational history and analytics (R3), JSONB, free tier with no expiry (R4) |
| Frontend | Next.js + TypeScript + Tailwind | SSR for public pages, React ecosystem, Vercel deploy (R6) |
| LLM | Gemini, behind a provider-independent interface | Native audio, JSON schema, low cost (R4); swappable to Claude |
| Interaction | REST/JSON + JWT/OAuth PKCE | Simple, browser-native, OpenAPI from FastAPI (R5) |
| ASR (research) | Local Whisper | Free, private, word timestamps (R1, R4) |
| Hosting | Vercel + Render + Neon | Near-zero cost, push-to-deploy, low ops (R4–R6) |

## 5.10 Sources

All accessed 2026-10-22.

| ID | Source |
|---|---|
| T1 | adrf: Async support for Django REST framework. https://github.com/em1208/adrf |
| T2 | Neon pricing (Free: 1 GB/project, 100 CU-hours/project, suspend after 5 min). https://neon.com/pricing |
| T3 | Gemini API: Structured output. https://ai.google.dev/gemini-api/docs/structured-output |
| T4 | Claude API: Structured outputs. https://platform.claude.com/docs/en/build-with-claude/structured-outputs |
| T5 | OpenAI API: Structured Outputs. https://developers.openai.com/api/docs/guides/structured-outputs |
| T6 | Gemini API pricing (free tier for 2.5 Flash; separate audio-input rate). https://ai.google.dev/gemini-api/docs/pricing |
| T7 | Anthropic pricing. https://www.anthropic.com/pricing |
| T8 | OpenAI API pricing. https://openai.com/api/pricing |
| T9 | OpenAI Whisper repository (MIT licence, model sizes and VRAM). https://github.com/openai/whisper |
| T10 | Render: Deploy for Free (15-min idle spin-down, 750 free instance hours, free Postgres expires after 30 days). https://render.com/docs/free |
| T11 | Vercel Hobby plan (free; "non-commercial, personal use only"). https://vercel.com/docs/plans/hobby |
