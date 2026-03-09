"""Pytest configuration and fixtures."""

import os
from collections.abc import Callable, Generator
from datetime import datetime
from typing import Any
from unittest.mock import Mock

# Set dummy environment variables before importing app modules
# This prevents the Slack App from failing during import in tests
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test-token")
os.environ.setdefault("SLACK_SIGNING_SECRET", "test-signing-secret")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import database
from app.models import Base

# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def setup_test_db() -> Generator[None]:
    """Set up an in-memory SQLite database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    database._db_state["engine"] = engine
    database._db_state["session_factory"] = sessionmaker(
        bind=engine, expire_on_commit=False
    )

    yield

    database.reset_engine()


# =============================================================================
# Slack Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_ack() -> Mock:
    """Mock Slack ack function."""
    return Mock()


@pytest.fixture
def mock_client() -> Mock:
    """Mock Slack WebClient with common return values configured."""
    client = Mock()
    client.chat_postMessage.return_value = {"ts": "1234567890.123456"}
    client.chat_update.return_value = {"ts": "1234567890.123456"}
    client.chat_postEphemeral.return_value = {"ok": True}
    client.views_open.return_value = {"ok": True}
    client.views_publish.return_value = {"ok": True}
    client.views_update.return_value = {"ok": True}
    return client


@pytest.fixture
def mock_respond() -> Mock:
    """Mock Slack respond function for slash commands."""
    return Mock()


# =============================================================================
# Slack Body/Event Factory Fixtures
# =============================================================================


@pytest.fixture
def make_slack_user_body() -> Callable[..., dict[str, Any]]:
    """Factory fixture for creating Slack request bodies with user info."""

    def _make_body(
        user_id: str = "U789",
        trigger_id: str | None = None,
        channel_id: str | None = None,
        message_ts: str | None = None,
    ) -> dict[str, Any]:
        body = {"user": {"id": user_id}}
        if trigger_id:
            body["trigger_id"] = trigger_id
        if channel_id:
            body["channel"] = {"id": channel_id}
        if message_ts:
            body["message"] = {"ts": message_ts}
        return body

    return _make_body


@pytest.fixture
def make_slack_action_body(
    make_slack_user_body: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    """Factory fixture for creating Slack action request bodies."""

    def _make_body(
        action_value: str,
        user_id: str = "U789",
        trigger_id: str | None = None,
        channel_id: str | None = None,
        message_ts: str | None = None,
    ) -> dict[str, Any]:
        body = make_slack_user_body(
            user_id=user_id,
            trigger_id=trigger_id,
            channel_id=channel_id,
            message_ts=message_ts,
        )
        body["actions"] = [{"value": action_value}]
        return body

    return _make_body


@pytest.fixture
def make_user_change_event() -> Callable[..., dict[str, Any]]:
    """Factory fixture for creating Slack user_change events."""

    def _make_event(
        user_id: str = "U789",
        display_name: str = "Test User",
        real_name: str = "Test User Real",
        username: str = "testuser",
        image_original: str = "https://example.com/avatar.jpg",
        image_512: str = "https://example.com/avatar512.jpg",
    ) -> dict[str, Any]:
        return {
            "user": {
                "id": user_id,
                "name": username,
                "profile": {
                    "display_name": display_name,
                    "real_name": real_name,
                    "image_original": image_original,
                    "image_512": image_512,
                },
            }
        }

    return _make_event


@pytest.fixture
def make_app_home_event() -> Callable[..., dict[str, Any]]:
    """Factory fixture for creating Slack app_home_opened events."""

    def _make_event(user_id: str = "U123", tab: str = "home") -> dict[str, Any]:
        return {"tab": tab, "user": user_id}

    return _make_event


# =============================================================================
# Poll Data Factory Fixtures
# =============================================================================


@pytest.fixture
def make_picture_data() -> Callable[..., dict[str, Any]]:
    """Factory fixture for creating picture data."""

    def _make_picture(
        picture_id: int = 1,
        avatar_url: str = "https://example.com/pic.jpg",
        duration: str = "2d 5h",
        week: str = "2024-W01",
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        return {
            "id": picture_id,
            "avatar_url": avatar_url,
            "duration": duration,
            "week": week,
            "timestamp": timestamp or datetime.now().isoformat(),
        }

    return _make_picture


@pytest.fixture
def make_user_poll_data(
    make_picture_data: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    """Factory fixture for creating user poll data."""

    def _make_user_data(
        user_id: str = "U456",
        display_name: str = "Test User",
        pictures: list[dict[str, Any]] | None = None,
        num_pictures: int = 1,
    ) -> dict[str, Any]:
        if pictures is None:
            pictures = [
                make_picture_data(
                    picture_id=i + 1, avatar_url=f"https://example.com/pic{i + 1}.jpg"
                )
                for i in range(num_pictures)
            ]
        return {
            "user_id": user_id,
            "display_name": display_name,
            "pictures": pictures,
        }

    return _make_user_data


@pytest.fixture
def make_poll(
    make_user_poll_data: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    """Factory fixture for creating poll data."""

    def _make_poll(
        poll_id: str = "poll_123",
        users: dict[str, Any] | None = None,
        user_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        if users is None:
            if user_ids:
                users = {uid: make_user_poll_data(user_id=uid) for uid in user_ids}
            else:
                users = {"U456": make_user_poll_data()}
        return {"id": poll_id, "users": users}

    return _make_poll


# =============================================================================
# Convenience Fixtures (Pre-configured common cases)
# =============================================================================


@pytest.fixture
def sample_user_body(
    make_slack_user_body: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Pre-configured user body for simple action tests."""
    return make_slack_user_body(user_id="U789")


@pytest.fixture
def sample_vote_body(
    make_slack_action_body: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Pre-configured body for vote action tests."""
    return make_slack_action_body(
        action_value="poll_123:1:U456",
        user_id="U789",
        channel_id="C123",
        message_ts="1234567890.123456",
    )


@pytest.fixture
def sample_user_event(
    make_user_change_event: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Pre-configured user change event."""
    return make_user_change_event()


@pytest.fixture
def sample_poll(make_poll: Callable[..., dict[str, Any]]) -> dict[str, Any]:
    """Pre-configured poll with single user and picture."""
    return make_poll()


# =============================================================================
# Modal View Fixtures
# =============================================================================


@pytest.fixture
def make_modal_view() -> Callable[..., dict[str, Any]]:
    """Factory fixture for creating Slack modal view state structures."""

    def _make_view(
        block_id: str, action_id: str, value_type: str, value: Any
    ) -> dict[str, Any]:
        """Create a modal view structure.

        :param block_id: The block ID containing the input
        :param action_id: The action ID of the input element
        :param value_type: The type of value (e.g., 'selected_user', 'selected_channel',
            'value')
        :param value: The actual value

        """
        return {"state": {"values": {block_id: {action_id: {value_type: value}}}}}

    return _make_view


@pytest.fixture
def user_select_view(
    make_modal_view: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Pre-configured view for user selection modal."""
    return make_modal_view(
        block_id="user_select_block",
        action_id="user_select",
        value_type="selected_user",
        value="U456",
    )


@pytest.fixture
def channel_select_view(
    make_modal_view: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Pre-configured view for channel selection modal."""
    return make_modal_view(
        block_id="channel_select_block",
        action_id="channel_select",
        value_type="selected_channel",
        value="C123",
    )
