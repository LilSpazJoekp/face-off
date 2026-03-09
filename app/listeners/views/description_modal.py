"""Handler for description modal submission."""

import logging
from collections.abc import Mapping
from typing import Any

from slack_bolt import Ack
from slack_sdk import WebClient

from ...app import app
from ...storage import (
    get_candidate_message_info,
    get_change_notification_info,
    get_poll,
    get_profile_change,
    update_picture_description,
    update_profile_change_description,
)

log = logging.getLogger(__name__)


def _value(record: Any, key: str) -> Any:
    """Get a field from either a model object or mapping."""
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


def _build_notification_blocks(change: Any) -> list[dict[str, Any]]:
    """Build the blocks for a profile change notification with description."""
    user_id = _value(change, "user_id")
    display_name = _value(change, "display_name")
    avatar_url = _value(change, "avatar_url")
    description = _value(change, "description")

    blocks = [
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "New Profile Picture"}],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<@{user_id}> just updated their look!",
            },
        },
    ]

    # Add description if set
    if description:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": description},
            },
        )

    blocks.append(
        {
            "type": "image",
            "image_url": avatar_url,
            "alt_text": f"{display_name}'s new profile picture",
        },
    )

    # Add description button
    button_text = "Edit Description" if description else "Add Description"
    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": button_text},
                    "action_id": "edit_change_description",
                    "value": _value(change, "id"),
                },
            ],
        },
    )

    return blocks


@app.view("description_modal")
def description_modal_callback(
    ack: Ack, body: dict[str, Any], client: WebClient, view: dict[str, Any]
) -> None:
    """Handle description modal submission."""
    # Import here to avoid circular import
    from ...scheduler import build_user_poll_blocks

    ack()

    metadata = view["private_metadata"]
    parts = metadata.split(":")

    # Get description from input
    description_value = view["state"]["values"]["description_block"][
        "description_input"
    ]
    description = description_value.get("value") or ""
    editor_id = body["user"]["id"]

    # Handle poll picture context: "poll:poll_id:picture_id:user_id"
    if parts[0] == "poll" and len(parts) == 4:
        poll_id = parts[1]
        picture_id = int(parts[2])
        user_id = parts[3]

        success = update_picture_description(picture_id, description.strip(), editor_id)
        if not success:
            log.error(f"Failed to update description for picture {picture_id}")
            return

        # Update the channel message
        message_info = get_candidate_message_info(poll_id, user_id)
        poll = get_poll(poll_id)
        if message_info and poll:
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
                return

            try:
                client.chat_update(
                    channel=_value(message_info, "message_channel")
                    or _value(message_info, "channel"),
                    ts=_value(message_info, "message_ts") or _value(message_info, "ts"),
                    text=f"Vote for {_value(user_data, 'display_name')}",
                    blocks=(build_user_poll_blocks(poll_id, user_data)),
                )
            except Exception:
                log.exception("Error updating poll message")

    # Handle profile change context: "change:change_id"
    elif parts[0] == "change" and len(parts) == 2:
        change_id = parts[1]

        success = update_profile_change_description(
            change_id, description.strip(), editor_id
        )
        if not success:
            log.error(f"Failed to update description for change {change_id}")
            return

        # Update the notification message
        notification_info = get_change_notification_info(change_id)
        change = get_profile_change(change_id)
        if notification_info and change:
            try:
                client.chat_update(
                    channel=_value(notification_info, "notification_channel")
                    or _value(notification_info, "channel"),
                    ts=_value(notification_info, "notification_ts")
                    or _value(notification_info, "ts"),
                    text=f"{_value(change, 'display_name')} changed their profile picture!",
                    blocks=(_build_notification_blocks(change)),
                )
            except Exception:
                log.exception("Error updating notification message")

    else:
        log.error(f"Invalid description modal metadata format: {metadata}")
