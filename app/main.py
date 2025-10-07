import json
import logging
from typing import Annotated, ClassVar

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="SecDev Course App", version="0.1.0")


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
    price_estimate: Annotated[int, Field(ge=0)] | None = None
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
    wish = {
        "id": Wish.COUNTER,
        "title": data.title,
        "link": data.link,
        "price_estimate": data.price_estimate,
        "notes": data.notes,
    }
    _DB["wishes"].append(wish)
    return wish


@app.patch("/wishes/{wish_id}")
def edit_wish(wish_id: int, data: Wish):
    wish = get_wish(wish_id)
    updates = data.model_dump(exclude_unset=True)
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
def price_filter(price_lt: int = Query(..., alias="price<")):
    return [
        wish
        for wish in _DB["wishes"]
        if wish["price_estimate"] is not None and wish["price_estimate"] < price_lt
    ]
