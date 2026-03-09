"""Tests for view_pictures action handler."""

from unittest.mock import patch

import pytest

from app.listeners.actions.view_pictures import (
    build_pictures_modal,
    view_pictures_callback,
)


class TestViewPicturesCallback:
    """Tests for the view_pictures_callback handler."""

    @pytest.fixture
    def view_pictures_body(self, make_slack_action_body):
        """Action body for view pictures."""
        return make_slack_action_body(
            action_value="poll_123:U456",
            user_id="U789",
            trigger_id="trigger_123",
        )

    @patch("app.listeners.actions.view_pictures.get_poll")
    @patch("app.listeners.actions.view_pictures.get_voter_votes")
    @patch("app.listeners.actions.view_pictures.get_max_votes")
    def test_opens_modal(
        self,
        mock_get_max,
        mock_get_votes,
        mock_get_poll,
        mock_ack,
        mock_client,
        view_pictures_body,
        sample_poll,
    ) -> None:
        """Test that the pictures modal is opened."""
        mock_get_poll.return_value = sample_poll
        mock_get_votes.return_value = []
        mock_get_max.return_value = 3

        view_pictures_callback(
            ack=mock_ack, body=view_pictures_body, client=mock_client
        )

        mock_ack.assert_called_once()
        mock_get_poll.assert_called_once_with("poll_123")
        mock_client.views_open.assert_called_once()

        call_kwargs = mock_client.views_open.call_args.kwargs
        assert call_kwargs["trigger_id"] == "trigger_123"
        assert call_kwargs["view"]["type"] == "modal"

    @patch("app.listeners.actions.view_pictures.get_poll")
    def test_poll_not_found(
        self, mock_get_poll, mock_ack, mock_client, view_pictures_body
    ) -> None:
        """Test handling when poll doesn't exist."""
        mock_get_poll.return_value = None

        view_pictures_callback(
            ack=mock_ack, body=view_pictures_body, client=mock_client
        )

        mock_ack.assert_called_once()
        mock_client.views_open.assert_not_called()

    def test_invalid_value_format(self, mock_ack, mock_client, make_slack_action_body) -> None:
        """Test handling of invalid action value format."""
        body = make_slack_action_body(action_value="invalid", trigger_id="trigger_123")

        view_pictures_callback(ack=mock_ack, body=body, client=mock_client)

        mock_ack.assert_called_once()
        mock_client.views_open.assert_not_called()


class TestBuildPicturesModal:
    """Tests for the build_pictures_modal function."""

    @pytest.fixture
    def poll_with_pictures(self, make_poll, make_user_poll_data, make_picture_data):
        """Poll with multiple pictures for modal tests."""
        pictures = [
            make_picture_data(
                picture_id=1,
                avatar_url="https://example.com/pic1.jpg",
                duration="2d",
                week="2024-W01",
            ),
            make_picture_data(
                picture_id=2,
                avatar_url="https://example.com/pic2.jpg",
                duration="1d",
                week="2024-W02",
            ),
        ]
        user_data = make_user_poll_data(user_id="U456", pictures=pictures)
        return make_poll(users={"U456": user_data})

    @patch("app.listeners.actions.view_pictures.get_picture_vote_count")
    def test_builds_modal_with_pictures(self, mock_vote_count, poll_with_pictures) -> None:
        """Test that modal is built with pictures and vote buttons."""
        mock_vote_count.return_value = 2

        view = build_pictures_modal(
            poll_id="poll_123",
            user_id="U456",
            poll=poll_with_pictures,
            voter_votes=[1],  # Voted for picture 1
            max_votes=3,
        )

        assert view["type"] == "modal"
        assert "Test User" in view["title"]["text"]

        # Should have remaining votes info
        first_block = view["blocks"][0]
        assert "2" in first_block["text"]["text"]  # 2 remaining
        assert "3" in first_block["text"]["text"]  # of 3 max

    @patch("app.listeners.actions.view_pictures.get_picture_vote_count")
    def test_shows_voted_status(self, mock_vote_count, sample_poll) -> None:
        """Test that voted pictures show voted status."""
        mock_vote_count.return_value = 1

        view = build_pictures_modal(
            poll_id="poll_123",
            user_id="U456",
            poll=sample_poll,
            voter_votes=[1],  # Voted for this picture
            max_votes=3,
        )

        # Find the context block with vote info
        context_blocks = [b for b in view["blocks"] if b.get("type") == "context"]
        assert any("You voted" in str(b) for b in context_blocks)

    @patch("app.listeners.actions.view_pictures.get_picture_vote_count")
    def test_user_not_found(self, mock_vote_count) -> None:
        """Test handling when user not in poll."""
        poll = {"users": {}}

        view = build_pictures_modal(
            poll_id="poll_123",
            user_id="U456",
            poll=poll,
            voter_votes=[],
            max_votes=3,
        )

        assert view["type"] == "modal"
        assert "Error" in view["title"]["text"]
