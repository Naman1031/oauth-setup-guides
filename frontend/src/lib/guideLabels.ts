// Human-readable text for the schema's controlled values.
// `Record<K, string>` forces us to provide a label for EVERY enum value:
// if a new value is added to the type, TypeScript flags this file.

import type {
  ComposioAvailability,
  Complexity,
  EvidenceLabel,
  OAuthStatus,
  OwnAppRequired,
  PortalExplorationStatus,
  ReviewRequirement,
  SourceType,
} from '@/types/guide'

export const oauthStatusLabels: Record<OAuthStatus, string> = {
  supported: 'OAuth supported',
  not_supported: 'OAuth not supported',
  not_found: 'OAuth support not found',
  inconclusive: 'Research inconclusive',
}

export const complexityLabels: Record<Complexity, string> = {
  easy: 'Easy',
  medium: 'Medium',
  complex: 'Complex',
}

export const evidenceLabels: Record<EvidenceLabel, string> = {
  verified: 'Verified',
  estimated: 'Estimated',
  unknown: 'Unknown',
}

export const reviewRequirementLabels: Record<ReviewRequirement, string> = {
  required: 'Required',
  conditional: 'Conditional',
  not_generally_required: 'Not generally required',
  unknown: 'Unknown',
}

export const composioAvailabilityLabels: Record<ComposioAvailability, string> = {
  available: 'Available',
  not_available: 'Not available',
  conditional: 'Conditional',
  unknown: 'Unknown',
}

export const ownAppRequiredLabels: Record<OwnAppRequired, string> = {
  no: 'No – managed OAuth can be used',
  yes: 'Yes – register your own OAuth app',
  conditional: 'Depends on your use case',
  unknown: 'Unknown',
}

export const portalStatusLabels: Record<PortalExplorationStatus, string> = {
  explored: 'Portal explored',
  partially_explored: 'Portal partially explored',
  not_accessible: 'Portal not accessible',
  not_attempted: 'Portal exploration not attempted',
}

export const sourceTypeLabels: Record<SourceType, string> = {
  official_provider_docs: 'Official docs',
  official_provider_support: 'Official support',
  official_provider_portal: 'Official portal page',
  official_composio_docs: 'Official Composio docs',
  community: 'Community (non-official)',
  other: 'Other (non-official)',
}

/** "10–30 min" or "1–3 h" depending on size. */
export function formatEffortRange(minMinutes: number, maxMinutes: number): string {
  if (maxMinutes < 120) return `${minMinutes}–${maxMinutes} min`
  const toHours = (minutes: number) => Math.round((minutes / 60) * 10) / 10
  return `${toHours(minMinutes)}–${toHours(maxMinutes)} h`
}
