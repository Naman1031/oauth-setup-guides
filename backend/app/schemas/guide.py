"""The shared guide content schema.

ONE model for both pre-built (applications.guide_content) and AI-generated
(generated_guides.guide_content) guides. It mirrors
frontend/src/types/guide.ts field for field.

Besides types, it enforces rules a type system can't express on its own:
every citation must point to a real source, Verified claims must say how
they were verified, and so on. Anything that fails validation is never
saved to the database.
"""

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, TypeAdapter, model_validator

# ---------- Reusable field types ----------

_http_url_adapter = TypeAdapter(HttpUrl)


def _validate_http_url(value: str) -> str:
    # Parse with Pydantic's HttpUrl (http/https only, valid host), but keep the
    # ORIGINAL string so source URLs are preserved exactly as researched.
    _http_url_adapter.validate_python(value)
    return value


HttpUrlStr = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048), AfterValidator(_validate_http_url)]

# Bounded strings keep stored guides (and, in Phase 3, model output) a sane size.
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,63}$")]
SourceIds = Annotated[list[Identifier], Field(max_length=20)]


# ---------- Controlled values ----------
# StrEnum members ARE strings, so they serialize to plain JSON strings.


class OAuthStatus(StrEnum):
    SUPPORTED = "supported"
    NOT_SUPPORTED = "not_supported"
    NOT_FOUND = "not_found"
    INCONCLUSIVE = "inconclusive"


class Complexity(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    COMPLEX = "complex"


class EvidenceLabel(StrEnum):
    VERIFIED = "verified"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class VerificationBasis(StrEnum):
    DOCUMENTATION = "documentation"
    TEST = "test"


class Responsibility(StrEnum):
    HUMAN = "human"
    AGENT = "agent"


class ReviewRequirement(StrEnum):
    REQUIRED = "required"
    CONDITIONAL = "conditional"
    NOT_GENERALLY_REQUIRED = "not_generally_required"
    UNKNOWN = "unknown"


class ComposioAvailability(StrEnum):
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class OwnAppRequired(StrEnum):
    NO = "no"
    YES = "yes"
    CONDITIONAL = "conditional"
    UNKNOWN = "unknown"


class PortalExplorationStatus(StrEnum):
    EXPLORED = "explored"
    PARTIALLY_EXPLORED = "partially_explored"
    NOT_ACCESSIBLE = "not_accessible"
    NOT_ATTEMPTED = "not_attempted"


class SourceType(StrEnum):
    OFFICIAL_PROVIDER_DOCS = "official_provider_docs"
    OFFICIAL_PROVIDER_SUPPORT = "official_provider_support"
    OFFICIAL_PROVIDER_PORTAL = "official_provider_portal"
    OFFICIAL_COMPOSIO_DOCS = "official_composio_docs"
    COMMUNITY = "community"
    OTHER = "other"


class TestedStatusValue(StrEnum):
    TESTED = "tested"
    NOT_TESTED = "not_tested"


# ---------- Building blocks ----------


class StrictModel(BaseModel):
    # extra="forbid": unknown fields are an error, not silently ignored.
    model_config = ConfigDict(extra="forbid")


class Source(StrictModel):
    id: Identifier
    title: ShortText
    url: HttpUrlStr
    domain: ShortText
    source_type: SourceType
    accessed_at: date


class Prerequisite(StrictModel):
    id: Identifier
    title: ShortText
    description: Text
    evidence_label: EvidenceLabel
    source_ids: SourceIds


class SetupStep(StrictModel):
    id: Identifier
    title: ShortText
    description: Text
    responsibility: Responsibility
    evidence_label: EvidenceLabel
    source_ids: SourceIds


class PermissionScope(StrictModel):
    name: ShortText
    explanation: Text
    is_conditional: bool
    condition_note: Text | None
    evidence_label: EvidenceLabel
    source_ids: SourceIds

    @model_validator(mode="after")
    def _conditional_needs_note(self) -> "PermissionScope":
        if self.is_conditional and not self.condition_note:
            raise ValueError(f"scope {self.name!r} is conditional but has no condition_note")
        return self


class CredentialConfigItem(StrictModel):
    name: ShortText
    description: Text
    where_obtained: Text
    is_secret: bool
    evidence_label: EvidenceLabel
    source_ids: SourceIds


class ReviewWait(StrictModel):
    evidence_label: EvidenceLabel
    summary: Text
    source_ids: SourceIds

    @model_validator(mode="after")
    def _verified_needs_source(self) -> "ReviewWait":
        # A "Verified" wait time must come from a cited, published source.
        if self.evidence_label == EvidenceLabel.VERIFIED and not self.source_ids:
            raise ValueError("a Verified review wait must cite at least one source")
        return self


class TimeApproval(StrictModel):
    active_effort_min_minutes: Annotated[int, Field(ge=0, le=60 * 24 * 30)]
    active_effort_max_minutes: Annotated[int, Field(ge=0, le=60 * 24 * 30)]
    active_effort_label: EvidenceLabel
    active_effort_basis: Text
    review_requirement: ReviewRequirement
    review_requirement_explanation: Text
    review_source_ids: SourceIds
    review_wait: ReviewWait
    elapsed_time_note: Text

    @model_validator(mode="after")
    def _range_is_ordered(self) -> "TimeApproval":
        if self.active_effort_min_minutes > self.active_effort_max_minutes:
            raise ValueError("active_effort_min_minutes must not exceed active_effort_max_minutes")
        return self


class AgentHumanTasks(StrictModel):
    agent_can_do: Annotated[list[Text], Field(max_length=20)]
    human_must_do: Annotated[list[Text], Field(max_length=20)]


class PortalPageInspected(StrictModel):
    url: HttpUrlStr
    observation: Text


class PortalExploration(StrictModel):
    status: PortalExplorationStatus
    entry_point_url: HttpUrlStr | None
    pages_inspected: Annotated[list[PortalPageInspected], Field(max_length=20)]
    safe_actions_attempted: Annotated[list[Text], Field(max_length=20)]
    observations: Annotated[list[Text], Field(max_length=20)]
    inaccessible_steps: Annotated[list[Text], Field(max_length=20)]
    stop_reason: Text
    human_handoff: Text
    sandbox_or_test_mode: Text
    source_ids: SourceIds

    @model_validator(mode="after")
    def _explored_needs_pages(self) -> "PortalExploration":
        # Can't claim hands-on exploration without listing what was inspected.
        if self.status in (PortalExplorationStatus.EXPLORED, PortalExplorationStatus.PARTIALLY_EXPLORED) and not self.pages_inspected:
            raise ValueError(f"portal status {self.status.value!r} requires at least one inspected page")
        return self


class ComposioManagedOAuth(StrictModel):
    availability: ComposioAvailability
    own_app_required: OwnAppRequired
    explanation: Text
    when_to_bring_own_app: Annotated[list[Text], Field(max_length=20)]
    evidence_label: EvidenceLabel
    source_ids: SourceIds


class CommonIssue(StrictModel):
    issue: ShortText
    explanation: Text
    resolution: Text
    source_ids: SourceIds


class EvidenceNote(StrictModel):
    claim: Text
    evidence_label: EvidenceLabel
    verification_basis: VerificationBasis | None
    source_ids: SourceIds

    @model_validator(mode="after")
    def _basis_only_for_verified(self) -> "EvidenceNote":
        is_verified = self.evidence_label == EvidenceLabel.VERIFIED
        if is_verified and self.verification_basis is None:
            raise ValueError(f"verified claim needs a verification_basis: {self.claim[:60]!r}")
        if not is_verified and self.verification_basis is not None:
            raise ValueError(f"only verified claims may have a verification_basis: {self.claim[:60]!r}")
        return self


class TestedStatus(StrictModel):
    status: TestedStatusValue
    notes: Text


class ChecklistItem(StrictModel):
    id: Identifier
    label: ShortText
    source_ids: SourceIds


# ---------- The guide ----------


class GuideContent(StrictModel):
    schema_version: Literal[1]
    application_name: ShortText
    website_url: HttpUrlStr | None
    oauth_status: OAuthStatus
    summary: Text
    complexity: Complexity
    complexity_rationale: Text
    prerequisites: Annotated[list[Prerequisite], Field(max_length=30)]
    setup_steps: Annotated[list[SetupStep], Field(max_length=40)]
    permissions_scopes: Annotated[list[PermissionScope], Field(max_length=50)]
    credentials_configuration: Annotated[list[CredentialConfigItem], Field(max_length=30)]
    time_approval: TimeApproval
    agent_human_tasks: AgentHumanTasks
    portal_exploration: PortalExploration
    composio_managed_oauth: ComposioManagedOAuth
    common_issues: Annotated[list[CommonIssue], Field(max_length=30)]
    sources: Annotated[list[Source], Field(max_length=50)]
    evidence_notes: Annotated[list[EvidenceNote], Field(max_length=50)]
    tested_status: TestedStatus
    last_researched_at: date
    checklist_items: Annotated[list[ChecklistItem], Field(max_length=40)]

    @model_validator(mode="after")
    def _check_cross_references(self) -> "GuideContent":
        """Rules that span several sections of the guide."""
        source_ids = [source.id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source ids must be unique")

        for label, items in (
            ("prerequisite", self.prerequisites),
            ("setup step", self.setup_steps),
            ("checklist item", self.checklist_items),
        ):
            ids = [item.id for item in items]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{label} ids must be unique")

        # Every citation anywhere in the guide must point at a listed source.
        known = set(source_ids)
        for location, ids in self._all_citations():
            unknown = [source_id for source_id in ids if source_id not in known]
            if unknown:
                raise ValueError(f"{location} cites unknown source id(s): {', '.join(unknown)}")

        # Only an actual test may mark the guide "tested", and vice versa.
        any_test_based = any(note.verification_basis == VerificationBasis.TEST for note in self.evidence_notes)
        if any_test_based and self.tested_status.status != TestedStatusValue.TESTED:
            raise ValueError("test-based evidence requires tested_status 'tested'")

        return self

    def _all_citations(self) -> list[tuple[str, list[str]]]:
        citations: list[tuple[str, list[str]]] = []
        citations += [(f"prerequisite {p.id}", p.source_ids) for p in self.prerequisites]
        citations += [(f"setup step {s.id}", s.source_ids) for s in self.setup_steps]
        citations += [(f"scope {s.name}", s.source_ids) for s in self.permissions_scopes]
        citations += [(f"credential {c.name}", c.source_ids) for c in self.credentials_configuration]
        citations += [
            ("time_approval.review_source_ids", self.time_approval.review_source_ids),
            ("time_approval.review_wait", self.time_approval.review_wait.source_ids),
            ("portal_exploration", self.portal_exploration.source_ids),
            ("composio_managed_oauth", self.composio_managed_oauth.source_ids),
        ]
        citations += [(f"common issue {i.issue}", i.source_ids) for i in self.common_issues]
        citations += [("evidence note", n.source_ids) for n in self.evidence_notes]
        citations += [(f"checklist item {c.id}", c.source_ids) for c in self.checklist_items]
        return citations
