from unittest.mock import patch

import pytest

from app.listeners.events.app_home_opened import app_home_opened_callback


class TestAppHomeOpened:
    """Tests for the app_home_opened_callback handler."""

    @pytest.fixture
    def home_event(self, make_app_home_event):
        """App home opened event fixture."""
        return make_app_home_event(user_id="U123")

    @pytest.fixture
    def mock_app_home_dependencies(self):
        """Fixture that patches all app home dependencies."""
        with (
            patch(
                "app.listeners.events.app_home_opened.get_poll_duration_hours"
            ) as mock_duration,
            patch("app.listeners.events.app_home_opened.get_poll_hour") as mock_hour,
            patch("app.listeners.events.app_home_opened.get_poll_day") as mock_day,
            patch(
                "app.listeners.events.app_home_opened.get_watched_users"
            ) as mock_users,
            patch(
                "app.listeners.events.app_home_opened.is_user_watched"
            ) as mock_watched,
            patch(
                "app.listeners.events.app_home_opened.is_consent_pending"
            ) as mock_pending,
            patch(
                "app.listeners.events.app_home_opened.get_notification_channel"
            ) as mock_channel,
        ):
            mock_users.return_value = []
            mock_watched.return_value = False
            mock_pending.return_value = False
            mock_channel.return_value = None
            mock_day.return_value = "thu"
            mock_hour.return_value = 15
            mock_duration.return_value = 24
            yield {
                "get_poll_duration_hours": mock_duration,
                "get_poll_hour": mock_hour,
                "get_poll_day": mock_day,
                "get_watched_users": mock_users,
                "is_user_watched": mock_watched,
                "is_consent_pending": mock_pending,
                "get_notification_channel": mock_channel,
            }

    def test_app_home_opened_callback(
        self, mock_client, home_event, mock_app_home_dependencies
    ):
        """Test that app home view is published correctly."""
        app_home_opened_callback(client=mock_client, event=home_event)

        mock_client.views_publish.assert_called_once()
        kwargs = mock_client.views_publish.call_args.kwargs
        assert kwargs["user_id"] == home_event["user"]
        assert kwargs["view"] is not None

    def test_event_tab_not_home(self, mock_client, make_app_home_event):
        """Test that non-home tab events are ignored."""
        event = make_app_home_event(tab="about")

        app_home_opened_callback(client=mock_client, event=event)

        mock_client.views_publish.assert_not_called()

    def test_views_publish_exception(
        self, mock_client, home_event, mock_app_home_dependencies
    ):
        """Test that exception in views_publish is handled gracefully."""
        mock_client.views_publish.side_effect = Exception("test exception")

        # Should not raise - exception is handled internally
        app_home_opened_callback(client=mock_client, event=home_event)

        mock_client.views_publish.assert_called_once()
