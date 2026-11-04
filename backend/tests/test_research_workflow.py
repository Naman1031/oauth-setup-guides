"""The research workflow end to end, with a fake OpenAI client (no cost)."""

import copy
import json
from contextlib import nullcontext

import httpx2
import openai
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import GeneratedGuide
from app.schemas.research import ErrorCode
from app.services.research.openai_runner import ResearchError
from app.services.research.workflow import run_research

from .conftest import requires_db
from .fake_openai import FakeClient, FakeResponses, message, refusal_message, search_call, successful_client

pytestmark = requires_db

INPUT = {"application_name": "Example App", "website_url": "https://example.com"}


def notion_guide() -> dict:
    path = get_settings().seed_data_dir / "notion.json"
    return copy.deepcopy(json.loads(path.read_text(encoding="utf-8"))["guide_content"])


def urls(guide: dict) -> list[str]:
    return [s["url"] for s in guide["sources"]]


def configured_settings():
    return get_settings().model_copy(update={"openai_api_key": "sk-test", "openai_model": "test-model"})


def run(db: Session, client: FakeClient, raw_input: dict = INPUT) -> list[tuple[str, dict]]:
    return list(run_research(raw_input, configured_settings(), lambda _settings: client, lambda: nullcontext(db)))


def saved_count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(GeneratedGuide))


def progress_states(events: list[tuple[str, dict]]) -> list[str]:
    return [f"{p['stage']}:{p['state']}" for name, p in events if name == "progress"]


def test_happy_path_streams_all_stages_in_order_and_saves(db: Session) -> None:
    guide = notion_guide()
    events = run(db, successful_client(guide, consulted=urls(guide)))

    assert progress_states(events) == [
        "validating_input:started", "validating_input:completed",
        "searching_documentation:started", "searching_documentation:completed",
        "analysing_requirements:started", "analysing_requirements:completed",
        "validating_guide:started", "validating_guide:completed",
        "saving_result:started", "saving_result:completed",
    ]
    assert ("activity", {"web_searches_completed": 1}) in events
    name, payload = events[-1]
    assert name == "complete"
    assert payload["guide_path"] == f"/guides/{payload['public_id']}"
    assert payload["result_type"] == "oauth_supported"

    row = db.scalar(select(GeneratedGuide).where(GeneratedGuide.public_id == payload["public_id"]))
    assert row.application_name == "Example App"
    assert row.submitted_website_url == "https://example.com"
    assert row.guide_content["tested_status"]["status"] == "not_tested"


def test_request_enforces_cost_controls(db: Session) -> None:
    guide = notion_guide()
    client = successful_client(guide, consulted=urls(guide))
    run(db, client)
    call = client.responses.calls[0]
    settings = configured_settings()
    assert call["tool_choice"] == "required"
    assert call["tools"] == [{"type": "web_search", "search_context_size": settings.openai_search_context_size}]
    assert call["max_tool_calls"] == settings.openai_max_tool_calls
    assert call["max_output_tokens"] == settings.openai_max_output_tokens
    assert call["store"] is False
    assert call["include"] == ["web_search_call.action.sources"]
    assert call["text"]["format"]["strict"] is True
    assert '"Example App"' in call["input"]  # user input passed as JSON data


def last_error(events: list[tuple[str, dict]]) -> dict:
    name, payload = events[-1]
    assert name == "error", events[-1]
    return payload


def test_invalid_input_stops_before_any_openai_call(db: Session) -> None:
    client = successful_client(notion_guide(), consulted=[])
    events = run(db, client, {"application_name": "X", "website_url": "http://169.254.169.254/"})
    assert last_error(events)["code"] == "invalid_input"
    assert client.responses.calls == []
    assert saved_count(db) == 0


def test_not_configured_without_key(db: Session) -> None:
    from app.services.research.openai_runner import make_openai_client

    settings = get_settings().model_copy(update={"openai_api_key": None, "openai_model": None})
    events = list(run_research(INPUT, settings, make_openai_client, lambda: nullcontext(db)))
    assert last_error(events)["code"] == "not_configured"


@pytest.mark.parametrize(
    ("client_kwargs", "expected"),
    [
        ({"output_override": [search_call("q", []), refusal_message()]}, "refused"),
        ({"status": "incomplete", "incomplete_reason": "max_output_tokens"}, "incomplete"),
        ({"status": "incomplete", "incomplete_reason": "content_filter"}, "refused"),
        ({"output_override": [search_call("q", []), message("not json at all")]}, "invalid_result"),
        ({"output_override": [message("{}")]}, "invalid_result"),  # no web search performed
        ({"output_override": [search_call("q", []), message(json.dumps({"oauth_status": "supported"}))]}, "invalid_result"),
    ],
    ids=["refusal", "max_tokens", "content_filter", "bad_json", "no_search", "schema_invalid"],
)
def test_failures_never_save(db: Session, client_kwargs: dict, expected: str) -> None:
    guide = notion_guide()
    events = run(db, successful_client(guide, consulted=urls(guide), **client_kwargs))
    assert last_error(events)["code"] == expected
    assert saved_count(db) == 0


def test_all_sources_unconfirmed_is_not_saved(db: Session) -> None:
    guide = notion_guide()
    events = run(db, successful_client(guide, consulted=["https://unrelated.example/page"]))
    assert last_error(events)["code"] == "invalid_result"
    assert saved_count(db) == 0


def test_honest_not_found_result_is_saved(db: Session) -> None:
    guide = notion_guide()
    guide.update(oauth_status="not_found", setup_steps=[], permissions_scopes=[], checklist_items=[])
    events = run(db, successful_client(guide, consulted=urls(guide)))
    assert events[-1][0] == "complete"
    assert events[-1][1]["result_type"] == "support_not_found"


def _status_error(cls, status: int, body: dict):
    response = httpx2.Response(status, request=httpx2.Request("POST", "https://api.openai.com/v1/responses"))
    return cls("error", response=response, body=body)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_status_error(openai.RateLimitError, 429, {"code": "insufficient_quota"}), "budget_exhausted"),
        (_status_error(openai.RateLimitError, 429, {"code": "project_spend_limit_exceeded"}), "budget_exhausted"),
        (_status_error(openai.RateLimitError, 429, {"code": "rate_limit_exceeded"}), "provider_rate_limited"),
        (_status_error(openai.AuthenticationError, 401, {}), "not_configured"),
        (_status_error(openai.InternalServerError, 500, {}), "provider_unavailable"),
        (openai.APITimeoutError(request=httpx2.Request("POST", "https://api.openai.com/v1/responses")), "timeout"),
    ],
    ids=["quota", "spend_limit", "rate_limit", "auth", "server_error", "timeout"],
)
def test_openai_errors_map_to_safe_codes(db: Session, error: Exception, expected: str) -> None:
    events = run(db, FakeClient(FakeResponses(error=error)))
    payload = last_error(events)
    assert payload["code"] == expected
    assert "sk-" not in json.dumps(events)
    assert saved_count(db) == 0


def test_error_payload_says_whether_retry_makes_sense(db: Session) -> None:
    events = run(db, FakeClient(FakeResponses(error=_status_error(openai.RateLimitError, 429, {"code": "insufficient_quota"}))))
    assert last_error(events)["retryable"] is False
    events = run(db, FakeClient(FakeResponses(error=_status_error(openai.InternalServerError, 500, {}))))
    assert last_error(events)["retryable"] is True


def test_research_error_detail_is_not_sent_to_client(db: Session) -> None:
    class ExplodingResponses(FakeResponses):
        def stream(self, **kwargs):
            raise ResearchError(ErrorCode.INTERNAL_ERROR, "secret internal detail")

    events = run(db, FakeClient(ExplodingResponses()))
    assert "secret internal detail" not in json.dumps(events)
