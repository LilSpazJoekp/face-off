"""Tests for storage module using SQLite."""

import logging
from datetime import datetime, timedelta

from typing import Any

from app.models import Poll, PollCandidate
from app.storage import (
    CT_TIMEZONE,
    add_pending_consent,
    add_watched_user,
    create_poll,
    get_change_duration,
    get_changes_by_user,
    get_max_votes,
    get_notification_channel,
    get_pending_consent,
    get_picture_vote_count,
    get_poll,
    get_user_total_votes,
    get_voter_remaining_votes,
    get_voter_votes,
    get_watched_users,
    has_voted_for_picture,
    is_consent_pending,
    is_user_watched,
    record_profile_change,
    record_vote,
    remove_pending_consent,
    remove_vote,
    remove_watched_user,
    set_max_votes,
    set_notification_channel,
)

test_logger = logging.getLogger(__name__)


def _get_candidate(poll: Poll, user_id: str) -> PollCandidate:
    """Find a candidate by user_id from a Poll model."""
    return next(
        candidate for candidate in poll.candidates if candidate.user_id == user_id
    )


class TestRecordProfileChange:
    def test_records_new_change(self) -> None:
        """Test recording a new profile change."""
        result = record_profile_change(
            "U123", "Test User", "https://example.com/avatar.jpg"
        )

        # Returns change_id string if successful
        assert result is not None
        assert isinstance(result, str)

    def test_detects_duplicate_avatar(self) -> None:
        """Test that duplicate avatars are detected."""
        # First call should succeed
        result1 = record_profile_change(
            "U123", "Test User", "https://example.com/avatar.jpg"
        )

        # Second call with same avatar should return None
        result2 = record_profile_change(
            "U123", "Test User", "https://example.com/avatar.jpg"
        )

        assert result1 is not None
        assert result2 is None

    def test_different_avatars_recorded(self) -> None:
        """Test that different avatars are recorded."""
        result1 = record_profile_change(
            "U123", "Test User", "https://example.com/avatar1.jpg"
        )
        result2 = record_profile_change(
            "U123", "Test User", "https://example.com/avatar2.jpg"
        )

        assert result1 is not None
        assert result2 is not None


class TestGetChangeDuration:
    def test_duration_days_hours(self) -> None:
        """Test duration formatting with days and hours."""
        now = datetime.now(CT_TIMEZONE)
        change = {
            "timestamp": (now - timedelta(days=2, hours=5)).isoformat(),
            "ended_at": now.isoformat(),
        }

        result = get_change_duration(change)
        assert "2d" in result
        assert "h" in result

    def test_duration_hours_minutes(self) -> None:
        """Test duration formatting with hours and minutes."""
        now = datetime.now(CT_TIMEZONE)
        change = {
            "timestamp": (now - timedelta(hours=3, minutes=30)).isoformat(),
            "ended_at": now.isoformat(),
        }

        result = get_change_duration(change)
        assert "3h" in result
        assert "m" in result

    def test_duration_minutes_only(self) -> None:
        """Test duration formatting with minutes only."""
        now = datetime.now(CT_TIMEZONE)
        change = {
            "timestamp": (now - timedelta(minutes=45)).isoformat(),
            "ended_at": now.isoformat(),
        }

        result = get_change_duration(change)
        assert "45m" in result

    def test_duration_ongoing(self) -> None:
        """Test duration for ongoing change (no ended_at)."""
        now = datetime.now(CT_TIMEZONE)
        change = {
            "timestamp": (now - timedelta(hours=1)).isoformat(),
            "ended_at": None,
        }

        result = get_change_duration(change)
        assert "1h" in result


class TestGetChangesByUser:
    def test_organizes_changes_by_user(self) -> None:
        """Test that changes are organized by user."""
        record_profile_change("U123", "User One", "https://example.com/pic1.jpg")
        record_profile_change("U456", "User Two", "https://example.com/pic2.jpg")

        result = get_changes_by_user()

        assert "U123" in result
        assert "U456" in result
        assert result["U123"][0].display_name == "User One"
        assert len(result["U123"]) == 1


class TestPollFunctions:
    def test_create_poll(self) -> None:
        """Test creating a poll."""
        users = {
            "U123": {
                "user_id": "U123",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic1.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                ],
            }
        }

        result = create_poll("poll_123", users)

        assert result.poll_id == "poll_123"
        assert any(candidate.user_id == "U123" for candidate in result.candidates)

    def test_create_poll_with_pictures(self) -> None:
        """Test creating a poll includes picture IDs."""
        users = {
            "U123": {
                "user_id": "U123",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic1.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                ],
            }
        }
        create_poll("poll_123", users)

        poll = get_poll("poll_123")
        candidate = _get_candidate(poll, "U123")
        pictures = candidate.pictures
        assert len(pictures) == 1
        assert pictures[0].id is not None

    def test_record_vote(self) -> None:
        """Test recording a vote for a picture."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic1.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                ],
            }
        }
        create_poll("poll_123", users)
        poll = get_poll("poll_123")
        picture_id = _get_candidate(poll, "U456").pictures[0].id

        result = record_vote("poll_123", "voter1", picture_id)

        assert result is True
        assert get_picture_vote_count("poll_123", picture_id) == 1

    def test_record_vote_poll_not_found(self) -> None:
        """Test recording vote when poll doesn't exist."""
        result = record_vote("nonexistent_poll", "U789", 999)

        assert result is False

    def test_record_vote_respects_max_votes(self) -> None:
        """Test that voting stops when max votes is reached."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": f"https://example.com/pic{i}.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                    for i in range(5)
                ],
            }
        }
        create_poll("poll_123", users)
        poll = get_poll("poll_123")
        pictures = _get_candidate(poll, "U456").pictures

        # Set max votes to 3
        set_max_votes(3)

        # Vote for 3 pictures should succeed
        for i in range(3):
            result = record_vote("poll_123", "voter1", pictures[i].id)
            assert result is True

        # 4th vote should fail
        result = record_vote("poll_123", "voter1", pictures[3].id)
        assert result is False

    def test_record_vote_same_picture_twice(self) -> None:
        """Test that voting for the same picture twice fails."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic1.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                ],
            }
        }
        create_poll("poll_123", users)
        poll = get_poll("poll_123")
        picture_id = _get_candidate(poll, "U456").pictures[0].id

        # First vote succeeds
        result1 = record_vote("poll_123", "voter1", picture_id)
        assert result1 is True

        # Second vote for same picture fails
        result2 = record_vote("poll_123", "voter1", picture_id)
        assert result2 is False

    def test_remove_vote(self) -> None:
        """Test removing a vote."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic1.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                ],
            }
        }
        create_poll("poll_123", users)
        poll = get_poll("poll_123")
        picture_id = _get_candidate(poll, "U456").pictures[0].id

        record_vote("poll_123", "voter1", picture_id)
        assert get_picture_vote_count("poll_123", picture_id) == 1

        result = remove_vote("poll_123", "voter1", picture_id)

        assert result is True
        assert get_picture_vote_count("poll_123", picture_id) == 0

    def test_remove_vote_not_found(self) -> None:
        """Test removing a vote that doesn't exist."""
        result = remove_vote("poll_123", "voter1", 999)
        assert result is False

    def test_has_voted_for_picture(self) -> None:
        """Test checking if voter voted for a picture."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic1.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                ],
            }
        }
        create_poll("poll_123", users)
        poll = get_poll("poll_123")
        picture_id = _get_candidate(poll, "U456").pictures[0].id

        assert has_voted_for_picture("poll_123", "voter1", picture_id) is False

        record_vote("poll_123", "voter1", picture_id)

        assert has_voted_for_picture("poll_123", "voter1", picture_id) is True

    def test_get_poll(self) -> None:
        """Test getting a poll."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic1.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                ],
            }
        }
        create_poll("poll_123", users)

        result = get_poll("poll_123")

        assert result.poll_id == "poll_123"
        candidate = _get_candidate(result, "U456")
        assert candidate.pictures[0].id is not None

    def test_get_poll_not_found(self) -> None:
        """Test getting a poll that doesn't exist."""
        result = get_poll("nonexistent_poll")

        assert result is None

    def test_get_voter_votes(self) -> None:
        """Test getting a voter's votes."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": f"https://example.com/pic{i}.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                    for i in range(3)
                ],
            }
        }
        create_poll("poll_123", users)
        poll = get_poll("poll_123")
        pictures = _get_candidate(poll, "U456").pictures

        record_vote("poll_123", "voter1", pictures[0].id)
        record_vote("poll_123", "voter1", pictures[2].id)

        result = get_voter_votes("poll_123", "voter1")

        assert pictures[0].id in result
        assert pictures[2].id in result
        assert len(result) == 2

    def test_get_voter_votes_no_votes(self) -> None:
        """Test getting votes when voter hasn't voted."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [],
            }
        }
        create_poll("poll_123", users)

        result = get_voter_votes("poll_123", "voter1")

        assert result == []

    def test_get_voter_remaining_votes(self) -> None:
        """Test getting remaining votes for a voter."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": f"https://example.com/pic{i}.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                    for i in range(3)
                ],
            }
        }
        create_poll("poll_123", users)
        poll = get_poll("poll_123")
        pictures = _get_candidate(poll, "U456").pictures
        set_max_votes(3)

        assert get_voter_remaining_votes("poll_123", "voter1") == 3

        record_vote("poll_123", "voter1", pictures[0].id)
        assert get_voter_remaining_votes("poll_123", "voter1") == 2

        record_vote("poll_123", "voter1", pictures[1].id)
        assert get_voter_remaining_votes("poll_123", "voter1") == 1

    def test_get_user_total_votes(self) -> None:
        """Test getting total votes for a user's pictures."""
        users = {
            "U456": {
                "user_id": "U456",
                "display_name": "User",
                "pictures": [
                    {
                        "avatar_url": f"https://example.com/pic{i}.jpg",
                        "duration": "2d",
                        "week": "2024-W01",
                        "timestamp": datetime.now(CT_TIMEZONE).isoformat(),
                    }
                    for i in range(2)
                ],
            }
        }
        create_poll("poll_123", users)
        poll = get_poll("poll_123")
        pictures = _get_candidate(poll, "U456").pictures

        # Multiple voters vote for this user's pictures
        record_vote("poll_123", "voter1", pictures[0].id)
        record_vote("poll_123", "voter2", pictures[0].id)
        record_vote("poll_123", "voter3", pictures[1].id)

        result = get_user_total_votes("poll_123", "U456")

        assert result == 3


class TestWatchedUsers:
    def test_get_watched_users_empty(self) -> None:
        """Test getting watched users when empty."""
        result = get_watched_users()

        assert result == []

    def test_add_and_get_watched_users(self) -> None:
        """Test adding and getting watched users."""
        add_watched_user("U123")
        add_watched_user("U456")

        result = get_watched_users()

        assert "U123" in result
        assert "U456" in result

    def test_is_user_watched_true(self) -> None:
        """Test checking if user is watched (true case)."""
        add_watched_user("U123")

        result = is_user_watched("U123")

        assert result is True

    def test_is_user_watched_false(self) -> None:
        """Test checking if user is watched (false case)."""
        result = is_user_watched("U123")

        assert result is False

    def test_add_watched_user_new(self) -> None:
        """Test adding a new watched user."""
        result = add_watched_user("U123")

        assert result is True
        assert is_user_watched("U123")

    def test_add_watched_user_already_exists(self) -> None:
        """Test adding a user who is already watched."""
        add_watched_user("U123")

        result = add_watched_user("U123")

        assert result is False

    def test_remove_watched_user_exists(self) -> None:
        """Test removing a watched user."""
        add_watched_user("U123")

        result = remove_watched_user("U123")

        assert result is True
        assert not is_user_watched("U123")

    def test_remove_watched_user_not_found(self) -> None:
        """Test removing a user who is not watched."""
        result = remove_watched_user("U123")

        assert result is False


class TestPendingConsent:
    def test_add_pending_consent(self) -> None:
        """Test adding pending consent."""
        result = add_pending_consent("U123", "U789")

        assert result is True
        assert is_consent_pending("U123")

    def test_add_pending_consent_already_watched(self) -> None:
        """Test adding consent for already watched user."""
        add_watched_user("U123")

        result = add_pending_consent("U123", "U789")

        assert result is False

    def test_add_pending_consent_already_pending(self) -> None:
        """Test adding consent when already pending."""
        add_pending_consent("U123", "U789")

        result = add_pending_consent("U123", "U456")

        assert result is False

    def test_get_pending_consent(self) -> None:
        """Test getting pending consent."""
        add_pending_consent("U123", "U789")

        result = get_pending_consent("U123")

        assert result.user_id == "U123"
        assert result.requested_by == "U789"

    def test_get_pending_consent_not_found(self) -> None:
        """Test getting pending consent when not found."""
        result = get_pending_consent("U123")

        assert result is None

    def test_is_consent_pending_true(self) -> None:
        """Test checking if consent is pending (true case)."""
        add_pending_consent("U123", "U789")

        result = is_consent_pending("U123")

        assert result is True

    def test_is_consent_pending_false(self) -> None:
        """Test checking if consent is pending (false case)."""
        result = is_consent_pending("U123")

        assert result is False

    def test_remove_pending_consent(self) -> None:
        """Test removing pending consent."""
        add_pending_consent("U123", "U789")

        result = remove_pending_consent("U123")

        assert result is True
        assert not is_consent_pending("U123")

    def test_add_watched_user_removes_pending_consent(self) -> None:
        """Test that adding a watched user removes pending consent."""
        add_pending_consent("U123", "U789")
        assert is_consent_pending("U123")

        add_watched_user("U123")

        assert not is_consent_pending("U123")


class TestNotificationChannel:
    def test_get_notification_channel_not_set(self) -> None:
        """Test getting channel when not configured."""
        result = get_notification_channel()

        assert result is None

    def test_set_and_get_notification_channel(self) -> None:
        """Test setting and getting the notification channel."""
        set_notification_channel("C123")

        result = get_notification_channel()

        assert result == "C123"

    def test_update_notification_channel(self) -> None:
        """Test updating the notification channel."""
        set_notification_channel("C123")
        set_notification_channel("C456")

        result = get_notification_channel()

        assert result == "C456"


class TestMaxVotes:
    def test_get_max_votes_default(self) -> None:
        """Test getting max votes returns default when not set."""
        result = get_max_votes()

        assert result == 3

    def test_set_and_get_max_votes(self) -> None:
        """Test setting and getting max votes."""
        set_max_votes(5)

        result = get_max_votes()

        assert result == 5

    def test_update_max_votes(self) -> None:
        """Test updating max votes."""
        set_max_votes(3)
        set_max_votes(10)

        result = get_max_votes()

        assert result == 10
