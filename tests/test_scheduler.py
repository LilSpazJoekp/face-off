"""Tests for scheduler module."""

from unittest.mock import patch

import pytest

from app.scheduler import (
    format_week_label,
    build_user_poll_blocks,
    create_weekly_poll,
)


class TestFormatWeekLabel:
    """Tests for the format_week_label function."""

    def test_valid_week_key(self):
        """Test formatting a valid week key."""
        result = format_week_label("2024-W01")
        # Should return something like "Jan 01"
        assert result is not None
        assert len(result) > 0

    def test_invalid_week_key(self):
        """Test handling of invalid week key."""
        result = format_week_label("invalid")
        assert result == "invalid"


class TestBuildUserPollBlocks:
    """Tests for the build_user_poll_blocks function."""

    @pytest.fixture
    def user_with_two_pictures(self, make_user_poll_data, make_picture_data):
        """User data with two pictures for poll blocks."""
        pictures = [
            make_picture_data(
                picture_id=1,
                avatar_url="https://example.com/pic1.jpg",
                week="2024-W01",
                duration="2d 5h",
                timestamp="2024-01-15T10:30:00",
            ),
            make_picture_data(
                picture_id=2,
                avatar_url="https://example.com/pic2.jpg",
                week="2024-W02",
                duration="3h 30m",
                timestamp="2024-01-22T14:00:00",
            ),
        ]
        return make_user_poll_data(user_id="U123", pictures=pictures)

    @pytest.fixture
    def user_with_one_picture(self, make_user_poll_data, make_picture_data):
        """User data with single picture."""
        pictures = [
            make_picture_data(
                picture_id=1,
                avatar_url="https://example.com/pic1.jpg",
                week="2024-W01",
                duration="2d 5h",
                timestamp="2024-01-15T10:30:00",
            ),
        ]
        return make_user_poll_data(user_id="U123", pictures=pictures)

    @patch("app.scheduler.get_user_total_votes")
    @patch("app.scheduler.get_picture_vote_count")
    def test_builds_blocks_with_pictures_and_vote_buttons(
        self,
        mock_get_votes,
        mock_get_total,
        user_with_two_pictures,
    ):
        """Test that poll blocks show pictures inline with vote buttons."""
        mock_get_votes.return_value = 5
        mock_get_total.return_value = 10

        blocks = build_user_poll_blocks("poll_123", user_with_two_pictures)

        # First block should have user mention
        assert blocks[0]["type"] == "section"
        assert "<@U123>" in blocks[0]["text"]["text"]

        # Should have image blocks for each picture
        image_blocks = [b for b in blocks if b.get("type") == "image"]
        assert len(image_blocks) == 2
        assert image_blocks[0]["image_url"] == "https://example.com/pic1.jpg"
        assert image_blocks[1]["image_url"] == "https://example.com/pic2.jpg"

        # Should have vote buttons as section accessories
        section_with_buttons = [
            b
            for b in blocks
            if b.get("type") == "section"
            and b.get("accessory", {}).get("action_id") == "vote_pfp"
        ]
        assert len(section_with_buttons) == 2

        # Check button values include picture IDs
        assert section_with_buttons[0]["accessory"]["value"] == "poll_123:1:U123"
        assert section_with_buttons[1]["accessory"]["value"] == "poll_123:2:U123"

        # Last block should be divider
        assert blocks[-1]["type"] == "divider"

    @patch("app.scheduler.get_user_total_votes")
    @patch("app.scheduler.get_picture_vote_count")
    def test_single_picture(
        self, mock_get_votes, mock_get_total, user_with_one_picture
    ):
        """Test with single picture."""
        mock_get_votes.return_value = 1
        mock_get_total.return_value = 1

        blocks = build_user_poll_blocks("poll_123", user_with_one_picture)

        image_blocks = [b for b in blocks if b.get("type") == "image"]
        assert len(image_blocks) == 1

    @patch("app.scheduler.get_user_total_votes")
    @patch("app.scheduler.get_picture_vote_count")
    def test_single_vote_pluralization(
        self, mock_get_votes, mock_get_total, user_with_one_picture
    ):
        """Test vote count with singular 'vote'."""
        mock_get_votes.return_value = 1
        mock_get_total.return_value = 1

        blocks = build_user_poll_blocks("poll_123", user_with_one_picture)

        # Find section with vote count
        vote_sections = [
            b
            for b in blocks
            if b.get("type") == "section"
            and b.get("accessory", {}).get("action_id") == "vote_pfp"
        ]
        assert len(vote_sections) == 1
        # Should say "1 vote" not "1 votes"
        assert "*1*" in vote_sections[0]["text"]["text"]
        assert "vote" in vote_sections[0]["text"]["text"]

    @patch("app.scheduler.get_user_total_votes")
    @patch("app.scheduler.get_picture_vote_count")
    def test_zero_votes(self, mock_get_votes, mock_get_total, user_with_one_picture):
        """Test vote count with zero votes."""
        mock_get_votes.return_value = 0
        mock_get_total.return_value = 0

        blocks = build_user_poll_blocks("poll_123", user_with_one_picture)

        vote_sections = [
            b
            for b in blocks
            if b.get("type") == "section"
            and b.get("accessory", {}).get("action_id") == "vote_pfp"
        ]
        assert "*0*" in vote_sections[0]["text"]["text"]
        assert "votes" in vote_sections[0]["text"]["text"]


class TestCreateWeeklyPoll:
    """Tests for the create_weekly_poll function."""

    @pytest.fixture
    def poll_changes_data(self, make_user_poll_data, make_picture_data):
        """Sample changes data for poll creation."""
        return {
            "U456": {
                "user_id": "U456",
                "display_name": "User One",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic1.jpg",
                        "week": "2024-W01",
                        "duration": "2d",
                    }
                ],
            },
            "U789": {
                "user_id": "U789",
                "display_name": "User Two",
                "pictures": [
                    {
                        "avatar_url": "https://example.com/pic2.jpg",
                        "week": "2024-W01",
                        "duration": "1d",
                    }
                ],
            },
        }

    @pytest.fixture
    def poll_data_after_creation(self):
        """Poll data structure returned after creation."""
        return {
            "users": {
                "U456": {
                    "user_id": "U456",
                    "display_name": "User One",
                    "pictures": [
                        {
                            "id": 1,
                            "avatar_url": "https://example.com/pic1.jpg",
                            "week": "2024-W01",
                            "duration": "2d",
                            "timestamp": "2024-01-15T10:00:00",
                        }
                    ],
                },
                "U789": {
                    "user_id": "U789",
                    "display_name": "User Two",
                    "pictures": [
                        {
                            "id": 2,
                            "avatar_url": "https://example.com/pic2.jpg",
                            "week": "2024-W01",
                            "duration": "1d",
                            "timestamp": "2024-01-16T10:00:00",
                        }
                    ],
                },
            }
        }

    @patch("app.scheduler.get_poll_duration_hours")
    @patch("app.scheduler.save_poll_summary_ts")
    @patch("app.scheduler.save_poll_message_ts")
    @patch("app.scheduler.get_all_pictures_with_votes")
    @patch("app.scheduler.get_user_total_votes")
    @patch("app.scheduler.get_notification_channel")
    @patch("app.scheduler.get_changes_by_user")
    @patch("app.scheduler.create_poll")
    @patch("app.scheduler.get_poll")
    @patch("app.scheduler.get_picture_vote_count")
    @patch("app.scheduler.get_max_votes")
    def test_creates_poll_successfully(
        self,
        mock_get_max,
        mock_get_vote_count,
        mock_get_poll,
        mock_create_poll,
        mock_get_changes,
        mock_get_channel,
        mock_get_user_votes,
        mock_get_all_pics,
        mock_save_message_ts,
        mock_save_summary_ts,
        mock_get_duration,
        mock_client,
        poll_changes_data,
        poll_data_after_creation,
    ):
        """Test that a poll is created with correct messages."""
        mock_get_channel.return_value = "C123"
        mock_get_duration.return_value = 24
        mock_get_changes.return_value = poll_changes_data
        mock_get_poll.return_value = poll_data_after_creation
        mock_get_vote_count.return_value = 0
        mock_get_max.return_value = 3
        mock_get_user_votes.return_value = 0
        mock_get_all_pics.return_value = []

        create_weekly_poll(mock_client)

        mock_get_channel.assert_called_once()
        mock_get_changes.assert_called_once()
        mock_create_poll.assert_called_once()

        # Should have 4 messages: header + 2 user polls + summary
        assert mock_client.chat_postMessage.call_count == 4

        # Check header message mentions max votes and week dates
        first_call = mock_client.chat_postMessage.call_args_list[0]
        header_blocks = first_call.kwargs["blocks"]
        header_text = header_blocks[1]["text"]["text"]
        assert "participated" in header_text
        # Max votes in separate section now
        votes_text = header_blocks[2]["text"]["text"]
        assert "3" in votes_text  # max votes

    @patch("app.scheduler.get_notification_channel")
    def test_skips_when_no_channel(self, mock_get_channel, mock_client):
        """Test that poll is skipped when no channel is configured."""
        mock_get_channel.return_value = None

        create_weekly_poll(mock_client)

        mock_client.chat_postMessage.assert_not_called()

    @patch("app.scheduler.get_notification_channel")
    @patch("app.scheduler.get_changes_by_user")
    def test_skips_when_no_changes(
        self, mock_get_changes, mock_get_channel, mock_client
    ):
        """Test that poll is skipped when there are no changes."""
        mock_get_channel.return_value = "C123"
        mock_get_changes.return_value = {}

        create_weekly_poll(mock_client)

        mock_client.chat_postMessage.assert_not_called()

    @patch("app.scheduler.get_notification_channel")
    @patch("app.scheduler.get_changes_by_user")
    def test_skips_when_changes_none(
        self, mock_get_changes, mock_get_channel, mock_client
    ):
        """Test that poll is skipped when changes is None."""
        mock_get_channel.return_value = "C123"
        mock_get_changes.return_value = None

        create_weekly_poll(mock_client)

        mock_client.chat_postMessage.assert_not_called()
