"""The one place where application errors become HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.errors import ApplicationError


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    # Same body and headers FastAPI produces for an HTTPException.
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApplicationError, application_error_handler)
