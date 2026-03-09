"""Tests for add_user_modal view handler."""

from unittest.mock import patch

from app.listeners.views.add_user_modal import add_user_modal_callback


class TestAddUserModalCallback:
    """Tests for the add_user_modal_callback handler."""

    @patch("app.listeners.views.add_user_modal.is_user_watched")
    @patch("app.listeners.views.add_user_modal.is_consent_pending")
    @patch("app.listeners.views.add_user_modal.add_pending_consent")
    @patch("app.listeners.views.add_user_modal.build_home_view")
    def test_adds_pending_consent(
        self,
        mock_build_home,
        mock_add_consent,
        mock_is_pending,
        mock_is_watched,
        mock_ack,
        mock_client,
        sample_user_body,
        user_select_view,
    ) -> None:
        """Test that pending consent is added for new user."""
        mock_is_watched.return_value = False
        mock_is_pending.return_value = False
        mock_add_consent.return_value = True
        mock_build_home.return_value = {"type": "home", "blocks": []}

        add_user_modal_callback(
            ack=mock_ack,
            body=sample_user_body,
            client=mock_client,
            view=user_select_view,
        )

        mock_ack.assert_called_once_with()
        mock_add_consent.assert_called_once_with("U456", "U789")
        mock_build_home.assert_called_once_with("U789")
        mock_client.views_publish.assert_called_once()

    @patch("app.listeners.views.add_user_modal.is_user_watched")
    def test_error_for_already_watched_user(
        self,
        mock_is_watched,
        mock_ack,
        mock_client,
        sample_user_body,
        user_select_view,
    ) -> None:
        """Test error is returned when user is already watched."""
        mock_is_watched.return_value = True

        add_user_modal_callback(
            ack=mock_ack,
            body=sample_user_body,
            client=mock_client,
            view=user_select_view,
        )

        mock_ack.assert_called_once_with(
            response_action="errors",
            errors={"user_select_block": "This user is already on the watch list."},
        )
        mock_client.views_publish.assert_not_called()

    @patch("app.listeners.views.add_user_modal.is_user_watched")
    @patch("app.listeners.views.add_user_modal.is_consent_pending")
    def test_error_for_pending_consent(
        self,
        mock_is_pending,
        mock_is_watched,
        mock_ack,
        mock_client,
        sample_user_body,
        user_select_view,
    ) -> None:
        """Test error is returned when consent is already pending."""
        mock_is_watched.return_value = False
        mock_is_pending.return_value = True

        add_user_modal_callback(
            ack=mock_ack,
            body=sample_user_body,
            client=mock_client,
            view=user_select_view,
        )

        mock_ack.assert_called_once_with(
            response_action="errors",
            errors={
                "user_select_block": "A consent request is already pending for this user."
            },
        )
        mock_client.views_publish.assert_not_called()
