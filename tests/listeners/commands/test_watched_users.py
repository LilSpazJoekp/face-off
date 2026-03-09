"""Tests for watched_users command handler."""

from unittest.mock import Mock, patch

import pytest

from app.listeners.commands.watched_users import watched_users_callback


class TestWatchedUsersCommand:
    """Tests for the watched_users_callback handler."""

    @patch("app.listeners.commands.watched_users.get_watched_users")
    def test_shows_watched_users(
        self, mock_get_users: Mock, mock_ack: Mock, mock_respond: Mock
    ) -> None:
        """Test that watched users are displayed."""
        mock_get_users.return_value = ["U123", "U456", "U789"]

        watched_users_callback(ack=mock_ack, respond=mock_respond)

        mock_ack.assert_called_once()
        mock_respond.assert_called_once()
        response_text = mock_respond.call_args.args[0]
        assert "<@U123>" in response_text
        assert "<@U456>" in response_text
        assert "<@U789>" in response_text

    @pytest.mark.parametrize("watched_users", [[], None])
    @patch("app.listeners.commands.watched_users.get_watched_users")
    def test_no_watched_users(
        self,
        mock_get_users: Mock,
        watched_users: list[str] | None,
        mock_ack: Mock,
        mock_respond: Mock,
    ) -> None:
        """Test response when no users are being watched or result is None."""
        mock_get_users.return_value = watched_users

        watched_users_callback(ack=mock_ack, respond=mock_respond)

        mock_ack.assert_called_once()
        mock_respond.assert_called_once()
        response_text = mock_respond.call_args.args[0]
        assert "No users" in response_text
