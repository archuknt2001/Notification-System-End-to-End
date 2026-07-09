"""
Service layer tests — NotificationService and EventService.
"""

import pytest
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.schemas.notification_schema import NotificationCreate, NotificationList, NotificationRead
from app.services.notification_service import NotificationService
from app.services.event_service import EventService
from tests.conftest import TENANT_A, TENANT_B, USER_A1, USER_A2, USER_B1


# ---------------------------------------------------------------------------
# NotificationService
# ---------------------------------------------------------------------------

class TestNotificationServiceCreate:
    def test_creates_and_returns_read_schema(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.create(TENANT_A, NotificationCreate(
            type="success", title="Hello", body="World"
        ))
        assert isinstance(result, NotificationRead)
        assert result.tenant_id == TENANT_A
        assert result.read is False

    def test_strips_whitespace_from_title_and_body(self, db_session):
        svc = NotificationService(db_session)
        result = svc.create(TENANT_A, NotificationCreate(
            type="warning", title="  Padded  ", body="  Body  "
        ))
        assert result.title == "Padded"
        assert result.body == "Body"

    def test_invalid_type_raises_validation_error(self, db_session):
        svc = NotificationService(db_session)
        bad = NotificationCreate.model_construct(
            type="not_valid_type", title="T", body="B"
        )
        with pytest.raises(ValidationError):
            svc.create(TENANT_A, bad)

    def test_user_id_set_correctly(self, db_session):
        svc = NotificationService(db_session)
        result = svc.create(TENANT_A, NotificationCreate(
            type="new_reply", title="T", body="B", user_id=USER_A1
        ))
        assert result.user_id == USER_A1

    def test_tenant_wide_when_no_user_id(self, db_session):
        svc = NotificationService(db_session)
        result = svc.create(TENANT_A, NotificationCreate(
            type="system_alert", title="T", body="B"
        ))
        assert result.user_id is None


class TestNotificationServiceList:
    def test_returns_notification_list_schema(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.list_notifications(TENANT_A, USER_A1, page=1, size=20)
        assert isinstance(result, NotificationList)
        assert result.total > 0
        assert all(isinstance(n, NotificationRead) for n in result.items)

    def test_pagination_math_correct(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.list_notifications(TENANT_A, USER_A1, page=1, size=2)
        assert result.page == 1
        assert result.size == 2
        assert result.total_pages == max(1, -(-result.total // 2))
        assert result.has_prev is False
        if result.total > 2:
            assert result.has_next is True

    def test_page_2_has_prev(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.list_notifications(TENANT_A, USER_A1, page=2, size=2)
        assert result.has_prev is True

    def test_pages_are_disjoint(self, db_session, seeded):
        svc = NotificationService(db_session)
        p1 = {n.id for n in svc.list_notifications(TENANT_A, USER_A1, page=1, size=2).items}
        p2 = {n.id for n in svc.list_notifications(TENANT_A, USER_A1, page=2, size=2).items}
        assert p1.isdisjoint(p2)

    def test_unread_comes_before_read(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.list_notifications(TENANT_A, USER_A1, page=1, size=100)
        reads = [n.read for n in result.items]
        flipped = False
        for r in reads:
            if not flipped and r:
                flipped = True
            elif flipped and not r:
                pytest.fail("Ordering violated: read notification appeared before unread")

    def test_no_cross_tenant_items(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.list_notifications(TENANT_A, USER_A1, page=1, size=100)
        for n in result.items:
            assert n.tenant_id == TENANT_A


class TestNotificationServiceUnreadCount:
    def test_returns_correct_count(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.get_unread_count(TENANT_A, USER_A1)
        assert result.unread_count == 4  # 2 wide + 2 own

    def test_zero_after_mark_all_read(self, db_session, seeded):
        svc = NotificationService(db_session)
        svc.mark_all_read(TENANT_A, USER_A1)
        result = svc.get_unread_count(TENANT_A, USER_A1)
        assert result.unread_count == 0


class TestNotificationServiceMarkRead:
    def test_marks_notification_read(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.mark_read(
            seeded["a1_unread_1"].id, TENANT_A, USER_A1
        )
        assert isinstance(result, NotificationRead)
        assert result.read is True
        assert result.read_at is not None

    def test_raises_not_found_cross_tenant(self, db_session, seeded):
        svc = NotificationService(db_session)
        with pytest.raises(NotFoundError):
            svc.mark_read(seeded["a1_unread_1"].id, TENANT_B, USER_B1)

    def test_raises_forbidden_wrong_user(self, db_session, seeded):
        svc = NotificationService(db_session)
        with pytest.raises(ForbiddenError):
            svc.mark_read(seeded["a1_unread_1"].id, TENANT_A, USER_A2)


class TestNotificationServiceMarkAllRead:
    def test_returns_updated_count(self, db_session, seeded):
        svc = NotificationService(db_session)
        result = svc.mark_all_read(TENANT_A, USER_A1)
        assert result["updated"] == 4

    def test_unread_becomes_zero(self, db_session, seeded):
        svc = NotificationService(db_session)
        svc.mark_all_read(TENANT_A, USER_A1)
        assert svc.get_unread_count(TENANT_A, USER_A1).unread_count == 0

    def test_other_tenant_unaffected(self, db_session, seeded):
        svc = NotificationService(db_session)
        before = svc.get_unread_count(TENANT_B, USER_B1).unread_count
        svc.mark_all_read(TENANT_A, USER_A1)
        after = svc.get_unread_count(TENANT_B, USER_B1).unread_count
        assert after == before


# ---------------------------------------------------------------------------
# EventService
# ---------------------------------------------------------------------------

class TestEventServiceMemberInvited:
    def test_creates_tenant_wide_notification(self, db_session):
        svc = EventService(db_session)
        result = svc.member_invited(
            tenant_id=TENANT_A,
            invited_by="Alice",
            invitee_name="Eve",
            invitee_email="eve@example.com",
        )
        assert result.type == "member_invited"
        assert result.user_id is None
        assert result.tenant_id == TENANT_A
        assert "Eve" in result.title

    def test_visible_to_all_users_in_tenant(self, db_session):
        event_svc = EventService(db_session)
        notif_svc = NotificationService(db_session)
        n = event_svc.member_invited(TENANT_A, "Alice", "Eve", "e@e.com")
        a1_ids = {x.id for x in notif_svc.list_notifications(TENANT_A, USER_A1, page=1, size=100).items}
        a2_ids = {x.id for x in notif_svc.list_notifications(TENANT_A, USER_A2, page=1, size=100).items}
        assert n.id in a1_ids
        assert n.id in a2_ids


class TestEventServiceCreatorReply:
    def test_creates_user_specific_notification(self, db_session):
        svc = EventService(db_session)
        result = svc.creator_reply(
            tenant_id=TENANT_A,
            recipient_user_id=USER_A1,
            creator_handle="@test_creator",
            preview="Let's talk!",
        )
        assert result.type == "new_reply"
        assert result.user_id == USER_A1
        assert "@test_creator" in result.title

    def test_only_recipient_can_see_it(self, db_session):
        event_svc = EventService(db_session)
        notif_svc = NotificationService(db_session)
        n = event_svc.creator_reply(TENANT_A, USER_A1, "@c", "hi")
        a1_ids = {x.id for x in notif_svc.list_notifications(TENANT_A, USER_A1, page=1, size=100).items}
        a2_ids = {x.id for x in notif_svc.list_notifications(TENANT_A, USER_A2, page=1, size=100).items}
        assert n.id in a1_ids
        assert n.id not in a2_ids

    def test_preview_truncated_at_120_chars(self, db_session):
        svc = EventService(db_session)
        long_preview = "x" * 200
        result = svc.creator_reply(TENANT_A, USER_A1, "@c", long_preview)
        assert "..." in result.body
        assert len(result.body) < len(long_preview) + 50
