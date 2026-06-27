"""History & Comparison endpoints.

GET /history                        — unified list across all four skills
GET /history/compare?a=X&b=Y        — side-by-side diff of two same-skill attempts
GET /history/{item_id}              — detail for one attempt (item_id = 'writing-5')
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.domain.models.user import User
from app.application.history import list_history, get_history_item
from app.application.comparison import compare_history

router = APIRouter()


@router.get("")
def history_list(
    skill: str | None = Query(None, pattern="^(writing|speaking|reading|listening)$"),
    sort: str = Query("newest", pattern="^(newest|oldest|highest|lowest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = list_history(db, current_user.id, skill=skill)

    if sort == "oldest":
        items.sort(key=lambda x: x["created_at"] or "")
    elif sort == "highest":
        items.sort(key=lambda x: (x["band"] is None, -(x["band"] or 0)))
    elif sort == "lowest":
        items.sort(key=lambda x: (x["band"] is None, x["band"] or 0))
    # "newest" is the default (already sorted by list_history)

    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start : start + page_size], "total": total, "page": page, "page_size": page_size}


@router.get("/compare")
def history_compare(
    a: str = Query(...),
    b: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = compare_history(db, current_user.id, a, b)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/{item_id}")
def history_detail(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = get_history_item(db, current_user.id, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="History item not found")
    return item
