/**
 * FilterBar — type filter dropdown + unread-only toggle.
 * Filters are applied client-side via useNotifications.filteredNotifications.
 */

import React from 'react'
import { useNotifications } from '../hooks/useNotifications'
import { ALL_TYPES } from '../utils/notificationIcons'

export default function FilterBar() {
  const { filter, setFilter, unreadCount } = useNotifications()

  const handleType = (e) => setFilter(f => ({ ...f, type: e.target.value || null }))
  const handleUnread = () => setFilter(f => ({ ...f, unreadOnly: !f.unreadOnly }))

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-100 bg-gray-50">
      {/* Type filter */}
      <select
        value={filter.type ?? ''}
        onChange={handleType}
        aria-label="Filter by type"
        className="
          flex-1 text-xs rounded-md border border-gray-200 bg-white
          px-2 py-1.5 text-gray-700 focus:outline-none focus:ring-1
          focus:ring-indigo-400 cursor-pointer
        "
      >
        <option value="">All types</option>
        {ALL_TYPES.map(t => (
          <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
        ))}
      </select>

      {/* Unread toggle */}
      <button
        onClick={handleUnread}
        aria-pressed={filter.unreadOnly}
        className={`
          flex-shrink-0 text-xs px-3 py-1.5 rounded-md font-medium
          transition-colors duration-100 border
          ${filter.unreadOnly
            ? 'bg-indigo-600 text-white border-indigo-600'
            : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-100'
          }
        `}
      >
        Unread
        {unreadCount > 0 && (
          <span className={`ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full font-bold
            ${filter.unreadOnly ? 'bg-white text-indigo-600' : 'bg-indigo-100 text-indigo-600'}`}>
            {unreadCount}
          </span>
        )}
      </button>
    </div>
  )
}
