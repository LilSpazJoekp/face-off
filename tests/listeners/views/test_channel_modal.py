"""Tests for channel_modal view handler."""

from unittest.mock import patch

from app.listeners.views.channel_modal import channel_modal_callback


class TestChannelModalCallback:
    """Tests for the channel_modal_callback handler."""

    @patch("app.listeners.views.channel_modal.set_notification_channel")
    @patch("app.listeners.views.channel_modal.build_home_view")
    def test_sets_notification_channel(
        self,
        mock_build_home,
        mock_set_channel,
        mock_ack,
        mock_client,
        sample_user_body,
        channel_select_view,
    ):
        """Test that notification channel is set."""
        mock_build_home.return_value = {"type": "home", "blocks": []}

        channel_modal_callback(
            ack=mock_ack,
            body=sample_user_body,
            client=mock_client,
            view=channel_select_view,
        )

        mock_ack.assert_called_once()
        mock_client.conversations_join.assert_called_once_with(channel="C123")
        mock_set_channel.assert_called_once_with("C123")
        mock_build_home.assert_called_once_with("U789")
        mock_client.views_publish.assert_called_once()

    @patch("app.listeners.views.channel_modal.set_notification_channel")
    @patch("app.listeners.views.channel_modal.build_home_view")
    def test_handles_join_failure(
        self,
        mock_build_home,
        mock_set_channel,
        mock_ack,
        mock_client,
        sample_user_body,
        channel_select_view,
    ):
        """Test that channel join failure is handled gracefully."""
        mock_client.conversations_join.side_effect = Exception("Already in channel")
        mock_build_home.return_value = {"type": "home", "blocks": []}

        channel_modal_callback(
            ack=mock_ack,
            body=sample_user_body,
            client=mock_client,
            view=channel_select_view,
        )

        # Should still set the channel despite join failure
        mock_ack.assert_called_once()
        mock_set_channel.assert_called_once_with("C123")
        mock_client.views_publish.assert_called_once()
