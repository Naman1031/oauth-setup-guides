"""One consistent error shape for the whole API: {"error": {"code", "message"}}.

Raw exception text and stack traces are never sent to the client; they
might reveal internals (file paths, SQL, connection details).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """Raise this from a route to return a specific status code and safe message."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # e.g. 404 for an unknown path, 405 for a wrong HTTP method
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = "Not found." if exc.status_code == 404 else "The request could not be processed."
        return error_response(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Field locations are safe and helpful; the submitted values are not echoed back.
        fields = sorted({".".join(str(part) for part in error["loc"] if part != "body") for error in exc.errors()})
        return error_response(422, "invalid_request", f"Invalid input: {', '.join(fields) or 'request'}.")

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Full details go to the server log only.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "internal_error", "Something went wrong. Please try again later.")
