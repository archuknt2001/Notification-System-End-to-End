/**
 * App.jsx — root component.
 *
 * Layout:
 *   ┌─────────────────────────────────┐
 *   │  Header (logo · TenantSwitcher · Bell) │
 *   ├─────────────────────────────────┤
 *   │  Hero card: identity info        │
 *   │  Demo Event Triggers             │
 *   │  Polling status bar              │
 *   └─────────────────────────────────┘
 *   NotificationDrawer (absolute positioned)
 */

import React, { useState } from 'react'
import { NotificationProvider } from './context/NotificationContext'
import { useNotifications } from './hooks/useNotifications'
import NotificationBell from './components/NotificationBell'
import NotificationDrawer from './components/NotificationDrawer'
import DemoTrigger from './components/DemoTrigger'

// ---------------------------------------------------------------------------
// Demo tenants / users — matches backend seed data
// ---------------------------------------------------------------------------
const DEMO_IDENTITIES = [
  { label: 'Alice — Stellar (Tenant A)', tenantId: 'tenant-stellar-0001', userId: 'user-alice-00000001' },
  { label: 'Bob — Stellar (Tenant A)',   tenantId: 'tenant-stellar-0001', userId: 'user-bob-000000001' },
  { label: 'Carol — Nova (Tenant B)',    tenantId: 'tenant-nova-00001',   userId: 'user-carol-0000001' },
  { label: 'Dave — Nova (Tenant B)',     tenantId: 'tenant-nova-00001',   userId: 'user-dave-00000001' },
  { label: 'Tenant A (no user)',         tenantId: 'tenant-stellar-0001', userId: null },
]

// ---------------------------------------------------------------------------
// Inner layout — needs to be inside NotificationProvider
// ---------------------------------------------------------------------------
function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { identity, setIdentity, unreadCount } = useNotifications()

  const currentLabel =
    DEMO_IDENTITIES.find(
      d => d.tenantId === identity.tenantId && d.userId === identity.userId
    )?.label ?? 'Custom'

  const handleIdentityChange = (e) => {
    const selected = DEMO_IDENTITIES[parseInt(e.target.value)]
    if (selected) setIdentity({ tenantId: selected.tenantId, userId: selected.userId })
    setDrawerOpen(false)
  }

  return (
    <div className="min-h-screen bg-gray-100 font-sans">

      {/* ---------------------------------------------------------------- */}
      {/* Header                                                           */}
      {/* ---------------------------------------------------------------- */}
      <header className="sticky top-0 z-40 bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">

          {/* Logo */}
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-indigo-600">CRM</span>
            <span className="hidden sm:inline text-sm text-gray-500 font-medium">Notification System</span>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3">
            {/* Tenant / User switcher */}
            <select
              value={DEMO_IDENTITIES.findIndex(
                d => d.tenantId === identity.tenantId && d.userId === identity.userId
              )}
              onChange={handleIdentityChange}
              aria-label="Switch user / tenant"
              className="
                text-xs rounded-lg border border-gray-200 bg-gray-50
                px-2 py-1.5 text-gray-700 max-w-[200px]
                focus:outline-none focus:ring-1 focus:ring-indigo-400 cursor-pointer
              "
            >
              {DEMO_IDENTITIES.map((d, i) => (
                <option key={i} value={i}>{d.label}</option>
              ))}
            </select>

            {/* Notification Bell */}
            <div className="relative">
              <NotificationBell
                onClick={() => setDrawerOpen(o => !o)}
                isOpen={drawerOpen}
              />
              <NotificationDrawer
                isOpen={drawerOpen}
                onClose={() => setDrawerOpen(false)}
              />
            </div>
          </div>
        </div>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* Main content                                                     */}
      {/* ---------------------------------------------------------------- */}
      <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">

        {/* Identity card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-base font-semibold text-gray-900">
                Logged in as: <span className="text-indigo-600">{currentLabel}</span>
              </h1>
              <div className="mt-1.5 flex flex-wrap gap-2 text-xs text-gray-500">
                <span className="px-2 py-0.5 bg-gray-100 rounded font-mono">
                  tenant: {identity.tenantId}
                </span>
                <span className="px-2 py-0.5 bg-gray-100 rounded font-mono">
                  user: {identity.userId ?? 'none (tenant-wide)'}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold
                ${unreadCount > 0 ? 'bg-indigo-100 text-indigo-700' : 'bg-gray-100 text-gray-600'}`}>
                <span>🔔</span>
                <span>{unreadCount} unread</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-gray-400">
                <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse inline-block" />
                Polling every 20s
              </div>
            </div>
          </div>
        </div>

        {/* Demo event triggers */}
        <DemoTrigger />

        {/* Info card */}
        <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-indigo-900 mb-2">How to use</h2>
          <ul className="text-xs text-indigo-700 space-y-1.5 list-disc list-inside">
            <li>Click the <strong>bell icon</strong> in the header to open the notification drawer.</li>
            <li>Use the <strong>user switcher</strong> to switch between tenants and users — demonstrates strict tenant isolation.</li>
            <li>Click a <strong>demo event button</strong> to fire a business event and watch the bell badge update.</li>
            <li>Click any notification card to <strong>mark it as read</strong>.</li>
            <li>Use <strong>Mark all read</strong> inside the drawer to clear the badge.</li>
            <li>Filter by <strong>type</strong> or toggle <strong>unread only</strong> using the filter bar.</li>
            <li>Notifications are <strong>polled every 20 seconds</strong> — the badge updates automatically.</li>
          </ul>
        </div>
      </main>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Root — wrap with provider
// ---------------------------------------------------------------------------
export default function App() {
  return (
    <NotificationProvider>
      <Layout />
    </NotificationProvider>
  )
}
