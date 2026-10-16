"""Run blocking graders without starving the server.

The Gemini graders make synchronous, multi-second HTTP calls. If a request
handler ran them inline it would occupy its worker for the whole call; enough
concurrent gradings would then starve fast endpoints. Instead we offload the
blocking call to the threadpool and cap how many run at once with a semaphore —
which also bounds concurrent Gemini calls for cost/quota safety. Excess
gradings queue instead of piling onto the model.
"""
import asyncio
import logging
from typing import Callable, TypeVar

from fastapi.concurrency import run_in_threadpool

from app.infrastructure.config import settings

logger = logging.getLogger("testora.ai")

_T = TypeVar("_T")

# Created at import; asyncio.Semaphore binds to the running loop lazily (3.10+).
_grading_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_GRADINGS)


async def run_grading(grade: Callable[..., _T], /, **kwargs) -> _T:
    """Execute a blocking grader off the event loop, bounded by the semaphore."""
    async with _grading_semaphore:
        return await run_in_threadpool(lambda: grade(**kwargs))


async def offload(func: Callable[..., _T], /, **kwargs) -> _T:
    """Vocabulary calls share the same concurrency ceiling as grading."""
    return await run_grading(func, **kwargs)
