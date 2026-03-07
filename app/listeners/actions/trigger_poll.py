"""Handler for trigger poll action."""

import logging

from slack_bolt import Ack, Respond

from ...app import app

log = logging.getLogger(__name__)


@app.action("trigger_poll_select")
def trigger_poll_callback(ack: Ack, respond: Respond, client, body: dict):
    """Trigger poll for selected week."""
    # Import here to avoid circular import
    from ...scheduler import create_weekly_poll

    ack()

    week = body["actions"][0]["selected_option"]["value"]
    is_current_week = week == "current"
    week_label = "current week" if is_current_week else "previous week"

    # Respond with prompt asking which week to create poll for
    respond(
        text=f"Creating poll for {week_label}...",
        replace_original=True,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Creating poll for *{week_label}*...",
                },
            }
        ],
    )

    created = create_weekly_poll(client, manual=True, current_week=is_current_week)
    if created:
        respond(
            f"Poll triggered for {week_label}! Check the notification channel.",
            replace_original=True,
        )
    else:
        respond(f"No updates to vote on for {week_label}", replace_original=True)
