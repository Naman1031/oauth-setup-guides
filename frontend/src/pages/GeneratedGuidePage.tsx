import { useParams } from 'react-router'
import { WORKING_TITLE } from '@/components/AppLayout'
import { GuideView } from '@/components/guide/GuideView'
import { LoadError, LoadingNote } from '@/components/LoadingStates'
import { useGuide } from '@/hooks/useGuide'
import { getGeneratedGuide } from '@/services/guideService'
import { NotFoundPage } from './NotFoundPage'

/** Unlisted AI-generated guide at /guides/:publicId */
export function GeneratedGuidePage() {
  const { publicId = '' } = useParams()
  const { state, retry } = useGuide(publicId, getGeneratedGuide)

  return (
    <>
      {/* React 19 moves <meta> into <head>. This asks search engines not to index
          unlisted guides. vercel.json also sends an X-Robots-Tag header for
          /guides/*, because not every crawler runs JavaScript. */}
      <meta name="robots" content="noindex, nofollow" />
      {state.kind === 'loading' && <LoadingNote label="Loading guide…" />}
      {state.kind === 'not-found' && <NotFoundPage message="This guide does not exist, or the link is incomplete." />}
      {state.kind === 'error' && <LoadError message="The guide could not be loaded." onRetry={retry} />}
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
