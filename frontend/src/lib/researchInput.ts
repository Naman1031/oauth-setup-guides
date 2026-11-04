// Client-side checks for the research form.
//
// IMPORTANT: this is only for quick feedback in the browser. Anyone can
// bypass frontend code, so the backend (Phase 3) repeats these checks
// with Pydantic and is the real security boundary.

export const MAX_APP_NAME_LENGTH = 100
export const MAX_URL_LENGTH = 2048

export interface ResearchInputErrors {
  applicationName?: string
  websiteUrl?: string
}

// Hostnames that always point at the user's own machine or local network.
const LOCAL_HOSTNAMES = new Set(['localhost', 'localhost.localdomain', '0.0.0.0', '[::1]', '::1'])

/** Rough IPv4 private/reserved check (10.x, 127.x, 169.254.x, 172.16–31.x, 192.168.x, 0.x, 100.64–127.x). */
function isPrivateIPv4(hostname: string): boolean {
  const match = hostname.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/)
  if (!match) return false
  const [a, b] = [Number(match[1]), Number(match[2])]
  return (
    a === 0 ||
    a === 10 ||
    a === 127 ||
    (a === 100 && b >= 64 && b <= 127) ||
    (a === 169 && b === 254) ||
    (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) ||
    a >= 224
  )
}

export function validateResearchInput(applicationName: string, websiteUrl: string): ResearchInputErrors {
  const errors: ResearchInputErrors = {}
  const name = applicationName.trim()

  if (name.length === 0) {
    errors.applicationName = 'Enter an application name.'
  } else if (name.length > MAX_APP_NAME_LENGTH) {
    errors.applicationName = `Keep the name under ${MAX_APP_NAME_LENGTH} characters.`
  }

  const urlText = websiteUrl.trim()
  if (urlText.length === 0) return errors // optional field

  if (urlText.length > MAX_URL_LENGTH) {
    errors.websiteUrl = 'That URL is too long.'
    return errors
  }

  let url: URL
  try {
    url = new URL(urlText)
  } catch {
    errors.websiteUrl = 'Enter a full URL starting with https:// or http://.'
    return errors
  }

  const hostname = url.hostname.toLowerCase()
  if (url.protocol !== 'https:' && url.protocol !== 'http:') {
    errors.websiteUrl = 'Only http:// and https:// URLs are accepted.'
  } else if (url.username || url.password) {
    errors.websiteUrl = 'URLs must not contain a username or password.'
  } else if (LOCAL_HOSTNAMES.has(hostname) || hostname.endsWith('.localhost') || hostname.endsWith('.local')) {
    errors.websiteUrl = 'Local addresses are not accepted. Use the public website.'
  } else if (isPrivateIPv4(hostname)) {
    errors.websiteUrl = 'Private or reserved IP addresses are not accepted.'
  } else if (hostname.startsWith('[')) {
    // A bracketed host is an IPv6 literal. Classifying those correctly is
    // left to the backend; the form simply asks for a domain instead.
    errors.websiteUrl = 'IPv6 addresses are not accepted. Use the public website domain.'
  } else if (!hostname.includes('.')) {
    errors.websiteUrl = 'Enter a public domain, e.g. https://example.com.'
  }

  return errors
}
