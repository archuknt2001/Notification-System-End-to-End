/**
 * useNotifications — convenience hook.
 *
 * Re-exports the context with a derived `filteredNotifications` list
 * that applies the current filter (type + unreadOnly) client-side.
 * This keeps filtering logic out of components.
 */

import { useMemo } from 'react'
import { useNotificationContext } from '../context/NotificationContext'

export function useNotifications() {
  const ctx = useNotificationContext()

  const filteredNotifications = useMemo(() => {
    let list = ctx.notifications
    if (ctx.filter.unreadOnly) {
      list = list.filter(n => !n.read)
    }
    if (ctx.filter.type) {
      list = list.filter(n => n.type === ctx.filter.type)
    }
    return list
  }, [ctx.notifications, ctx.filter])

  return { ...ctx, filteredNotifications }
}
