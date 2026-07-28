"""
API endpoint tests — /api/v1/notifications

Tests all 5 endpoints: POST, GET (list), GET (unread-count),
PATCH (read-all), PATCH ({id}/read).
Covers happy path, validation errors, and error envelope shape.
"""

import pytest
from tests.conftest import (
    TENANT_A, TENANT_B, USER_A1, USER_A2,
    HDR_A1, HDR_A2, HDR_B1, HDR_A_NO_USER,
)


def ok(r):
    """Assert 2xx success envelope."""
    body = r.json()
    assert r.status_code < 300, f"Expected success, got {r.status_code}: {body}"
    assert body["success"] is True
    return body


def err(r, status):
    """Assert error envelope with specific status."""
    body = r.json()
    assert r.status_code == status, f"Expected {status}, got {r.status_code}: {body}"
    assert body["success"] is False
    return body


# ---------------------------------------------------------------------------
# POST /notifications
# ---------------------------------------------------------------------------

class TestCreateNotification:
    def test_creates_tenant_wide(self, client):
        r = client.post("/api/v1/notifications",
            json={"type": "system_alert", "title": "Alert", "body": "Body"},
            headers=HDR_A1)
        body = ok(r)
        assert r.status_code == 201
        assert body["data"]["tenant_id"] == TENANT_A
        assert body["data"]["user_id"] is None
        assert body["data"]["read"] is False

    def test_creates_user_specific(self, client):
        r = client.post("/api/v1/notifications",
            json={"type": "new_reply", "title": "Reply", "body": "B", "user_id": USER_A1},
            headers=HDR_A1)
        body = ok(r)
        assert body["data"]["user_id"] == USER_A1

    def test_invalid_type_returns_422(self, client):
        r = client.post("/api/v1/notifications",
            json={"type": "not_a_real_type", "title": "T", "body": "B"},
            headers=HDR_A1)
        err(r, 422)

    def test_missing_title_returns_422(self, client):
        r = client.post("/api/v1/notifications",
            json={"type": "warning", "body": "B"},
            headers=HDR_A1)
        err(r, 422)

    def test_missing_tenant_header_returns_422(self, client):
        r = client.post("/api/v1/notifications",
            json={"type": "warning", "title": "T", "body": "B"})
        body = err(r, 422)
        assert "errors" in body

    def test_response_has_id_and_created_at(self, client):
        r = client.post("/api/v1/notifications",
            json={"type": "success", "title": "T", "body": "B"},
            headers=HDR_A1)
        body = ok(r)
        assert "id" in body["data"]
        assert "created_at" in body["data"]


# ---------------------------------------------------------------------------
# GET /notifications/unread-count
# ---------------------------------------------------------------------------

class TestUnreadCount:
    def test_returns_unread_count(self, client, seeded):
        r = client.get("/api/v1/notifications/unread-count", headers=HDR_A1)
        body = ok(r)
        assert "unread_count" in body["data"]
        assert body["data"]["unread_count"] >= 0

    def test_decreases_after_mark_all_read(self, client, seeded):
        r1 = client.get("/api/v1/notifications/unread-count", headers=HDR_A1)
        client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        r2 = client.get("/api/v1/notifications/unread-count", headers=HDR_A1)
        assert r2.json()["data"]["unread_count"] == 0

    def test_tenant_a_and_b_independent(self, client, seeded):
        count_a = client.get("/api/v1/notifications/unread-count", headers=HDR_A1).json()["data"]["unread_count"]
        count_b = client.get("/api/v1/notifications/unread-count", headers=HDR_B1).json()["data"]["unread_count"]
        # After marking A all read, B must be unchanged
        client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        count_b_after = client.get("/api/v1/notifications/unread-count", headers=HDR_B1).json()["data"]["unread_count"]
        assert count_b_after == count_b

    def test_missing_tenant_returns_422(self, client):
        r = client.get("/api/v1/notifications/unread-count")
        err(r, 422)


# ---------------------------------------------------------------------------
# GET /notifications
# ---------------------------------------------------------------------------

class TestListNotifications:
    def test_returns_success_with_data_and_meta(self, client, seeded):
        r = client.get("/api/v1/notifications", headers=HDR_A1)
        body = ok(r)
        assert isinstance(body["data"], list)
        assert "meta" in body
        assert "total" in body["meta"]
        assert "page" in body["meta"]
        assert "size" in body["meta"]
        assert "total_pages" in body["meta"]
        assert "has_next" in body["meta"]
        assert "has_prev" in body["meta"]

    def test_default_page_is_1(self, client, seeded):
        r = client.get("/api/v1/notifications", headers=HDR_A1)
        assert r.json()["meta"]["page"] == 1

    def test_custom_page_and_size(self, client, seeded):
        r = client.get("/api/v1/notifications?page=1&size=2", headers=HDR_A1)
        body = ok(r)
        assert body["meta"]["size"] == 2
        assert len(body["data"]) <= 2

    def test_pages_are_disjoint(self, client, seeded):
        p1 = {n["id"] for n in client.get("/api/v1/notifications?page=1&size=2", headers=HDR_A1).json()["data"]}
        p2 = {n["id"] for n in client.get("/api/v1/notifications?page=2&size=2", headers=HDR_A1).json()["data"]}
        assert p1.isdisjoint(p2)

    def test_all_items_belong_to_tenant(self, client, seeded):
        items = client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]
        for item in items:
            assert item["tenant_id"] == TENANT_A

    def test_visibility_no_other_users_items(self, client, seeded):
        items = client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]
        for item in items:
            assert item["user_id"] in (None, USER_A1), \
                f"A1 should not see user_id={item['user_id']}"

    def test_unread_first_ordering(self, client, seeded):
        items = client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]
        reads = [item["read"] for item in items]
        flipped = False
        for r in reads:
            if not flipped and r:
                flipped = True
            elif flipped and not r:
                pytest.fail(f"Ordering violated: {reads}")

    def test_has_prev_false_on_page_1(self, client, seeded):
        meta = client.get("/api/v1/notifications?page=1&size=2", headers=HDR_A1).json()["meta"]
        assert meta["has_prev"] is False

    def test_missing_tenant_returns_422(self, client):
        r = client.get("/api/v1/notifications")
        err(r, 422)


# ---------------------------------------------------------------------------
# PATCH /notifications/{id}/read
# ---------------------------------------------------------------------------

class TestMarkRead:
    def test_marks_notification_read(self, client, seeded):
        nid = seeded["a_wide_unread_1"].id
        r = client.patch(f"/api/v1/notifications/{nid}/read", headers=HDR_A1)
        body = ok(r)
        assert body["data"]["read"] is True
        assert body["data"]["read_at"] is not None

    def test_idempotent(self, client, seeded):
        nid = seeded["a1_unread_1"].id
        client.patch(f"/api/v1/notifications/{nid}/read", headers=HDR_A1)
        r2 = client.patch(f"/api/v1/notifications/{nid}/read", headers=HDR_A1)
        ok(r2)

    def test_cross_tenant_returns_404(self, client, seeded):
        nid = seeded["a_wide_unread_1"].id
        r = client.patch(f"/api/v1/notifications/{nid}/read", headers=HDR_B1)
        err(r, 404)

    def test_wrong_user_returns_403(self, client, seeded):
        nid = seeded["a1_unread_1"].id  # belongs to USER_A1
        r = client.patch(f"/api/v1/notifications/{nid}/read", headers=HDR_A2)
        err(r, 403)

    def test_missing_id_returns_404(self, client):
        r = client.patch(
            "/api/v1/notifications/00000000-0000-0000-0000-000000000000/read",
            headers=HDR_A1)
        err(r, 404)

    def test_missing_tenant_returns_422(self, client):
        r = client.patch("/api/v1/notifications/some-id/read")
        err(r, 422)


# ---------------------------------------------------------------------------
# PATCH /notifications/read-all
# ---------------------------------------------------------------------------

class TestMarkAllRead:
    def test_marks_all_visible_unread(self, client, seeded):
        r = client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        body = ok(r)
        assert body["data"]["updated"] >= 1
        count = client.get("/api/v1/notifications/unread-count", headers=HDR_A1).json()["data"]["unread_count"]
        assert count == 0

    def test_idempotent_second_call(self, client, seeded):
        client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        r2 = client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        body = ok(r2)
        assert body["data"]["updated"] == 0

    def test_does_not_affect_other_tenant(self, client, seeded):
        count_b_before = client.get("/api/v1/notifications/unread-count", headers=HDR_B1).json()["data"]["unread_count"]
        client.patch("/api/v1/notifications/read-all", headers=HDR_A1)
        count_b_after = client.get("/api/v1/notifications/unread-count", headers=HDR_B1).json()["data"]["unread_count"]
        assert count_b_after == count_b_before

    def test_missing_tenant_returns_422(self, client):
        r = client.patch("/api/v1/notifications/read-all")
        err(r, 422)
