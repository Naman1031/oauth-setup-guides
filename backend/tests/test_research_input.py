"""Authoritative input validation for research requests."""

import pytest
from pydantic import ValidationError

from app.schemas.research import ResearchRequest


@pytest.mark.parametrize(
    "url",
    ["https://linear.app", "http://example.com/path?x=1", "https://docs.example.co.uk", "https://8.8.8.8/", "https://bücher.de"],
)
def test_accepts_public_urls(url: str) -> None:
    assert ResearchRequest(application_name="Linear", website_url=url).website_url == url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://user:pw@example.com",
        "https://user@example.com",
        "http://localhost:8000",
        "http://api.localhost",
        "http://printer.local",
        "http://intranet",
        "http://127.0.0.1",
        "http://10.0.0.5",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "http://169.254.169.254/latest/meta-data",
        "http://100.64.0.1",
        "http://0.0.0.0",
        "http://[::1]/",
        "http://[fd00::1]/",
        "http://224.0.0.1",
        "https://example.com:99999",
        "https://exa mple.com",
        "https://example.com/\x00",
        "https://" + "a" * 2050 + ".com",
    ],
)
def test_rejects_unsafe_or_malformed_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(application_name="X", website_url=url)


def test_blank_url_becomes_none() -> None:
    assert ResearchRequest(application_name="Linear", website_url="   ").website_url is None


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, "Line\x00ar", "Lin\near"])
def test_rejects_bad_names(name: str) -> None:
    with pytest.raises(ValidationError):
        ResearchRequest(application_name=name)


def test_name_is_trimmed() -> None:
    assert ResearchRequest(application_name="  Linear  ").application_name == "Linear"


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ResearchRequest.model_validate({"application_name": "Linear", "client_secret": "nope"})
