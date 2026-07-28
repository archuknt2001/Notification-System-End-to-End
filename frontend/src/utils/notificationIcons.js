/**
 * Maps notification type strings to emoji icons and Tailwind colour classes.
 */

const TYPE_META = {
  member_invited:     { icon: '👥', color: 'text-blue-500',   bg: 'bg-blue-50' },
  new_reply:          { icon: '💬', color: 'text-purple-500', bg: 'bg-purple-50' },
  report_ready:       { icon: '📊', color: 'text-teal-500',   bg: 'bg-teal-50' },
  campaign_started:   { icon: '🚀', color: 'text-green-500',  bg: 'bg-green-50' },
  campaign_completed: { icon: '✅', color: 'text-green-600',  bg: 'bg-green-50' },
  payment_received:   { icon: '💰', color: 'text-emerald-500',bg: 'bg-emerald-50' },
  invoice_due:        { icon: '🧾', color: 'text-orange-500', bg: 'bg-orange-50' },
  warning:            { icon: '⚠️', color: 'text-yellow-600', bg: 'bg-yellow-50' },
  success:            { icon: '🎉', color: 'text-green-500',  bg: 'bg-green-50' },
  system_alert:       { icon: '🔔', color: 'text-red-500',    bg: 'bg-red-50' },
  error:              { icon: '❌', color: 'text-red-600',    bg: 'bg-red-50' },
}

const DEFAULT_META = { icon: '📣', color: 'text-gray-500', bg: 'bg-gray-50' }

export function getTypeMeta(type) {
  return TYPE_META[type] ?? DEFAULT_META
}

export const ALL_TYPES = Object.keys(TYPE_META)
