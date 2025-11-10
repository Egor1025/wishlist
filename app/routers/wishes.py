import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.context import get_cid
from app.core.errors import ApiError
from app.database import get_db
from app.models import WishORM
from app.schemas import WishIn, WishOut

router = APIRouter(prefix="/wishes")

audit = logging.getLogger("app.audit")


def _utcnow() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


MAX_SEARCH_QUERY_LENGTH = 100


def _escape_like(value: str) -> str:
    value = value.replace("\\", "\\\\")
    value = value.replace("%", "\\%")
    value = value.replace("_", "\\_")
    return f"%{value}%"


@router.get("/search", response_model=list[WishOut])
def search_wishes(
    q: str = Query(..., min_length=1, max_length=MAX_SEARCH_QUERY_LENGTH),
    db: Session = Depends(get_db),
):
    pattern = _escape_like(q)
    result = db.query(WishORM).filter(WishORM.title.ilike(pattern, escape="\\")).all()
    return result


@router.get("/{wish_id}", response_model=WishOut)
def get_wish(wish_id: int, db: Session = Depends(get_db)):
    wish = db.get(WishORM, wish_id)
    if not wish:
        raise ApiError(code="not_found", message="wish doesn't exist", status=404)
    return wish


@router.post("", status_code=201, response_model=WishOut)
def create_wish(data: WishIn, db: Session = Depends(get_db)):
    if not data.title:
        raise ApiError(code="validation_error", message="title is required", status=422)

    wish = WishORM(
        title=data.title,
        link=data.link,
        price_estimate=data.price_estimate,
        updated_at=_utcnow(),
        notes=data.notes,
    )
    db.add(wish)
    db.commit()
    db.refresh(wish)

    audit.info(
        json.dumps(
            {
                "action": "create",
                "wish_id": wish.id,
                "success": True,
                "correlation_id": get_cid(),
            },
            ensure_ascii=False,
        )
    )
    return wish


@router.patch("/{wish_id}", response_model=WishOut)
def edit_wish(wish_id: int, data: WishIn, db: Session = Depends(get_db)):
    wish = db.get(WishORM, wish_id)
    if not wish:
        raise ApiError(code="not_found", message="wish doesn't exist", status=404)

    updates = data.model_dump(exclude_unset=True)

    if "title" in updates and not updates["title"]:
        raise ApiError(
            code="validation_error", message="title can't be empty", status=422
        )

    for field, value in updates.items():
        setattr(wish, field, value)
    wish.updated_at = _utcnow()

    db.commit()
    db.refresh(wish)

    audit.info(
        json.dumps(
            {
                "action": "update",
                "wish_id": wish.id,
                "success": True,
                "correlation_id": get_cid(),
            },
            ensure_ascii=False,
        )
    )
    return wish


@router.delete("/{wish_id}", status_code=204)
def delete_wish(wish_id: int, db: Session = Depends(get_db)):
    wish = db.get(WishORM, wish_id)
    if not wish:
        raise ApiError(code="not_found", message="wish doesn't exist", status=404)

    db.delete(wish)
    db.commit()

    audit.info(
        json.dumps(
            {
                "action": "delete",
                "wish_id": wish.id,
                "success": True,
                "correlation_id": get_cid(),
            },
            ensure_ascii=False,
        )
    )
    return None


@router.get("", response_model=list[WishOut])
def price_filter(
    price_lt: Decimal = Query(..., alias="price<"), db: Session = Depends(get_db)
):
    result = (
        db.query(WishORM)
        .filter(WishORM.price_estimate.isnot(None))
        .filter(WishORM.price_estimate < price_lt)
        .all()
    )
    return result
