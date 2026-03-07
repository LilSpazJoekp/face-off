"""Handler for profile picture poll votes."""

import logging
from collections.abc import Mapping
from typing import Any

from ...app import app
from ..utils import plural
from ...storage import (
    record_vote,
    remove_vote,
    get_poll,
    get_max_votes,
    has_voted_for_picture,
    get_voter_remaining_votes,
)

log = logging.getLogger(__name__)


def _value(record: Any, key: str) -> Any:
    """Get a field from either a model object or mapping."""
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


@app.action("vote_pfp")
def vote_pfp_callback(ack, body, client):
    """Handle a vote button click from a channel message."""
    ack()

    action = body["actions"][0]
    value = action["value"]  # Format: "poll_id:picture_id:user_id"

    try:
        parts = value.split(":")
        if len(parts) != 3:
            raise ValueError("Expected 3 parts")
        poll_id, picture_id_str, user_id = parts
        picture_id = int(picture_id_str)
    except (ValueError, TypeError) as e:
        log.error(f"Invalid vote value format: {value} - {e}")
        return

    voter_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    message_ts = body["message"]["ts"]

    # Check if poll exists
    poll = get_poll(poll_id)
    if not poll:
        log.error(f"Poll not found: {poll_id}")
        return

    # Check if already voted for this picture
    already_voted = has_voted_for_picture(poll_id, voter_id, picture_id)

    if already_voted:
        # Remove the vote (toggle off)
        remove_vote(poll_id, voter_id, picture_id)
        action_taken = "removed"
    else:
        # Try to add vote (may fail if at max)
        success = record_vote(poll_id, voter_id, picture_id)
        if success:
            action_taken = "added"
        else:
            action_taken = "failed"

    # Get updated poll data and rebuild message blocks
    poll = get_poll(poll_id)
    if not poll:
        log.error(f"Poll not found after vote update: {poll_id}")
        return

    if isinstance(poll, Mapping):
        user_data = (poll.get("users") or {}).get(user_id)
    else:
        user_data = next(
            (
                candidate
                for candidate in poll.candidates
                if candidate.user_id == user_id
            ),
            None,
        )

    if not user_data:
        log.error(f"User data not found for {user_id}")
        return

    try:
        # Import here to avoid circular import
        from ...scheduler import build_user_poll_blocks, update_poll_summary

        # Update the channel message with new vote counts
        blocks = build_user_poll_blocks(poll_id, user_data)
        display_name = _value(user_data, "display_name")
        client.chat_update(
            channel=channel_id,
            ts=message_ts,
            text=f"Vote for {display_name}",
            blocks=blocks,
        )

        # Send ephemeral confirmation to voter
        remaining = get_voter_remaining_votes(poll_id, voter_id)
        if action_taken == "added":
            message = f"Vote recorded! You have {plural(remaining):vote} remaining."
        elif action_taken == "removed":
            message = f"Vote removed. You have {plural(remaining):vote} remaining."
        else:
            message = f"Could not record vote - you've used all {plural(get_max_votes()):vote}."

        client.chat_postEphemeral(channel=channel_id, user=voter_id, text=message)

        # Update the summary leaderboard
        update_poll_summary(client, poll_id)

    except Exception as e:
        log.error(f"Error updating poll message: {e}")
