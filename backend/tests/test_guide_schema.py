"""Schema tests: no database needed."""

import copy
import json
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.api import ResultType
from app.schemas.guide import GuideContent, OAuthStatus
from app.services.seeding import SeedRecord

SEED_FILES = sorted(get_settings().seed_data_dir.glob("*.json"))


def load_guide(slug: str = "github") -> dict[str, Any]:
    path = get_settings().seed_data_dir / f"{slug}.json"
    return copy.deepcopy(json.loads(path.read_text(encoding="utf-8"))["guide_content"])


def test_there_are_six_seed_files() -> None:
    assert {path.stem for path in SEED_FILES} == {"github", "slack", "google-drive", "notion", "hubspot", "discord"}


@pytest.mark.parametrize("path", SEED_FILES, ids=lambda p: p.stem)
def test_every_seed_file_is_valid(path) -> None:
    SeedRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.parametrize("path", SEED_FILES, ids=lambda p: p.stem)
def test_round_trip_preserves_content_exactly(path) -> None:
    # What we store in JSONB must equal the researched file: no URL rewriting, no dropped fields.
    original = json.loads(path.read_text(encoding="utf-8"))["guide_content"]
    assert GuideContent.model_validate(original).model_dump(mode="json") == original


def expect_invalid(guide: dict[str, Any], message_part: str) -> None:
    with pytest.raises(ValidationError) as excinfo:
        GuideContent.model_validate(guide)
    assert message_part in str(excinfo.value)


def test_rejects_citation_to_unknown_source() -> None:
    guide = load_guide()
    guide["setup_steps"][0]["source_ids"] = ["does-not-exist"]
    expect_invalid(guide, "unknown source id")


def test_rejects_duplicate_source_ids() -> None:
    guide = load_guide()
    guide["sources"].append(copy.deepcopy(guide["sources"][0]))
    expect_invalid(guide, "source ids must be unique")


def test_verified_claim_needs_basis() -> None:
    guide = load_guide()
    guide["evidence_notes"][0].update(evidence_label="verified", verification_basis=None)
    expect_invalid(guide, "needs a verification_basis")


def test_unverified_claim_must_not_have_basis() -> None:
    guide = load_guide()
    guide["evidence_notes"][0].update(evidence_label="estimated", verification_basis="documentation")
    expect_invalid(guide, "only verified claims")


def test_conditional_scope_needs_condition_note() -> None:
    guide = load_guide()
    scope = next(s for s in guide["permissions_scopes"] if s["is_conditional"])
    scope["condition_note"] = None
    expect_invalid(guide, "has no condition_note")


@pytest.mark.parametrize("bad_url", ["javascript:alert(1)", "ftp://example.com/file", "not a url", "https://"])
def test_rejects_non_http_urls(bad_url: str) -> None:
    guide = load_guide()
    guide["sources"][0]["url"] = bad_url
    with pytest.raises(ValidationError):
        GuideContent.model_validate(guide)


def test_rejects_unknown_fields() -> None:
    guide = load_guide()
    guide["client_secret"] = "should never be accepted"
    expect_invalid(guide, "Extra inputs are not permitted")


def test_rejects_invalid_enum_value() -> None:
    guide = load_guide()
    guide["oauth_status"] = "probably"
    with pytest.raises(ValidationError):
        GuideContent.model_validate(guide)


def test_rejects_reversed_effort_range() -> None:
    guide = load_guide()
    guide["time_approval"].update(active_effort_min_minutes=60, active_effort_max_minutes=10)
    expect_invalid(guide, "must not exceed")


def test_verified_review_wait_needs_a_source() -> None:
    guide = load_guide()
    guide["time_approval"]["review_wait"].update(evidence_label="verified", source_ids=[])
    expect_invalid(guide, "must cite at least one source")


def test_explored_portal_must_list_pages() -> None:
    guide = load_guide()
    guide["portal_exploration"].update(status="explored", pages_inspected=[])
    expect_invalid(guide, "requires at least one inspected page")


def test_test_based_evidence_requires_tested_status() -> None:
    guide = load_guide()
    guide["evidence_notes"][0].update(evidence_label="verified", verification_basis="test")
    guide["tested_status"]["status"] = "not_tested"
    expect_invalid(guide, "test-based evidence")


def test_rejects_overlong_text() -> None:
    guide = load_guide()
    guide["summary"] = "x" * 5000
    with pytest.raises(ValidationError):
        GuideContent.model_validate(guide)


def test_schema_can_represent_non_supported_outcomes() -> None:
    # An honest "not found" result with no setup steps is still a valid guide.
    guide = load_guide()
    guide.update(oauth_status="not_found", setup_steps=[], permissions_scopes=[], checklist_items=[])
    assert GuideContent.model_validate(guide).oauth_status == OAuthStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (OAuthStatus.SUPPORTED, ResultType.OAUTH_SUPPORTED),
        (OAuthStatus.NOT_SUPPORTED, ResultType.OAUTH_NOT_SUPPORTED),
        (OAuthStatus.NOT_FOUND, ResultType.SUPPORT_NOT_FOUND),
        (OAuthStatus.INCONCLUSIVE, ResultType.INCONCLUSIVE),
    ],
)
def test_result_type_mapping(status: OAuthStatus, expected: ResultType) -> None:
    assert ResultType.from_oauth_status(status) == expected
