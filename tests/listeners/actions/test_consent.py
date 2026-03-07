"""Tests for consent action handlers."""

from unittest.mock import patch

from app.listeners.actions.consent import (
    consent_accept_callback,
    consent_decline_callback,
)


class TestConsentAccept:
    """Tests for the consent_accept_callback handler."""

    @patch("app.listeners.actions.consent.is_consent_pending")
    @patch("app.listeners.actions.consent.add_watched_user")
    @patch("app.listeners.actions.consent.build_home_view")
    def test_accepts_consent_and_adds_user(
        self,
        mock_build_home,
        mock_add_user,
        mock_is_pending,
        mock_ack,
        mock_client,
        sample_user_body,
    ):
        """Test that accepting consent adds user to watch list."""
        mock_is_pending.return_value = True
        mock_add_user.return_value = True
        mock_build_home.return_value = {"type": "home", "blocks": []}

        consent_accept_callback(ack=mock_ack, body=sample_user_body, client=mock_client)

        mock_ack.assert_called_once()
        mock_is_pending.assert_called_once_with("U789")
        mock_add_user.assert_called_once_with("U789")
        mock_build_home.assert_called_once_with("U789")
        mock_client.views_publish.assert_called_once()

    @patch("app.listeners.actions.consent.is_consent_pending")
    @patch("app.listeners.actions.consent.add_watched_user")
    def test_no_pending_consent(
        self, mock_add_user, mock_is_pending, mock_ack, mock_client, sample_user_body
    ):
        """Test handling when there's no pending consent."""
        mock_is_pending.return_value = False

        consent_accept_callback(ack=mock_ack, body=sample_user_body, client=mock_client)

        mock_ack.assert_called_once()
        mock_add_user.assert_not_called()
        mock_client.views_publish.assert_not_called()


class TestConsentDecline:
    """Tests for the consent_decline_callback handler."""

    @patch("app.listeners.actions.consent.remove_pending_consent")
    @patch("app.listeners.actions.consent.build_home_view")
    def test_declines_consent(
        self,
        mock_build_home,
        mock_remove_pending,
        mock_ack,
        mock_client,
        sample_user_body,
    ):
        """Test that declining consent removes pending request."""
        mock_build_home.return_value = {"type": "home", "blocks": []}

        consent_decline_callback(
            ack=mock_ack, body=sample_user_body, client=mock_client
        )

        mock_ack.assert_called_once()
        mock_remove_pending.assert_called_once_with("U789")
        mock_build_home.assert_called_once_with("U789")
        mock_client.views_publish.assert_called_once()
