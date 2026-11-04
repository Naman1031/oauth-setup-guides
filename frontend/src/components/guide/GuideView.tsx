// The ONE component that renders any guide, pre-built or AI-generated.
// It only reads data from `guide`; there is no "if provider === 'github'"
// logic anywhere. That is what lets the library grow to 100+ apps.

import { EyeOff } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import type { GuideContent } from '@/types/guide'
import { GuideActions } from './GuideActions'
import { GuideChecklist } from './GuideChecklist'
import { SourceProvider } from './GuideParts'
import {
  AgentHumanSection,
  CommonIssuesSection,
  ComposioSection,
  CredentialsSection,
  OverviewSection,
  PrerequisitesSection,
  ScopesSection,
  SetupStepsSection,
  SourcesSection,
  TimeApprovalSection,
} from './GuideSections'

interface GuideViewProps {
  guide: GuideContent
  /** Unique per guide; used as the checklist's localStorage key. */
  guideKey: string
  /** The exact URL copied by "Share Guide". */
  shareUrl: string
  /** Generated guides are unlisted: we explain what that means. */
  isUnlisted: boolean
}

const tableOfContents = [
  ['overview', 'Overview'],
  ['prerequisites', 'Prerequisites'],
  ['setup', 'Setup'],
  ['scopes', 'Scopes'],
  ['credentials', 'Credentials'],
  ['time', 'Time & approval'],
  ['agent-human', 'Agent vs. human'],
  ['composio', 'Composio'],
  ['issues', 'Common issues'],
  ['sources', 'Sources'],
  ['checklist', 'Checklist'],
] as const

export function GuideView({ guide, guideKey, shareUrl, isUnlisted }: GuideViewProps) {
  return (
    <SourceProvider sources={guide.sources}>
      <article className="space-y-6">
        <header className="space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-sm text-muted-foreground">OAuth setup guide</p>
              <h1 className="text-3xl font-semibold tracking-tight">{guide.application_name}</h1>
            </div>
            <GuideActions guide={guide} shareUrl={shareUrl} />
          </div>

          {isUnlisted && (
            <Alert>
              <EyeOff />
              <AlertTitle>Unlisted, not private</AlertTitle>
              <AlertDescription>
                This guide is not shown in the directory, but anyone who has this URL can open it.
              </AlertDescription>
            </Alert>
          )}

          <nav aria-label="Guide sections" className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {tableOfContents.map(([id, label]) => (
              <a key={id} href={`#${id}`} className="text-muted-foreground hover:text-foreground">
                {label}
              </a>
            ))}
          </nav>
        </header>

        <OverviewSection guide={guide} />
        <PrerequisitesSection guide={guide} />
        <SetupStepsSection guide={guide} />
        <ScopesSection guide={guide} />
        <CredentialsSection guide={guide} />
        <TimeApprovalSection guide={guide} />
        <AgentHumanSection guide={guide} />
        <ComposioSection guide={guide} />
        <CommonIssuesSection guide={guide} />
        <SourcesSection guide={guide} />
        {/* key={guideKey}: a different guide gets a brand-new checklist component,
            so its saved ticks are loaded fresh instead of reusing old state. */}
        <GuideChecklist key={guideKey} guideKey={guideKey} items={guide.checklist_items} />
      </article>
    </SourceProvider>
  )
}
