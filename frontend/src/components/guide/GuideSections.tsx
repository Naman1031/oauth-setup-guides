// The ten content sections of a guide, in the order required by the spec.
// Each section receives the whole `guide` object and renders one part of it.
// Nothing here knows which provider it is showing: it is purely data-driven.

import type { ReactNode } from 'react'
import { Bot, KeyRound, ShieldCheck, User } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  complexityLabels,
  composioAvailabilityLabels,
  formatEffortRange,
  oauthStatusLabels,
  ownAppRequiredLabels,
  portalStatusLabels,
  reviewRequirementLabels,
  sourceTypeLabels,
} from '@/lib/guideLabels'
import type { EvidenceLabel, GuideContent, OAuthStatus } from '@/types/guide'
import { EmptyNote, EvidenceBadge, ExternalLink, GuideSection, MutedBadge, SourceRefs, SubHeading } from './GuideParts'

interface SectionProps {
  guide: GuideContent
}

// ---------- 1. Overview ----------

/** Explains non-"supported" outcomes so they are never mistaken for a normal guide. */
const statusExplanations: Record<Exclude<OAuthStatus, 'supported'>, string> = {
  not_supported: 'Reliable evidence indicates this application does not offer the relevant OAuth flow.',
  not_found: 'The research did not find credible evidence that this application supports OAuth.',
  inconclusive: 'Sources conflict or evidence is insufficient. Treat the details below with caution.',
}

export function OverviewSection({ guide }: SectionProps) {
  return (
    <GuideSection id="overview" number={1} title="Overview">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={guide.oauth_status === 'supported' ? 'default' : 'secondary'}>
          {oauthStatusLabels[guide.oauth_status]}
        </Badge>
        <MutedBadge>Complexity: {complexityLabels[guide.complexity]}</MutedBadge>
      </div>
      {guide.oauth_status !== 'supported' && (
        <Alert>
          <AlertTitle>{oauthStatusLabels[guide.oauth_status]}</AlertTitle>
          <AlertDescription>{statusExplanations[guide.oauth_status]}</AlertDescription>
        </Alert>
      )}
      <p>{guide.summary}</p>
      <div>
        <SubHeading>Why {complexityLabels[guide.complexity].toLowerCase()}?</SubHeading>
        <p className="mt-1 text-muted-foreground">{guide.complexity_rationale}</p>
      </div>
    </GuideSection>
  )
}

// ---------- 2. Prerequisites ----------

export function PrerequisitesSection({ guide }: SectionProps) {
  return (
    <GuideSection id="prerequisites" number={2} title="Prerequisites">
      {guide.prerequisites.length === 0 ? (
        <EmptyNote />
      ) : (
        <ul className="space-y-3">
          {guide.prerequisites.map((item) => (
            <li key={item.id}>
              <div className="flex flex-wrap items-center gap-2 font-medium">
                {item.title} <EvidenceBadge label={item.evidence_label} />
              </div>
              <p className="mt-1 text-muted-foreground">
                {item.description}
                <SourceRefs ids={item.source_ids} />
              </p>
            </li>
          ))}
        </ul>
      )}
    </GuideSection>
  )
}

// ---------- 3. Setup instructions ----------

export function SetupStepsSection({ guide }: SectionProps) {
  return (
    <GuideSection id="setup" number={3} title="Setup instructions">
      {guide.setup_steps.length === 0 ? (
        <EmptyNote>Not applicable – no setup steps could be established from reliable sources.</EmptyNote>
      ) : (
        <ol className="space-y-4">
          {guide.setup_steps.map((step, index) => (
            <li key={step.id} className="flex gap-3">
              <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-foreground">
                {index + 1}
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 font-medium">
                  {step.title}
                  <MutedBadge>
                    {step.responsibility === 'human' ? <User className="size-3" /> : <Bot className="size-3" />}
                    {step.responsibility === 'human' ? 'You' : 'Agent'}
                  </MutedBadge>
                  <EvidenceBadge label={step.evidence_label} />
                </div>
                <p className="mt-1 text-muted-foreground">
                  {step.description}
                  <SourceRefs ids={step.source_ids} />
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </GuideSection>
  )
}

// ---------- 4. Permissions and scopes ----------

export function ScopesSection({ guide }: SectionProps) {
  return (
    <GuideSection id="scopes" number={4} title="Permissions and scopes">
      {guide.permissions_scopes.length === 0 ? (
        <EmptyNote />
      ) : (
        <ul className="divide-y">
          {guide.permissions_scopes.map((scope) => (
            <li key={scope.name} className="py-3 first:pt-0 last:pb-0">
              <div className="flex flex-wrap items-center gap-2">
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs break-all">{scope.name}</code>
                <MutedBadge>{scope.is_conditional ? 'Conditional' : 'Commonly needed'}</MutedBadge>
                <EvidenceBadge label={scope.evidence_label} />
              </div>
              <p className="mt-1 text-muted-foreground">
                {scope.explanation}
                <SourceRefs ids={scope.source_ids} />
              </p>
              {scope.condition_note && (
                <p className="mt-1 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">When needed:</span> {scope.condition_note}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </GuideSection>
  )
}

// ---------- 5. Credentials and configuration ----------

export function CredentialsSection({ guide }: SectionProps) {
  return (
    <GuideSection id="credentials" number={5} title="Credentials and configuration">
      <Alert>
        <KeyRound />
        <AlertDescription>
          Never paste client secrets or tokens into this tool. Keep secrets in your own backend's environment variables.
        </AlertDescription>
      </Alert>
      {guide.credentials_configuration.length === 0 ? (
        <EmptyNote />
      ) : (
        <ul className="space-y-3">
          {guide.credentials_configuration.map((item) => (
            <li key={item.name}>
              <div className="flex flex-wrap items-center gap-2 font-medium">
                {item.name}
                {item.is_secret && (
                  <Badge variant="outline" className="border-rose-200 bg-rose-50 text-rose-800">
                    Secret
                  </Badge>
                )}
                <EvidenceBadge label={item.evidence_label} />
              </div>
              <p className="mt-1 text-muted-foreground">
                {item.description}
                <SourceRefs ids={item.source_ids} />
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">Where:</span> {item.where_obtained}
              </p>
            </li>
          ))}
        </ul>
      )}
    </GuideSection>
  )
}

// ---------- 6. Time and approval ----------

function InfoTile({ title, value, children }: { title: string; value: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border bg-muted/40 p-4">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">{title}</p>
      <p className="mt-1 text-base font-semibold">{value}</p>
      <div className="mt-2 space-y-2 text-xs text-muted-foreground">{children}</div>
    </div>
  )
}

// A provider-published timeframe is "Verified"; we never present our own guess as one.
const reviewWaitHeadline: Record<EvidenceLabel, string> = {
  verified: 'Published by provider',
  estimated: 'Estimated',
  unknown: 'Unknown',
}

export function TimeApprovalSection({ guide }: SectionProps) {
  const ta = guide.time_approval
  return (
    <GuideSection id="time" number={6} title="Time and approval">
      <div className="grid gap-3 md:grid-cols-3">
        <InfoTile title="Active setup effort" value={formatEffortRange(ta.active_effort_min_minutes, ta.active_effort_max_minutes)}>
          <EvidenceBadge label={ta.active_effort_label} />
          <p>{ta.active_effort_basis}</p>
        </InfoTile>
        <InfoTile title="Provider review" value={reviewRequirementLabels[ta.review_requirement]}>
          <p>
            {ta.review_requirement_explanation}
            <SourceRefs ids={ta.review_source_ids} />
          </p>
        </InfoTile>
        <InfoTile title="Review wait" value={reviewWaitHeadline[ta.review_wait.evidence_label]}>
          <EvidenceBadge label={ta.review_wait.evidence_label} />
          <p>
            {ta.review_wait.summary}
            <SourceRefs ids={ta.review_wait.source_ids} />
          </p>
        </InfoTile>
      </div>
      <p>
        <span className="font-medium">Total elapsed time: </span>
        <span className="text-muted-foreground">{ta.elapsed_time_note}</span>
      </p>
    </GuideSection>
  )
}

// ---------- 7. Agent vs. human tasks (+ portal exploration record) ----------

function TaskList({ items }: { items: string[] }) {
  if (items.length === 0) return <EmptyNote />
  return (
    <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  )
}

export function AgentHumanSection({ guide }: SectionProps) {
  const tasks = guide.agent_human_tasks
  const portal = guide.portal_exploration
  return (
    <GuideSection id="agent-human" number={7} title="Agent vs. human tasks">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border p-4">
          <SubHeading>
            <span className="inline-flex items-center gap-1.5">
              <Bot className="size-4" /> The research agent can
            </span>
          </SubHeading>
          <div className="mt-2">
            <TaskList items={tasks.agent_can_do} />
          </div>
        </div>
        <div className="rounded-lg border p-4">
          <SubHeading>
            <span className="inline-flex items-center gap-1.5">
              <User className="size-4" /> You (the developer) must
            </span>
          </SubHeading>
          <div className="mt-2">
            <TaskList items={tasks.human_must_do} />
          </div>
        </div>
      </div>

      <div className="space-y-3 rounded-lg border border-dashed p-4">
        <div className="flex flex-wrap items-center gap-2">
          <SubHeading>Portal exploration record</SubHeading>
          <MutedBadge>{portalStatusLabels[portal.status]}</MutedBadge>
        </div>
        <p className="text-xs text-muted-foreground">
          What was actually inspected on public, signed-out pages. Documentation research is listed separately under Sources.
          <SourceRefs ids={portal.source_ids} />
        </p>
        {portal.entry_point_url && (
          <p>
            <span className="font-medium">Setup entry point: </span>
            <ExternalLink href={portal.entry_point_url} className="break-all">
              {portal.entry_point_url}
            </ExternalLink>
          </p>
        )}
        <div>
          <p className="font-medium">Pages inspected</p>
          {portal.pages_inspected.length === 0 ? (
            <EmptyNote>None</EmptyNote>
          ) : (
            <ul className="mt-1 space-y-1 text-muted-foreground">
              {portal.pages_inspected.map((page) => (
                <li key={page.url}>
                  <ExternalLink href={page.url} className="break-all">
                    {page.url}
                  </ExternalLink>{' '}
                  – {page.observation}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <p className="font-medium">Safe actions attempted</p>
          <TaskList items={portal.safe_actions_attempted} />
        </div>
        <div>
          <p className="font-medium">Observations</p>
          <TaskList items={portal.observations} />
        </div>
        <div>
          <p className="font-medium">Could not be accessed</p>
          <TaskList items={portal.inaccessible_steps} />
        </div>
        <p>
          <span className="font-medium">Why exploration stopped: </span>
          <span className="text-muted-foreground">{portal.stop_reason}</span>
        </p>
        <p>
          <span className="font-medium">Sandbox / test mode: </span>
          <span className="text-muted-foreground">{portal.sandbox_or_test_mode}</span>
        </p>
        <Alert>
          <User />
          <AlertTitle>Your next step (human handoff)</AlertTitle>
          <AlertDescription>{portal.human_handoff}</AlertDescription>
        </Alert>
      </div>
    </GuideSection>
  )
}

// ---------- 8. Composio Managed OAuth ----------

export function ComposioSection({ guide }: SectionProps) {
  const composio = guide.composio_managed_oauth
  return (
    <GuideSection id="composio" number={8} title="Composio Managed OAuth">
      <div className="flex flex-wrap items-center gap-2">
        <MutedBadge>Availability: {composioAvailabilityLabels[composio.availability]}</MutedBadge>
        <EvidenceBadge label={composio.evidence_label} />
      </div>
      <p>
        <span className="font-medium">Own OAuth app required? </span>
        <span className="text-muted-foreground">{ownAppRequiredLabels[composio.own_app_required]}</span>
      </p>
      <p className="text-muted-foreground">
        {composio.explanation}
        <SourceRefs ids={composio.source_ids} />
      </p>
      <div>
        <SubHeading>When bringing your own OAuth app may be appropriate</SubHeading>
        <div className="mt-2">
          <TaskList items={composio.when_to_bring_own_app} />
        </div>
      </div>
    </GuideSection>
  )
}

// ---------- 9. Common issues ----------

export function CommonIssuesSection({ guide }: SectionProps) {
  return (
    <GuideSection id="issues" number={9} title="Common issues">
      {guide.common_issues.length === 0 ? (
        <EmptyNote>Unknown – no documented issues were found.</EmptyNote>
      ) : (
        <ul className="divide-y">
          {guide.common_issues.map((issue) => (
            <li key={issue.issue} className="py-3 first:pt-0 last:pb-0">
              <p className="font-medium">
                <code className="font-mono text-xs">{issue.issue}</code>
              </p>
              <p className="mt-1 text-muted-foreground">{issue.explanation}</p>
              <p className="mt-1">
                <span className="font-medium">Fix: </span>
                <span className="text-muted-foreground">{issue.resolution}</span>
                <SourceRefs ids={issue.source_ids} />
              </p>
            </li>
          ))}
        </ul>
      )}
    </GuideSection>
  )
}

// ---------- 10. Sources and reliability ----------

export function SourcesSection({ guide }: SectionProps) {
  const tested = guide.tested_status
  return (
    <GuideSection id="sources" number={10} title="Sources and reliability">
      <div className="flex flex-wrap items-center gap-2">
        <MutedBadge>Last researched: {guide.last_researched_at}</MutedBadge>
        <Badge variant="outline" className={tested.status === 'tested' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-slate-200 bg-slate-100 text-slate-700'}>
          <ShieldCheck className="size-3" />
          {tested.status === 'tested' ? 'Tested' : 'Not tested'}
        </Badge>
      </div>
      <p className="text-muted-foreground">{tested.notes}</p>

      <div>
        <SubHeading>Sources</SubHeading>
        <ol className="mt-2 space-y-2">
          {guide.sources.map((source, index) => (
            <li key={source.id} className="flex gap-2">
              <span className="w-6 shrink-0 text-right text-muted-foreground">[{index + 1}]</span>
              <div className="min-w-0">
                <ExternalLink href={source.url}>{source.title}</ExternalLink>
                <p className="text-xs break-all text-muted-foreground">
                  {source.domain} · {sourceTypeLabels[source.source_type]} · accessed {source.accessed_at}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div>
        <SubHeading>Evidence notes</SubHeading>
        {guide.evidence_notes.length === 0 ? (
          <EmptyNote>None</EmptyNote>
        ) : (
          <ul className="mt-2 space-y-2">
            {guide.evidence_notes.map((note) => (
              <li key={note.claim} className="flex flex-wrap items-start gap-2">
                <EvidenceBadge label={note.evidence_label} />
                {note.verification_basis && <MutedBadge>{note.verification_basis}-based</MutedBadge>}
                <span className="min-w-0 flex-1 text-muted-foreground">
                  {note.claim}
                  <SourceRefs ids={note.source_ids} />
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </GuideSection>
  )
}
