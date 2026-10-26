"""Small async client for OpenAI-compatible `/v1/chat/completions` servers.

Targets self-hosted Qwen behind Ollama, LM Studio, llama.cpp server, MLX-LM,
vLLM or SGLang. Only what grading needs:

  * timeout + retries per `retry.py` (transient only; 429 Retry-After honoured;
    400/401/403 never retried);
  * structured output: `response_format: json_schema` first, and if the server
    rejects it, `json_object` + the schema in the system prompt. The caller
    validates locally either way;
  * Qwen3 thinking disabled for grading (`chat_template_kwargs.enable_thinking
    = false` and the `/no_think` soft switch), and any `<think>` block stripped
    from the reply before parsing;
  * fixed `seed` and caller-supplied temperature.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
from typing import Any, Awaitable, Callable, TypeVar

import httpx
from pydantic import BaseModel

from app.infrastructure.ai.engine import strip_think
from app.infrastructure.ai.retry import (
    DEFAULT_POLICY,
    PermanentError,
    RetryPolicy,
    SchemaError,
    TransientError,
    TruncatedResponse,
    is_transient_status,
    parse_retry_after,
)

logger = logging.getLogger("testora.ai.openai_compat")

_T = TypeVar("_T")

NO_THINK_SUFFIX = "/no_think"

# Whether a server accepts `response_format: json_schema`, learned once per
# (base_url, model) for the life of the process instead of per request.
_JSON_SCHEMA_SUPPORT: dict[tuple[str, str], bool] = {}

# httpx errors that mean the URL/config is wrong; retrying cannot help.
_MISCONFIGURATION_ERRORS = (httpx.UnsupportedProtocol, httpx.InvalidURL, httpx.LocalProtocolError)


def reset_json_schema_cache() -> None:
    """Forget learned server capabilities (tests, or after changing servers)."""
    _JSON_SCHEMA_SUPPORT.clear()


def _looks_like_unsupported_format(status: int, body: str) -> bool:
    """A 400/422 caused by `response_format: json_schema` itself."""
    if status not in (400, 404, 415, 422, 501):
        return False
    lowered = body.lower()
    return any(k in lowered for k in ("response_format", "json_schema", "guided", "grammar", "schema"))


class OpenAICompatClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None = None,
        timeout: float = 180.0,
        connect_timeout: float = 10.0,
        policy: RetryPolicy = DEFAULT_POLICY,
        disable_thinking: bool = True,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or ""
        self.timeout = httpx.Timeout(timeout, connect=connect_timeout)
        self.policy = policy
        self.disable_thinking = disable_thinking
        self._transport = transport
        self._sleep = sleep

    @property
    def json_schema_supported(self) -> bool:
        return _JSON_SCHEMA_SUPPORT.get((self.base_url, self.model), True)

    @json_schema_supported.setter
    def json_schema_supported(self, value: bool) -> None:
        _JSON_SCHEMA_SUPPORT[(self.base_url, self.model)] = value

    # ------------------------------------------------------------------ #
    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._headers(),
            transport=self._transport,
        )

    async def _post(self, path: str, payload: dict) -> dict:
        """POST with retries. Raises PermanentError / TransientError when exhausted."""
        attempt = 0
        while True:
            attempt += 1
            try:
                async with self._client() as client:
                    resp = await client.post(path, json=payload)
                if resp.status_code < 400:
                    try:
                        return resp.json()
                    except ValueError as exc:
                        raise SchemaError("server returned a non-JSON body") from exc
                body = resp.text[:2000]
                if not is_transient_status(resp.status_code):
                    raise PermanentError(f"HTTP {resp.status_code} from {path}", status=resp.status_code, body=body)
                error: TransientError = TransientError(
                    f"HTTP {resp.status_code} from {path}",
                    status=resp.status_code,
                    retry_after=parse_retry_after(resp.headers.get("retry-after")),
                )
            except _MISCONFIGURATION_ERRORS as exc:
                raise PermanentError(
                    f"QWEN_BASE_URL {self.base_url!r} is invalid or uses an unsupported scheme "
                    f"({type(exc).__name__}); expected e.g. http://localhost:11434/v1"
                ) from exc
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                error = TransientError(f"{type(exc).__name__} calling {path}")
            delay = self.policy.delay(attempt, error.retry_after)
            logger.warning(
                "OpenAI-compatible call attempt %d/%d failed: %s",
                attempt,
                self.policy.max_attempts,
                error,
            )
            if delay is None:
                raise error
            await self._sleep(delay)

    # ------------------------------------------------------------------ #
    def _messages(self, system: str, user: str) -> list[dict]:
        if self.disable_thinking:
            user = f"{user}\n\n{NO_THINK_SUFFIX}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _payload(self, messages: list[dict], *, temperature: float, max_tokens: int, seed: int | None) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if seed is not None:
            payload["seed"] = seed
        if self.disable_thinking:
            # vLLM / SGLang / llama.cpp read this; others ignore unknown keys.
            payload["chat_template_kwargs"] = {"enable_thinking": False}
        return payload

    @staticmethod
    def _content(data: dict) -> str:
        try:
            choice = data["choices"][0]
            content = choice["message"].get("content") or ""
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise SchemaError("unexpected chat completion shape") from exc
        if choice.get("finish_reason") == "length":
            raise TruncatedResponse("response was truncated at max_tokens")
        return strip_think(content)

    async def chat_text(
        self,
        *,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
    ) -> str:
        payload = self._payload(self._messages(system, user), temperature=temperature, max_tokens=max_tokens, seed=seed)
        return self._content(await self._post("/chat/completions", payload))

    async def chat_json(
        self,
        *,
        system: str,
        user: str,
        schema: type[BaseModel],
        temperature: float,
        max_tokens: int,
        seed: int | None = None,
    ) -> str:
        """Return the reply text (think-stripped); the caller validates it."""
        json_schema = schema.model_json_schema()
        if self.json_schema_supported:
            payload = self._payload(
                self._messages(system, user), temperature=temperature, max_tokens=max_tokens, seed=seed
            )
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": json_schema, "strict": False},
            }
            try:
                return self._content(await self._post("/chat/completions", payload))
            except PermanentError as exc:
                if not _looks_like_unsupported_format(exc.status or 0, exc.body):
                    raise
                logger.info("Server rejected json_schema output (HTTP %s); using json_object", exc.status)
                self.json_schema_supported = False

        fallback_system = (
            f"{system}\n\nReturn ONLY one JSON object that validates against this JSON Schema:\n"
            f"{json.dumps(json_schema, separators=(',', ':'))}"
        )
        payload = self._payload(
            self._messages(fallback_system, user), temperature=temperature, max_tokens=max_tokens, seed=seed
        )
        payload["response_format"] = {"type": "json_object"}
        return self._content(await self._post("/chat/completions", payload))

    async def list_models(self) -> list[str]:
        """GET /models (single attempt, short timeout) — for health checks."""
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(5.0),
            headers=self._headers(),
            transport=self._transport,
        ) as client:
            resp = await client.get("/models")
        resp.raise_for_status()
        data = resp.json()
        return [str(m.get("id")) for m in data.get("data", []) if isinstance(m, dict)]


def run_sync(factory: Callable[[], Awaitable[_T]]) -> _T:
    """Run a coroutine from synchronous code (graders run in a threadpool).

    Uses asyncio.run directly when no loop is running in this thread, else a
    short-lived helper thread, so it never blocks or nests a running loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(factory())).result()
