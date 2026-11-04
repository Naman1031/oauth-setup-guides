// Starts a research run and reads its Server-Sent Events stream.
//
// The browser's built-in EventSource only supports GET, but we must POST the
// form data, so we read the streamed `fetch` response body ourselves.

import { API_BASE_URL } from '@/services/guideService'

export type StageKey =
  | 'validating_input'
  | 'searching_documentation'
  | 'analysing_requirements'
  | 'validating_guide'
  | 'saving_result'

export type ResearchEvent =
  | { event: 'progress'; data: { stage: StageKey; label: string; state: 'started' | 'completed' } }
  | { event: 'activity'; data: { web_searches_completed: number } }
  | { event: 'complete'; data: { public_id: string; guide_path: string; result_type: string; application_name: string } }
  | { event: 'error'; data: { code: string; message: string; retryable: boolean } }

/** A failure before or outside the stream (HTTP error, network, disconnect). */
export class ResearchRequestError extends Error {
  readonly retryable: boolean
  constructor(message: string, retryable: boolean) {
    super(message)
    this.retryable = retryable
  }
}

/** Parse one SSE block ("event: x\ndata: {...}") into a typed event, or null if malformed. */
function parseBlock(block: string): ResearchEvent | null {
  let event = ''
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7).trim()
    else if (line.startsWith('data: ')) data += line.slice(6)
  }
  if (!event || !data) return null
  try {
    return { event, data: JSON.parse(data) } as ResearchEvent
  } catch {
    return null
  }
}

export async function streamResearch(
  input: { application_name: string; website_url: string | null },
  onEvent: (event: ResearchEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}/api/research/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify(input),
      signal,
    })
  } catch (error) {
    if (signal.aborted) throw error
    throw new ResearchRequestError('Could not reach the server.', true)
  }

  if (!response.ok || !response.body) {
    // Errors before streaming (e.g. 429 rate limit) use the API's JSON error shape.
    let message = `Request failed (${response.status}).`
    try {
      const body = (await response.json()) as { error?: { message?: string } }
      if (body.error?.message) message = body.error.message
    } catch {
      // keep the generic message
    }
    throw new ResearchRequestError(message, response.status === 429 || response.status >= 500)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finished = false

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      // Network chunks can split an event anywhere, so buffer until a blank line.
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
      let boundary = buffer.indexOf('\n\n')
      while (boundary !== -1) {
        const parsed = parseBlock(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        if (parsed) {
          onEvent(parsed)
          if (parsed.event === 'complete' || parsed.event === 'error') finished = true
        }
        boundary = buffer.indexOf('\n\n')
      }
    }
  } catch (error) {
    if (signal.aborted) throw error
    throw new ResearchRequestError('The connection was interrupted.', true)
  }

  // The backend always ends with `complete` or `error`; anything else means the
  // connection dropped. We never treat that as success.
  if (!finished) throw new ResearchRequestError('The connection closed before research finished.', true)
}
