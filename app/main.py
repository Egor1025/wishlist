import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.context import get_cid, set_cid
from app.core.errors import ApiError
from app.database import init_db
from app.routers.wishes import router as wishes_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="SecDev Course App", version="0.1.0", lifespan=lifespan)

logger = logging.getLogger("app.api")


@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    cid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_cid(cid)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response


@app.middleware("http")
async def access_log(request: Request, call_next):
    start = time.perf_counter()
    cid = get_cid()
    method = request.method
    path = request.url.path

    logger.info(
        "incoming_request",
        extra={
            "correlation_id": cid,
            "method": method,
            "path": path,
        },
    )

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "request_completed",
        extra={
            "correlation_id": cid,
            "method": method,
            "path": path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2),
        },
    )

    return response


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=()"
    response.headers["Strict-Transport-Security"] = (
        "max-age=63072000; includeSubDomains; preload"
    )
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    return response


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    cid = get_cid()
    body = {"code": exc.code, "message": exc.message}
    if cid is not None:
        body["correlation_id"] = cid

    logger.warning(
        "api_error",
        extra={
            "correlation_id": cid,
            "path": request.url.path,
            "status": exc.status,
            "code": exc.code,
        },
    )

    return JSONResponse(
        status_code=exc.status,
        content={"error": body},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    cid = get_cid()
    detail = exc.detail if isinstance(exc.detail, str) else "http_error"
    body = {"code": "http_error", "message": detail}
    if cid is not None:
        body["correlation_id"] = cid

    logger.warning(
        "http_error",
        extra={
            "correlation_id": cid,
            "path": request.url.path,
            "status": exc.status_code,
            "code": body["code"],
        },
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": body},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    cid = get_cid()
    body = {"code": "validation_error", "message": "Invalid request"}
    if cid is not None:
        body["correlation_id"] = cid

    logger.info(
        "validation_error",
        extra={
            "correlation_id": cid,
            "path": request.url.path,
            "status": 422,
        },
    )

    return JSONResponse(
        status_code=422,
        content={"error": body},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    cid = get_cid()
    body = {"code": "internal_error", "message": "Internal server error"}
    if cid is not None:
        body["correlation_id"] = cid

    logger.error(
        "unhandled_error",
        extra={
            "correlation_id": cid,
            "path": request.url.path,
            "status": 500,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={"error": body},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(wishes_router)
