from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.infrastructure.time import utcnow
from app.api.dependencies import get_current_user, get_db, user_rate_limit
from app.api.schemas.analytics import Payload
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


@router.get("/dashboard", response_model=Payload)
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return dashboard_summary(db, current_user)


@router.get("/diagnostic", response_model=Payload)
def get_diagnostic(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return diagnostic_state(db, current_user.id)


@router.post(
    "/diagnostic/start",
    status_code=status.HTTP_201_CREATED,
    response_model=Payload,
    dependencies=[Depends(user_rate_limit("learning-write", 30))],
)
def begin_diagnostic(
    payload: DiagnosticStartIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return start_diagnostic(db, current_user.id, payload.skills)


@router.post("/diagnostic/refresh", response_model=Payload)
def check_diagnostic(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = refresh_diagnostic(db, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="No diagnostic is in progress")
    return result


@router.post("/diagnostic/accept-level", response_model=Payload)
def accept_level(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = accept_diagnostic_level(db, current_user)
    if result is None:
        raise HTTPException(status_code=409, detail="Complete a diagnostic before updating your level")
    return result


@router.post("/diagnostic/skip", response_model=Payload)
def skip_diagnostic(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = DiagnosticSession(
        user_id=current_user.id,
        status="skipped",
        skills=[],
        completed_at=utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return diagnostic_state(db, current_user.id)


@router.get("/study-plan", response_model=Payload)
def study_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_weekly_plan(db, current_user)


@router.post(
    "/study-plan/recalculate", response_model=Payload, dependencies=[Depends(user_rate_limit("learning-write", 30))]
)
def recalculate_study_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_weekly_plan(db, current_user, recalculate=True)


@router.post("/study-plan/reset", response_model=Payload)
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


@router.patch("/study-plan/{item_id}", response_model=Payload)
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


@router.get("/study-plan/{item_id}/explain", response_model=Payload)
def explain_plan_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(StudyPlanItem).filter(StudyPlanItem.id == item_id, StudyPlanItem.user_id == current_user.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Study plan item not found")
    return {
        "id": item.id,
        "title": item.title,
        "reason": item.reason,
        "source": {"type": item.source_type, "ref": item.source_ref},
    }


@router.get("/mistakes", response_model=Payload)
def mistakes(
    skill: str | None = Query(None, pattern="^(writing|reading|listening)$"),
    review_status: str | None = Query(None, alias="status", pattern="^(new|reviewing|mastered)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_notebook(db, current_user.id, skill, review_status, page, page_size)


@router.patch("/mistakes/{skill}/{source_id}", response_model=Payload)
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
