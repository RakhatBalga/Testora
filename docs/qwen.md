# Self-hosted Qwen for grading

Testora can grade with a Qwen model that we host ourselves instead of Gemini.
The backend talks to it over an **OpenAI-compatible API** (`/v1/chat/completions`),
so any server that speaks that protocol works: Ollama, LM Studio, MLX-LM on a
Mac, or vLLM / SGLang on a rented GPU.

Only the model changes. Prompts, JSON schema, temperature (0.1 examiner / 0.35
coach), seed, and the scoring rules (snap to 0.5, clamp 0–9, overall recomputed
in code, hard caps, verbatim mistake check) are shared with Gemini through
`backend/app/infrastructure/ai/engine.py` and `app/domain/grading.py`. Every
`Feedback` records `provider`, `model` and `prompt_version`.

> **Do not switch production to Qwen before it is measured.** Run the offline
> evaluator on the same essays with `get_writing_grader(provider="gemini")` and
> `get_writing_grader(provider="qwen")`: QWK and MAE per criterion with bootstrap
> CIs, mean bias, the score histogram (no collapse to a flat 7.0), 5-run
> stability, the share of failed or invalid-JSON gradings, and the injection set.
> Switch only if Qwen is not worse than Gemini within the CIs.

## Settings (`backend/.env`)

| Variable | Example | Notes |
|---|---|---|
| `AI_PROVIDER` | `qwen` | `mock \| gemini \| qwen \| claude` |
| `QWEN_BASE_URL` | `http://localhost:11434/v1` | include `/v1`; required |
| `QWEN_MODEL` | `testora-qwen3` | the id the server lists at `/v1/models`; required |
| `QWEN_API_KEY` | *(empty)* | sent as `Authorization: Bearer …` when set |
| `QWEN_TIMEOUT_SECONDS` | `180` | per call; local inference is slow |
| `QWEN_DISABLE_THINKING` | `true` | Qwen3 "thinking" off for grading |

If `AI_PROVIDER=qwen` but the URL or model is empty, the app falls back to the
mock grader, and production refuses to start (same rule as a missing Gemini key).

Test a server with one real grading: `cd backend && venv/bin/python ../ai/smoke_test.py`.

## How the client behaves

- **Structured output.** First `response_format: {type: "json_schema"}` (vLLM,
  SGLang, LM Studio, llama.cpp server, Ollama ≥ 0.5). If the server rejects it,
  the client switches to `json_object` and puts the schema in the system prompt.
  The reply is always validated locally; invalid JSON is re-asked once.
- **Thinking.** Grading sends `chat_template_kwargs: {enable_thinking: false}`
  (vLLM / SGLang / llama.cpp) and appends Qwen3's `/no_think` switch (works on
  Ollama and others). Any `<think>…</think>` text is stripped before parsing.
- **Retries.** Timeouts, connection errors, 408, 5xx and 429 are retried up to
  3 times with 1 s / 2 s backoff; `Retry-After` is honoured up to 30 s. 400,
  401, 403 and 404 are never retried. Users only see a generic "try again"
  message; details go to the logs.
- **Speaking.** Qwen text models cannot hear audio. The Qwen Speaking grader
  works from a transcript; without one it returns a clean "not supported on this
  provider yet" failure (the quota is refunded). Plan: faster-whisper ASR
  (`backend/requirements-asr.txt`) → transcript → this grader; later possibly a
  Qwen-Omni model (Qwen2.5-Omni-7B / Qwen3-Omni-30B-A3B) for audio input.

## 1. On the Mac (development and demo)

The owner's Mac is an M4 with 16 GB unified memory. Roughly 10–11 GB of that is
usable by the GPU, so **`qwen3:8b` (Q4, ~5 GB)** is the realistic model;
`qwen3:14b` (~9 GB) loads but leaves little room for the 16k context.

| Mac memory | Model (Ollama tag) | Download |
|---|---|---|
| 16 GB | `qwen3:8b` | ~5 GB |
| 32 GB | `qwen3:14b` or `qwen3:30b-a3b` (MoE, fast) | ~9 / ~19 GB |
| 64 GB+ | `qwen3:32b` | ~20 GB |

**Ollama** (simplest):

```bash
brew install ollama        # or the app from ollama.com
ollama serve &
ollama pull qwen3:8b
ollama create testora-qwen3 -f ai/ollama/Modelfile   # sets num_ctx 16384
```

`.env`: `QWEN_BASE_URL=http://localhost:11434/v1`, `QWEN_MODEL=testora-qwen3`.
The Modelfile matters: Ollama's default context window is smaller than the
examiner prompt plus the reply, and it truncates silently.

**LM Studio:** load a Qwen3 GGUF or MLX model, set the context length to at
least 16k in the model settings, start the local server (port 1234). Use the
model id shown at `http://localhost:1234/v1/models`.

**MLX-LM:** `pip install mlx-lm`, then
`mlx_lm.server --model mlx-community/Qwen3-8B-4bit --port 8080`
(`QWEN_BASE_URL=http://localhost:8080/v1`). *Uncertain:* recent versions may not
honour `response_format`; the client still validates and re-asks, but expect
more failed gradings than with Ollama or LM Studio.

Mac tips: set `MAX_CONCURRENT_GRADINGS=2` (one essay = examiner + Better Version
in parallel) and consider `WRITING_COACH_ENABLED=false` to cut latency for demos.

## 2. On a rented GPU (vLLM)

`ai/vllm/docker-compose.yml` starts vLLM with an API key, a 16k context and
prefix caching (the long examiner prompt is the same for every essay).

| GPU memory | Model (Hugging Face id) | Notes |
|---|---|---|
| 24 GB (RTX 4090, L4, A10) | `Qwen/Qwen3-14B-AWQ` | the default; `Qwen/Qwen3-8B` in bf16 also fits |
| 48 GB (A6000, L40S) | `Qwen/Qwen3-32B-AWQ` or `Qwen/Qwen3-30B-A3B-Instruct-2507-FP8` | best quality/price |
| 80 GB (A100, H100) | `Qwen/Qwen3-32B` (bf16) | full precision; room for batching |

```bash
export VLLM_API_KEY=$(openssl rand -hex 24)
export QWEN_HF_MODEL=Qwen/Qwen3-14B-AWQ
docker compose -f ai/vllm/docker-compose.yml up -d
```

Backend: `QWEN_MODEL=testora-qwen` (the served name), `QWEN_API_KEY=$VLLM_API_KEY`.
Check model ids on Hugging Face before renting; the `-2507` instruct models
do not think at all, which is fine for grading.

## 3. How Render reaches the model

Render's servers cannot see `localhost` on the Mac. You need a **public HTTPS
URL plus an API key**:

- **Rented GPU:** use the provider's HTTPS proxy (e.g. RunPod's
  `https://<pod>-8000.proxy.runpod.net`) or a Cloudflare Tunnel on the box.
  vLLM checks `--api-key`, so set `QWEN_API_KEY` on Render.
- **Mac (demo only):** `cloudflared tunnel --url http://localhost:11434 --http-host-header localhost:11434`
  prints a temporary `https://….trycloudflare.com` URL. **Ollama has no
  authentication**, so anyone with the URL can use your Mac. Put Cloudflare
  Access or a small reverse proxy that checks a bearer token in front of it,
  and stop the tunnel after the demo. The Mac must stay awake and online.

On Render set `AI_PROVIDER=qwen`, `QWEN_BASE_URL=https://…/v1`, `QWEN_MODEL`,
`QWEN_API_KEY`, `QWEN_TIMEOUT_SECONDS`. `ping_qwen()` in
`app/infrastructure/ai/qwen.py` can be wired into `/health/ready`.

## Latency and cost (estimates, measure before relying on them)

One Writing grading = examiner (~3.5k tokens in, ~1–2k out) + coach (~3k in,
~1k out) + Better Version (~1k in, ~0.5k out).

| Setup | Time per essay (examiner + coach) | Cost |
|---|---|---|
| M4 16 GB, `qwen3:8b` Q4 | ~1.5–3 min (≈20 tokens/s output) | electricity only |
| 24 GB GPU, `Qwen3-14B-AWQ` | ~30–60 s | ≈ $0.3–0.8 per GPU-hour |
| 48–80 GB GPU, 32B | ~30–60 s, several essays in parallel | ≈ $0.7–2.5 per GPU-hour |
| Gemini 2.5 Flash (today) | ~15–30 s | ≈ $0.01 per essay |

GPU prices vary by provider and week. A rented GPU only pays off for a batch
(e.g. an evaluation run of 500 essays in an hour) or steady traffic; for a
few essays a day Gemini is cheaper. Self-hosting is about **data control**
(student essays never leave our servers) and independence from one vendor.
The frontend's submit timeout must exceed the slowest grading time above.
