"""
Repository layer tests.

Covers all 6 methods of NotificationRepository:
  create, find_visible, find_by_id, count_unread, mark_read, mark_all_read

Tenant isolation is verified in every read/write path.
"""

import pytest
from app.core.exceptions import ForbiddenError, NotFoundError
from app.repositories.notification_repository import NotificationRepository
from tests.conftest import (
    TENANT_A, TENANT_B, USER_A1, USER_A2, USER_B1,
    make_notification,
)


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------

class TestCreate:
    def test_creates_with_correct_fields(self, db_session):
        repo = NotificationRepository(db_session)
        n = repo.create(
            tenant_id=TENANT_A,
            type="success",
            title="Hello",
            body="Body text",
            user_id=USER_A1,
        )
        assert n.id is not None
        assert n.tenant_id == TENANT_A
        assert n.user_id == USER_A1
        assert n.type == "success"
        assert n.title == "Hello"
        assert n.body == "Body text"
        assert n.read is False
        assert n.created_at is not None
        assert n.read_at is None

    def test_creates_tenant_wide_when_no_user(self, db_session):
        repo = NotificationRepository(db_session)
        n = repo.create(tenant_id=TENANT_A, type="system_alert",
                        title="T", body="B")
        assert n.user_id is None

    def test_persists_to_db(self, db_session):
        repo = NotificationRepository(db_session)
        n = repo.create(tenant_id=TENANT_A, type="warning", title="T", body="B")
        fetched = repo.find_by_id(n.id, TENANT_A)
        assert fetched.id == n.id


# ---------------------------------------------------------------------------
# find_visible()
# ---------------------------------------------------------------------------

class TestFindVisible:
    def test_user_sees_own_and_tenant_wide(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        items, total = repo.find_visible(TENANT_A, USER_A1, offset=0, limit=100)
        ids = {n.id for n in items}

        # Should see tenant-wide
        assert seeded["a_wide_unread_1"].id in ids
        assert seeded["a_wide_unread_2"].id in ids
        assert seeded["a_wide_read"].id in ids

        # Should see own notifications
        assert seeded["a1_unread_1"].id in ids
        assert seeded["a1_unread_2"].id in ids
        assert seeded["a1_read"].id in ids

        # Must NOT see other user's private notifications
        assert seeded["a2_unread"].id not in ids
        assert seeded["a2_read"].id not in ids

    def test_user_cannot_see_other_tenant(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        items, _ = repo.find_visible(TENANT_A, USER_A1, offset=0, limit=100)
        ids = {n.id for n in items}
        assert seeded["b_wide_unread"].id not in ids
        assert seeded["b1_unread"].id not in ids

    def test_tenant_wide_caller_sees_only_wide(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        items, total = repo.find_visible(TENANT_A, None, offset=0, limit=100)
        for n in items:
            assert n.user_id is None, f"Tenant-level caller saw user-specific: {n.id}"

    def test_ordering_unread_first_then_newest(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        items, _ = repo.find_visible(TENANT_A, USER_A1, offset=0, limit=100)
        reads = [n.read for n in items]
        flipped = False
        for r in reads:
            if not flipped and r:
                flipped = True
            elif flipped and not r:
                pytest.fail(f"Ordering violated: {reads}")

    def test_pagination_offset_limit(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        all_items, total = repo.find_visible(TENANT_A, USER_A1, offset=0, limit=100)
        page1, _ = repo.find_visible(TENANT_A, USER_A1, offset=0, limit=2)
        page2, _ = repo.find_visible(TENANT_A, USER_A1, offset=2, limit=2)
        assert len(page1) == 2
        assert len(page2) == 2
        ids1 = {n.id for n in page1}
        ids2 = {n.id for n in page2}
        assert ids1.isdisjoint(ids2), "Pages must not overlap"

    def test_total_count_matches_reality(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        items, total = repo.find_visible(TENANT_A, USER_A1, offset=0, limit=100)
        assert total == len(items)

    def test_empty_when_no_notifications(self, db_session):
        repo = NotificationRepository(db_session)
        items, total = repo.find_visible("no-such-tenant", "no-user", offset=0, limit=100)
        assert items == []
        assert total == 0


# ---------------------------------------------------------------------------
# find_by_id()
# ---------------------------------------------------------------------------

class TestFindById:
    def test_finds_existing_notification(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        n = repo.find_by_id(seeded["a_wide_unread_1"].id, TENANT_A)
        assert n.id == seeded["a_wide_unread_1"].id

    def test_raises_not_found_for_wrong_tenant(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        with pytest.raises(NotFoundError):
            repo.find_by_id(seeded["a_wide_unread_1"].id, TENANT_B)

    def test_raises_not_found_for_missing_id(self, db_session):
        repo = NotificationRepository(db_session)
        with pytest.raises(NotFoundError):
            repo.find_by_id("00000000-0000-0000-0000-000000000000", TENANT_A)


# ---------------------------------------------------------------------------
# count_unread()
# ---------------------------------------------------------------------------

class TestCountUnread:
    def test_counts_visible_unread_only(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        # A1 sees: 2 tenant-wide unread + 2 own unread = 4
        count = repo.count_unread(TENANT_A, USER_A1)
        assert count == 4

    def test_does_not_count_read(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        # Mark all A1-visible as read
        repo.mark_all_read(TENANT_A, USER_A1)
        count = repo.count_unread(TENANT_A, USER_A1)
        assert count == 0

    def test_tenant_level_caller_counts_only_wide(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        # Tenant-wide caller sees only user_id=NULL rows: 2 unread
        count = repo.count_unread(TENANT_A, None)
        assert count == 2

    def test_isolated_from_other_tenant(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        count_a = repo.count_unread(TENANT_A, USER_A1)
        count_b = repo.count_unread(TENANT_B, USER_B1)
        # Each tenant's count is independent
        assert count_a > 0
        assert count_b > 0
        # Marking all read for A must not change B
        repo.mark_all_read(TENANT_A, USER_A1)
        count_b_after = repo.count_unread(TENANT_B, USER_B1)
        assert count_b_after == count_b


# ---------------------------------------------------------------------------
# mark_read()
# ---------------------------------------------------------------------------

class TestMarkRead:
    def test_marks_tenant_wide_notification(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        n = repo.mark_read(seeded["a_wide_unread_1"].id, TENANT_A, USER_A1)
        assert n.read is True
        assert n.read_at is not None

    def test_marks_own_notification(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        n = repo.mark_read(seeded["a1_unread_1"].id, TENANT_A, USER_A1)
        assert n.read is True

    def test_idempotent_on_already_read(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        # Already read
        n = repo.mark_read(seeded["a1_read"].id, TENANT_A, USER_A1)
        assert n.read is True  # no error, still read

    def test_raises_forbidden_for_other_users_notification(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        # A2 tries to mark A1's private notification
        with pytest.raises(ForbiddenError):
            repo.mark_read(seeded["a1_unread_1"].id, TENANT_A, USER_A2)

    def test_raises_not_found_cross_tenant(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        with pytest.raises(NotFoundError):
            repo.mark_read(seeded["a_wide_unread_1"].id, TENANT_B, USER_B1)

    def test_raises_not_found_missing_id(self, db_session):
        repo = NotificationRepository(db_session)
        with pytest.raises(NotFoundError):
            repo.mark_read("00000000-0000-0000-0000-000000000000", TENANT_A, USER_A1)

    def test_decrements_unread_count(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        before = repo.count_unread(TENANT_A, USER_A1)
        repo.mark_read(seeded["a1_unread_1"].id, TENANT_A, USER_A1)
        after = repo.count_unread(TENANT_A, USER_A1)
        assert after == before - 1


# ---------------------------------------------------------------------------
# mark_all_read()
# ---------------------------------------------------------------------------

class TestMarkAllRead:
    def test_marks_all_visible_unread(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        updated = repo.mark_all_read(TENANT_A, USER_A1)
        assert updated > 0
        assert repo.count_unread(TENANT_A, USER_A1) == 0

    def test_returns_count_of_updated_rows(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        # A1 visible unread = 2 wide + 2 own = 4
        updated = repo.mark_all_read(TENANT_A, USER_A1)
        assert updated == 4

    def test_idempotent_on_second_call(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        repo.mark_all_read(TENANT_A, USER_A1)
        updated2 = repo.mark_all_read(TENANT_A, USER_A1)
        assert updated2 == 0

    def test_does_not_affect_other_tenant(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        before_b = repo.count_unread(TENANT_B, USER_B1)
        repo.mark_all_read(TENANT_A, USER_A1)
        after_b = repo.count_unread(TENANT_B, USER_B1)
        assert after_b == before_b

    def test_does_not_affect_other_user_same_tenant(self, db_session, seeded):
        repo = NotificationRepository(db_session)
        # A1's mark_all_read marks: 2 tenant-wide + 2 A1-specific = 4 rows.
        # A2 sees: 2 tenant-wide + 1 A2-specific = 3 total unread.
        # After A1 marks all, the 2 tenant-wide rows become read.
        # A2's private unread (a2_unread) is NOT touched.
        before_a2 = repo.count_unread(TENANT_A, USER_A2)  # 3: 2 wide + 1 private
        assert before_a2 == 3

        repo.mark_all_read(TENANT_A, USER_A1)

        after_a2 = repo.count_unread(TENANT_A, USER_A2)   # 1: only private remains
        assert after_a2 == 1, (
            "A2 should still have 1 unread (own private notification) after A1's mark_all_read"
        )
