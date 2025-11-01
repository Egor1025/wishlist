import json
import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.database import get_db
from app.models import WishORM
from app.schemas import WishIn, WishOut

router = APIRouter()

audit = logging.getLogger("app.audit")


def _utcnow() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _normalize_price(value: Decimal | int | float | str | None) -> Decimal | None:
    if value is None:
        return None
    dec = Decimal(str(value))
    if dec < 0:
        raise ApiError(
            code="validation_error", message="price can't be negative", status=422
        )
    return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.get("/wishes/{wish_id}", response_model=WishOut)
def get_wish(wish_id: int, db: Session = Depends(get_db)):
    wish = db.get(WishORM, wish_id)
    if not wish:
        raise ApiError(code="not_found", message="wish doesn't exist", status=404)
    return wish


@router.post("/wishes", status_code=201, response_model=WishOut)
def create_wish(data: WishIn, db: Session = Depends(get_db)):
    if not data.title:
        raise ApiError(code="validation_error", message="title is required", status=422)

    normalized_price = _normalize_price(data.price_estimate)
    wish = WishORM(
        title=data.title,
        link=data.link,
        price_estimate=normalized_price,
        updated_at=_utcnow(),
        notes=data.notes,
    )
    db.add(wish)
    db.commit()
    db.refresh(wish)
    return wish


@router.patch("/wishes/{wish_id}", response_model=WishOut)
def edit_wish(wish_id: int, data: WishIn, db: Session = Depends(get_db)):
    wish = db.get(WishORM, wish_id)
    if not wish:
        raise ApiError(code="not_found", message="wish doesn't exist", status=404)

    updates = data.model_dump(exclude_unset=True)
    if "price_estimate" in updates:
        updates["price_estimate"] = _normalize_price(updates["price_estimate"])
    if "title" in updates and not updates["title"]:
        raise ApiError(
            code="validation_error", message="title can't be empty", status=422
        )

    for field, value in updates.items():
        setattr(wish, field, value)
    wish.updated_at = _utcnow()

    db.commit()
    db.refresh(wish)
    return wish


@router.delete("/wishes/{wish_id}", status_code=204)
def delete_wish(wish_id: int, db: Session = Depends(get_db)):
    wish = db.get(WishORM, wish_id)
    if not wish:
        raise ApiError(code="not_found", message="wish doesn't exist", status=404)

    db.delete(wish)
    db.commit()

    audit.info(
        json.dumps(
            {"action": "delete", "object_id": wish_id, "result": "success"},
            ensure_ascii=False,
        )
    )
    return None


@router.get("/wishes", response_model=list[WishOut])
def price_filter(
    price_lt: Decimal = Query(..., alias="price<"), db: Session = Depends(get_db)
):
    normalized = _normalize_price(price_lt)
    result = (
        db.query(WishORM)
        .filter(WishORM.price_estimate.isnot(None))
        .filter(WishORM.price_estimate < normalized)
        .all()
    )
    return result
