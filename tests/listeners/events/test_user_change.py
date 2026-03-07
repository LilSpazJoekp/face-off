"""Tests for user_change event handler."""

from unittest.mock import patch

from app.listeners.events.user_change import user_change_callback


class TestUserChangeEvent:
    """Tests for the user_change_callback handler."""

    @patch("app.listeners.events.user_change.save_change_notification_ts")
    @patch("app.listeners.events.user_change.get_watched_users")
    @patch("app.listeners.events.user_change.get_notification_channel")
    @patch("app.listeners.events.user_change.record_profile_change")
    def test_records_change_for_watched_user(
        self,
        mock_record,
        mock_get_channel,
        mock_get_users,
        mock_save_ts,
        mock_client,
        sample_user_event,
    ):
        """Test that profile change is recorded for a watched user."""
        mock_get_users.return_value = ["U789"]
        mock_get_channel.return_value = "C123"
        mock_record.return_value = "change_123"

        user_change_callback(event=sample_user_event, client=mock_client)

        mock_get_users.assert_called_once()
        mock_record.assert_called_once_with(
            "U789", "Test User", "https://example.com/avatar.jpg"
        )
        mock_client.chat_postMessage.assert_called_once()
        mock_save_ts.assert_called_once()

    @patch("app.listeners.events.user_change.get_watched_users")
    def test_ignores_unwatched_user(
        self, mock_get_users, mock_client, sample_user_event
    ):
        """Test that changes from unwatched users are ignored."""
        mock_get_users.return_value = ["U111", "U222"]

        user_change_callback(event=sample_user_event, client=mock_client)

        mock_get_users.assert_called_once()
        mock_client.chat_postMessage.assert_not_called()

    @patch("app.listeners.events.user_change.get_watched_users")
    @patch("app.listeners.events.user_change.get_notification_channel")
    def test_no_notification_channel(
        self, mock_get_channel, mock_get_users, mock_client, sample_user_event
    ):
        """Test handling when no notification channel is configured."""
        mock_get_users.return_value = ["U789"]
        mock_get_channel.return_value = None

        user_change_callback(event=sample_user_event, client=mock_client)

        mock_client.chat_postMessage.assert_not_called()

    @patch("app.listeners.events.user_change.get_watched_users")
    @patch("app.listeners.events.user_change.get_notification_channel")
    @patch("app.listeners.events.user_change.record_profile_change")
    def test_duplicate_avatar_skipped(
        self,
        mock_record,
        mock_get_channel,
        mock_get_users,
        mock_client,
        sample_user_event,
    ):
        """Test that duplicate avatars are not notified."""
        mock_get_users.return_value = ["U789"]
        mock_get_channel.return_value = "C123"
        mock_record.return_value = None  # Duplicate

        user_change_callback(event=sample_user_event, client=mock_client)

        mock_client.chat_postMessage.assert_not_called()

    def test_no_user_id(self, mock_client):
        """Test handling when user id is missing."""
        event = {"user": {}}

        user_change_callback(event=event, client=mock_client)

        mock_client.chat_postMessage.assert_not_called()

    @patch("app.listeners.events.user_change.get_watched_users")
    def test_empty_watched_list(self, mock_get_users, mock_client, sample_user_event):
        """Test handling when watched list is empty."""
        mock_get_users.return_value = []

        user_change_callback(event=sample_user_event, client=mock_client)

        mock_client.chat_postMessage.assert_not_called()

    @patch("app.listeners.events.user_change.save_change_notification_ts")
    @patch("app.listeners.events.user_change.get_watched_users")
    @patch("app.listeners.events.user_change.get_notification_channel")
    @patch("app.listeners.events.user_change.record_profile_change")
    def test_uses_fallback_display_name(
        self,
        mock_record,
        mock_get_channel,
        mock_get_users,
        mock_save_ts,
        mock_client,
        make_user_change_event,
    ):
        """Test that fallback display name is used when display_name is empty."""
        mock_get_users.return_value = ["U789"]
        mock_get_channel.return_value = "C123"
        mock_record.return_value = "change_123"

        event = make_user_change_event(display_name="", real_name="Real Name")

        user_change_callback(event=event, client=mock_client)

        # Should use real_name as fallback
        mock_record.assert_called_once_with(
            "U789", "Real Name", "https://example.com/avatar.jpg"
        )

    @patch("app.listeners.events.user_change.save_change_notification_ts")
    @patch("app.listeners.events.user_change.get_watched_users")
    @patch("app.listeners.events.user_change.get_notification_channel")
    @patch("app.listeners.events.user_change.record_profile_change")
    def test_uses_image_512_fallback(
        self,
        mock_record,
        mock_get_channel,
        mock_get_users,
        mock_save_ts,
        mock_client,
        make_user_change_event,
    ):
        """Test that image_512 is used when image_original is not available."""
        mock_get_users.return_value = ["U789"]
        mock_get_channel.return_value = "C123"
        mock_record.return_value = "change_123"

        event = make_user_change_event(
            image_original=None, image_512="https://example.com/avatar512.jpg"
        )
        # Remove image_original from profile to test fallback
        del event["user"]["profile"]["image_original"]

        user_change_callback(event=event, client=mock_client)

        mock_record.assert_called_once_with(
            "U789", "Test User", "https://example.com/avatar512.jpg"
        )
