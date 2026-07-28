"""
Tenant isolation tests — the most critical security requirement.

These tests verify that:
1. Users NEVER see another tenant's notifications in any list.
2. Unread counts never leak across tenants.
3. A tenant cannot mark another tenant's notification as read.
4. ID guessing across tenants is structurally impossible.
5. Even with the same user ID across different tenants, data stays separate.
"""

import pytest
from tests.conftest import (
    TENANT_A, TENANT_B, USER_A1, USER_A2, USER_B1, USER_B2,
    HDR_A1, HDR_A2, HDR_B1, HDR_B2, HDR_A_NO_USER,
    make_notification,
)


# ---------------------------------------------------------------------------
# List endpoint isolation
# ---------------------------------------------------------------------------

class TestListIsolation:
    def test_tenant_a_list_contains_no_tenant_b_rows(self, client, seeded):
        items = client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]
        for item in items:
            assert item["tenant_id"] == TENANT_A, \
                f"Tenant A list leaked Tenant B row: {item['id']}"

    def test_tenant_b_list_contains_no_tenant_a_rows(self, client, seeded):
        items = client.get("/api/v1/notifications?size=100", headers=HDR_B1).json()["data"]
        for item in items:
            assert item["tenant_id"] == TENANT_B, \
                f"Tenant B list leaked Tenant A row: {item['id']}"

    def test_tenant_a_ids_not_in_tenant_b_list(self, client, seeded):
        a_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]}
        b_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_B1).json()["data"]}
        assert a_ids.isdisjoint(b_ids), \
            f"Overlap between tenant lists: {a_ids & b_ids}"

    def test_user_a2_cannot_see_user_a1_private_notifications(self, client, seeded):
        a1_private_id = seeded["a1_unread_1"].id
        a2_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A2).json()["data"]}
        assert a1_private_id not in a2_ids, \
            "User A2 can see User A1's private notification!"

    def test_user_a1_cannot_see_user_a2_private_notifications(self, client, seeded):
        a2_private_id = seeded["a2_unread"].id
        a1_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]}
        assert a2_private_id not in a1_ids, \
            "User A1 can see User A2's private notification!"

    def test_both_users_see_tenant_wide_notifications(self, client, seeded):
        wide_id = seeded["a_wide_unread_1"].id
        a1_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]}
        a2_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A2).json()["data"]}
        assert wide_id in a1_ids, "A1 must see tenant-wide notification"
        assert wide_id in a2_ids, "A2 must see tenant-wide notification"


# ---------------------------------------------------------------------------
# Unread count isolation
# ---------------------------------------------------------------------------

class TestUnreadCountIsolation:
    def test_counts_are_independent_per_tenant(self, client, seeded):
        count_a = client.get("/api/v1/notifications/unread-count", headers=HDR_A1).json()["data"]["unread_count"]
        count_b = client.get("/api/v1/notifications/unread-count", headers=HDR_B1).json()["data"]["unread_count"]
        # mark all read for A
        client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        count_a_after = client.get("/api/v1/notifications/unread-count", headers=HDR_A1).json()["data"]["unread_count"]
        count_b_after = client.get("/api/v1/notifications/unread-count", headers=HDR_B1).json()["data"]["unread_count"]
        assert count_a_after == 0
        assert count_b_after == count_b  # B must be untouched

    def test_user_a1_and_a2_have_independent_counts(self, client, seeded):
        count_a1 = client.get("/api/v1/notifications/unread-count", headers=HDR_A1).json()["data"]["unread_count"]
        count_a2 = client.get("/api/v1/notifications/unread-count", headers=HDR_A2).json()["data"]["unread_count"]
        # Mark all read for A1 only
        client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        count_a1_after = client.get("/api/v1/notifications/unread-count", headers=HDR_A1).json()["data"]["unread_count"]
        count_a2_after = client.get("/api/v1/notifications/unread-count", headers=HDR_A2).json()["data"]["unread_count"]
        assert count_a1_after == 0
        # A2's user-specific unread should still be there
        assert count_a2_after > 0


# ---------------------------------------------------------------------------
# Mark-read isolation (ID guessing attack)
# ---------------------------------------------------------------------------

class TestMarkReadIsolation:
    def test_cannot_mark_other_tenant_notification_as_read(self, client, seeded):
        # A's notification ID used by B caller
        nid = seeded["a_wide_unread_1"].id
        r = client.patch(f"/api/v1/notifications/{nid}/read", headers=HDR_B1)
        assert r.status_code == 404, \
            "Cross-tenant mark-read should return 404, not expose the resource"

    def test_cannot_mark_other_users_private_notification(self, client, seeded):
        nid = seeded["a1_unread_1"].id  # private to USER_A1
        r = client.patch(f"/api/v1/notifications/{nid}/read", headers=HDR_A2)
        assert r.status_code == 403, \
            "Wrong-user mark-read should return 403"

    def test_mark_all_read_scoped_to_tenant(self, client, seeded):
        b_unread_before = client.get("/api/v1/notifications/unread-count", headers=HDR_B1).json()["data"]["unread_count"]
        client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        b_unread_after = client.get("/api/v1/notifications/unread-count", headers=HDR_B1).json()["data"]["unread_count"]
        assert b_unread_after == b_unread_before


# ---------------------------------------------------------------------------
# Event creation isolation
# ---------------------------------------------------------------------------

class TestEventIsolation:
    def test_member_invited_event_not_visible_to_other_tenant(self, client):
        r = client.post("/api/v1/events/member-invited", json={
            "invited_by": "Alice", "invitee_name": "Eve", "invitee_email": "e@e.com"
        }, headers=HDR_A1)
        nid = r.json()["data"]["id"]
        b_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_B1).json()["data"]}
        assert nid not in b_ids

    def test_creator_reply_not_visible_to_other_tenant(self, client):
        r = client.post("/api/v1/events/creator-reply", json={
            "recipient_user_id": USER_A1,
            "creator_handle": "@test",
            "preview": "Hi"
        }, headers=HDR_A1)
        nid = r.json()["data"]["id"]
        b_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_B1).json()["data"]}
        assert nid not in b_ids

    def test_notification_created_in_correct_tenant(self, client):
        r = client.post("/api/v1/notifications", json={
            "type": "warning", "title": "T", "body": "B"
        }, headers=HDR_B1)
        body = r.json()
        assert body["data"]["tenant_id"] == TENANT_B
        # Must not appear in Tenant A's list
        a_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]}
        assert body["data"]["id"] not in a_ids


# ---------------------------------------------------------------------------
# Same user ID across different tenants
# ---------------------------------------------------------------------------

class TestSameUserIdDifferentTenants:
    """
    Edge case: two tenants happen to have a user with the same ID string.
    Each must still only see their own tenant's notifications.
    """

    def test_same_user_id_different_tenants_isolated(self, client, db_session):
        SHARED_USER_ID = "shared-user-id-999"
        hdr_ta = {"X-Tenant-Id": TENANT_A, "X-User-Id": SHARED_USER_ID}
        hdr_tb = {"X-Tenant-Id": TENANT_B, "X-User-Id": SHARED_USER_ID}

        # Create one notification in each tenant for the shared user ID
        make_notification(db_session, tenant_id=TENANT_A, user_id=SHARED_USER_ID,
                          type="success", title="A notification", body="For A")
        make_notification(db_session, tenant_id=TENANT_B, user_id=SHARED_USER_ID,
                          type="warning", title="B notification", body="For B")

        a_items = client.get("/api/v1/notifications?size=100", headers=hdr_ta).json()["data"]
        b_items = client.get("/api/v1/notifications?size=100", headers=hdr_tb).json()["data"]

        a_ids = {n["id"] for n in a_items}
        b_ids = {n["id"] for n in b_items}

        # Each set must be completely disjoint
        assert a_ids.isdisjoint(b_ids), \
            f"Same userId across tenants leaked data: {a_ids & b_ids}"
        for n in a_items:
            assert n["tenant_id"] == TENANT_A
        for n in b_items:
            assert n["tenant_id"] == TENANT_B
