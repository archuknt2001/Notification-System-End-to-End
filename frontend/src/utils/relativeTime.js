/**
 * Relative time formatter using date-fns.
 * Returns strings like "2 minutes ago", "just now", "3 days ago".
 */
import { formatDistanceToNowStrict, parseISO } from 'date-fns'

export function relativeTime(isoString) {
  if (!isoString) return ''
  try {
    const date = typeof isoString === 'string' ? parseISO(isoString) : isoString
    return formatDistanceToNowStrict(date, { addSuffix: true })
  } catch {
    return ''
  }
}
