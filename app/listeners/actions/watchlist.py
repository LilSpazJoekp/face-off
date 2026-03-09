"""Actions for managing the watched users list."""

import logging
from typing import Any

from slack_bolt import Ack
from slack_sdk import WebClient

from ...app import app
from ...storage import remove_watched_user
from ..events.app_home_opened import build_home_view

log = logging.getLogger(__name__)


@app.action("open_add_user_modal")
def open_add_user_modal_callback(
    ack: Ack, body: dict[str, Any], client: WebClient
) -> None:
    """Open the modal to add a user to the watch list."""
    ack()

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "add_user_modal_submit",
            "title": {"type": "plain_text", "text": "Add User to Watch List"},
            "submit": {"type": "plain_text", "text": "Send Request"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Select a user to add to the profile picture watch list. They will see a consent request in their app Home tab.",
                    },
                },
                {
                    "type": "input",
                    "block_id": "user_select_block",
                    "element": {
                        "type": "users_select",
                        "action_id": "user_select",
                        "placeholder": {"type": "plain_text", "text": "Select a user"},
                    },
                    "label": {"type": "plain_text", "text": "User"},
                },
            ],
        },
    )


@app.action("remove_watched_user")
def remove_watched_user_callback(
    ack: Ack, body: dict[str, Any], client: WebClient
) -> None:
    """Remove a user from the watch list."""
    ack()

    action = body["actions"][0]
    user_to_remove = action["value"]
    requesting_user = body["user"]["id"]

    removed = remove_watched_user(user_to_remove)

    if removed:
        log.info(f"User {user_to_remove} removed from watch list by {requesting_user}")

    # Refresh the home view
    view = build_home_view(requesting_user)
    client.views_publish(user_id=requesting_user, view=view)


@app.action("remove_self_from_watchlist")
def remove_self_from_watchlist_callback(
    ack: Ack, body: dict[str, Any], client: WebClient
) -> None:
    """Allow a user to remove themselves from the watch list."""
    ack()

    user_id = body["user"]["id"]
    removed = remove_watched_user(user_id)

    if removed:
        log.info(f"User {user_id} removed themselves from watch list")

    # Refresh the home view
    view = build_home_view(user_id)
    client.views_publish(user_id=user_id, view=view)
