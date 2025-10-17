import json
import logging
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, ClassVar

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="SecDev Course App", version="0.1.0")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_price(value: Decimal | int | float | str | None) -> Decimal | None:
    if value is None:
        return None

    dec = Decimal(str(value))
    if dec < 0:
        raise ApiError(
            code="validation_error", message="price can't be negative", status=422
        )
    return dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Normalize FastAPI HTTPException into our error envelope
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": detail}},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


_DB = {"wishes": []}


class Wish(BaseModel):
    COUNTER: ClassVar[int] = 0
    title: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    link: str | None = None
    price_estimate: Decimal | None = None
    updated_at: datetime | None = None
    notes: str | None = None


@app.get("/wishes/{wish_id}")
def get_wish(wish_id: int):
    for wish in _DB["wishes"]:
        if wish["id"] == wish_id:
            return wish
    raise ApiError(code="not_found", message="wish doesn't exist", status=404)


@app.post("/wishes", status_code=201)
def create_wish(data: Wish):
    if not data.title:
        raise ApiError(code="validation_error", message="title is required", status=422)
    Wish.COUNTER += 1
    normalized_price = _normalize_price(data.price_estimate)
    wish = {
        "id": Wish.COUNTER,
        "title": data.title,
        "link": data.link,
        "price_estimate": normalized_price,
        "updated_at": _utcnow(),
        "notes": data.notes,
    }
    _DB["wishes"].append(wish)
    return wish


@app.patch("/wishes/{wish_id}")
def edit_wish(wish_id: int, data: Wish):
    wish = get_wish(wish_id)
    updates = data.model_dump(exclude_unset=True)
    if "price_estimate" in updates:
        updates["price_estimate"] = _normalize_price(updates["price_estimate"])
    updates["updated_at"] = _utcnow()
    for field, value in updates.items():
        if field == "title" and not value:
            raise ApiError(
                code="validation_error", message="title can't be empty", status=422
            )
        wish[field] = value
    return wish


audit = logging.getLogger("app.audit")


@app.delete("/wishes/{wish_id}", status_code=204)
def delete_wish(wish_id: int):
    wish = get_wish(wish_id)
    _DB["wishes"].remove(wish)

    audit.info(
        json.dumps(
            {"action": "delete", "object_id": wish_id, "result": "success"},
            ensure_ascii=False,
        )
    )

    return None


@app.get("/wishes")
def price_filter(price_lt: Decimal = Query(..., alias="price<")):
    return [
        wish
        for wish in _DB["wishes"]
        if wish["price_estimate"] is not None
        and wish["price_estimate"] < _normalize_price(price_lt)
    ]
