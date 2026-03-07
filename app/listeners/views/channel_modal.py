"""View handler for the channel selection modal."""

import logging

from ...app import app
from ...storage import set_notification_channel
from ..events.app_home_opened import build_home_view

log = logging.getLogger(__name__)


@app.view("channel_modal_submit")
def channel_modal_callback(ack, body, client, view):
    """Handle the channel modal submission."""
    ack()

    user_id = body["user"]["id"]

    # Get the selected channel from the modal
    values = view["state"]["values"]
    selected_channel = values["channel_select_block"]["channel_select"][
        "selected_channel"
    ]

    # Join the channel so the bot can post messages
    try:
        client.conversations_join(channel=selected_channel)
        log.info(f"Bot joined channel {selected_channel}")
    except Exception as e:
        # May fail if already in channel or it's a DM - that's ok
        log.debug(f"Could not join channel {selected_channel}: {e}")

    # Save the channel setting
    set_notification_channel(selected_channel)

    log.info(f"Notification channel set to {selected_channel} by {user_id}")

    # Refresh the home view
    home_view = build_home_view(user_id)
    client.views_publish(user_id=user_id, view=home_view)
