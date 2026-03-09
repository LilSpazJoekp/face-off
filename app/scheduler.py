"""Scheduler module for weekly profile picture polls."""

import logging
import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from slack_bolt import App
from slack_sdk import WebClient

from .listeners import plural
from .models import PollCandidate
from .storage import (
    create_poll,
    end_poll,
    get_active_polls_with_end_time,
    get_all_pictures_with_votes,
    get_changes_by_user,
    get_max_votes,
    get_notification_channel,
    get_picture_vote_count,
    get_poll,
    get_poll_day,
    get_poll_duration_hours,
    get_poll_hour,
    get_user_total_votes,
    save_poll_message_ts,
    save_poll_summary_ts,
)

log = logging.getLogger(__name__)

CT_TIMEZONE = pytz.timezone("America/Chicago")


def _coerce_datetime(value: datetime | str) -> datetime:
    """Normalize datetime values used in block formatting."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _value(record: Any, key: str) -> Any:
    """Get a field from either a model object or mapping."""
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key)


def format_week_label(week_key: str) -> str:
    """Convert week key (YYYY-WXX) to readable format."""
    try:
        year, week = week_key.split("-W")
        date = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
        return date.strftime("%b %d")
    except Exception:
        return week_key


def build_user_poll_blocks(
    poll_id: str,
    user_data: PollCandidate | Mapping[str, Any],
    ended: bool = False,
) -> list[dict[str, Any]]:
    """Build the Block Kit blocks for a single user's poll message with vote buttons per picture."""
    user_id = str(_value(user_data, "user_id"))
    display_name = str(_value(user_data, "display_name"))
    pictures = list(_value(user_data, "pictures") or [])

    # Header showing user and picture count
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<@{user_id}> changed their profile picture {plural(len(pictures), '*'):time}.",
            },
        },
    ]

    # Add each profile picture with its own vote button
    for pic in pictures:
        picture_id = int(_value(pic, "id"))
        week_label = format_week_label(str(_value(pic, "week")))
        picture_timestamp = _coerce_datetime(_value(pic, "timestamp"))
        vote_count = get_picture_vote_count(poll_id, picture_id)
        description = _value(pic, "description")

        # Description section if set
        if description:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": description,
                    },
                },
            )

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
            },
        )

        # Show when picture was updated
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Updated {picture_timestamp:%b %d at %-I:%M %p}",
                    },
                ],
            },
        )

        # Vote button and count for this picture (hide button if ended)
        if ended:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{plural(vote_count, '*'):vote}",
                    },
                },
            )
        else:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{plural(vote_count, '*'):vote}",
                    },
                    "accessory": {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Vote",
                        },
                        "style": "primary",
                        "action_id": "vote_pfp",
                        "value": f"{poll_id}:{picture_id}:{user_id}",
                    },
                },
            )

        # Add/Edit Description button (hide if ended)
        if not ended:
            button_text = "Edit Description" if description else "Add Description"
            blocks.append(
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": button_text,
                            },
                            "action_id": "edit_description",
                            "value": f"{poll_id}:{picture_id}",
                        },
                    ],
                },
            )

        if (
            description
            and _value(pic, "description_edited_by")
            and _value(pic, "description_edited_at")
        ):
            edited_at = _coerce_datetime(_value(pic, "description_edited_at"))
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Description last edited by <@{_value(pic, 'description_edited_by')}> on {edited_at:%b %d}_",
                        },
                    ],
                },
            )

    # Total votes for this user
    total_votes = get_user_total_votes(poll_id, user_id)
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*{plural(total_votes):vote} total*",
                },
            ],
        },
    )

    blocks.append({"type": "divider"})

    return blocks


def build_summary_blocks(
    poll_id: str,
    show_end_button: bool = False,
    ended: bool = False,
) -> list[dict[str, Any]]:
    """Build leaderboard summary blocks showing top pictures by votes."""
    pictures_with_votes = get_all_pictures_with_votes(poll_id)

    medals = [":first_place_medal:", ":second_place_medal:", ":third_place_medal:"]

    header_text = "Poll Results (Ended)" if ended else "Poll Summary"
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": header_text,
            },
        },
    ]

    # Top 3 pictures
    shown = 0
    top_pictures: list[tuple[str, datetime, int]] = []
    for item in pictures_with_votes[:3]:
        if isinstance(item, tuple):
            picture, user_id, _display_name, vote_count = item
            if vote_count == 0:
                continue
            top_pictures.append(
                (user_id, _coerce_datetime(picture.timestamp), vote_count)
            )
            continue

        vote_count = int(item["vote_count"])
        if vote_count == 0:
            continue
        top_pictures.append(
            (
                str(item["user_id"]),
                _coerce_datetime(item["timestamp"]),
                vote_count,
            )
        )

    for i, (user_id, picture_timestamp, vote_count) in enumerate(top_pictures):
        medal = medals[i] if i < 3 else ""
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{medal} <@{user_id}>'s picture ({picture_timestamp:%b %d}) - {plural(vote_count, '*'):vote}",
                },
            },
        )
        shown += 1

    if shown == 0:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_No votes yet..._",
                },
            },
        )

    # Total votes
    total_votes = 0
    for item in pictures_with_votes:
        if isinstance(item, tuple):
            total_votes += item[3]
        else:
            total_votes += int(item["vote_count"])
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"_{plural(total_votes):vote} cast_",
                },
            ],
        },
    )

    # End Poll button for manual polls
    if show_end_button and not ended:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "End Poll"},
                        "style": "danger",
                        "action_id": "end_poll",
                        "value": poll_id,
                        "confirm": {
                            "title": {"type": "plain_text", "text": "End this poll?"},
                            "text": {
                                "type": "mrkdwn",
                                "text": "This will stop accepting votes and show final results.",
                            },
                            "confirm": {"type": "plain_text", "text": "End Poll"},
                            "deny": {"type": "plain_text", "text": "Cancel"},
                        },
                    },
                ],
            },
        )

    return blocks


def update_poll_summary(client: WebClient, poll_id: str) -> None:
    """Update the summary message with current leaderboard."""
    poll = get_poll(poll_id)
    if not poll:
        return

    summary_channel = _value(poll, "summary_message_channel") or _value(
        poll, "summary_channel"
    )
    summary_ts = _value(poll, "summary_message_ts") or _value(poll, "summary_ts")
    if not summary_channel or not summary_ts:
        return

    # Manual polls have no ends_at, so show end button for those
    ended_value = _value(poll, "ended")
    is_manual = _value(poll, "ends_at") is None
    is_ended = ended_value == "Y" if isinstance(ended_value, str) else bool(ended_value)

    blocks = build_summary_blocks(poll_id, show_end_button=is_manual, ended=is_ended)
    try:
        client.chat_update(
            channel=summary_channel,
            ts=summary_ts,
            text="Poll Summary",
            blocks=blocks,
        )
    except Exception:
        log.exception("Error updating poll summary")


def update_poll_user_messages(
    client: WebClient, poll_id: str, ended: bool = False
) -> None:
    """Update all user poll messages (e.g., when poll ends to remove vote buttons)."""
    poll = get_poll(poll_id)
    if not poll:
        return

    if isinstance(poll, Mapping):
        user_items = list((poll.get("users") or {}).items())
        for user_id, user_data in user_items:
            if not user_data.get("message_ts") or not user_data.get("message_channel"):
                continue

            blocks = build_user_poll_blocks(poll_id, user_data, ended=ended)
            try:
                client.chat_update(
                    channel=user_data["message_channel"],
                    ts=user_data["message_ts"],
                    text=f"Vote for {user_data['display_name']}",
                    blocks=blocks,
                )
            except Exception:
                log.exception("Error updating poll message for %s", user_id)
        return

    for candidate in poll.candidates:
        if not candidate.message_ts or not candidate.message_channel:
            continue

        blocks = build_user_poll_blocks(poll_id, candidate, ended=ended)
        try:
            client.chat_update(
                channel=candidate.message_channel,
                ts=candidate.message_ts,
                text=f"Vote for {candidate.display_name}",
                blocks=blocks,
            )
        except Exception:
            log.exception("Error updating poll message for %s", candidate.user_id)


def create_weekly_poll(
    client: WebClient,
    manual: bool = False,
    scheduler: BackgroundScheduler | None = None,
    current_week: bool = False,
) -> bool:
    """Create a poll for voting on profile pictures - one message per user."""
    log.info("Creating weekly profile picture poll...")

    # Get notification channel from storage
    notification_channel = get_notification_channel()
    if not notification_channel:
        log.warning("No notification channel configured, skipping poll")
        return False

    # Calculate the poll period: from previous poll day to today
    # e.g., if poll runs Thursday, include changes from last Thursday to yesterday (Wednesday)
    today = datetime.now(CT_TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)
    if current_week:
        # get number of days since last scheduled poll day
        poll_day = ["mon", "tues", "wed", "thur", "fri", "sat", "sun"].index(
            get_poll_day()
        )

        days_since_last_poll = (today.weekday() - poll_day) % 7
        week_start = today - timedelta(days=days_since_last_poll)
        week_end = today + timedelta(
            days=1
        )  # Include today's changes (until is exclusive)
    else:
        week_start = today - timedelta(days=7)  # 7 days ago (previous poll day)
        week_end = today  # Up to (but not including) today

    week_start_str = week_start.strftime("%b %d")
    week_end_str = (week_end - timedelta(days=1)).strftime(
        "%b %d"
    )  # Show the last included day

    log.info(
        "Creating weekly profile picture poll for period %s - %s...",
        week_start_str,
        week_end_str,
    )

    # Get changes from the past week only
    users_data = get_changes_by_user(since=week_start, until=week_end)

    if not users_data:
        log.info("No profile picture changes to poll, skipping")
        return False

    # Calculate poll end time for scheduled polls
    ends_at = None
    if not manual:
        duration_hours = get_poll_duration_hours()
        ends_at = datetime.now(CT_TIMEZONE) + timedelta(hours=duration_hours)

    # Create poll ID and store poll data
    poll_id = f"poll_{uuid.uuid4().hex[:8]}"
    create_poll(poll_id, users_data, ends_at=ends_at)

    # Schedule poll end job for scheduled polls
    if ends_at and scheduler:
        schedule_poll_end(scheduler, client, poll_id, ends_at)

    # Send header message
    try:
        total_users = len(users_data)
        if users_data and isinstance(next(iter(users_data.values())), list):
            total_pics = sum(len(changes) for changes in users_data.values())
        else:
            total_pics = sum(len(user["pictures"]) for user in users_data.values())
        max_votes = get_max_votes()

        client.chat_postMessage(
            channel=notification_channel,
            text="Vote for the Best Profile Picture!",
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Best Profile Picture Poll",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{plural(total_users, '*'):user} participated with {plural(total_pics, '*'):picture} for the week of {week_start_str} to {week_end_str}.",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"You have {plural(max_votes, '*'):vote} to vote on your favorite picture!",
                    },
                },
                {"type": "divider"},
            ],
        )

        # Get poll data with picture IDs
        poll_data = get_poll(poll_id)

        # Send one message per user
        if isinstance(poll_data, Mapping):
            for user_id, user_data in poll_data["users"].items():
                blocks = build_user_poll_blocks(poll_id, user_data)

                result = client.chat_postMessage(
                    channel=notification_channel,
                    text=f"Vote for {user_data['display_name']}",
                    blocks=blocks,
                    metadata={
                        "event_type": "pfp_poll_user",
                        "event_payload": {"poll_id": poll_id, "user_id": user_id},
                    },
                )

                save_poll_message_ts(
                    poll_id, user_id, notification_channel, result["ts"]
                )
        else:
            for candidate in poll_data.candidates:
                blocks = build_user_poll_blocks(poll_id, candidate)

                result = client.chat_postMessage(
                    channel=notification_channel,
                    text=f"Vote for {candidate.display_name}",
                    blocks=blocks,
                    metadata={
                        "event_type": "pfp_poll_user",
                        "event_payload": {
                            "poll_id": poll_id,
                            "user_id": candidate.user_id,
                        },
                    },
                )

                save_poll_message_ts(
                    poll_id, candidate.user_id, notification_channel, result["ts"]
                )

        # Send summary message at the end
        summary_blocks = build_summary_blocks(poll_id, show_end_button=manual)
        summary_result = client.chat_postMessage(
            channel=notification_channel,
            text="Poll Summary",
            blocks=summary_blocks,
        )

        # Save summary message_ts for later updates
        save_poll_summary_ts(poll_id, notification_channel, summary_result["ts"])

        log.info("Poll created with %d user(s), ID: %s", total_users, poll_id)
    except Exception:
        log.exception("Error creating poll")
        return False
    else:
        return True


DAY_NAMES = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}


def end_poll_job(client: WebClient, poll_id: str) -> None:
    """End a poll and update all messages. Called by scheduler."""
    log.info("Auto-ending poll %s", poll_id)

    success = end_poll(poll_id)
    if not success:
        log.error("Failed to end poll %s", poll_id)
        return

    # Update all user messages to remove vote buttons
    update_poll_user_messages(client, poll_id, ended=True)

    # Update the summary message
    poll = get_poll(poll_id)
    if not poll:
        return

    summary_channel = _value(poll, "summary_message_channel") or _value(
        poll, "summary_channel"
    )
    summary_ts = _value(poll, "summary_message_ts") or _value(poll, "summary_ts")
    if summary_channel and summary_ts:
        blocks = build_summary_blocks(poll_id, show_end_button=False, ended=True)
        try:
            client.chat_update(
                channel=summary_channel,
                ts=summary_ts,
                text="Poll Results (Ended)",
                blocks=blocks,
            )
        except Exception:
            log.exception("Error updating poll summary after auto-end")


def schedule_poll_end(
    scheduler: BackgroundScheduler,
    client: WebClient,
    poll_id: str,
    ends_at: datetime,
) -> None:
    """Schedule a job to end a poll at the specified time."""
    job_id = f"end_poll_{poll_id}"

    # Ensure ends_at is timezone-aware
    if ends_at.tzinfo is None:
        ends_at = CT_TIMEZONE.localize(ends_at)

    # Don't schedule if already past
    now = datetime.now(CT_TIMEZONE)
    if ends_at <= now:
        log.info("Poll %s end time already passed, ending now", poll_id)
        end_poll_job(client, poll_id)
        return

    scheduler.add_job(
        end_poll_job,
        "date",
        run_date=ends_at,
        args=[client, poll_id],
        id=job_id,
        replace_existing=True,
    )
    log.info("Scheduled poll %s to end at %s", poll_id, ends_at)


def start_scheduler(app: App) -> BackgroundScheduler:
    """Set up and start the scheduler for the weekly poll."""
    scheduler = BackgroundScheduler(timezone=CT_TIMEZONE)

    # Get configurable schedule settings
    poll_day = get_poll_day()
    poll_hour = get_poll_hour()

    trigger = CronTrigger(
        day_of_week=poll_day,
        hour=poll_hour,
        minute=0,
        timezone=CT_TIMEZONE,
    )

    def poll_job() -> None:
        create_weekly_poll(app.client, scheduler=scheduler)

    scheduler.add_job(poll_job, trigger, id="weekly_poll")
    scheduler.start()

    day_name = DAY_NAMES.get(poll_day, poll_day)
    log.info("Scheduled weekly poll for %ss at %s:00 CT", day_name, poll_hour)

    # Schedule end jobs for any active polls from previous runs
    active_polls = get_active_polls_with_end_time()
    for poll_info in active_polls:
        if isinstance(poll_info, Mapping):
            poll_id = poll_info["poll_id"]
            ends_at = poll_info["ends_at"]
        else:
            poll_id = poll_info.poll_id
            ends_at = poll_info.ends_at

        if ends_at is None:
            continue
        schedule_poll_end(scheduler, app.client, poll_id, ends_at)

    # Store scheduler on app for access elsewhere
    app.scheduler = scheduler

    return scheduler


def reschedule_poll(scheduler: BackgroundScheduler) -> bool:
    """Reschedule the poll job with current settings. Call after changing poll settings."""
    if not scheduler.get_jobs():
        log.warning("No jobs found in scheduler, cannot reschedule")
        return False

    poll_day = get_poll_day()
    poll_hour = get_poll_hour()

    trigger = CronTrigger(
        day_of_week=poll_day,
        hour=poll_hour,
        minute=0,
        timezone=CT_TIMEZONE,
    )

    scheduler.reschedule_job("weekly_poll", trigger=trigger)

    day_name = DAY_NAMES.get(poll_day, poll_day)
    log.info("Rescheduled weekly poll for %ss at %s:00 CT", day_name, poll_hour)

    return True
