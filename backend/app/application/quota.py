"""Atomic budgets reserved before AI calls, shared across workers.

Three budgets apply to every AI call: the per-user lifetime free reviews, the
per-user daily attempts and a global daily cap across all users. An interrupted
worker leaves its reservation charged until `reconcile_stale_reservations`
releases it (on startup and lazily per user). Known failures refund lifetime
reviews, but never the daily budgets.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import uuid

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.models.ai_quota import AIGlobalBudget, AIQuotaBucket, AIReservation
from app.infrastructure.config import settings
from app.infrastructure.time import local_midnight_after_now, local_today, utcnow


def _consumed_count(db: Session, model, user_id: int) -> int:
    q = db.query(model).filter(model.user_id == user_id)
    if hasattr(model, "status"):
        # Only really graded essays count. Failed gradings are free, pre-check
        # rejections (Band 0, no AI call) are free, and a pending row is the
        # in-flight request itself, which its own reservation already charges.
        q = q.filter(model.status == "graded", model.band > 0)
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
    reconcile_stale_reservations(db, user_id=user.id)
    bucket = db.get(AIQuotaBucket, (user.id, _kind(model), "lifetime"))
    used = bucket.used if bucket else _consumed_count(db, model, user.id)
    return {"limit": limit, "used": used, "remaining": max(0, limit - used), "exempt": False}


def enforce_free_quota(db: Session, model, user, limit: int, skill: str) -> None:
    """Early UX check only; reserve_ai_call performs the atomic enforcement."""
    state = quota_status(db, model, user, limit)
    if not state["exempt"] and state["remaining"] == 0:
        raise _quota_error(skill, limit)


def _quota_error(kind: str, limit: int) -> HTTPException:
    if kind == "global":
        return HTTPException(
            503,
            {
                "code": "ai_global_budget_exhausted",
                "message": "AI reviews are paused for today because the daily capacity is used up. "
                "Please try again tomorrow.",
                "resets_at": local_midnight_after_now().isoformat(),
            },
            headers={"Retry-After": "3600"},
        )
    if kind == "attempts":
        reset = local_midnight_after_now()
        now = datetime.now(reset.tzinfo)
        return HTTPException(
            429,
            {
                "code": "ai_daily_limit",
                "message": "Daily AI limit reached. This limit covers reviews and vocabulary, including failed attempts.",
                "resets_at": reset.isoformat(),
            },
            headers={"Retry-After": str(max(1, int((reset - now).total_seconds())))},
        )
    return HTTPException(
        403,
        {
            "code": "ai_free_reviews_exhausted",
            "message": f"You've used your {limit} free {kind} reviews. This allowance does not reset daily.",
        },
    )


def _upsert_insert(db: Session):
    return {"postgresql": pg_insert, "sqlite": sqlite_insert}[db.get_bind().dialect.name]


def _increment(db: Session, user_id: int, kind: str, period: str, limit: int, initial: int = 0):
    insert = _upsert_insert(db)
    db.execute(
        insert(AIQuotaBucket)
        .values(user_id=user_id, kind=kind, period=period, used=initial)
        .on_conflict_do_nothing(index_elements=["user_id", "kind", "period"])
    )
    changed = db.execute(
        update(AIQuotaBucket)
        .where(
            AIQuotaBucket.user_id == user_id,
            AIQuotaBucket.kind == kind,
            AIQuotaBucket.period == period,
            AIQuotaBucket.used < limit,
        )
        .values(used=AIQuotaBucket.used + 1)
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        raise _quota_error(kind, limit)


def _increment_global(db: Session, period: str) -> None:
    """Fail closed once the all-users daily budget is spent (negative = off)."""
    limit = settings.AI_GLOBAL_DAILY_ATTEMPTS
    if limit < 0:
        return
    db.execute(
        _upsert_insert(db)(AIGlobalBudget)
        .values(period=period, used=0)
        .on_conflict_do_nothing(index_elements=["period"])
    )
    changed = db.execute(
        update(AIGlobalBudget)
        .where(
            AIGlobalBudget.period == period,
            AIGlobalBudget.used < limit,
        )
        .values(used=AIGlobalBudget.used + 1)
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        raise _quota_error("global", limit)


def _expire_reservation(db: Session, row: AIReservation) -> bool:
    """Release one dead reservation and refund its lifetime review (once).

    The conditional UPDATE makes this idempotent: if the reservation already
    completed, was released, or was expired by a concurrent sweep, nothing is
    refunded a second time.
    """
    changed = db.execute(
        update(AIReservation)
        .where(AIReservation.id == row.id, AIReservation.status == "reserved")
        .values(status="expired", active_resource=None)
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        return False
    if row.charged:
        db.execute(
            update(AIQuotaBucket)
            .where(
                AIQuotaBucket.user_id == row.user_id,
                AIQuotaBucket.kind == row.kind,
                AIQuotaBucket.period == "lifetime",
                AIQuotaBucket.used > 0,
            )
            .values(used=AIQuotaBucket.used - 1)
            .execution_options(synchronize_session=False)
        )
    return True


def release_resource(db: Session, resource: str) -> int:
    """Expire the live reservation that holds `resource` (its grading is known dead).

    Does not commit; the caller commits together with the state change.
    """
    rows = db.query(AIReservation).filter(AIReservation.active_resource == resource, AIReservation.status == "reserved")
    return sum(_expire_reservation(db, row) for row in rows.all())


def reconcile_stale_reservations(db: Session, user_id: int | None = None) -> int:
    """Release reservations whose worker died and refund their lifetime review.

    Runs for quota-exempt users too (they hold resource locks, just no charge).
    """
    cutoff = utcnow() - timedelta(minutes=settings.grading_stale_minutes)
    query = db.query(AIReservation).filter(
        AIReservation.status == "reserved",
        AIReservation.created_at < cutoff,
    )
    if user_id is not None:
        query = query.filter(AIReservation.user_id == user_id)
    released = sum(_expire_reservation(db, row) for row in query.all())
    if released:
        db.commit()
    return released


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
        db.add(
            AIReservation(
                id=key, user_id=user_id, kind=kind, charged=charged, active_resource=resource, status="reserved"
            )
        )
        db.flush()
        day = local_today().isoformat()
        _increment(db, user_id, "attempts", day, settings.AI_DAILY_ATTEMPTS)
        if charged:
            _increment(db, user_id, kind, "lifetime", limit, _consumed_count(db, model, user_id))
        _increment_global(db, day)
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
        changed = db.execute(
            update(AIReservation)
            .where(
                AIReservation.id == key,
                AIReservation.status == "reserved",
            )
            .values(status="completed" if result.success else "released", active_resource=None)
            .execution_options(synchronize_session=False)
        )
        if changed.rowcount == 1 and charged and not result.success:
            db.execute(
                update(AIQuotaBucket)
                .where(
                    AIQuotaBucket.user_id == user_id,
                    AIQuotaBucket.kind == kind,
                    AIQuotaBucket.period == "lifetime",
                )
                .values(used=AIQuotaBucket.used - 1)
                .execution_options(synchronize_session=False)
            )
        db.commit()
