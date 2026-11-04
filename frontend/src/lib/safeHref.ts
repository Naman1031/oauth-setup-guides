/**
 * Only allow http(s) links. Guide content may later come from an AI model,
 * and a `javascript:` URL in an <a href> would run code when clicked.
 * Returns the normalized URL, or undefined if it must not be linked.
 */
export function safeHref(url: string): string | undefined {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : undefined
  } catch {
    return undefined
  }
}
