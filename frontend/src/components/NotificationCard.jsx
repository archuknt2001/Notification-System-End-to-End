/**
 * NotificationCard — a single notification row in the drawer.
 *
 * Read/unread styling:
 *   Unread → white bg, left indigo border, bold title
 *   Read   → gray bg, no border, normal weight
 */

import React from 'react'
import { relativeTime } from '../utils/relativeTime'
import { getTypeMeta } from '../utils/notificationIcons'

export default function NotificationCard({ notification, onMarkRead }) {
  const { id, type, title, body, read, created_at, user_id } = notification
  const { icon, bg } = getTypeMeta(type)

  const handleClick = () => {
    if (!read) onMarkRead(id)
  }

  return (
    <div
      role="listitem"
      onClick={handleClick}
      className={`
        relative flex gap-3 px-4 py-3 cursor-pointer
        border-b border-gray-100 last:border-0
        transition-colors duration-100
        ${read
          ? 'bg-gray-50 hover:bg-gray-100'
          : 'bg-white border-l-4 border-l-indigo-500 hover:bg-indigo-50'
        }
      `}
    >
      {/* Icon */}
      <div className={`mt-0.5 flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center text-lg ${bg}`}>
        {icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className={`text-sm leading-snug truncate ${read ? 'font-normal text-gray-700' : 'font-semibold text-gray-900'}`}>
            {title}
          </p>
          {/* Unread dot */}
          {!read && (
            <span className="mt-1 flex-shrink-0 w-2 h-2 rounded-full bg-indigo-500" aria-hidden="true" />
          )}
        </div>
        <p className="mt-0.5 text-xs text-gray-500 line-clamp-2">{body}</p>
        <div className="mt-1 flex items-center gap-2">
          <span className="text-[11px] text-gray-400">{relativeTime(created_at)}</span>
          {/* Scope badge: user-specific vs tenant-wide */}
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
            user_id ? 'bg-purple-100 text-purple-600' : 'bg-blue-100 text-blue-600'
          }`}>
            {user_id ? 'personal' : 'team'}
          </span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 font-medium">
            {type.replace(/_/g, ' ')}
          </span>
        </div>
      </div>
    </div>
  )
}
