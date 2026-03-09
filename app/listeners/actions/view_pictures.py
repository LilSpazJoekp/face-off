"""Actions for viewing user pictures in a poll."""

import logging
from collections.abc import Mapping
from typing import Any

from slack_bolt import Ack
from slack_sdk import WebClient

from ...app import app
from ...storage import (
    get_max_votes,
    get_picture_vote_count,
    get_poll,
    get_voter_votes,
)
from ..utils import plural

log = logging.getLogger(__name__)


def _value(record: Any, key: str) -> Any:
    """Get a field from either a model object or mapping."""
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


def build_pictures_modal(
    poll_id: str,
    user_id: str,
    poll: Any,
    voter_votes: list[int],
    max_votes: int,
) -> dict[str, Any]:
    """Build the modal view for a user's pictures with vote buttons."""
    # Import here to avoid circular import
    from ...scheduler import format_week_label

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
        return {
            "type": "modal",
            "title": {"type": "plain_text", "text": "Error"},
            "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": "User not found in poll."},
                }
            ],
        }

    display_name = _value(user_data, "display_name")
    pictures = list(_value(user_data, "pictures") or [])
    votes_used = len(voter_votes)
    votes_remaining = max_votes - votes_used

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"You have *{votes_remaining}* of {plural(max_votes, '*'):vote} remaining",
            },
        },
        {"type": "divider"},
    ]

    # Add each picture with vote button
    for pic in pictures:
        picture_id = int(_value(pic, "id"))
        week_label = format_week_label(str(_value(pic, "week")))
        vote_count = get_picture_vote_count(poll_id, picture_id)
        has_voted = picture_id in voter_votes

        # Picture image
        blocks.append(
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": f"{week_label} - {_value(pic, 'duration')}",
                },
                "image_url": _value(pic, "avatar_url"),
                "alt_text": f"{display_name}'s profile picture",
            }
        )

        # Vote count and button
        vote_text = f"{plural(vote_count, '*'):vote}"
        if has_voted:
            vote_text += " (You voted)"

        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": vote_text}],
            }
        )

        # Vote/Unvote button
        if has_voted:
            button = {
                "type": "button",
                "text": {"type": "plain_text", "text": "Remove Vote"},
                "action_id": "vote_pfp",
                "value": f"{poll_id}:{picture_id}:{user_id}",
            }
        else:
            button = {
                "type": "button",
                "text": {"type": "plain_text", "text": "Vote"},
                "style": "primary",
                "action_id": "vote_pfp",
                "value": f"{poll_id}:{picture_id}:{user_id}",
            }
            # Disable if no votes remaining
            if votes_remaining <= 0:
                button["style"] = None
                button["text"]["text"] = "No votes left"

        blocks.append({"type": "actions", "elements": [button]})
        blocks.append({"type": "divider"})

    # Remove trailing divider
    if blocks and blocks[-1].get("type") == "divider":
        blocks.pop()

    return {
        "type": "modal",
        "callback_id": "pictures_modal",
        "private_metadata": f"{poll_id}:{user_id}",
        "title": {"type": "plain_text", "text": f"{display_name[:20]}'s Pictures"},
        "close": {"type": "plain_text", "text": "Done"},
        "blocks": blocks,
    }


@app.action("view_user_pictures")
def view_pictures_callback(ack: Ack, body: dict[str, Any], client: WebClient) -> None:
    """Open modal showing user's pictures with vote buttons."""
    ack()

    value = body["actions"][0]["value"]
    parts = value.split(":")
    if len(parts) != 2:
        log.error(f"Invalid view_pictures value format: {value}")
        return

    poll_id, user_id = parts

    poll = get_poll(poll_id)
    if not poll:
        log.error(f"Poll not found: {poll_id}")
        return

    voter_id = body["user"]["id"]
    voter_votes = get_voter_votes(poll_id, voter_id)
    max_votes = get_max_votes()

    view = build_pictures_modal(poll_id, user_id, poll, voter_votes, max_votes)
    client.views_open(trigger_id=body["trigger_id"], view=view)
