"""Free-tier AI grading quotas.

Until subscriptions exist, every account gets a fixed number of AI gradings
per skill (writing / speaking). This is a cost-protection measure: grading
runs on a paid Gemini key, so an unauthenticated-signup + submit loop must
not be able to run up the bill. Failed gradings are not counted — the user
never received a grade for them.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.config import settings


def _consumed_count(db: Session, model, user_id: int) -> int:
    """Count quota-consuming submissions for a user.

    Writing has a `status` column ("failed" rows never produced a grade);
    speaking has no status, so an ungraded/failed row is `band` NULL or 0.
    Either way, only gradings the user actually received are counted.
    """
    q = db.query(model).filter(model.user_id == user_id)
    if hasattr(model, "status"):
        q = q.filter(model.status != "failed")
    else:
        q = q.filter(model.band > 0)
    return q.count()


def quota_status(db: Session, model, user, limit: int) -> dict:
    """Return the user's free-quota state for a submission model.

    Shape: {"limit", "used", "remaining", "exempt"}. Exempt users and
    negative limits report unlimited via exempt=True (remaining stays at
    limit so UIs don't render a countdown).
    """
    exempt = limit < 0 or user.username in settings.quota_exempt_users
    if exempt:
        return {"limit": limit, "used": 0, "remaining": limit, "exempt": True}
    used = _consumed_count(db, model, user.id)
    return {
        "limit": limit,
        "used": used,
        "remaining": max(0, limit - used),
        "exempt": False,
    }


def enforce_free_quota(db: Session, model, user, limit: int, skill: str) -> None:
    """Raise 403 if the user has used up their free gradings for this skill.

    `model` is the submission model (WritingSubmission / SpeakingSubmission);
    it must have `user_id` and `status` columns. Rows with status "failed"
    do not consume quota. Usernames in QUOTA_EXEMPT_USERS (owner/demo
    accounts) are never limited.
    """
    if limit < 0:  # unlimited (dev escape hatch)
        return
    if user.username in settings.quota_exempt_users:
        return
    used = _consumed_count(db, model, user.id)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You've used your {limit} free {skill} reviews. "
                "Paid plans are coming soon — thanks for trying Testora!"
            ),
        )
