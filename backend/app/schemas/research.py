"""Research request input and the streamed progress events.

This is the AUTHORITATIVE input check (the browser's check is only for
convenience). The submitted URL is never fetched by our server: it is only
passed to the research model as a hint, so we reject anything that points
at private infrastructure or carries credentials.
"""

import ipaddress
import unicodedata
from enum import StrEnum
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

MAX_APP_NAME_LENGTH = 100
MAX_URL_LENGTH = 2048

_LOCAL_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home", ".corp", ".intranet")


def validate_public_website_url(raw: str) -> str:
    """Return the URL if it is a plausible public http(s) website, else raise ValueError."""
    url = raw.strip()
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL is too long")
    if any(unicodedata.category(ch).startswith("C") for ch in url):
        raise ValueError("URL contains control characters")

    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("only http:// and https:// URLs are accepted")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URLs must not contain a username or password")
    host = (parts.hostname or "").rstrip(".")
    if not host:
        raise ValueError("URL has no host")
    try:
        parts.port  # noqa: B018  (accessing .port validates it; raises ValueError if malformed)
    except ValueError as error:
        raise ValueError("URL has an invalid port") from error

    # IP literals: allow only globally routable public addresses.
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        if not address.is_global or address.is_multicast:
            raise ValueError("private, local or reserved IP addresses are not accepted")
        return url

    if host == "localhost" or host.endswith(_LOCAL_SUFFIXES):
        raise ValueError("local addresses are not accepted")
    if "." not in host:
        raise ValueError("enter a public domain, e.g. https://example.com")
    labels = host.split(".")
    if any(not label or len(label) > 63 for label in labels) or len(host) > 253:
        raise ValueError("malformed host name")
    if not all(ch.isalnum() or ch == "-" for label in labels for ch in label):
        raise ValueError("malformed host name")
    return url


class ResearchRequest(BaseModel):
    """Body of POST /api/research/stream."""

    model_config = ConfigDict(extra="forbid")

    application_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_APP_NAME_LENGTH)]
    website_url: Annotated[str | None, Field(max_length=MAX_URL_LENGTH)] = None

    @field_validator("application_name")
    @classmethod
    def _plain_text_name(cls, value: str) -> str:
        if any(unicodedata.category(ch).startswith("C") for ch in value):
            raise ValueError("application name contains control characters")
        return value

    @field_validator("website_url")
    @classmethod
    def _safe_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return validate_public_website_url(value)


class Stage(StrEnum):
    """The five stages shown in the UI, in order. Keys are stable; labels are for display."""

    VALIDATING_INPUT = "validating_input"
    SEARCHING_DOCUMENTATION = "searching_documentation"
    ANALYSING_REQUIREMENTS = "analysing_requirements"
    VALIDATING_GUIDE = "validating_guide"
    SAVING_RESULT = "saving_result"


STAGE_LABELS: dict[Stage, str] = {
    Stage.VALIDATING_INPUT: "Validating the application input",
    Stage.SEARCHING_DOCUMENTATION: "Searching official documentation",
    Stage.ANALYSING_REQUIREMENTS: "Analysing OAuth setup requirements",
    Stage.VALIDATING_GUIDE: "Validating the guide and its evidence",
    Stage.SAVING_RESULT: "Saving the completed result",
}


class ErrorCode(StrEnum):
    """Safe, user-facing error codes sent in the final `error` event."""

    INVALID_INPUT = "invalid_input"
    NOT_CONFIGURED = "not_configured"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    BUDGET_EXHAUSTED = "budget_exhausted"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    REFUSED = "refused"
    INCOMPLETE = "incomplete"
    INVALID_RESULT = "invalid_result"
    SAVE_FAILED = "save_failed"
    INTERNAL_ERROR = "internal_error"


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_INPUT: "Please check the application name and website URL.",
    ErrorCode.NOT_CONFIGURED: "The research service is not configured on this server.",
    ErrorCode.PROVIDER_RATE_LIMITED: "The research service is busy. Please wait a minute and try again.",
    ErrorCode.BUDGET_EXHAUSTED: "The research service has reached its usage limit. Please try again later.",
    ErrorCode.PROVIDER_UNAVAILABLE: "The research service could not be reached. Please try again.",
    ErrorCode.TIMEOUT: "Research took too long and was stopped. Please try again.",
    ErrorCode.REFUSED: "The research request was declined. Try a different application name.",
    ErrorCode.INCOMPLETE: "The research result was cut off before it finished. Please try again.",
    ErrorCode.INVALID_RESULT: "The research result did not pass validation, so it was not saved. Please try again.",
    ErrorCode.SAVE_FAILED: "The result could not be saved. Please try again.",
    ErrorCode.INTERNAL_ERROR: "Something went wrong. Please try again.",
}

# Which errors are worth retrying from the UI (budget/config/input problems are not).
RETRYABLE: frozenset[ErrorCode] = frozenset(
    {
        ErrorCode.PROVIDER_RATE_LIMITED,
        ErrorCode.PROVIDER_UNAVAILABLE,
        ErrorCode.TIMEOUT,
        ErrorCode.INCOMPLETE,
        ErrorCode.INVALID_RESULT,
        ErrorCode.SAVE_FAILED,
        ErrorCode.INTERNAL_ERROR,
    }
)
