/**
 * NotificationContext — global notification state.
 *
 * Provides:
 *   notifications   list[Notification]   current page of visible notifications
 *   unreadCount     number               badge count
 *   meta            object               pagination metadata
 *   loading         bool                 initial load in progress
 *   refreshing      bool                 background poll in progress
 *   identity        object               { tenantId, userId }
 *   setIdentity     fn                   switch tenant/user (triggers full reload)
 *   refresh         fn                   manual reload
 *   loadMore        fn                   fetch next page (append)
 *   markOneRead     fn(id)               optimistic mark-read
 *   markAllRead     fn()                 optimistic mark-all-read
 *   filter          object               { type: string|null, unreadOnly: bool }
 *   setFilter       fn
 *
 * Polling: every POLL_INTERVAL ms the unread count is fetched silently.
 * When the count changes the full list is also refreshed.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import * as api from '../services/api'

const POLL_INTERVAL = 20_000 // 20 seconds
const PAGE_SIZE = 20

const NotificationContext = createContext(null)

export function NotificationProvider({ children }) {
  // Identity — tenant + user. Default matches seed data Tenant A / Alice.
  const [identity, setIdentityState] = useState({
    tenantId: 'tenant-stellar-0001',
    userId: 'user-alice-00000001',
  })

  // Notification list state
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [meta, setMeta] = useState({ page: 1, total: 0, total_pages: 1, has_next: false })
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  // Filter state (Phase 9)
  const [filter, setFilter] = useState({ type: null, unreadOnly: false })

  // Refs to avoid stale closures in the poll interval
  const identityRef = useRef(identity)
  const unreadCountRef = useRef(unreadCount)
  identityRef.current = identity
  unreadCountRef.current = unreadCount

  // ------------------------------------------------------------------
  // Fetch helpers
  // ------------------------------------------------------------------

  const fetchList = useCallback(async (currentIdentity, page = 1, append = false) => {
    try {
      const res = await api.fetchNotifications(currentIdentity, { page, size: PAGE_SIZE })
      if (res.success) {
        setNotifications(prev => append ? [...prev, ...res.data] : res.data)
        setMeta(res.meta)
      }
    } catch (err) {
      console.error('fetchList error:', err)
    }
  }, [])

  const fetchCount = useCallback(async (currentIdentity) => {
    try {
      const res = await api.fetchUnreadCount(currentIdentity)
      if (res.success) {
        const newCount = res.data.unread_count
        // If count changed, also refresh the list to reflect new notifications
        if (newCount !== unreadCountRef.current) {
          setUnreadCount(newCount)
          await fetchList(currentIdentity)
        }
      }
    } catch (err) {
      console.error('fetchCount error:', err)
    }
  }, [fetchList])

  // ------------------------------------------------------------------
  // Full refresh (used on identity change and manual refresh)
  // ------------------------------------------------------------------
  const refresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await Promise.all([
        fetchList(identityRef.current),
        (async () => {
          const res = await api.fetchUnreadCount(identityRef.current)
          if (res.success) setUnreadCount(res.data.unread_count)
        })(),
      ])
    } finally {
      setRefreshing(false)
    }
  }, [fetchList])

  // ------------------------------------------------------------------
  // Load more (pagination)
  // ------------------------------------------------------------------
  const loadMore = useCallback(async () => {
    if (!meta.has_next) return
    await fetchList(identityRef.current, meta.page + 1, true)
  }, [fetchList, meta])

  // ------------------------------------------------------------------
  // Identity switch
  // ------------------------------------------------------------------
  const setIdentity = useCallback((newIdentity) => {
    setIdentityState(newIdentity)
    setNotifications([])
    setUnreadCount(0)
    setMeta({ page: 1, total: 0, total_pages: 1, has_next: false })
    setLoading(true)
  }, [])

  // ------------------------------------------------------------------
  // Optimistic mark-read
  // ------------------------------------------------------------------
  const markOneRead = useCallback(async (id) => {
    // Optimistic update immediately
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    )
    setUnreadCount(prev => Math.max(0, prev - 1))
    try {
      await api.markRead(identityRef.current, id)
    } catch (err) {
      // Roll back optimistic update on error
      console.error('markOneRead error:', err)
      await refresh()
    }
  }, [refresh])

  // ------------------------------------------------------------------
  // Optimistic mark-all-read
  // ------------------------------------------------------------------
  const markAllRead = useCallback(async () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })))
    setUnreadCount(0)
    try {
      await api.markAllRead(identityRef.current)
    } catch (err) {
      console.error('markAllRead error:', err)
      await refresh()
    }
  }, [refresh])

  // ------------------------------------------------------------------
  // Initial load + reload on identity change
  // ------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      setLoading(true)
      try {
        await Promise.all([
          fetchList(identity),
          (async () => {
            const res = await api.fetchUnreadCount(identity)
            if (!cancelled && res.success) setUnreadCount(res.data.unread_count)
          })(),
        ])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [identity, fetchList])

  // ------------------------------------------------------------------
  // Polling — every POLL_INTERVAL ms fetch unread count silently
  // ------------------------------------------------------------------
  useEffect(() => {
    const timer = setInterval(() => {
      fetchCount(identityRef.current)
    }, POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [fetchCount])

  const value = {
    notifications,
    unreadCount,
    meta,
    loading,
    refreshing,
    identity,
    setIdentity,
    refresh,
    loadMore,
    markOneRead,
    markAllRead,
    filter,
    setFilter,
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}

export function useNotificationContext() {
  const ctx = useContext(NotificationContext)
  if (!ctx) throw new Error('useNotificationContext must be used within NotificationProvider')
  return ctx
}
