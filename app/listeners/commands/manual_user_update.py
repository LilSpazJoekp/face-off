"""Command to manually trigger a profile picture update for a user."""

import logging
import re
from typing import Any

from slack_bolt import Ack, Respond
from slack_sdk import WebClient

from ...app import app
from ...services.profile_change_service import ProfileChangeService

log = logging.getLogger(__name__)


@app.command("/manual-user-update")
def manual_user_update_callback(
    ack: Ack, respond: Respond, command: dict[str, Any], client: WebClient
) -> None:
    """Manually trigger a profile picture update for a user."""
    ack()

    # The command.get("text") contains whatever comes after /manual-user-update
    text = command.get("text", "").strip()
    user_id = None

    # Try to extract user ID from text (e.g., /manual-user-update @user or /manual-user-update U123)
    if text:
        # Match <@U12345678|name> or <@U12345678> or U12345678
        match = re.search(r"(?:<@)?([A-Z0-9]+)(?:\|[^>]+)?(?:>)?", text)
        if match:
            user_id = match.group(1)

    # Fallback to the user who ran the command if no user specified
    if not user_id:
        user_id = command.get("user_id")

    if not user_id:
        respond("Please provide a user ID or mention a user.")
        return

    try:
        # Fetch the latest user info from Slack
        result = client.users_info(user=user_id)
        if not result.get("ok"):
            respond(f"Could not find user {user_id}.")
            return

        user = result.get("user")

        # Check if user is watched (process_user_change also checks this, but good to give feedback)
        from ..commands.watched_users import get_watched_users

        watched_users = get_watched_users()
        if user_id not in watched_users:
            respond(
                f"<@{user_id}> is not in the watched users list. Please add them first."
            )
            return

        change_id = ProfileChangeService.process_user_change(user, client)

        if change_id:
            respond(f"Successfully processed update for <@{user_id}>!")
        else:
            respond(
                f"No new profile picture update detected for <@{user_id}> (it might already be recorded)."
            )

    except Exception as e:
        log.exception("Error in manual_user_update")
        respond(f"An error occurred while processing the update: {e}")
