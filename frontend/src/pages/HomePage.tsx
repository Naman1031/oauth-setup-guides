import { useEffect, useState } from 'react'
import { Search } from 'lucide-react'
import { ApplicationCard } from '@/components/ApplicationCard'
import { ResearchForm } from '@/components/ResearchForm'
import { WORKING_TITLE } from '@/components/AppLayout'
import { Input } from '@/components/ui/input'
import { listApplications } from '@/services/guideService'
import type { ApplicationSummary } from '@/types/guide'

export function HomePage() {
  const [applications, setApplications] = useState<ApplicationSummary[] | null>(null)
  const [loadFailed, setLoadFailed] = useState(false)
  const [query, setQuery] = useState('')

  // Load the directory once when the page first appears.
  useEffect(() => {
    let cancelled = false // ignore the result if the user already left the page
    listApplications()
      .then((result) => {
        if (!cancelled) setApplications(result)
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  // Derived data: recomputed on every render from state, never stored separately.
  const normalizedQuery = query.trim().toLowerCase()
  const visibleApplications = (applications ?? []).filter((app) => app.name.toLowerCase().includes(normalizedQuery))

  return (
    <div className="space-y-12">
      <title>{WORKING_TITLE}</title>

      <section className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Understand OAuth setup before you integrate</h1>
        <p className="max-w-2xl text-muted-foreground">
          Source-backed guides that separate your active setup work from provider review time, and show what you must
          do yourself versus what research can tell you.
        </p>
      </section>

      <section aria-labelledby="explore-heading" className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 id="explore-heading" className="text-xl font-semibold tracking-tight">
            Explore applications
          </h2>
          <div className="relative sm:w-72">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by name"
              aria-label="Search applications by name"
              className="pl-8"
            />
          </div>
        </div>

        {loadFailed && <p className="text-sm text-destructive">The application directory could not be loaded.</p>}
        {applications === null && !loadFailed && <p className="text-sm text-muted-foreground">Loading applications…</p>}
        {applications !== null && visibleApplications.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No application matches “{query.trim()}”. You can research it below.
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visibleApplications.map((app) => (
            <ApplicationCard key={app.slug} app={app} />
          ))}
        </div>
      </section>

      <section aria-labelledby="research-heading" className="space-y-4 rounded-xl border bg-card p-5 sm:p-6">
        <div className="space-y-1">
          <h2 id="research-heading" className="text-xl font-semibold tracking-tight">
            Research a new application
          </h2>
          <p className="text-sm text-muted-foreground">
            Generate a guide for an application that isn't in the directory yet.
          </p>
        </div>
        <ResearchForm />
      </section>
    </div>
  )
}
