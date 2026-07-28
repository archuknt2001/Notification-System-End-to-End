/**
 * API service layer.
 * All HTTP calls go through this module — components never use axios directly.
 *
 * BASE_URL resolution:
 *   - In production (Vercel): reads VITE_API_URL environment variable
 *     e.g. VITE_API_URL=https://your-backend.railway.app/api/v1
 *   - In local dev: falls back to '/api/v1' which is proxied by Vite to localhost:8000
 *
 * Set VITE_API_URL in Vercel dashboard → Project Settings → Environment Variables
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

/** Build an axios instance scoped to a specific identity. */
function client(identity) {
  return axios.create({
    baseURL: BASE_URL,
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': identity.tenantId,
      ...(identity.userId ? { 'X-User-Id': identity.userId } : {}),
    },
  })
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export async function fetchNotifications(identity, { page = 1, size = 20 } = {}) {
  const res = await client(identity).get('/notifications', { params: { page, size } })
  return res.data // { success, data: [...], meta: {...} }
}

export async function fetchUnreadCount(identity) {
  const res = await client(identity).get('/notifications/unread-count')
  return res.data // { success, data: { unread_count } }
}

export async function markRead(identity, notificationId) {
  const res = await client(identity).patch(`/notifications/${notificationId}/read`)
  return res.data
}

export async function markAllRead(identity) {
  const res = await client(identity).patch('/notifications/read-all')
  return res.data
}

export async function createNotification(identity, payload) {
  const res = await client(identity).post('/notifications', payload)
  return res.data
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

export async function fireMemberInvited(identity, { invitedBy, inviteeName, inviteeEmail }) {
  const res = await client(identity).post('/events/member-invited', {
    invited_by: invitedBy,
    invitee_name: inviteeName,
    invitee_email: inviteeEmail,
  })
  return res.data
}

export async function fireCreatorReply(identity, { recipientUserId, creatorHandle, preview }) {
  const res = await client(identity).post('/events/creator-reply', {
    recipient_user_id: recipientUserId,
    creator_handle: creatorHandle,
    preview,
  })
  return res.data
}

export async function fireCampaignStarted(identity, { campaignName }) {
  const res = await client(identity).post('/events/campaign-started', { campaign_name: campaignName })
  return res.data
}

export async function fireCampaignCompleted(identity, { campaignName }) {
  const res = await client(identity).post('/events/campaign-completed', { campaign_name: campaignName })
  return res.data
}

export async function firePaymentReceived(identity, { recipientUserId, amount, source }) {
  const res = await client(identity).post('/events/payment-received', {
    recipient_user_id: recipientUserId,
    amount,
    source,
  })
  return res.data
}

export async function fireReportReady(identity, { recipientUserId, reportName }) {
  const res = await client(identity).post('/events/report-ready', {
    recipient_user_id: recipientUserId,
    report_name: reportName,
  })
  return res.data
}

export async function fireSystemAlert(identity, { title, message, userId = null }) {
  const res = await client(identity).post('/events/system-alert', {
    title,
    message,
    user_id: userId,
  })
  return res.data
}
