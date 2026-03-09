"""Tests for user_change event handler."""

from unittest.mock import patch

from app.listeners.events.user_change import user_change_callback


class TestUserChangeEvent:
    """Tests for the user_change_callback handler."""

    @patch("app.listeners.events.user_change.ProfileChangeService.process_user_change")
    def test_calls_process_user_change(
        self,
        mock_process,
        mock_client,
        sample_user_event,
    ):
        """Test that user_change_callback calls ProfileChangeService.process_user_change."""
        user_change_callback(event=sample_user_event, client=mock_client)

        mock_process.assert_called_once_with(sample_user_event["user"], mock_client)

    def test_no_user_id(self, mock_client):
        """Test handling when user id is missing."""
        event = {"user": {}}

        user_change_callback(event=event, client=mock_client)

        # It should still call process_user_change, which handles missing user_id
        with patch(
            "app.listeners.events.user_change.ProfileChangeService.process_user_change"
        ) as mock_process:
            user_change_callback(event=event, client=mock_client)
            mock_process.assert_called_once_with({}, mock_client)
