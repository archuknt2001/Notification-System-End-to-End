"""
API endpoint tests — /api/v1/events

Verifies all 8 event endpoints fire correctly and produce
properly typed, correctly targeted notifications.
"""

import pytest
from tests.conftest import (
    TENANT_A, TENANT_B, USER_A1, USER_A2, USER_B1,
    HDR_A1, HDR_A2, HDR_B1,
)


def ok(r, status=201):
    body = r.json()
    assert r.status_code == status, f"Expected {status}, got {r.status_code}: {body}"
    assert body["success"] is True
    return body


def err(r, status):
    body = r.json()
    assert r.status_code == status, f"Expected {status}, got {r.status_code}: {body}"
    assert body["success"] is False
    return body


class TestMemberInvited:
    def test_creates_tenant_wide_notification(self, client):
        r = client.post("/api/v1/events/member-invited", json={
            "invited_by": "Alice",
            "invitee_name": "Eve",
            "invitee_email": "eve@example.com"
        }, headers=HDR_A1)
        body = ok(r)
        assert body["data"]["type"] == "member_invited"
        assert body["data"]["user_id"] is None
        assert body["data"]["tenant_id"] == TENANT_A

    def test_visible_to_all_tenant_users(self, client):
        r = client.post("/api/v1/events/member-invited", json={
            "invited_by": "Alice", "invitee_name": "Eve", "invitee_email": "e@e.com"
        }, headers=HDR_A1)
        nid = r.json()["data"]["id"]
        a1_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]}
        a2_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A2).json()["data"]}
        assert nid in a1_ids
        assert nid in a2_ids

    def test_not_visible_to_other_tenant(self, client):
        r = client.post("/api/v1/events/member-invited", json={
            "invited_by": "Alice", "invitee_name": "Eve", "invitee_email": "e@e.com"
        }, headers=HDR_A1)
        nid = r.json()["data"]["id"]
        b_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_B1).json()["data"]}
        assert nid not in b_ids

    def test_missing_tenant_returns_422(self, client):
        r = client.post("/api/v1/events/member-invited", json={
            "invited_by": "Alice", "invitee_name": "Eve", "invitee_email": "e@e.com"
        })
        err(r, 422)


class TestCreatorReply:
    def test_creates_user_specific_notification(self, client):
        r = client.post("/api/v1/events/creator-reply", json={
            "recipient_user_id": USER_A1,
            "creator_handle": "@nova",
            "preview": "Sounds great!"
        }, headers=HDR_A1)
        body = ok(r)
        assert body["data"]["type"] == "new_reply"
        assert body["data"]["user_id"] == USER_A1

    def test_only_recipient_sees_it(self, client):
        r = client.post("/api/v1/events/creator-reply", json={
            "recipient_user_id": USER_A1,
            "creator_handle": "@nova",
            "preview": "Hi!"
        }, headers=HDR_A1)
        nid = r.json()["data"]["id"]
        a1_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A1).json()["data"]}
        a2_ids = {n["id"] for n in client.get("/api/v1/notifications?size=100", headers=HDR_A2).json()["data"]}
        assert nid in a1_ids
        assert nid not in a2_ids


class TestCampaignEvents:
    def test_campaign_started(self, client):
        r = client.post("/api/v1/events/campaign-started",
            json={"campaign_name": "Test Campaign"}, headers=HDR_A1)
        body = ok(r)
        assert body["data"]["type"] == "campaign_started"
        assert body["data"]["user_id"] is None

    def test_campaign_completed(self, client):
        r = client.post("/api/v1/events/campaign-completed",
            json={"campaign_name": "Old Campaign"}, headers=HDR_A1)
        body = ok(r)
        assert body["data"]["type"] == "campaign_completed"
        assert body["data"]["user_id"] is None


class TestPaymentReceived:
    def test_creates_user_specific(self, client):
        r = client.post("/api/v1/events/payment-received", json={
            "recipient_user_id": USER_A1,
            "amount": "$5,000",
            "source": "BrandX"
        }, headers=HDR_A1)
        body = ok(r)
        assert body["data"]["type"] == "payment_received"
        assert body["data"]["user_id"] == USER_A1


class TestReportReady:
    def test_creates_user_specific(self, client):
        r = client.post("/api/v1/events/report-ready", json={
            "recipient_user_id": USER_A1,
            "report_name": "Q3 Analytics"
        }, headers=HDR_A1)
        body = ok(r)
        assert body["data"]["type"] == "report_ready"
        assert body["data"]["user_id"] == USER_A1


class TestInvoiceDue:
    def test_overdue_urgency_text(self, client):
        r = client.post("/api/v1/events/invoice-due", json={
            "recipient_user_id": USER_A1,
            "invoice_number": "INV-001",
            "amount": "$1,000",
            "due_in_days": 0
        }, headers=HDR_A1)
        body = ok(r)
        assert "overdue" in body["data"]["title"].lower()

    def test_future_due_text(self, client):
        r = client.post("/api/v1/events/invoice-due", json={
            "recipient_user_id": USER_A1,
            "invoice_number": "INV-002",
            "amount": "$1,000",
            "due_in_days": 5
        }, headers=HDR_A1)
        body = ok(r)
        assert "5 days" in body["data"]["title"].lower()

    def test_due_tomorrow_text(self, client):
        r = client.post("/api/v1/events/invoice-due", json={
            "recipient_user_id": USER_A1,
            "invoice_number": "INV-003",
            "amount": "$500",
            "due_in_days": 1
        }, headers=HDR_A1)
        body = ok(r)
        assert "tomorrow" in body["data"]["title"].lower()


class TestSystemAlert:
    def test_tenant_wide_when_no_user_id(self, client):
        r = client.post("/api/v1/events/system-alert", json={
            "title": "Maintenance",
            "message": "Offline Sunday."
        }, headers=HDR_A1)
        body = ok(r)
        assert body["data"]["user_id"] is None

    def test_user_specific_when_user_id_given(self, client):
        r = client.post("/api/v1/events/system-alert", json={
            "title": "Your account",
            "message": "Unusual login.",
            "user_id": USER_A1
        }, headers=HDR_A1)
        body = ok(r)
        assert body["data"]["user_id"] == USER_A1
