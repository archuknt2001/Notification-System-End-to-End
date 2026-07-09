/**
 * DemoTrigger — panel to fire business events from the UI.
 * Demonstrates the full event pipeline without needing an external tool.
 */

import React, { useState } from 'react'
import { useNotifications } from '../hooks/useNotifications'
import * as api from '../services/api'

const DEMO_EVENTS = [
  {
    label: 'Member Invited',
    description: 'Tenant-wide notification',
    icon: '👥',
    color: 'bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700',
    fire: (identity) => api.fireMemberInvited(identity, {
      invitedBy: 'Alice',
      inviteeName: 'Jordan Lee',
      inviteeEmail: 'jordan@example.com',
    }),
  },
  {
    label: 'Creator Reply',
    description: 'Personal notification',
    icon: '💬',
    color: 'bg-purple-50 hover:bg-purple-100 border-purple-200 text-purple-700',
    fire: (identity) => api.fireCreatorReply(identity, {
      recipientUserId: identity.userId,
      creatorHandle: '@nova_style',
      preview: 'Love the brief! Let\'s hop on a call tomorrow?',
    }),
  },
  {
    label: 'Campaign Started',
    description: 'Tenant-wide notification',
    icon: '🚀',
    color: 'bg-green-50 hover:bg-green-100 border-green-200 text-green-700',
    fire: (identity) => api.fireCampaignStarted(identity, { campaignName: 'Autumn Vibes 2025' }),
  },
  {
    label: 'Campaign Completed',
    description: 'Tenant-wide notification',
    icon: '✅',
    color: 'bg-emerald-50 hover:bg-emerald-100 border-emerald-200 text-emerald-700',
    fire: (identity) => api.fireCampaignCompleted(identity, { campaignName: 'Summer Glow' }),
  },
  {
    label: 'Payment Received',
    description: 'Personal notification',
    icon: '💰',
    color: 'bg-teal-50 hover:bg-teal-100 border-teal-200 text-teal-700',
    fire: (identity) => api.firePaymentReceived(identity, {
      recipientUserId: identity.userId,
      amount: '$8,500',
      source: 'BrandX Corp',
    }),
  },
  {
    label: 'Report Ready',
    description: 'Personal notification',
    icon: '📊',
    color: 'bg-cyan-50 hover:bg-cyan-100 border-cyan-200 text-cyan-700',
    fire: (identity) => api.fireReportReady(identity, {
      recipientUserId: identity.userId,
      reportName: 'Q3 Campaign Performance',
    }),
  },
  {
    label: 'System Alert',
    description: 'Tenant-wide notification',
    icon: '🔔',
    color: 'bg-red-50 hover:bg-red-100 border-red-200 text-red-700',
    fire: (identity) => api.fireSystemAlert(identity, {
      title: 'Scheduled Maintenance',
      message: 'Platform offline Sunday 02:00–04:00 UTC.',
    }),
  },
]

export default function DemoTrigger() {
  const { identity, refresh } = useNotifications()
  const [firing, setFiring] = useState(null)
  const [toast, setToast] = useState(null)

  const fire = async (event, idx) => {
    setFiring(idx)
    setToast(null)
    try {
      await event.fire(identity)
      await refresh()
      setToast({ type: 'success', message: `${event.label} fired!` })
    } catch (err) {
      setToast({ type: 'error', message: err?.response?.data?.message ?? 'Request failed' })
    } finally {
      setFiring(null)
      setTimeout(() => setToast(null), 3000)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-900">Fire Demo Events</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Each button fires a business event through the full pipeline.
        </p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2 p-4">
        {DEMO_EVENTS.map((event, idx) => (
          <button
            key={event.label}
            onClick={() => fire(event, idx)}
            disabled={firing !== null}
            className={`
              flex flex-col items-center gap-1.5 p-3 rounded-lg border text-center
              transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed
              ${event.color}
            `}
          >
            <span className="text-2xl">
              {firing === idx ? (
                <svg className="w-6 h-6 animate-spin text-current mx-auto" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
              ) : event.icon}
            </span>
            <span className="text-xs font-semibold leading-tight">{event.label}</span>
            <span className="text-[10px] opacity-70">{event.description}</span>
          </button>
        ))}
      </div>

      {/* Toast message */}
      {toast && (
        <div className={`mx-4 mb-4 px-4 py-2.5 rounded-lg text-xs font-medium animate-fade-in ${
          toast.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'
        }`}>
          {toast.type === 'success' ? '✅ ' : '❌ '}{toast.message}
        </div>
      )}
    </div>
  )
}
