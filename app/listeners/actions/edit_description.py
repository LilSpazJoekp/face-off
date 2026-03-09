"""Handler for editing picture descriptions."""

import logging
from collections.abc import Mapping
from typing import Any

from slack_bolt import Ack
from slack_sdk import WebClient

from ...app import app
from ...storage import get_picture, get_profile_change

log = logging.getLogger(__name__)


def _value(record: Any, key: str) -> Any:
    """Get a field from either a model object or mapping."""
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


@app.action("edit_description")
def edit_description_callback(
    ack: Ack, body: dict[str, Any], client: WebClient
) -> None:
    """Open modal to edit picture description (poll context)."""
    ack()

    value = body["actions"][0]["value"]  # "poll_id:picture_id"

    try:
        parts = value.split(":")
        if len(parts) != 2:
            msg = "Expected 2 parts"
            raise ValueError(msg)
        poll_id, picture_id_str = parts
        picture_id = int(picture_id_str)
    except (ValueError, TypeError):
        log.exception(f"Invalid edit_description value format: {value} ")
        return

    picture = get_picture(picture_id)
    if not picture:
        log.error(f"Picture not found: {picture_id}")
        return

    if isinstance(picture, Mapping):
        picture_user_id = picture.get("user_id", "")
    else:
        picture_user_id = picture.candidate.user_id if picture.candidate else ""

    view = {
        "type": "modal",
        "callback_id": "description_modal",
        "private_metadata": f"poll:{poll_id}:{picture_id}:{picture_user_id}",
        "title": {"type": "plain_text", "text": "Edit Description"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "image",
                "image_url": _value(picture, "avatar_url"),
                "alt_text": "Profile picture",
            },
            {
                "type": "input",
                "block_id": "description_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "multiline": True,
                    "max_length": 500,
                    "initial_value": _value(picture, "description") or "",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Add a description for this picture...",
                    },
                },
                "label": {"type": "plain_text", "text": "Description"},
                "optional": True,
            },
        ],
    }

    try:
        client.views_open(trigger_id=body["trigger_id"], view=view)
    except Exception:
        log.exception("Error opening description modal")


@app.action("edit_change_description")
def edit_change_description_callback(
    ack: Ack, body: dict[str, Any], client: WebClient
) -> None:
    """Open modal to edit profile change description (pre-poll context)."""
    ack()

    change_id = body["actions"][0]["value"]

    change = get_profile_change(change_id)
    if not change:
        log.error(f"Profile change not found: {change_id}")
        return

    view = {
        "type": "modal",
        "callback_id": "description_modal",
        "private_metadata": f"change:{change_id}",
        "title": {"type": "plain_text", "text": "Add Description"},
        "submit": {"type": "plain_text", "text": "Save"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "image",
                "image_url": _value(change, "avatar_url"),
                "alt_text": "Profile picture",
            },
            {
                "type": "input",
                "block_id": "description_block",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "description_input",
                    "multiline": True,
                    "max_length": 500,
                    "initial_value": _value(change, "description") or "",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Add a description for this picture...",
                    },
                },
                "label": {"type": "plain_text", "text": "Description"},
                "optional": True,
            },
        ],
    }

    try:
        client.views_open(trigger_id=body["trigger_id"], view=view)
    except Exception:
        log.exception("Error opening description modal")
