"""POST /api/research/stream: run one research workflow and stream its progress.

Server-Sent Events (SSE) format, one event per block:

    event: progress
    data: {"stage": "searching_documentation", "label": "...", "state": "started"}

The stream ends with exactly one `complete` or `error` event.
"""

import json
from collections.abc import Callable, Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.schemas.research import ResearchRequest
from app.services.research.openai_runner import ResponsesClient, make_openai_client
from app.services.research.rate_limit import ResearchRateLimiter
from app.services.research.workflow import run_research

router = APIRouter(prefix="/api")

MAX_BODY_BYTES = 4096  # name ≤ 100 chars + URL ≤ 2048 chars fits comfortably

LIMIT_MESSAGES = {
    "busy": "Another research request is running. Please try again in a moment.",
    "ip_hourly": "You've reached the research limit for this hour. Please try again later.",
    "daily": "The daily research limit has been reached. Please try again tomorrow.",
}


# Dependencies (overridden in tests to avoid real OpenAI calls).
def get_rate_limiter(request: Request) -> ResearchRateLimiter:
    return request.app.state.research_limiter


def get_client_factory() -> Callable[[Settings], ResponsesClient]:
    return make_openai_client


def get_research_session_factory() -> Callable[[], Session]:
    return get_session_factory()


def format_sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/research/stream", response_class=StreamingResponse)
def research_stream(
    request: Request,
    body: Annotated[dict[str, Any], Body()],
    limiter: Annotated[ResearchRateLimiter, Depends(get_rate_limiter)],
    client_factory: Annotated[Callable[[Settings], ResponsesClient], Depends(get_client_factory)],
    session_factory: Annotated[Callable[[], Session], Depends(get_research_session_factory)],
) -> StreamingResponse:
    if int(request.headers.get("content-length") or 0) > MAX_BODY_BYTES:
        raise ApiError(413, "payload_too_large", "The request is too large.")

    # Reject bad input BEFORE taking a rate-limit slot, so typos don't use up
    # someone's hourly quota. (The workflow's stage 1 validates again.)
    try:
        ResearchRequest.model_validate(body)
    except ValidationError as error:
        fields = sorted({str(e["loc"][0]) for e in error.errors() if e["loc"]})
        raise ApiError(422, "invalid_request", f"Invalid input: {', '.join(fields) or 'request'}.") from error

    # Behind Render's proxy, uvicorn's --proxy-headers makes this the real client IP.
    client_ip = request.client.host if request.client else "unknown"
    decision = limiter.try_acquire(client_ip)
    if not decision.allowed:
        raise ApiError(
            429, "rate_limited", LIMIT_MESSAGES[decision.reason],
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )

    settings = get_settings()

    def event_stream() -> Iterator[str]:
        try:
            for name, payload in run_research(body, settings, client_factory, session_factory):
                yield format_sse(name, payload)
        finally:
            # Runs on success, error, AND if the browser disconnects mid-stream.
            limiter.release()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},  # don't buffer events in proxies
    )
