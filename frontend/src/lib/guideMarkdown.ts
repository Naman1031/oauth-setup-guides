// Turns a guide into clean Markdown for the "Copy Guide" button.
// It is a pure function (same input → same output, no side effects),
// which makes it easy to test and reason about.

import type { GuideContent, Source } from '@/types/guide'
import {
  complexityLabels,
  composioAvailabilityLabels,
  evidenceLabels,
  formatEffortRange,
  oauthStatusLabels,
  ownAppRequiredLabels,
  portalStatusLabels,
  reviewRequirementLabels,
  sourceTypeLabels,
} from '@/lib/guideLabels'

export function guideToMarkdown(guide: GuideContent, shareUrl: string): string {
  // Map each source ID to its 1-based position so citations read like [1], [3].
  const sourceNumber = new Map<string, number>()
  guide.sources.forEach((source, index) => sourceNumber.set(source.id, index + 1))
  const cite = (ids: string[]) =>
    ids.length === 0 ? '' : ' ' + ids.map((id) => `[${sourceNumber.get(id) ?? '?'}]`).join('')

  const lines: string[] = []
  const add = (...text: string[]) => lines.push(...text)
  const ta = guide.time_approval
  const portal = guide.portal_exploration
  const composio = guide.composio_managed_oauth

  add(`# ${guide.application_name} – OAuth setup guide`, '')
  add(`Guide URL: ${shareUrl}`)
  add(`Last researched: ${guide.last_researched_at} · Tested: ${guide.tested_status.status === 'tested' ? 'Tested' : 'Not tested'}`, '')

  add('## 1. Overview', '')
  add(`- Status: ${oauthStatusLabels[guide.oauth_status]}`)
  add(`- Complexity: ${complexityLabels[guide.complexity]} – ${guide.complexity_rationale}`, '')
  add(guide.summary, '')

  add('## 2. Prerequisites', '')
  guide.prerequisites.forEach((item) =>
    add(`- **${item.title}** (${evidenceLabels[item.evidence_label]}): ${item.description}${cite(item.source_ids)}`),
  )
  add('')

  add('## 3. Setup instructions', '')
  guide.setup_steps.forEach((step, index) =>
    add(
      `${index + 1}. **${step.title}** – ${step.responsibility === 'human' ? 'Human' : 'Agent'} · ${evidenceLabels[step.evidence_label]}`,
      `   ${step.description}${cite(step.source_ids)}`,
    ),
  )
  add('')

  add('## 4. Permissions and scopes', '')
  guide.permissions_scopes.forEach((scope) =>
    add(
      `- \`${scope.name}\` (${scope.is_conditional ? 'Conditional' : 'Commonly needed'} · ${evidenceLabels[scope.evidence_label]}): ${scope.explanation}` +
        (scope.condition_note ? ` When: ${scope.condition_note}` : '') +
        cite(scope.source_ids),
    ),
  )
  add('')

  add('## 5. Credentials and configuration', '')
  guide.credentials_configuration.forEach((item) =>
    add(
      `- **${item.name}**${item.is_secret ? ' (secret – keep on your backend)' : ''}: ${item.description} Where: ${item.where_obtained}${cite(item.source_ids)}`,
    ),
  )
  add('')

  add('## 6. Time and approval', '')
  add(`- Active setup effort: ${formatEffortRange(ta.active_effort_min_minutes, ta.active_effort_max_minutes)} (${evidenceLabels[ta.active_effort_label]}) – ${ta.active_effort_basis}`)
  add(`- Provider review: ${reviewRequirementLabels[ta.review_requirement]} – ${ta.review_requirement_explanation}${cite(ta.review_source_ids)}`)
  add(`- Review wait (${evidenceLabels[ta.review_wait.evidence_label]}): ${ta.review_wait.summary}${cite(ta.review_wait.source_ids)}`)
  add(`- Total elapsed time: ${ta.elapsed_time_note}`, '')

  add('## 7. Agent vs. human tasks', '')
  add('**The research agent can:**')
  guide.agent_human_tasks.agent_can_do.forEach((task) => add(`- ${task}`))
  add('', '**The human developer must:**')
  guide.agent_human_tasks.human_must_do.forEach((task) => add(`- ${task}`))
  add('', `**Portal exploration:** ${portalStatusLabels[portal.status]}`)
  portal.pages_inspected.forEach((page) => add(`- Inspected ${page.url}: ${page.observation}`))
  add(`- Stopped because: ${portal.stop_reason}`)
  add(`- Human handoff: ${portal.human_handoff}`)
  add(`- Sandbox / test mode: ${portal.sandbox_or_test_mode}`, '')

  add('## 8. Composio Managed OAuth', '')
  add(`- Availability: ${composioAvailabilityLabels[composio.availability]} (${evidenceLabels[composio.evidence_label]})${cite(composio.source_ids)}`)
  add(`- Own OAuth app required: ${ownAppRequiredLabels[composio.own_app_required]}`)
  add(`- ${composio.explanation}`)
  composio.when_to_bring_own_app.forEach((reason) => add(`- Bring your own app when: ${reason}`))
  add('')

  add('## 9. Common issues', '')
  guide.common_issues.forEach((issue) =>
    add(`- **${issue.issue}**: ${issue.explanation} Fix: ${issue.resolution}${cite(issue.source_ids)}`),
  )
  add('')

  add('## 10. Sources and reliability', '')
  guide.sources.forEach((source: Source, index) =>
    add(`${index + 1}. ${source.title} – ${source.url} (${sourceTypeLabels[source.source_type]}, accessed ${source.accessed_at})`),
  )
  add('', '**Evidence notes:**')
  guide.evidence_notes.forEach((note) =>
    add(
      `- ${evidenceLabels[note.evidence_label]}${note.verification_basis ? ` (${note.verification_basis}-based)` : ''}: ${note.claim}${cite(note.source_ids)}`,
    ),
  )
  add('', `Tested status: ${guide.tested_status.status === 'tested' ? 'Tested' : 'Not tested'} – ${guide.tested_status.notes}`, '')

  add('## Checklist', '')
  guide.checklist_items.forEach((item) => add(`- [ ] ${item.label}`))

  return lines.join('\n')
}
