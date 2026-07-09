/**
 * NotificationDrawer — slide-in panel showing the notification list.
 *
 * Features:
 *  - Loading skeleton (3 cards) on initial load
 *  - Empty state with illustration
 *  - Notification cards with read/unread styling
 *  - Mark All Read button
 *  - Load More button (pagination)
 *  - Filter bar (type + unread toggle)
 *  - Click outside to close
 */

import React, { useEffect, useRef } from 'react'
import { useNotifications } from '../hooks/useNotifications'
import NotificationCard from './NotificationCard'
import SkeletonCard from './SkeletonCard'
import FilterBar from './FilterBar'

export default function NotificationDrawer({ isOpen, onClose }) {
  const {
    filteredNotifications,
    unreadCount,
    meta,
    loading,
    refreshing,
    markOneRead,
    markAllRead,
    loadMore,
    refresh,
  } = useNotifications()

  const drawerRef = useRef(null)

  // Close on Escape
  useEffect(() => {
    const handleKey = (e) => { if (e.key === 'Escape') onClose() }
    if (isOpen) document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [isOpen, onClose])

  // Click outside to close
  useEffect(() => {
    const handleClick = (e) => {
      if (drawerRef.current && !drawerRef.current.contains(e.target)) {
        onClose()
      }
    }
    if (isOpen) {
      // Defer so the click that opened the drawer doesn't also close it
      const t = setTimeout(() => document.addEventListener('mousedown', handleClick), 0)
      return () => { clearTimeout(t); document.removeEventListener('mousedown', handleClick) }
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      ref={drawerRef}
      role="dialog"
      aria-label="Notifications"
      aria-modal="true"
      className="
        absolute top-14 right-4 z-50
        w-[380px] max-h-[80vh]
        bg-white rounded-xl shadow-2xl border border-gray-200
        flex flex-col overflow-hidden
        animate-slide-in
      "
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-900">Notifications</h2>
          {unreadCount > 0 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-medium">
              {unreadCount} unread
            </span>
          )}
          {refreshing && (
            <svg className="w-3.5 h-3.5 text-indigo-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          )}
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium transition-colors"
            >
              Mark all read
            </button>
          )}
          <button
            onClick={refresh}
            aria-label="Refresh notifications"
            className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <button
            onClick={onClose}
            aria-label="Close notifications"
            className="p-1 rounded text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <FilterBar />

      {/* List */}
      <div className="flex-1 overflow-y-auto" role="list" aria-label="Notification list">
        {loading ? (
          // Skeleton
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : filteredNotifications.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center py-16 text-center px-6">
            <div className="text-5xl mb-3">🔕</div>
            <p className="text-sm font-medium text-gray-700">All caught up!</p>
            <p className="text-xs text-gray-400 mt-1">No notifications match your current filter.</p>
          </div>
        ) : (
          filteredNotifications.map(n => (
            <NotificationCard
              key={n.id}
              notification={n}
              onMarkRead={markOneRead}
            />
          ))
        )}
      </div>

      {/* Load more */}
      {!loading && meta.has_next && (
        <div className="border-t border-gray-100 p-3 text-center">
          <button
            onClick={loadMore}
            className="
              text-xs text-indigo-600 hover:text-indigo-800 font-medium
              px-4 py-1.5 rounded-lg hover:bg-indigo-50 transition-colors
            "
          >
            Load more ({meta.total - filteredNotifications.length} remaining)
          </button>
        </div>
      )}

      {/* Footer: total count */}
      {!loading && meta.total > 0 && (
        <div className="border-t border-gray-100 px-4 py-2 text-center">
          <span className="text-[11px] text-gray-400">
            Showing {filteredNotifications.length} of {meta.total} notifications
          </span>
        </div>
      )}
    </div>
  )
}
