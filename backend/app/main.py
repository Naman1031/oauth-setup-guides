"""FastAPI application entry point.

Run locally:  uvicorn app.main:app --reload   (from the backend/ folder)
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.routes import router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)

    app = FastAPI(
        title="OAuth Setup Guides API",
        # The interactive /docs page is handy locally but not needed in production.
        docs_url=None if settings.environment == "production" else "/docs",
        redoc_url=None,
        openapi_url=None if settings.environment == "production" else "/openapi.json",
    )

    # CORS: the browser only lets these exact origins (our frontend) call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,  # no cookies or auth; the API has no logins
    )

    # API responses are data, not pages: ask search engines never to index
    # them. A middleware runs on EVERY response, including error responses.
    @app.middleware("http")
    async def add_noindex_header(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        return response

    register_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
