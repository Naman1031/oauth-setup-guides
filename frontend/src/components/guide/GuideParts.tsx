// Small, reusable pieces used by every guide section.

import { createContext, useContext, type ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'
import { evidenceLabels } from '@/lib/guideLabels'
import { safeHref } from '@/lib/safeHref'
import { cn } from '@/lib/utils'
import type { EvidenceLabel, Source } from '@/types/guide'

// ---------- Safe links ----------

export function ExternalLink({ href, children, className }: { href: string; children: ReactNode; className?: string }) {
  const safe = safeHref(href)
  if (!safe) return <span className={className}>{children}</span>
  return (
    // rel="noopener noreferrer": the new tab can't control this page or see where it came from.
    <a href={safe} target="_blank" rel="noopener noreferrer" className={cn('text-primary underline-offset-4 hover:underline', className)}>
      {children}
    </a>
  )
}

// ---------- Source citations ----------

/** The guide's sources, numbered 1..n, shared with every section via React context. */
interface NumberedSource {
  number: number
  source: Source
}
const SourceContext = createContext<Map<string, NumberedSource>>(new Map())

export function SourceProvider({ sources, children }: { sources: Source[]; children: ReactNode }) {
  const byId = new Map(sources.map((source, index) => [source.id, { number: index + 1, source }]))
  return <SourceContext.Provider value={byId}>{children}</SourceContext.Provider>
}

/** Renders citations like [1][4], each linking to the source page. */
export function SourceRefs({ ids }: { ids: string[] }) {
  const byId = useContext(SourceContext)
  if (ids.length === 0) return null
  return (
    <span className="ml-1 inline-flex flex-wrap gap-0.5 align-baseline text-xs">
      {ids.map((id) => {
        const entry = byId.get(id)
        if (!entry) return <span key={id} className="text-muted-foreground">[?]</span>
        return (
          <ExternalLink key={id} href={entry.source.url} className="font-medium">
            <span title={entry.source.title}>[{entry.number}]</span>
          </ExternalLink>
        )
      })}
    </span>
  )
}

// ---------- Badges ----------

const evidenceStyles: Record<EvidenceLabel, string> = {
  verified: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  estimated: 'border-amber-200 bg-amber-50 text-amber-800',
  unknown: 'border-slate-200 bg-slate-100 text-slate-700',
}

export function EvidenceBadge({ label }: { label: EvidenceLabel }) {
  return (
    <Badge variant="outline" className={evidenceStyles[label]}>
      {evidenceLabels[label]}
    </Badge>
  )
}

export function MutedBadge({ children }: { children: ReactNode }) {
  return (
    <Badge variant="outline" className="border-border bg-muted text-muted-foreground">
      {children}
    </Badge>
  )
}

// ---------- Layout ----------

export function GuideSection({ id, number, title, children }: { id: string; number?: number; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 rounded-xl border bg-card p-5 sm:p-6">
      <h2 className="mb-4 text-lg font-semibold tracking-tight">
        {number !== undefined && <span className="mr-2 text-muted-foreground">{number}.</span>}
        {title}
      </h2>
      <div className="space-y-4 text-sm leading-relaxed">{children}</div>
    </section>
  )
}

/** Shown instead of silently hiding a section that has no data. */
export function EmptyNote({ children = 'Not applicable' }: { children?: ReactNode }) {
  return <p className="text-muted-foreground italic">{children}</p>
}

export function SubHeading({ children }: { children: ReactNode }) {
  return <h3 className="text-sm font-semibold text-foreground">{children}</h3>
}
