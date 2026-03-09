"""Tests for watchlist action handlers."""

from unittest.mock import patch

import pytest

from app.listeners.actions.watchlist import (
    open_add_user_modal_callback,
    remove_self_from_watchlist_callback,
    remove_watched_user_callback,
)


class TestOpenAddUserModal:
    """Tests for the open_add_user_modal_callback handler."""

    @pytest.fixture
    def trigger_body(self, make_slack_user_body):
        """Body with trigger_id for modal tests."""
        return make_slack_user_body(trigger_id="trigger_123")

    def test_opens_modal(self, mock_ack, mock_client, trigger_body) -> None:
        """Test that the add user modal is opened."""
        open_add_user_modal_callback(
            ack=mock_ack, body=trigger_body, client=mock_client
        )

        mock_ack.assert_called_once()
        mock_client.views_open.assert_called_once()

        call_kwargs = mock_client.views_open.call_args.kwargs
        assert call_kwargs["trigger_id"] == "trigger_123"
        assert call_kwargs["view"]["type"] == "modal"
        assert call_kwargs["view"]["callback_id"] == "add_user_modal_submit"


class TestRemoveWatchedUser:
    """Tests for the remove_watched_user_callback handler."""

    @pytest.fixture
    def remove_user_body(self, make_slack_action_body):
        """Body for remove user action."""
        return make_slack_action_body(action_value="U456", user_id="U789")

    @patch("app.listeners.actions.watchlist.remove_watched_user")
    @patch("app.listeners.actions.watchlist.build_home_view")
    def test_removes_user_and_refreshes_home(
        self,
        mock_build_home,
        mock_remove,
        mock_ack,
        mock_client,
        remove_user_body,
    ) -> None:
        """Test that a user is removed and home view refreshed."""
        mock_remove.return_value = True
        mock_build_home.return_value = {"type": "home", "blocks": []}

        remove_watched_user_callback(
            ack=mock_ack, body=remove_user_body, client=mock_client
        )

        mock_ack.assert_called_once()
        mock_remove.assert_called_once_with("U456")
        mock_build_home.assert_called_once_with("U789")
        mock_client.views_publish.assert_called_once()

    @patch("app.listeners.actions.watchlist.remove_watched_user")
    @patch("app.listeners.actions.watchlist.build_home_view")
    def test_user_not_found(
        self, mock_build_home, mock_remove, mock_ack, mock_client, remove_user_body
    ) -> None:
        """Test handling when user is not in watch list."""
        mock_remove.return_value = False
        mock_build_home.return_value = {"type": "home", "blocks": []}

        remove_watched_user_callback(
            ack=mock_ack, body=remove_user_body, client=mock_client
        )

        mock_ack.assert_called_once()
        # Home view should still be refreshed
        mock_client.views_publish.assert_called_once()


class TestRemoveSelfFromWatchlist:
    """Tests for the remove_self_from_watchlist_callback handler."""

    @patch("app.listeners.actions.watchlist.remove_watched_user")
    @patch("app.listeners.actions.watchlist.build_home_view")
    def test_removes_self_and_refreshes_home(
        self,
        mock_build_home,
        mock_remove,
        mock_ack,
        mock_client,
        sample_user_body,
    ) -> None:
        """Test that a user can remove themselves."""
        mock_remove.return_value = True
        mock_build_home.return_value = {"type": "home", "blocks": []}

        remove_self_from_watchlist_callback(
            ack=mock_ack, body=sample_user_body, client=mock_client
        )

        mock_ack.assert_called_once()
        mock_remove.assert_called_once_with("U789")
        mock_build_home.assert_called_once_with("U789")
        mock_client.views_publish.assert_called_once()
