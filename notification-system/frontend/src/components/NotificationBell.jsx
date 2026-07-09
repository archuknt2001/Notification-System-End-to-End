/**
 * NotificationBell — the bell icon with unread badge.
 * Clicking toggles the notification drawer open/closed.
 */

import React from 'react'
import { useNotifications } from '../hooks/useNotifications'

export default function NotificationBell({ onClick, isOpen }) {
  const { unreadCount, refreshing } = useNotifications()

  return (
    <button
      onClick={onClick}
      aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
      aria-expanded={isOpen}
      className={`
        relative p-2 rounded-full transition-colors duration-150
        hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-500
        ${isOpen ? 'bg-gray-100' : ''}
      `}
    >
      {/* Bell icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className={`h-6 w-6 transition-colors ${refreshing ? 'text-indigo-400' : 'text-gray-600'}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
        />
      </svg>

      {/* Unread badge */}
      {unreadCount > 0 && (
        <span
          className="
            absolute -top-0.5 -right-0.5
            min-w-[18px] h-[18px] px-1
            flex items-center justify-center
            bg-red-500 text-white text-[10px] font-bold
            rounded-full ring-2 ring-white
            animate-fade-in
          "
          aria-hidden="true"
        >
          {unreadCount > 99 ? '99+' : unreadCount}
        </span>
      )}
    </button>
  )
}
