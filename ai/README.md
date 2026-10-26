# ai/ — serving configs for self-hosted Qwen

The grading code lives in `backend/app/infrastructure/ai/` (`qwen.py`,
`openai_compat.py`). This folder only holds what is needed to **run a Qwen
model behind an OpenAI-compatible API** that the backend calls with
`AI_PROVIDER=qwen`. Full guide: [`docs/qwen.md`](../docs/qwen.md).

| Path | What |
|---|---|
| `ollama/Modelfile` | Mac (Ollama): Qwen3 with a context window large enough for the examiner prompt |
| `vllm/docker-compose.yml` | Rented NVIDIA GPU: vLLM OpenAI-compatible server with an API key |
| `smoke_test.py` | Sends one real grading request through the production pipeline and prints the result |

Quick check after starting a server:

```bash
cd backend
QWEN_BASE_URL=http://localhost:11434/v1 QWEN_MODEL=testora-qwen3 \
  venv/bin/python ../ai/smoke_test.py
```
