import { Link, useParams } from 'react-router'
import { WORKING_TITLE } from '@/components/AppLayout'
import { GuideView } from '@/components/guide/GuideView'
import { useGuide } from '@/hooks/useGuide'
import { getApplicationGuide } from '@/services/guideService'
import { NotFoundPage } from './NotFoundPage'

/** Pre-built directory guide at /apps/:slug */
export function ApplicationGuidePage() {
  const { slug = '' } = useParams() // the ":slug" part of the URL
  const state = useGuide(slug, getApplicationGuide)

  if (state.kind === 'loading') return <p className="text-sm text-muted-foreground">Loading guide…</p>
  if (state.kind === 'not-found') return <NotFoundPage message="There is no guide for this application." />
  if (state.kind === 'error') return <p className="text-sm text-destructive">The guide could not be loaded. Try refreshing the page.</p>

  return (
    <>
      <title>{`${state.guide.application_name} OAuth setup · ${WORKING_TITLE}`}</title>
      <Link to="/" className="mb-6 inline-block text-sm text-muted-foreground hover:text-foreground">
        ← All applications
      </Link>
      <GuideView
        guide={state.guide}
        guideKey={`app:${slug}`}
        shareUrl={`${window.location.origin}/apps/${slug}`}
        isUnlisted={false}
      />
    </>
  )
}
