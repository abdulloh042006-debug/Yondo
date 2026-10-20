from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ApplicationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def problem_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        'code': code,
        'message': message,
        'request_id': getattr(request.state, 'request_id', None),
    }
    if errors is not None:
        content['errors'] = errors
    return JSONResponse(status_code=status_code, content=content)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        return problem_response(
            request, status_code=exc.status_code, code=exc.code, message=exc.message
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return problem_response(
            request,
            status_code=422,
            code='validation_error',
            message='Request validation failed',
            # Pydantic validators can include ValueError/bytes objects in ctx/input.
            # Return only safe, stable details; do not echo potentially sensitive input.
            errors=[
                {'type': error['type'], 'loc': list(error['loc']), 'msg': error['msg']}
                for error in exc.errors()
            ],
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else 'HTTP request failed'
        return problem_response(
            request, status_code=exc.status_code, code='http_error', message=message
        )

