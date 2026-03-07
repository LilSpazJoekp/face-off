"""Tests for vote_pfp action handler."""

from unittest.mock import patch

import pytest

from app.listeners.actions.vote_pfp import vote_pfp_callback


class TestVotePfpCallback:
    """Tests for the vote_pfp_callback handler."""

    @pytest.fixture
    def vote_body(self, sample_vote_body):
        """Vote action body fixture."""
        return sample_vote_body

    @patch("app.scheduler.update_poll_summary")
    @patch("app.scheduler.build_user_poll_blocks")
    @patch("app.listeners.actions.vote_pfp.get_voter_remaining_votes")
    @patch("app.listeners.actions.vote_pfp.get_poll")
    @patch("app.listeners.actions.vote_pfp.has_voted_for_picture")
    @patch("app.listeners.actions.vote_pfp.record_vote")
    def test_successful_vote(
        self,
        mock_record,
        mock_has_voted,
        mock_get_poll,
        mock_get_remaining,
        mock_build_blocks,
        mock_update_summary,
        mock_ack,
        mock_client,
        vote_body,
        sample_poll,
    ):
        """Test a successful vote for a picture."""
        mock_get_poll.return_value = sample_poll
        mock_has_voted.return_value = False
        mock_record.return_value = True
        mock_get_remaining.return_value = 2
        mock_build_blocks.return_value = [{"type": "section"}]

        vote_pfp_callback(ack=mock_ack, body=vote_body, client=mock_client)

        mock_ack.assert_called_once()
        mock_has_voted.assert_called_once_with("poll_123", "U789", 1)
        mock_record.assert_called_once_with("poll_123", "U789", 1)
        mock_client.chat_update.assert_called_once()
        mock_client.chat_postEphemeral.assert_called_once()

    @patch("app.scheduler.update_poll_summary")
    @patch("app.scheduler.build_user_poll_blocks")
    @patch("app.listeners.actions.vote_pfp.get_voter_remaining_votes")
    @patch("app.listeners.actions.vote_pfp.get_poll")
    @patch("app.listeners.actions.vote_pfp.has_voted_for_picture")
    @patch("app.listeners.actions.vote_pfp.remove_vote")
    def test_remove_vote(
        self,
        mock_remove,
        mock_has_voted,
        mock_get_poll,
        mock_get_remaining,
        mock_build_blocks,
        mock_update_summary,
        mock_ack,
        mock_client,
        vote_body,
        sample_poll,
    ):
        """Test removing a vote (toggle off)."""
        mock_get_poll.return_value = sample_poll
        mock_has_voted.return_value = True  # Already voted
        mock_remove.return_value = True
        mock_get_remaining.return_value = 3
        mock_build_blocks.return_value = [{"type": "section"}]

        vote_pfp_callback(ack=mock_ack, body=vote_body, client=mock_client)

        mock_ack.assert_called_once()
        mock_remove.assert_called_once_with("poll_123", "U789", 1)
        mock_client.chat_update.assert_called_once()
        mock_client.chat_postEphemeral.assert_called_once()

    @patch("app.listeners.actions.vote_pfp.get_poll")
    def test_poll_not_found(self, mock_get_poll, mock_ack, mock_client, vote_body):
        """Test handling when poll doesn't exist."""
        mock_get_poll.return_value = None

        vote_pfp_callback(ack=mock_ack, body=vote_body, client=mock_client)

        mock_ack.assert_called_once()
        mock_client.chat_update.assert_not_called()

    def test_invalid_value_format(self, mock_ack, mock_client, make_slack_action_body):
        """Test handling of invalid action value format."""
        body = make_slack_action_body(action_value="invalid_format")

        vote_pfp_callback(ack=mock_ack, body=body, client=mock_client)

        mock_ack.assert_called_once()
        mock_client.chat_update.assert_not_called()

    @patch("app.scheduler.update_poll_summary")
    @patch("app.scheduler.build_user_poll_blocks")
    @patch("app.listeners.actions.vote_pfp.get_voter_remaining_votes")
    @patch("app.listeners.actions.vote_pfp.get_max_votes")
    @patch("app.listeners.actions.vote_pfp.get_poll")
    @patch("app.listeners.actions.vote_pfp.has_voted_for_picture")
    @patch("app.listeners.actions.vote_pfp.record_vote")
    def test_vote_at_max_fails(
        self,
        mock_record,
        mock_has_voted,
        mock_get_poll,
        mock_get_max,
        mock_get_remaining,
        mock_build_blocks,
        mock_update_summary,
        mock_ack,
        mock_client,
        vote_body,
        sample_poll,
    ):
        """Test that voting fails when at max votes."""
        mock_get_poll.return_value = sample_poll
        mock_has_voted.return_value = False
        mock_record.return_value = False  # At max votes
        mock_get_remaining.return_value = 0
        mock_get_max.return_value = 3
        mock_build_blocks.return_value = [{"type": "section"}]

        vote_pfp_callback(ack=mock_ack, body=vote_body, client=mock_client)

        mock_ack.assert_called_once()
        # Message should still be updated
        mock_client.chat_update.assert_called_once()
        # Ephemeral message should tell user they're at max
        mock_client.chat_postEphemeral.assert_called_once()
