// The shared guide content schema.
//
// Every guide (the six hand-researched ones AND the AI-generated ones)
// has exactly this shape. In Phase 2 the backend defines the same shape
// as a Pydantic model and stores it in a JSONB column. Keeping one shape
// is what lets a single <GuideView> component render any application
// without provider-specific code.

// ---------- Controlled values ("enums") ----------
// TypeScript union types restrict a string to a fixed set of values.
// If you write `oauth_status: "yes"` the compiler will reject it.

export type OAuthStatus = 'supported' | 'not_supported' | 'not_found' | 'inconclusive'

export type Complexity = 'easy' | 'medium' | 'complex'

export type EvidenceLabel = 'verified' | 'estimated' | 'unknown'

/** For a Verified claim: was it confirmed by reading docs, or by an actual test? */
export type VerificationBasis = 'documentation' | 'test'

export type Responsibility = 'human' | 'agent'

export type ReviewRequirement = 'required' | 'conditional' | 'not_generally_required' | 'unknown'

export type ComposioAvailability = 'available' | 'not_available' | 'conditional' | 'unknown'

export type OwnAppRequired = 'no' | 'yes' | 'conditional' | 'unknown'

export type PortalExplorationStatus =
  | 'explored'
  | 'partially_explored'
  | 'not_accessible'
  | 'not_attempted'

export type SourceType =
  | 'official_provider_docs'
  | 'official_provider_support'
  | 'official_provider_portal'
  | 'official_composio_docs'
  | 'community'
  | 'other'

export type TestedStatusValue = 'tested' | 'not_tested'

// ---------- Building blocks ----------

/** A cited page. Other items point at sources by `id` instead of repeating URLs. */
export interface Source {
  id: string
  title: string
  url: string
  domain: string
  source_type: SourceType
  accessed_at: string // ISO date, e.g. "2026-11-04"
}

export interface Prerequisite {
  id: string
  title: string
  description: string
  evidence_label: EvidenceLabel
  source_ids: string[]
}

export interface SetupStep {
  id: string
  title: string
  description: string
  responsibility: Responsibility
  evidence_label: EvidenceLabel
  source_ids: string[]
}

export interface PermissionScope {
  name: string
  explanation: string
  is_conditional: boolean
  /** When is it needed? Required if `is_conditional` is true. */
  condition_note: string | null
  evidence_label: EvidenceLabel
  source_ids: string[]
}

export interface CredentialConfigItem {
  name: string
  description: string
  where_obtained: string
  /** True for values that must never be exposed (e.g. a client secret). */
  is_secret: boolean
  evidence_label: EvidenceLabel
  source_ids: string[]
}

export interface ReviewWait {
  /** Verified only when an official source publishes a timeframe. */
  evidence_label: EvidenceLabel
  summary: string
  source_ids: string[]
}

export interface TimeApproval {
  active_effort_min_minutes: number
  active_effort_max_minutes: number
  active_effort_label: EvidenceLabel
  active_effort_basis: string
  review_requirement: ReviewRequirement
  review_requirement_explanation: string
  review_source_ids: string[]
  review_wait: ReviewWait
  elapsed_time_note: string
}

export interface AgentHumanTasks {
  agent_can_do: string[]
  human_must_do: string[]
}

export interface PortalPageInspected {
  url: string
  observation: string
}

export interface PortalExploration {
  status: PortalExplorationStatus
  entry_point_url: string | null
  pages_inspected: PortalPageInspected[]
  safe_actions_attempted: string[]
  observations: string[]
  inaccessible_steps: string[]
  stop_reason: string
  human_handoff: string
  sandbox_or_test_mode: string
  source_ids: string[]
}

export interface ComposioManagedOAuth {
  availability: ComposioAvailability
  own_app_required: OwnAppRequired
  explanation: string
  when_to_bring_own_app: string[]
  evidence_label: EvidenceLabel
  source_ids: string[]
}

export interface CommonIssue {
  issue: string
  explanation: string
  resolution: string
  source_ids: string[]
}

export interface EvidenceNote {
  claim: string
  evidence_label: EvidenceLabel
  /** Only set when evidence_label is "verified". */
  verification_basis: VerificationBasis | null
  source_ids: string[]
}

export interface TestedStatus {
  status: TestedStatusValue
  notes: string
}

export interface ChecklistItem {
  /** Stable ID: used as the localStorage key, so it must not change between edits. */
  id: string
  label: string
  source_ids: string[]
}

// ---------- The guide itself ----------

export interface GuideContent {
  schema_version: 1
  application_name: string
  website_url: string | null
  oauth_status: OAuthStatus
  summary: string
  complexity: Complexity
  complexity_rationale: string
  prerequisites: Prerequisite[]
  setup_steps: SetupStep[]
  permissions_scopes: PermissionScope[]
  credentials_configuration: CredentialConfigItem[]
  time_approval: TimeApproval
  agent_human_tasks: AgentHumanTasks
  portal_exploration: PortalExploration
  composio_managed_oauth: ComposioManagedOAuth
  common_issues: CommonIssue[]
  sources: Source[]
  evidence_notes: EvidenceNote[]
  tested_status: TestedStatus
  last_researched_at: string // ISO date
  checklist_items: ChecklistItem[]
}

// ---------- Directory records ----------

/** What a directory card needs (matches the future GET /api/applications item). */
export interface ApplicationSummary {
  slug: string
  name: string
  category: string
  short_description: string
  complexity: Complexity
}

/**
 * One seed file = one row of the future `applications` table:
 * relational columns at the top level, guide sections inside `guide_content`.
 */
export interface ApplicationRecord {
  slug: string
  name: string
  category: string
  short_description: string
  guide_content: GuideContent
}
