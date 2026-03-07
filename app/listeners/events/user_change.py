"""Handler for user profile change events."""

import logging

from slack_sdk.errors import SlackApiError

from ...app import app
from ...storage import (
    record_profile_change,
    get_watched_users,
    get_notification_channel,
    save_change_notification_ts,
)

log = logging.getLogger(__name__)


@app.event("user_change")
def user_change_callback(event, client):
    """Handle user profile changes and detect profile picture updates."""
    user = event.get("user", {})
    user_id = user.get("id")

    if not user_id:
        return

    # Get watched users from storage
    watched_users = get_watched_users()

    # Only track users who have consented to be watched
    if not watched_users or user_id not in watched_users:
        log.debug(f"Ignoring user {user_id} - not in watched list")
        return

    # Get notification channel from storage
    notification_channel = get_notification_channel()
    if not notification_channel:
        log.warning("No notification channel configured, skipping notification")
        return

    # make sure we're in the notification channel
    try:
        client.conversations_join(channel=notification_channel)
    except SlackApiError as e:
        log.error(f"Failed to join notification channel: {e}")
        return

    profile = user.get("profile", {})
    new_avatar = profile.get("image_original") or profile.get("image_512")
    display_name = (
        profile.get("display_name")
        or profile.get("real_name")
        or user.get("name")
        or user_id
    )

    if not new_avatar:
        return

    # Record the change (returns change_id if new, None if duplicate)
    change_id = record_profile_change(user_id, display_name, new_avatar)

    if not change_id:
        log.debug(f"Duplicate avatar detected for {display_name}, skipping")
        return

    log.info(f"Profile picture change detected for {display_name}")

    # Send notification to the channel
    try:
        result = client.chat_postMessage(
            channel=notification_channel,
            text=f"{display_name} changed their profile picture!",
            blocks=[
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
                {
                    "type": "image",
                    "image_url": new_avatar,
                    "alt_text": f"{display_name}'s new profile picture",
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Add Description"},
                            "action_id": "edit_change_description",
                            "value": change_id,
                        }
                    ],
                },
            ],
        )

        # Save notification message ts for later updates
        save_change_notification_ts(change_id, notification_channel, result["ts"])

        log.info(f"Notification sent to {notification_channel}")
    except Exception as e:
        log.error(f"Error sending notification: {e}")
