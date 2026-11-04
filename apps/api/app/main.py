from __future__ import annotations

from time import perf_counter

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.errors import error_response, register_error_handlers
from app.api.v1.router import api_router
from app.core.config import settings
from app.db.session import get_db
from app.services.observability import (
    REQUEST_ID_HEADER,
    accepted_request_id,
    emit_event,
    report_unexpected_error,
    route_template,
)


app = FastAPI(title="StockX Marketplace API")
register_error_handlers(app)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = accepted_request_id(request.headers.get(REQUEST_ID_HEADER))
    request.state.request_id = request_id
    started = perf_counter()
    error_code = None
    try:
        response = await call_next(request)
    except Exception as exc:
        error_code = "internal_server_error"
        template = route_template(request.scope)
        emit_event(
            "application_error",
            request_id=request_id,
            route=template,
            method=request.method,
            status=500,
            error_code=error_code,
            exception_type=type(exc).__name__,
        )
        report_unexpected_error(
            request_id=request_id,
            route=template,
            method=request.method,
            exception_type=type(exc).__name__,
        )
        response = error_response(500, error_code, "An unexpected server error occurred.")
    response.headers[REQUEST_ID_HEADER] = request_id
    emit_event(
        "request_completed",
        request_id=request_id,
        route=route_template(request.scope),
        method=request.method,
        status=response.status_code,
        duration_ms=round((perf_counter() - started) * 1000, 3),
        error_code=error_code or getattr(request.state, "error_code", None),
    )
    return response


app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get(
    "/ready",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable"}},
)
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "service_not_ready",
            "The service is not ready.",
        )
    return {"status": "ready"}
