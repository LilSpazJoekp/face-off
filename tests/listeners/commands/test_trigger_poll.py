"""Tests for trigger_poll command handler."""

from unittest.mock import Mock, patch

from app.listeners.commands.trigger_poll import trigger_poll_callback


class TestTriggerPollCommand:
    """Tests for the trigger_poll_callback handler."""

    @patch("app.scheduler.create_weekly_poll")
    def test_triggers_poll_successfully(
        self,
        mock_create_poll: Mock,
        mock_ack: Mock,
        mock_respond: Mock,
        mock_client: Mock,
    ) -> None:
        """Test that the poll is triggered and response sent."""
        trigger_poll_callback(ack=mock_ack, respond=mock_respond, client=mock_client)

        mock_ack.assert_called_once()
        mock_create_poll.assert_called_once_with(mock_client, manual=True)
        mock_respond.assert_called_once()
        assert "triggered" in mock_respond.call_args.args[0].lower()
