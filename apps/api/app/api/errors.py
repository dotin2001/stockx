from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.observability import emit_event, route_template


class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        headers: dict[str, str] | None = None,
        clear_refresh_cookie: bool = False,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers or {}
        self.clear_refresh_cookie = clear_refresh_cookie


def error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError) -> JSONResponse:
        request.state.error_code = exc.code
        emit_event(
            "application_error",
            request_id=getattr(request.state, "request_id", "unavailable"),
            route=route_template(request.scope),
            method=request.method,
            status=exc.status_code,
            error_code=exc.code,
        )
        response = error_response(exc.status_code, exc.code, exc.message, headers=exc.headers)
        if exc.clear_refresh_cookie:
            from app.core.config import settings

            response.delete_cookie(key=settings.refresh_cookie_name, path="/api/v1/auth")
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request.state.error_code = "validation_error"
        emit_event(
            "application_error",
            request_id=getattr(request.state, "request_id", "unavailable"),
            route=route_template(request.scope),
            method=request.method,
            status=status.HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="validation_error",
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": jsonable_encoder(exc.errors()),
                }
            },
        )
