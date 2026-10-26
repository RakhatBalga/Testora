"""Concurrency gate for blocking AI calls made from sync (threadpool) handlers.

Handlers that do database work are plain `def`, so FastAPI runs them in its
threadpool and the event loop stays free. This gate keeps the two limits the
old async path had: at most MAX_CONCURRENT_GRADINGS model calls at once (cost /
rate-limit protection), and a bounded number of requests waiting for a slot so
queued submissions cannot occupy every threadpool thread and starve fast
endpoints. Excess requests get a clear 503 instead of hanging.
"""
import contextvars
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Callable, TypeVar

from fastapi import HTTPException

from app.infrastructure.config import settings

_T = TypeVar("_T")

_slots = threading.BoundedSemaphore(settings.MAX_CONCURRENT_GRADINGS)
# Requests allowed to be inside a grading flow (running or queued).
_admission = threading.BoundedSemaphore(settings.MAX_CONCURRENT_GRADINGS * 2)
# Runs the secondary call (Better Version) alongside the examiner call.
_executor = ThreadPoolExecutor(max_workers=settings.MAX_CONCURRENT_GRADINGS, thread_name_prefix="grading")


def _busy() -> HTTPException:
    return HTTPException(503, "Grading is busy right now. Please try again in a minute.",
                         headers={"Retry-After": "30"})


@contextmanager
def grading_admission():
    """Reject immediately (503) when too many gradings are already in flight."""
    if not _admission.acquire(blocking=False):
        raise _busy()
    try:
        yield
    finally:
        _admission.release()


def run_graded(call: Callable[..., _T], /, **kwargs) -> _T:
    """Run one blocking model call in the current thread, bounded by the slots."""
    if not _slots.acquire(timeout=settings.GRADING_QUEUE_TIMEOUT_SECONDS):
        raise _busy()
    try:
        return call(**kwargs)
    finally:
        _slots.release()


def run_graded_pair(primary: Callable, primary_kwargs: dict, secondary: Callable, secondary_kwargs: dict):
    """Run two independent model calls concurrently.

    Returns (primary_result, secondary_result_or_exception): a primary failure
    propagates, a secondary failure is returned so the caller can degrade.
    """
    future = _executor.submit(contextvars.copy_context().run, run_graded, secondary, **secondary_kwargs)
    try:
        primary_result = run_graded(primary, **primary_kwargs)
    except BaseException:
        future.cancel()
        raise
    try:
        secondary_result = future.result()
    except BaseException as exc:  # noqa: BLE001 - optional enhancement
        secondary_result = exc
    return primary_result, secondary_result
