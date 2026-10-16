"""Atomic budgets reserved before AI calls, shared across workers.

An interrupted worker leaves its reservation charged until reconciliation.
Known failures refund lifetime reviews, but never the daily attempt budget.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models.ai_quota import AIQuotaBucket, AIReservation
from app.infrastructure.config import settings


def _consumed_count(db: Session, model, user_id: int) -> int:
    q = db.query(model).filter(model.user_id == user_id)
    if hasattr(model, "status"):
        q = q.filter(model.status != "failed")
    else:
        q = q.filter(model.band.isnot(None))
    return q.count()


def _kind(model) -> str:
    return "writing" if hasattr(model, "status") else "speaking"


def _exempt(user, limit: int) -> bool:
    return limit < 0 or user.id in settings.quota_exempt_user_ids


def quota_status(db: Session, model, user, limit: int) -> dict:
    if _exempt(user, limit):
        return {"limit": limit, "used": 0, "remaining": limit, "exempt": True}
    bucket = db.get(AIQuotaBucket, (user.id, _kind(model), "lifetime"))
    used = bucket.used if bucket else _consumed_count(db, model, user.id)
    return {"limit": limit, "used": used, "remaining": max(0, limit - used), "exempt": False}


def enforce_free_quota(db: Session, model, user, limit: int, skill: str) -> None:
    """Early UX check only; reserve_ai_call performs the atomic enforcement."""
    state = quota_status(db, model, user, limit)
    if not state["exempt"] and state["remaining"] == 0:
        raise _quota_error(skill, limit)


def _quota_error(kind: str, limit: int) -> HTTPException:
    if kind == "attempts":
        now = datetime.now(timezone.utc)
        reset = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return HTTPException(429, {
            "code": "ai_daily_limit",
            "message": "Daily AI limit reached. This limit covers reviews and vocabulary, including failed attempts.",
            "resets_at": reset.isoformat(),
        }, headers={"Retry-After": str(max(1, int((reset - now).total_seconds())))})
    return HTTPException(403, {
        "code": "ai_free_reviews_exhausted",
        "message": f"You've used your {limit} free {kind} reviews. This allowance does not reset daily.",
    })


def _increment(db: Session, user_id: int, kind: str, period: str, limit: int, initial: int = 0):
    insert = {"postgresql": pg_insert, "sqlite": sqlite_insert}[db.get_bind().dialect.name]
    db.execute(insert(AIQuotaBucket).values(user_id=user_id, kind=kind, period=period, used=initial)
               .on_conflict_do_nothing(index_elements=["user_id", "kind", "period"]))
    changed = db.execute(update(AIQuotaBucket).where(
        AIQuotaBucket.user_id == user_id, AIQuotaBucket.kind == kind,
        AIQuotaBucket.period == period, AIQuotaBucket.used < limit,
    ).values(used=AIQuotaBucket.used + 1).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise _quota_error(kind, limit)


@dataclass
class ReservationResult:
    success: bool = False


@contextmanager
def reserve_ai_call(db: Session, user, kind: str, *, model=None, limit: int = -1, resource: str | None = None):
    user_id = user.id
    charged = model is not None and not _exempt(user, limit)
    key = uuid.uuid4().hex
    try:
        # Take the resource before budget locks, matching completion lock order.
        db.add(AIReservation(id=key, user_id=user_id, kind=kind,
                             active_resource=resource, status="reserved"))
        db.flush()
        _increment(db, user_id, "attempts", datetime.now(timezone.utc).date().isoformat(), settings.AI_DAILY_ATTEMPTS)
        if charged:
            _increment(db, user_id, kind, "lifetime", limit, _consumed_count(db, model, user_id))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This AI request is already in progress.")
    except BaseException:
        db.rollback()
        raise
    result = ReservationResult()
    try:
        yield result
    except BaseException:
        db.rollback()
        raise
    finally:
        changed = db.execute(update(AIReservation).where(
            AIReservation.id == key, AIReservation.status == "reserved",
        ).values(status="completed" if result.success else "released", active_resource=None)
          .execution_options(synchronize_session=False))
        if changed.rowcount == 1 and charged and not result.success:
            db.execute(update(AIQuotaBucket).where(
                AIQuotaBucket.user_id == user_id, AIQuotaBucket.kind == kind,
                AIQuotaBucket.period == "lifetime",
            ).values(used=AIQuotaBucket.used - 1).execution_options(synchronize_session=False))
        db.commit()
