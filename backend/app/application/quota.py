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
    used = (
        db.query(model)
        .filter(model.user_id == user.id, model.status != "failed")
        .count()
    )
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"You've used your {limit} free {skill} reviews. "
                "Paid plans are coming soon — thanks for trying Testora!"
            ),
        )
