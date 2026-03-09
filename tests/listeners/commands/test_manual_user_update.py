"""Tests for manual_user_update command handler."""

from unittest.mock import patch

from app.listeners.commands.manual_user_update import manual_user_update_callback


class TestManualUserUpdateCommand:
    """Tests for the manual_user_update_callback handler."""

    @patch(
        "app.listeners.commands.manual_user_update.ProfileChangeService.process_user_change"
    )
    def test_manual_update_success(
        self, mock_process_change, mock_ack, mock_respond, mock_client
    ) -> None:
        """Test that a manual update is processed successfully."""
        user_id = "U123"
        command = {"user_id": "U789", "text": f"<@{user_id}>"}

        # We need to mock get_watched_users which is imported inside the function
        with patch(
            "app.listeners.commands.watched_users.get_watched_users"
        ) as mock_get_watched:
            mock_get_watched.return_value = [user_id]
            mock_client.users_info.return_value = {
                "ok": True,
                "user": {"id": user_id, "profile": {}},
            }
            mock_process_change.return_value = "change_123"

            manual_user_update_callback(
                ack=mock_ack, respond=mock_respond, command=command, client=mock_client
            )

        mock_ack.assert_called_once()
        mock_client.users_info.assert_called_once_with(user=user_id)
        mock_process_change.assert_called_once()
        mock_respond.assert_called_once()
        assert "successfully" in mock_respond.call_args.args[0].lower()

    def test_manual_update_user_not_watched(self, mock_ack, mock_respond, mock_client) -> None:
        """Test response when user is not in the watched list."""
        user_id = "U123"
        command = {"user_id": "U789", "text": f"<@{user_id}>"}

        with patch(
            "app.listeners.commands.watched_users.get_watched_users"
        ) as mock_get_watched:
            mock_get_watched.return_value = []
            mock_client.users_info.return_value = {"ok": True, "user": {"id": user_id}}

            manual_user_update_callback(
                ack=mock_ack, respond=mock_respond, command=command, client=mock_client
            )

        mock_ack.assert_called_once()
        mock_respond.assert_called_once()
        assert "not in the watched users list" in mock_respond.call_args.args[0].lower()

    def test_manual_update_no_user_found(self, mock_ack, mock_respond, mock_client) -> None:
        """Test response when Slack user is not found."""
        user_id = "U123"
        command = {"user_id": "U789", "text": f"<@{user_id}>"}
        mock_client.users_info.return_value = {"ok": False}

        manual_user_update_callback(
            ack=mock_ack, respond=mock_respond, command=command, client=mock_client
        )

        mock_ack.assert_called_once()
        mock_respond.assert_called_once()
        assert "could not find user" in mock_respond.call_args.args[0].lower()

    @patch(
        "app.listeners.commands.manual_user_update.ProfileChangeService.process_user_change"
    )
    def test_manual_update_no_new_change(
        self, mock_process_change, mock_ack, mock_respond, mock_client
    ) -> None:
        """Test response when no new profile picture change is detected."""
        user_id = "U123"
        command = {"user_id": "U789", "text": f"<@{user_id}>"}

        with patch(
            "app.listeners.commands.watched_users.get_watched_users"
        ) as mock_get_watched:
            mock_get_watched.return_value = [user_id]
            mock_client.users_info.return_value = {"ok": True, "user": {"id": user_id}}
            mock_process_change.return_value = None

            manual_user_update_callback(
                ack=mock_ack, respond=mock_respond, command=command, client=mock_client
            )

        mock_ack.assert_called_once()
        mock_respond.assert_called_once()
        assert (
            "no new profile picture update detected"
            in mock_respond.call_args.args[0].lower()
        )
