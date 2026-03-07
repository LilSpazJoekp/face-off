"""Actions for app settings."""

import logging

from ...app import app
from ...storage import (
    get_notification_channel,
    get_poll_day,
    get_poll_hour,
    get_poll_duration_hours,
)

log = logging.getLogger(__name__)


@app.action("open_channel_modal")
def open_channel_modal_callback(ack, body, client):
    """Open the modal to select a notification channel."""
    ack()

    current_channel = get_notification_channel()

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "channel_modal_submit",
            "title": {"type": "plain_text", "text": "Notification Channel"},
            "submit": {"type": "plain_text", "text": "Save"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Select the channel where profile picture change notifications and weekly polls will be posted.",
                    },
                },
                {
                    "type": "input",
                    "block_id": "channel_select_block",
                    "element": {
                        "type": "channels_select",
                        "action_id": "channel_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a channel",
                        },
                        **(
                            {"initial_channel": current_channel}
                            if current_channel
                            else {}
                        ),
                    },
                    "label": {"type": "plain_text", "text": "Channel"},
                },
            ],
        },
    )


@app.action("open_poll_schedule_modal")
def open_poll_schedule_modal_callback(ack, body, client):
    """Open the modal to configure poll schedule."""
    ack()

    current_day = get_poll_day()
    current_hour = get_poll_hour()
    current_duration = get_poll_duration_hours()

    # Build day options
    days = [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ]
    day_options = [
        {"text": {"type": "plain_text", "text": label}, "value": value}
        for value, label in days
    ]
    initial_day = next(
        (opt for opt in day_options if opt["value"] == current_day), day_options[0]
    )

    # Build hour options (0-23)
    hour_options = []
    for h in range(24):
        if h == 0:
            label = "12:00 AM"
        elif h < 12:
            label = f"{h}:00 AM"
        elif h == 12:
            label = "12:00 PM"
        else:
            label = f"{h - 12}:00 PM"
        hour_options.append(
            {"text": {"type": "plain_text", "text": label}, "value": str(h)}
        )
    initial_hour = hour_options[current_hour]

    # Build duration options
    duration_options = [
        {"text": {"type": "plain_text", "text": "1 hour"}, "value": "1"},
        {"text": {"type": "plain_text", "text": "2 hours"}, "value": "2"},
        {"text": {"type": "plain_text", "text": "4 hours"}, "value": "4"},
        {"text": {"type": "plain_text", "text": "8 hours"}, "value": "8"},
        {"text": {"type": "plain_text", "text": "12 hours"}, "value": "12"},
        {"text": {"type": "plain_text", "text": "1 day"}, "value": "24"},
        {"text": {"type": "plain_text", "text": "2 days"}, "value": "48"},
        {"text": {"type": "plain_text", "text": "3 days"}, "value": "72"},
    ]
    initial_duration = next(
        (opt for opt in duration_options if opt["value"] == str(current_duration)),
        duration_options[5],  # default to 1 day
    )

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "poll_schedule_modal_submit",
            "title": {"type": "plain_text", "text": "Poll Schedule"},
            "submit": {"type": "plain_text", "text": "Save"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Configure when weekly polls are created.",
                    },
                },
                {
                    "type": "input",
                    "block_id": "poll_day_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "poll_day_select",
                        "placeholder": {"type": "plain_text", "text": "Select a day"},
                        "options": day_options,
                        "initial_option": initial_day,
                    },
                    "label": {"type": "plain_text", "text": "Day of Week"},
                },
                {
                    "type": "input",
                    "block_id": "poll_hour_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "poll_hour_select",
                        "placeholder": {"type": "plain_text", "text": "Select a time"},
                        "options": hour_options,
                        "initial_option": initial_hour,
                    },
                    "label": {"type": "plain_text", "text": "Time (Central Time)"},
                },
                {
                    "type": "input",
                    "block_id": "poll_duration_block",
                    "element": {
                        "type": "static_select",
                        "action_id": "poll_duration_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select duration",
                        },
                        "options": duration_options,
                        "initial_option": initial_duration,
                    },
                    "label": {"type": "plain_text", "text": "Voting Duration"},
                },
            ],
        },
    )
