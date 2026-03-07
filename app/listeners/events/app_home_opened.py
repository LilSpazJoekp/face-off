from logging import Logger
from collections.abc import Mapping

from slack_sdk import WebClient

from ...app import app
from ...storage import (
    get_watched_users,
    is_user_watched,
    is_consent_pending,
    get_pending_consent,
    get_notification_channel,
    get_poll_day,
    get_poll_hour,
    get_poll_duration_hours,
)

log = Logger(__name__)


def build_home_view(user_id: str) -> dict:
    """Build the app home view for a user."""
    watched_users = get_watched_users()
    user_is_watched = is_user_watched(user_id)
    user_consent_pending = is_consent_pending(user_id)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Profile Picture Tracker",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Track profile picture changes and vote for the best ones each week!",
            },
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Your Status",
            },
        },
    ]

    # User's own status section

    if user_is_watched:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "You are currently being tracked for profile picture changes.",
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Remove Myself",
                    },
                    "style": "danger",
                    "action_id": "remove_self_from_watchlist",
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Remove yourself?"},
                        "text": {
                            "type": "mrkdwn",
                            "text": "Are you sure you want to stop being tracked for profile picture changes?",
                        },
                        "confirm": {"type": "plain_text", "text": "Yes, remove me"},
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    },
                },
            }
        )
    elif user_consent_pending:
        pending_info = get_pending_consent(user_id)
        if isinstance(pending_info, Mapping):
            requested_by = pending_info.get("requested_by", "someone")
        elif pending_info:
            requested_by = pending_info.requested_by
        else:
            requested_by = "someone"

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*<@{requested_by}> wants to add you to the watch list.*\n\nIf you accept, your profile picture changes will be tracked and announced. You'll also be included in weekly polls.",
                },
            }
        )
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "_You can remove yourself from the watch list at any time._",
                    }
                ],
            }
        )
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Accept"},
                        "style": "primary",
                        "action_id": "consent_accept",
                        "value": user_id,
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Decline"},
                        "style": "danger",
                        "action_id": "consent_decline",
                        "value": user_id,
                    },
                ],
            }
        )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "You are not currently being tracked.",
                },
            }
        )

    blocks.append({"type": "divider"})

    # Watched users management section
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Watched Users",
            },
        }
    )

    if watched_users:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Currently tracking *{len(watched_users)}* user(s):",
                },
            }
        )

        for watched_user_id in watched_users:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"<@{watched_user_id}>"},
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Remove",
                        },
                        "style": "danger",
                        "action_id": "remove_watched_user",
                        "value": watched_user_id,
                        "confirm": {
                            "title": {"type": "plain_text", "text": "Remove user?"},
                            "text": {
                                "type": "mrkdwn",
                                "text": f"Remove <@{watched_user_id}> from the watch list?",
                            },
                            "confirm": {"type": "plain_text", "text": "Remove"},
                            "deny": {"type": "plain_text", "text": "Cancel"},
                        },
                    },
                }
            )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_No users are being tracked yet._"},
            }
        )

    blocks.append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Add User to Watch List",
                    },
                    "style": "primary",
                    "action_id": "open_add_user_modal",
                }
            ],
        }
    )

    blocks.append({"type": "divider"})

    # Settings section
    blocks.append(
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Settings",
            },
        }
    )

    if notification_channel := get_notification_channel():
        channel_text = f"Notifications are sent to <#{notification_channel}>"
    else:
        channel_text = "_No notification channel configured._"

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Notification Channel*\n{channel_text}",
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Change Channel",
                },
                "action_id": "open_channel_modal",
            },
        }
    )

    # Poll schedule settings
    poll_day = get_poll_day()
    poll_hour = get_poll_hour()
    poll_duration = get_poll_duration_hours()

    day_names = {
        "mon": "Monday",
        "tue": "Tuesday",
        "wed": "Wednesday",
        "thu": "Thursday",
        "fri": "Friday",
        "sat": "Saturday",
        "sun": "Sunday",
    }
    day_name = day_names.get(poll_day, poll_day.capitalize())

    # Format hour for display
    if poll_hour == 0:
        hour_display = "12:00 AM"
    elif poll_hour < 12:
        hour_display = f"{poll_hour}:00 AM"
    elif poll_hour == 12:
        hour_display = "12:00 PM"
    else:
        hour_display = f"{poll_hour - 12}:00 PM"

    # Format duration for display
    if poll_duration >= 24:
        duration_display = (
            f"{poll_duration // 24} day{'s' if poll_duration >= 48 else ''}"
        )
    else:
        duration_display = f"{poll_duration} hour{'s' if poll_duration != 1 else ''}"

    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Poll Schedule*\nPolls run every *{day_name}* at *{hour_display} CT*\nVoting open for *{duration_display}*",
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Change Schedule",
                },
                "action_id": "open_poll_schedule_modal",
            },
        }
    )

    return {"type": "home", "blocks": blocks}


@app.event("app_home_opened")
def app_home_opened_callback(client: WebClient, event: dict):
    # ignore the app_home_opened event for anything but the Home tab
    if event["tab"] != "home":
        return
    try:
        user_id = event["user"]
        view = build_home_view(user_id)
        client.views_publish(user_id=user_id, view=view)
    except Exception as e:
        log.error(f"Error publishing home tab: {e}")
