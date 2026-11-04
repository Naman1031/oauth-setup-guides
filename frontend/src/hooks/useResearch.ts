// State for one research run, driven ONLY by events the backend sends.
// There are no timers here: a stage changes when its event arrives.

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { ResearchRequestError, streamResearch, type ResearchEvent, type StageKey } from '@/services/researchService'

export type StageState = 'pending' | 'started' | 'completed' | 'failed'

export const STAGES: { key: StageKey; label: string }[] = [
  { key: 'validating_input', label: 'Validating the application input' },
  { key: 'searching_documentation', label: 'Searching official documentation' },
  { key: 'analysing_requirements', label: 'Analysing OAuth setup requirements' },
  { key: 'validating_guide', label: 'Validating the guide and its evidence' },
  { key: 'saving_result', label: 'Saving the completed result' },
]

const initialStages = (): Record<StageKey, StageState> =>
  Object.fromEntries(STAGES.map((stage) => [stage.key, 'pending'])) as Record<StageKey, StageState>

export interface ResearchState {
  status: 'idle' | 'running' | 'failed'
  stages: Record<StageKey, StageState>
  webSearches: number
  error: { message: string; retryable: boolean } | null
}

export function useResearch() {
  const navigate = useNavigate()
  const [state, setState] = useState<ResearchState>({ status: 'idle', stages: initialStages(), webSearches: 0, error: null })
  const abortRef = useRef<AbortController | null>(null)

  // Leaving the page cancels the request (the backend then stops streaming).
  useEffect(() => () => abortRef.current?.abort(), [])

  function handleEvent(event: ResearchEvent) {
    if (event.event === 'progress') {
      setState((s) => ({ ...s, stages: { ...s.stages, [event.data.stage]: event.data.state } }))
    } else if (event.event === 'activity') {
      setState((s) => ({ ...s, webSearches: event.data.web_searches_completed }))
    } else if (event.event === 'complete') {
      navigate(event.data.guide_path)
    } else if (event.event === 'error') {
      fail(event.data.message, event.data.retryable)
    }
  }

  function fail(message: string, retryable: boolean) {
    setState((s) => {
      // Mark whichever stage was in progress as failed.
      const stages = { ...s.stages }
      for (const stage of STAGES) if (stages[stage.key] === 'started') stages[stage.key] = 'failed'
      return { ...s, status: 'failed', stages, error: { message, retryable } }
    })
  }

  async function start(applicationName: string, websiteUrl: string) {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    setState({ status: 'running', stages: initialStages(), webSearches: 0, error: null })
    try {
      await streamResearch(
        { application_name: applicationName.trim(), website_url: websiteUrl.trim() || null },
        handleEvent,
        controller.signal,
      )
    } catch (error) {
      if (controller.signal.aborted) return
      if (error instanceof ResearchRequestError) fail(error.message, error.retryable)
      else fail('Something went wrong. Please try again.', true)
    }
  }

  function reset() {
    abortRef.current?.abort()
    setState({ status: 'idle', stages: initialStages(), webSearches: 0, error: null })
  }

  return { state, start, reset }
}
