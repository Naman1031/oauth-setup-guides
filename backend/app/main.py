"""FastAPI application entry point.

Run locally:  uvicorn app.main:app --reload   (from the backend/ folder)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.research import router as research_router
from app.api.routes import router
from app.core.config import get_settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.services.research.rate_limit import ResearchRateLimiter


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

    # Security headers (noindex, nosniff, ...) on every response; see security_headers.py.
    # Starlette makes the LAST-added middleware the outermost, so this also
    # wraps CORS preflight responses. (Crash responses come from Starlette's
    # built-in error middleware outside it; errors.py adds the headers there.)
    app.add_middleware(SecurityHeadersMiddleware)

    # One limiter per server process (see rate_limit.py for the limitation).
    app.state.research_limiter = ResearchRateLimiter(
        per_ip_per_hour=settings.research_requests_per_ip_per_hour,
        per_day=settings.research_requests_per_day,
        max_concurrent=settings.research_max_concurrent,
    )

    register_error_handlers(app)
    app.include_router(router)
    app.include_router(research_router)
    return app


app = create_app()
