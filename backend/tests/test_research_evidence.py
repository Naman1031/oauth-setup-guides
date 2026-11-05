"""Evidence reconciliation: the model's claims vs. what the API says happened."""

import copy
import json
from datetime import date

from app.core.config import get_settings
from app.schemas.guide import GuideContent
from app.services.research.evidence import check_useful, extract_trace, normalize_url, presanitize, reconcile
from app.services.research.output_schema import guide_json_schema

from .fake_openai import message, open_page_call, search_call

TODAY = date(2026, 11, 5)


def github_guide() -> dict:
    path = get_settings().seed_data_dir / "github.json"
    return copy.deepcopy(json.loads(path.read_text(encoding="utf-8"))["guide_content"])


def all_urls(guide: dict) -> list[str]:
    return [s["url"] for s in guide["sources"]]


def test_normalize_url() -> None:
    assert normalize_url("HTTPS://Docs.GitHub.com/en/apps/?utm_source=openai#frag") == "https://docs.github.com/en/apps"
    assert normalize_url("https://a.com/x?b=1&utm_medium=x") == "https://a.com/x?b=1"


def test_extract_trace_reads_actions() -> None:
    trace = extract_trace([search_call("q1", ["https://a.com/1"]), open_page_call("https://b.com/p"), message("{}")])
    assert trace.web_search_calls == 2
    assert trace.search_queries == ["q1"]
    assert trace.opened_pages == ["https://b.com/p"]
    assert trace.consulted_urls == {"https://a.com/1", "https://b.com/p"}


def test_repeated_actions_are_listed_once() -> None:
    # Seen in the first live run: the model opened the same page twice.
    trace = extract_trace([search_call("q", []), search_call("q", []), open_page_call("https://b.com/p"), open_page_call("https://b.com/p")])
    assert trace.search_queries == ["q"]
    assert trace.opened_pages == ["https://b.com/p"]
    assert trace.web_search_calls == 4  # still counts every (billed) call


def test_unconsulted_source_is_dropped_and_claims_downgraded() -> None:
    raw = github_guide()
    consulted = [u for u in all_urls(raw) if "troubleshooting" not in u]  # pretend 2 pages were never seen
    trace = extract_trace([search_call("github oauth", consulted)])
    guide, report = reconcile(GuideContent.model_validate(raw), trace, "GitHub", TODAY)

    assert len(report.dropped_sources) == 2
    kept_ids = {s.id for s in guide.sources}
    assert "gh-trouble-token" not in kept_ids
    issue = next(i for i in guide.common_issues if i.issue == "incorrect_client_credentials")
    assert issue.source_ids == []  # its only source was dropped


def test_verified_claim_without_remaining_source_becomes_unknown() -> None:
    raw = github_guide()
    raw["evidence_notes"].append({"claim": "Made-up fact.", "evidence_label": "verified", "verification_basis": "documentation", "source_ids": ["gh-trouble-auth"]})
    consulted = [u for u in all_urls(raw) if "troubleshooting-authorization" not in u]
    guide, report = reconcile(GuideContent.model_validate(raw), extract_trace([search_call("q", consulted)]), "GitHub", TODAY)
    note = next(n for n in guide.evidence_notes if n.claim == "Made-up fact.")
    assert note.evidence_label == "unknown" and note.verification_basis is None
    assert report.downgraded_claims >= 1


def test_portal_pages_must_have_been_opened() -> None:
    raw = github_guide()  # claims it inspected github.com/settings/applications/new
    trace = extract_trace([search_call("q", all_urls(raw))])  # ...but never opened it
    guide, report = reconcile(GuideContent.model_validate(raw), trace, "GitHub", TODAY)
    assert guide.portal_exploration.status == "not_attempted"
    assert guide.portal_exploration.pages_inspected == []
    assert report.portal_downgraded
    assert guide.portal_exploration.safe_actions_attempted == ["Web search: “q”"]


def test_opened_portal_page_is_kept() -> None:
    raw = github_guide()
    portal = "https://github.com/settings/applications/new"
    trace = extract_trace([search_call("q", all_urls(raw)), open_page_call(portal)])
    guide, _ = reconcile(GuideContent.model_validate(raw), trace, "GitHub", TODAY)
    assert guide.portal_exploration.status == "not_accessible"
    assert [p.url for p in guide.portal_exploration.pages_inspected] == [portal]
    assert f"Opened public page: {portal}" in guide.portal_exploration.safe_actions_attempted


def test_backend_owned_fields_are_overwritten() -> None:
    raw = github_guide()
    raw["sources"][0]["domain"] = "not-the-real-domain.example"
    raw["sources"][0]["accessed_at"] = "2001-01-01"
    guide, _ = reconcile(GuideContent.model_validate(raw), extract_trace([search_call("q", all_urls(raw))]), "My App", TODAY)
    assert guide.sources[0].domain == "docs.github.com"
    assert guide.sources[0].accessed_at == TODAY
    assert guide.application_name == "My App"
    assert guide.last_researched_at == TODAY
    assert guide.tested_status.status == "not_tested"


def test_presanitize_removes_test_claims() -> None:
    raw = github_guide()
    raw["evidence_notes"][0]["verification_basis"] = "test"
    raw["tested_status"]["status"] = "tested"
    GuideContent.model_validate(presanitize(raw))  # would raise without presanitize
    assert raw["evidence_notes"][0]["verification_basis"] == "documentation"


def test_check_useful() -> None:
    guide = GuideContent.model_validate(github_guide())
    assert check_useful(guide) is None
    assert check_useful(guide.model_copy(update={"sources": []})) is not None
    assert check_useful(guide.model_copy(update={"setup_steps": []})) is not None


def test_model_schema_is_strict_and_has_no_length_keywords() -> None:
    schema = json.dumps(guide_json_schema())
    assert "maxLength" not in schema and "minLength" not in schema
    root = guide_json_schema()
    assert root["additionalProperties"] is False
    assert set(root["required"]) == set(root["properties"])


def test_portal_note_distinguishes_documentation_pages_from_no_pages() -> None:
    # Seen in the Craigslist live run: an API doc page was opened, but no portal page.
    raw = github_guide()
    with_doc_page = extract_trace([search_call("q", all_urls(raw)), open_page_call("https://docs.github.com/en/apps")])
    guide, _ = reconcile(GuideContent.model_validate(raw), with_doc_page, "GitHub", TODAY)
    assert "were documentation, not a setup portal" in guide.portal_exploration.observations[0]

    search_only = extract_trace([search_call("q", all_urls(raw))])
    guide, _ = reconcile(GuideContent.model_validate(github_guide()), search_only, "GitHub", TODAY)
    assert "did not open any page directly" in guide.portal_exploration.observations[0]


def test_prompt_defines_supported_as_delegated_user_authorization() -> None:
    # Product decision (2026-11-05): own-account-only access (client_credentials, API keys) is "not_supported".
    from app.services.research.prompt import INSTRUCTIONS

    assert "END USERS must connect their own accounts" in INSTRUCTIONS
    assert "client_credentials grant using" in INSTRUCTIONS and '"not_supported"' in INSTRUCTIONS
