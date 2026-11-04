"""One streamed Responses API call with the built-in web_search tool.

Cost controls applied on EVERY call:
- tool_choice="required": research must actually search (spec 6.3);
- max_tool_calls: hard cap on paid web-search calls;
- max_output_tokens: cap on generated (incl. reasoning) tokens;
- max_retries=0: the SDK never silently repeats an expensive request;
- store=False: OpenAI doesn't keep the response for later retrieval.
"""

import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import openai

from app.core.config import Settings
from app.schemas.research import ErrorCode
from app.services.research.evidence import ResearchTrace, extract_trace
from app.services.research.output_schema import text_format_config
from app.services.research.prompt import INSTRUCTIONS, build_user_input

logger = logging.getLogger(__name__)


class ResearchError(Exception):
    """A failure with a safe, user-facing code. `detail` is for server logs only."""

    def __init__(self, code: ErrorCode, detail: str = "") -> None:
        super().__init__(detail or code.value)
        self.code = code
        self.detail = detail


class ResponsesClient(Protocol):
    """The tiny slice of the OpenAI client we use (lets tests pass a fake)."""

    @property
    def responses(self) -> Any: ...


@dataclass
class StreamSignal:
    """Something real happened in the stream that the UI may show."""

    kind: str  # "search_started" | "search_completed" | "writing_started"


@dataclass
class ResearchCallResult:
    raw_guide: dict[str, Any]
    trace: ResearchTrace
    usage: dict[str, int]


def make_openai_client(settings: Settings) -> ResponsesClient:
    if settings.openai_api_key is None or not settings.openai_model:
        raise ResearchError(ErrorCode.NOT_CONFIGURED, "OPENAI_API_KEY or OPENAI_MODEL is not set")
    return openai.OpenAI(
        api_key=settings.openai_api_key.get_secret_value(),
        timeout=settings.openai_timeout_seconds,
        max_retries=0,
    )


def _usage_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {}
    details = getattr(usage, "output_tokens_details", None)
    return {
        "input_tokens": getattr(usage, "input_tokens", 0) or 0,
        "output_tokens": getattr(usage, "output_tokens", 0) or 0,
        "reasoning_tokens": getattr(details, "reasoning_tokens", 0) or 0 if details else 0,
    }


def _map_openai_error(error: Exception) -> ResearchError:
    """Translate SDK exceptions into safe codes. Raw messages go to the log only."""
    if isinstance(error, openai.RateLimitError):
        code = str(getattr(error, "code", "") or "")
        body = json.dumps(getattr(error, "body", None) or {})
        if "insufficient_quota" in (code + body) or "spend_limit" in (code + body):
            return ResearchError(ErrorCode.BUDGET_EXHAUSTED, f"429 budget: {code}")
        return ResearchError(ErrorCode.PROVIDER_RATE_LIMITED, f"429: {code}")
    if isinstance(error, openai.APITimeoutError):
        return ResearchError(ErrorCode.TIMEOUT, "OpenAI request timed out")
    if isinstance(error, openai.APIConnectionError):
        return ResearchError(ErrorCode.PROVIDER_UNAVAILABLE, "could not connect to OpenAI")
    if isinstance(error, (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError)):
        return ResearchError(ErrorCode.NOT_CONFIGURED, f"{type(error).__name__}: {getattr(error, 'message', '')}")
    if isinstance(error, openai.APIStatusError):
        status = getattr(error, "status_code", 0)
        if status >= 500:
            return ResearchError(ErrorCode.PROVIDER_UNAVAILABLE, f"OpenAI {status}")
        return ResearchError(ErrorCode.INTERNAL_ERROR, f"OpenAI {status}: {getattr(error, 'message', '')}")
    return ResearchError(ErrorCode.INTERNAL_ERROR, f"{type(error).__name__}: {error}")


def _final_text_and_refusal(final: Any) -> tuple[str, bool]:
    text_parts: list[str] = []
    refused = False
    for item in getattr(final, "output", None) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "refusal":
                refused = True
            elif getattr(part, "type", None) == "output_text":
                text_parts.append(getattr(part, "text", "") or "")
    return "".join(text_parts), refused


def run_research_call(
    client: ResponsesClient,
    settings: Settings,
    application_name: str,
    website_url: str | None,
    today: date,
) -> Iterator[StreamSignal | ResearchCallResult]:
    """Run the call as a generator.

    It yields a StreamSignal each time something real happens in the stream,
    and yields the ResearchCallResult LAST. Raises ResearchError on failure.
    The caller just loops: `for item in run_research_call(...)`.
    """
    started = time.monotonic()
    try:
        with client.responses.stream(
            model=settings.openai_model,
            instructions=INSTRUCTIONS,
            input=build_user_input(application_name, website_url, today),
            tools=[{"type": "web_search", "search_context_size": settings.openai_search_context_size}],
            tool_choice="required",
            include=["web_search_call.action.sources"],
            max_tool_calls=settings.openai_max_tool_calls,
            max_output_tokens=settings.openai_max_output_tokens,
            reasoning={"effort": settings.openai_reasoning_effort},
            text=text_format_config(),
            store=False,
        ) as stream:
            writing_started = False
            for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.web_search_call.in_progress":
                    yield StreamSignal("search_started")
                elif event_type == "response.web_search_call.completed":
                    yield StreamSignal("search_completed")
                elif event_type == "response.output_text.delta" and not writing_started:
                    writing_started = True
                    yield StreamSignal("writing_started")
                elif event_type == "response.refusal.delta":
                    raise ResearchError(ErrorCode.REFUSED, "model refused")
                elif event_type in ("response.failed", "error"):
                    raise ResearchError(ErrorCode.PROVIDER_UNAVAILABLE, f"stream event {event_type}")
            final = stream.get_final_response()
    except ResearchError:
        raise
    except openai.OpenAIError as error:
        raise _map_openai_error(error) from error

    usage = _usage_dict(getattr(final, "usage", None))
    trace = extract_trace(getattr(final, "output", None) or [])
    logger.info(
        "research call model=%s status=%s web_search_calls=%d input_tokens=%s output_tokens=%s reasoning_tokens=%s seconds=%.1f",
        settings.openai_model,
        getattr(final, "status", None),
        trace.web_search_calls,
        usage.get("input_tokens"),
        usage.get("output_tokens"),
        usage.get("reasoning_tokens"),
        time.monotonic() - started,
    )

    status = getattr(final, "status", None)
    if status == "incomplete":
        reason = getattr(getattr(final, "incomplete_details", None), "reason", None)
        if reason == "content_filter":
            raise ResearchError(ErrorCode.REFUSED, "incomplete: content_filter")
        raise ResearchError(ErrorCode.INCOMPLETE, f"incomplete: {reason}")
    if status not in (None, "completed"):
        raise ResearchError(ErrorCode.PROVIDER_UNAVAILABLE, f"final status {status}")

    text, refused = _final_text_and_refusal(final)
    if refused:
        raise ResearchError(ErrorCode.REFUSED, "refusal content in final response")
    if trace.web_search_calls == 0:
        raise ResearchError(ErrorCode.INVALID_RESULT, "no web search was performed")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise ResearchError(ErrorCode.INVALID_RESULT, f"output is not valid JSON: {error}") from error
    if not isinstance(raw, dict):
        raise ResearchError(ErrorCode.INVALID_RESULT, "output JSON is not an object")
    yield ResearchCallResult(raw_guide=raw, trace=trace, usage=usage)
