from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.api.schemas.learning import DiagnosticStartIn, MistakeStatusIn, PlanStatusIn
from app.application.learning import (
    accept_diagnostic_level,
    diagnostic_state,
    get_weekly_plan,
    list_notebook,
    refresh_diagnostic,
    set_mistake_status,
    set_plan_status,
    start_diagnostic,
)
from app.application.learning.dashboard import dashboard_summary
from app.domain.models.learning import DiagnosticSession, StudyPlanItem
from app.domain.models.user import User
from app.application.learning.study_plan import week_start

router = APIRouter()


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return dashboard_summary(db, current_user)


@router.get("/diagnostic")
def get_diagnostic(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return diagnostic_state(db, current_user.id)


@router.post("/diagnostic/start", status_code=status.HTTP_201_CREATED)
def begin_diagnostic(
    payload: DiagnosticStartIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return start_diagnostic(db, current_user.id, payload.skills)


@router.post("/diagnostic/refresh")
def check_diagnostic(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = refresh_diagnostic(db, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="No diagnostic is in progress")
    return result


@router.post("/diagnostic/accept-level")
def accept_level(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = accept_diagnostic_level(db, current_user)
    if result is None:
        raise HTTPException(status_code=409, detail="Complete a diagnostic before updating your level")
    return result


@router.post("/diagnostic/skip")
def skip_diagnostic(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = DiagnosticSession(
        user_id=current_user.id,
        status="skipped",
        skills=[],
        completed_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return diagnostic_state(db, current_user.id)


@router.get("/study-plan")
def study_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_weekly_plan(db, current_user)


@router.post("/study-plan/recalculate")
def recalculate_study_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_weekly_plan(db, current_user, recalculate=True)


@router.post("/study-plan/reset")
def reset_study_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(StudyPlanItem).filter(
        StudyPlanItem.user_id == current_user.id,
        StudyPlanItem.week_start == week_start(),
    ).delete(synchronize_session=False)
    db.commit()
    return get_weekly_plan(db, current_user, recalculate=True)


@router.patch("/study-plan/{item_id}")
def update_plan_item(
    item_id: int,
    payload: PlanStatusIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = set_plan_status(db, current_user.id, item_id, payload.status)
    if item is None:
        raise HTTPException(status_code=404, detail="Study plan item not found")
    return item


@router.get("/study-plan/{item_id}/explain")
def explain_plan_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(StudyPlanItem).filter(StudyPlanItem.id == item_id, StudyPlanItem.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Study plan item not found")
    return {"id": item.id, "title": item.title, "reason": item.reason, "source": {"type": item.source_type, "ref": item.source_ref}}


@router.get("/mistakes")
def mistakes(
    skill: str | None = Query(None, pattern="^(writing|reading|listening)$"),
    review_status: str | None = Query(None, alias="status", pattern="^(new|reviewing|mastered)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_notebook(db, current_user.id, skill, review_status, page, page_size)


@router.patch("/mistakes/{skill}/{source_id}")
def update_mistake(
    skill: str,
    source_id: int,
    payload: MistakeStatusIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if skill not in {"writing", "reading", "listening"}:
        raise HTTPException(status_code=422, detail="Unsupported skill")
    if not set_mistake_status(db, current_user.id, skill, source_id, payload.status):
        raise HTTPException(status_code=404, detail="Mistake not found")
    return {"skill": skill, "source_id": source_id, "status": payload.status}
