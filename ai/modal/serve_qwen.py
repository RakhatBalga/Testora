"""Qwen3-8B behind an OpenAI-compatible API on Modal (vLLM).

The backend and the E1 tooling call it through the existing `qwen` provider, so
the same prompts, schema and scoring rules are used as for any other server.

One-time setup:
    uvx modal setup                                   # log in (browser)
    uvx modal secret create testora-vllm VLLM_API_KEY=$(openssl rand -hex 24)

Deploy / stop:
    TESTORA_GPU=A10G uvx modal deploy ai/modal/serve_qwen.py
    uvx modal app stop testora-qwen-serve

Use (backend/.env or the E1 run):
    AI_PROVIDER=qwen
    QWEN_BASE_URL=https://<workspace>--testora-qwen-serve-serve.modal.run/v1
    QWEN_MODEL=testora-qwen            # base model
    QWEN_API_KEY=<the VLLM_API_KEY above>
    QWEN_TIMEOUT_SECONDS=600           # the first call also waits for a cold start

Cost: the container holds a GPU only while it is up. It stops SCALEDOWN_SECONDS
after the last request and starts again on the next one (weights are cached on a
volume; a cold start still takes a few minutes). Nothing is billed while it is down.

Fine-tuned adapters: every directory in the `testora-runs` volume under
`adapters/<name>/` that holds an `adapter_config.json` is served as the model
`testora-qwen-<name>` next to the base model (set QWEN_MODEL to that id).
"""

import os
import subprocess
from pathlib import Path

import modal

APP_NAME = "testora-qwen-serve"
BASE_MODEL = "Qwen/Qwen3-8B"
SERVED_NAME = "testora-qwen"
PORT = 8000

# Choose the GPU for each deploy by price and time, and pass it explicitly.
# Qwen3-8B in bf16 needs about 17 GB plus the 16k-token context: 24 GB cards fit.
GPU = os.environ.get("TESTORA_GPU", "A10G")
SCALEDOWN_SECONDS = 300
STARTUP_TIMEOUT_SECONDS = 20 * 60

HF_DIR = "/root/.cache/huggingface"
VLLM_CACHE = "/root/.cache/vllm"
RUNS_DIR = "/runs"
ADAPTERS_DIR = f"{RUNS_DIR}/adapters"

# vllm 0.32.0 resolves with transformers 5.19.0 (the versions used for training).
image = (
    modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("vllm==0.32.0", "transformers==5.19.0", "huggingface_hub[hf_xet]")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "0"})
)

app = modal.App(APP_NAME)
hf_vol = modal.Volume.from_name("testora-hf-cache", create_if_missing=True)
vllm_vol = modal.Volume.from_name("testora-vllm-cache", create_if_missing=True)
runs_vol = modal.Volume.from_name("testora-runs", create_if_missing=True)


def adapter_modules(adapters_dir: str = ADAPTERS_DIR) -> list[str]:
    """`name=path` pairs for every trained adapter found on the runs volume."""
    root = Path(adapters_dir)
    if not root.is_dir():
        return []
    return [
        f"{SERVED_NAME}-{path.name}={path}"
        for path in sorted(root.iterdir())
        if (path / "adapter_config.json").is_file()
    ]


def vllm_command(api_key: str, adapters: list[str]) -> list[str]:
    command = [
        "vllm", "serve", BASE_MODEL,
        "--served-model-name", SERVED_NAME,
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "--api-key", api_key,
        "--max-model-len", "16384",
        "--gpu-memory-utilization", "0.90",
        # The examiner system prompt is identical for every essay: cache it.
        "--enable-prefix-caching",
    ]  # fmt: skip
    if adapters:
        command += ["--enable-lora", "--lora-modules", *adapters]
    return command


@app.function(
    image=image,
    gpu=GPU,
    volumes={HF_DIR: hf_vol, VLLM_CACHE: vllm_vol, RUNS_DIR: runs_vol},
    secrets=[modal.Secret.from_name("testora-vllm", required_keys=["VLLM_API_KEY"])],
    scaledown_window=SCALEDOWN_SECONDS,
    max_containers=1,
    timeout=60 * 60,
)
@modal.concurrent(max_inputs=16)
@modal.web_server(port=PORT, startup_timeout=STARTUP_TIMEOUT_SECONDS)
def serve() -> None:
    adapters = adapter_modules()
    print(f"[{APP_NAME}] gpu={GPU} base={BASE_MODEL} adapters={adapters or 'none'}")
    subprocess.Popen(vllm_command(os.environ["VLLM_API_KEY"], adapters))
