"""OpenAI-compatible client used for self-hosted Qwen, against a fake server.

No network: httpx.MockTransport plays the server (Ollama / vLLM behaviour).
"""

import asyncio
import json

import httpx
import pytest
from pydantic import BaseModel

from app.infrastructure.ai.engine import extract_json_text, strip_think
from app.infrastructure.ai.openai_compat import OpenAICompatClient, run_sync
from app.infrastructure.ai.retry import (
    PermanentError,
    RetryPolicy,
    TransientError,
    TruncatedResponse,
    parse_retry_after,
)


class _Answer(BaseModel):
    band: float


def _reply(content, finish="stop"):
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": finish}],
        },
    )


class _Server:
    """Records requests and plays back a list of responses / exceptions."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request):
        self.requests.append(request)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def body(self, i=-1) -> dict:
        return json.loads(self.requests[i].content)


def _client(server, **kw):
    sleeps: list[float] = []

    async def fake_sleep(s):
        sleeps.append(s)

    c = OpenAICompatClient(
        base_url="http://qwen.test/v1",
        model="qwen3:14b",
        api_key=kw.pop("api_key", "secret-token"),
        transport=httpx.MockTransport(server),
        sleep=fake_sleep,
        **kw,
    )
    return c, sleeps


def _chat_json(c):
    return asyncio.run(c.chat_json(system="S", user="U", schema=_Answer, temperature=0.1, max_tokens=64, seed=7))


def test_json_schema_request_shape_and_auth():
    server = _Server(_reply('{"band": 6.5}'))
    c, _ = _client(server)
    assert json.loads(_chat_json(c)) == {"band": 6.5}
    req = server.requests[0]
    assert req.url.path == "/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer secret-token"
    body = server.body()
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"]["properties"]["band"]
    assert body["seed"] == 7 and body["temperature"] == 0.1 and body["model"] == "qwen3:14b"
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert body["messages"][1]["content"].endswith("/no_think")


def test_no_auth_header_without_key_and_thinking_toggle():
    server = _Server(_reply('{"band": 6}'))
    c, _ = _client(server, api_key="", disable_thinking=False)
    _chat_json(c)
    assert "authorization" not in server.requests[0].headers
    body = server.body()
    assert "chat_template_kwargs" not in body
    assert not body["messages"][1]["content"].endswith("/no_think")


def test_falls_back_to_json_object_when_json_schema_rejected():
    server = _Server(
        httpx.Response(400, json={"error": {"message": "response_format json_schema is not supported"}}),
        _reply('{"band": 7}'),
        _reply('{"band": 7.5}'),
    )
    c, sleeps = _client(server)
    assert json.loads(_chat_json(c)) == {"band": 7}
    fallback = server.body(1)
    assert fallback["response_format"] == {"type": "json_object"}
    assert '"band"' in fallback["messages"][0]["content"]  # schema in the system prompt
    assert sleeps == []  # a fallback is not a retry
    # Remembered: the next call goes straight to json_object.
    _chat_json(c)
    assert server.body(2)["response_format"] == {"type": "json_object"}


def test_unrelated_400_is_permanent_and_not_retried():
    server = _Server(httpx.Response(400, json={"error": {"message": "context length exceeded"}}))
    c, sleeps = _client(server)
    with pytest.raises(PermanentError) as exc:
        _chat_json(c)
    assert exc.value.status == 400 and len(server.requests) == 1 and sleeps == []


@pytest.mark.parametrize("status", [401, 403])
def test_auth_errors_are_never_retried(status):
    server = _Server(httpx.Response(status, json={"error": "nope"}))
    c, sleeps = _client(server)
    with pytest.raises(PermanentError):
        _chat_json(c)
    assert len(server.requests) == 1 and sleeps == []


def test_5xx_retried_with_backoff_then_succeeds():
    server = _Server(httpx.Response(502), httpx.Response(503), _reply('{"band": 5}'))
    c, sleeps = _client(server)
    assert json.loads(_chat_json(c)) == {"band": 5}
    assert sleeps == [1.0, 2.0]


def test_429_respects_retry_after():
    server = _Server(httpx.Response(429, headers={"Retry-After": "4"}), _reply('{"band": 5}'))
    c, sleeps = _client(server)
    _chat_json(c)
    assert sleeps == [4.0]


def test_429_with_huge_retry_after_gives_up():
    server = _Server(httpx.Response(429, headers={"Retry-After": "3600"}))
    c, sleeps = _client(server)
    with pytest.raises(TransientError):
        _chat_json(c)
    assert sleeps == []


def test_timeouts_retried_then_surface_as_transient():
    server = _Server(*(httpx.ReadTimeout("slow") for _ in range(3)))
    c, sleeps = _client(server, policy=RetryPolicy(max_attempts=3, backoff_base=0.5))
    with pytest.raises(TransientError):
        _chat_json(c)
    assert len(server.requests) == 3 and sleeps == [0.5, 1.0]


def test_connection_error_retried():
    server = _Server(httpx.ConnectError("refused"), _reply('{"band": 4}'))
    c, _ = _client(server)
    assert json.loads(_chat_json(c)) == {"band": 4}


def test_truncated_reply_raises():
    server = _Server(_reply('{"band": ', finish="length"))
    c, _ = _client(server)
    with pytest.raises(TruncatedResponse):
        _chat_json(c)


def test_think_block_is_stripped_from_reply():
    server = _Server(_reply('<think>\nThe essay is good, maybe 9?\n</think>\n\n{"band": 6.5}'))
    c, _ = _client(server)
    assert json.loads(_chat_json(c)) == {"band": 6.5}


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("<think>a</think>{}", "{}"),
        ("reasoning without opening</think>{}", "{}"),
        ("{} <think>unterminated", "{}"),
        ("<THINK>x</THINK> ok", "ok"),
    ],
)
def test_strip_think_variants(raw, expected):
    assert strip_think(raw) == expected


def test_extract_json_handles_fences_and_prose():
    assert extract_json_text('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json_text('Sure! {"a": {"b": 2}} Hope this helps') == '{"a": {"b": 2}}'


def test_list_models():
    server = _Server(httpx.Response(200, json={"object": "list", "data": [{"id": "qwen3:14b"}, {"id": "x"}]}))
    c, _ = _client(server)
    assert asyncio.run(c.list_models()) == ["qwen3:14b", "x"]
    assert server.requests[0].url.path == "/v1/models"


def test_parse_retry_after_forms():
    assert parse_retry_after("3") == 3.0
    assert parse_retry_after(None) is None
    assert parse_retry_after("garbage") is None
    assert parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT") == 0.0  # in the past


def test_run_sync_works_inside_a_running_loop():
    async def value():
        return 42

    async def outer():
        return run_sync(value)

    assert run_sync(value) == 42
    assert asyncio.run(outer()) == 42
