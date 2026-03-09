"""Tests for settings action handlers."""

from unittest.mock import patch

import pytest

from app.listeners.actions.settings import open_channel_modal_callback


class TestOpenChannelModal:
    """Tests for the open_channel_modal_callback handler."""

    @pytest.fixture
    def trigger_body(self, make_slack_user_body):
        """Body with trigger_id for modal tests."""
        return make_slack_user_body(trigger_id="trigger_123")

    @patch("app.listeners.actions.settings.get_notification_channel")
    def test_opens_modal_with_current_channel(
        self, mock_get_channel, mock_ack, mock_client, trigger_body
    ) -> None:
        """Test that the channel modal opens with current channel selected."""
        mock_get_channel.return_value = "C123"

        open_channel_modal_callback(ack=mock_ack, body=trigger_body, client=mock_client)

        mock_ack.assert_called_once()
        mock_client.views_open.assert_called_once()

        call_kwargs = mock_client.views_open.call_args.kwargs
        assert call_kwargs["trigger_id"] == "trigger_123"
        assert call_kwargs["view"]["type"] == "modal"
        assert call_kwargs["view"]["callback_id"] == "channel_modal_submit"

        # Check initial_channel is set
        channel_input = call_kwargs["view"]["blocks"][1]["element"]
        assert channel_input["initial_channel"] == "C123"

    @patch("app.listeners.actions.settings.get_notification_channel")
    def test_opens_modal_without_current_channel(
        self, mock_get_channel, mock_ack, mock_client, trigger_body
    ) -> None:
        """Test that the channel modal opens when no channel is configured."""
        mock_get_channel.return_value = None

        open_channel_modal_callback(ack=mock_ack, body=trigger_body, client=mock_client)

        mock_ack.assert_called_once()
        mock_client.views_open.assert_called_once()

        call_kwargs = mock_client.views_open.call_args.kwargs
        channel_input = call_kwargs["view"]["blocks"][1]["element"]
        assert "initial_channel" not in channel_input
