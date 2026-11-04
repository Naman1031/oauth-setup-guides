import { useParams } from 'react-router'
import { WORKING_TITLE } from '@/components/AppLayout'
import { GuideView } from '@/components/guide/GuideView'
import { useGuide } from '@/hooks/useGuide'
import { getGeneratedGuide } from '@/services/guideService'
import { NotFoundPage } from './NotFoundPage'

/** Unlisted AI-generated guide at /guides/:publicId */
export function GeneratedGuidePage() {
  const { publicId = '' } = useParams()
  const state = useGuide(publicId, getGeneratedGuide)

  return (
    <>
      {/* React 19 moves <meta> into <head>. This asks search engines not to index
          unlisted guides. Phase 4 adds an X-Robots-Tag header as well, because
          not every crawler runs JavaScript. */}
      <meta name="robots" content="noindex, nofollow" />
      {state.kind === 'loading' && <p className="text-sm text-muted-foreground">Loading guide…</p>}
      {state.kind === 'not-found' && <NotFoundPage message="This guide does not exist, or the link is incomplete." />}
      {state.kind === 'error' && <p className="text-sm text-destructive">The guide could not be loaded. Try refreshing the page.</p>}
      {state.kind === 'loaded' && (
        <>
          <title>{`${state.guide.application_name} OAuth setup · ${WORKING_TITLE}`}</title>
          <GuideView
            guide={state.guide}
            guideKey={`generated:${publicId}`}
            shareUrl={`${window.location.origin}/guides/${publicId}`}
            isUnlisted={true}
          />
        </>
      )}
    </>
  )
}
