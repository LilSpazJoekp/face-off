"""Storage compatibility layer backed by injected service dependencies."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

import pytz

from .dependencies import inject_services
from .models import (
    PendingConsent,
    Poll,
    PollCandidate,
    PollCandidatePicture,
    ProfileChange,
)
from .services.poll_service import PollService, UserPollInput
from .services.profile_change_service import ProfileChangeService
from .services.settings_service import SettingsService
from .services.user_watchlist_service import UserWatchlistService

CT_TIMEZONE = pytz.timezone("America/Chicago")


@inject_services("profile_change_service")
def record_profile_change(
    user_id: str,
    display_name: str,
    avatar_url: str,
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> str | None:
    """Record a profile picture change."""
    return profile_change_service.record_change(user_id, display_name, avatar_url)


@inject_services("profile_change_service")
def get_change_duration(
    change: ProfileChange | Mapping[str, Any],
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> str:
    """Calculate and format the duration a profile picture was used."""
    return profile_change_service.get_change_duration(change)


@inject_services("profile_change_service")
def get_changes_by_week(
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> dict[str, list[ProfileChange]]:
    """Get all changes organized by week."""
    return profile_change_service.get_changes_by_week()


@inject_services("profile_change_service")
def get_sorted_weeks(
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> list[str]:
    """Get list of week keys sorted from newest to oldest."""
    return profile_change_service.get_sorted_weeks()


@inject_services("profile_change_service")
def get_changes_by_user(
    since: datetime | None = None,
    until: datetime | None = None,
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> dict[str, list[ProfileChange]]:
    """Get changes organized by user, optionally filtered by date range."""
    return profile_change_service.get_changes_by_user(since, until)


@inject_services("profile_change_service")
def get_weekly_changes(
    since_days: int = 7,
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> list[ProfileChange]:
    """Get profile changes from the past N days."""
    return profile_change_service.get_weekly_changes(since_days)


@inject_services("profile_change_service")
def clear_old_changes(
    days_old: int = 7,
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> None:
    """Remove changes older than N days after poll is created."""
    profile_change_service.clear_old_changes(days_old)


@inject_services("profile_change_service")
def get_profile_change(
    change_id: str,
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> ProfileChange | None:
    """Get a single profile change by ID."""
    return profile_change_service.get_change(change_id)


@inject_services("profile_change_service")
def update_profile_change_description(
    change_id: str,
    description: str,
    edited_by: str,
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> bool:
    """Update a profile change's description."""
    return profile_change_service.update_description(change_id, description, edited_by)


@inject_services("profile_change_service")
def save_change_notification_ts(
    change_id: str,
    channel: str,
    message_ts: str,
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> bool:
    """Save the notification message timestamp for a profile change."""
    return profile_change_service.save_notification_ts(change_id, channel, message_ts)


@inject_services("profile_change_service")
def get_change_notification_info(
    change_id: str,
    profile_change_service: type[ProfileChangeService] = ProfileChangeService,
) -> ProfileChange | None:
    """Get the notification channel and ts for a profile change."""
    return profile_change_service.get_notification_info(change_id)


@inject_services("poll_service")
def create_poll(
    poll_id: str,
    users: Mapping[str, UserPollInput | list[ProfileChange]],
    ends_at: datetime | None = None,
    poll_service: type[PollService] = PollService,
) -> Poll:
    """Create a new poll with users as candidates."""
    return poll_service.create_poll(poll_id, users, ends_at)


@inject_services("poll_service")
def get_poll(
    poll_id: str,
    poll_service: type[PollService] = PollService,
) -> Poll | None:
    """Get poll data by ID."""
    return poll_service.get_poll(poll_id)


@inject_services("poll_service")
def end_poll(
    poll_id: str,
    poll_service: type[PollService] = PollService,
) -> bool:
    """End a poll, preventing further votes."""
    return poll_service.end_poll(poll_id)


@inject_services("poll_service")
def is_poll_ended(
    poll_id: str,
    poll_service: type[PollService] = PollService,
) -> bool:
    """Check if a poll has ended."""
    return poll_service.is_poll_ended(poll_id)


@inject_services("poll_service")
def get_active_polls_with_end_time(
    poll_service: type[PollService] = PollService,
) -> list[Poll]:
    """Get all active polls that have an ends_at time set."""
    return poll_service.get_active_polls_with_end_time()


@inject_services("poll_service")
def record_vote(
    poll_id: str,
    voter_id: str,
    picture_id: int,
    poll_service: type[PollService] = PollService,
) -> bool:
    """Record a vote for a specific picture."""
    return poll_service.record_vote(poll_id, voter_id, picture_id)


@inject_services("poll_service")
def remove_vote(
    poll_id: str,
    voter_id: str,
    picture_id: int,
    poll_service: type[PollService] = PollService,
) -> bool:
    """Remove a vote for a specific picture (toggle off)."""
    return poll_service.remove_vote(poll_id, voter_id, picture_id)


@inject_services("poll_service")
def has_voted_for_picture(
    poll_id: str,
    voter_id: str,
    picture_id: int,
    poll_service: type[PollService] = PollService,
) -> bool:
    """Check if a voter has voted for a specific picture."""
    return poll_service.has_voted_for_picture(poll_id, voter_id, picture_id)


@inject_services("poll_service")
def get_vote_counts(
    poll_id: str,
    poll_service: type[PollService] = PollService,
) -> dict[int, int]:
    """Get vote counts for each picture in a poll."""
    return poll_service.get_vote_counts(poll_id)


@inject_services("poll_service")
def get_picture_vote_count(
    poll_id: str,
    picture_id: int,
    poll_service: type[PollService] = PollService,
) -> int:
    """Get vote count for a specific picture."""
    return poll_service.get_picture_vote_count(poll_id, picture_id)


@inject_services("poll_service")
def get_user_total_votes(
    poll_id: str,
    user_id: str,
    poll_service: type[PollService] = PollService,
) -> int:
    """Get total votes across all pictures for a specific user in the poll."""
    return poll_service.get_user_total_votes(poll_id, user_id)


@inject_services("poll_service")
def get_voter_votes(
    poll_id: str,
    voter_id: str,
    poll_service: type[PollService] = PollService,
) -> list[int]:
    """Get list of picture_ids the voter has voted for."""
    return poll_service.get_voter_votes(poll_id, voter_id)


@inject_services("poll_service")
def get_voter_remaining_votes(
    poll_id: str,
    voter_id: str,
    poll_service: type[PollService] = PollService,
) -> int:
    """Get how many more votes the voter can cast."""
    return poll_service.get_voter_remaining_votes(poll_id, voter_id)


@inject_services("poll_service")
def get_all_pictures_with_votes(
    poll_id: str,
    poll_service: type[PollService] = PollService,
) -> list[tuple[PollCandidatePicture, str, str, int]]:
    """Get all pictures in a poll with their vote counts, sorted by votes descending."""
    return poll_service.get_all_pictures_with_votes(poll_id)


@inject_services("poll_service")
def save_poll_message_ts(
    poll_id: str,
    user_id: str,
    channel: str,
    message_ts: str,
    poll_service: type[PollService] = PollService,
) -> bool:
    """Save the message timestamp for a user's poll message."""
    return poll_service.save_poll_message_ts(poll_id, user_id, channel, message_ts)


@inject_services("poll_service")
def save_poll_summary_ts(
    poll_id: str,
    channel: str,
    message_ts: str,
    poll_service: type[PollService] = PollService,
) -> bool:
    """Save the message timestamp for a poll's summary message."""
    return poll_service.save_poll_summary_ts(poll_id, channel, message_ts)


@inject_services("poll_service")
def get_candidate_message_info(
    poll_id: str,
    user_id: str,
    poll_service: type[PollService] = PollService,
) -> PollCandidate | None:
    """Get the message channel and ts for a candidate's poll message."""
    return poll_service.get_candidate_message_info(poll_id, user_id)


@inject_services("poll_service")
def get_picture(
    picture_id: int,
    poll_service: type[PollService] = PollService,
) -> PollCandidatePicture | None:
    """Get a single picture by ID."""
    return poll_service.get_picture(picture_id)


@inject_services("poll_service")
def update_picture_description(
    picture_id: int,
    description: str,
    edited_by: str,
    poll_service: type[PollService] = PollService,
) -> bool:
    """Update a picture's description."""
    return poll_service.update_picture_description(picture_id, description, edited_by)


@inject_services("user_watchlist_service")
def get_watched_users(
    user_watchlist_service: type[UserWatchlistService] = UserWatchlistService,
) -> list[str]:
    """Get list of user IDs who have consented to be watched."""
    return user_watchlist_service.get_watched_users()


@inject_services("user_watchlist_service")
def is_user_watched(
    user_id: str,
    user_watchlist_service: type[UserWatchlistService] = UserWatchlistService,
) -> bool:
    """Check if a user is in the watched list."""
    return user_watchlist_service.is_user_watched(user_id)


@inject_services("user_watchlist_service")
def add_watched_user(
    user_id: str,
    user_watchlist_service: type[UserWatchlistService] = UserWatchlistService,
) -> bool:
    """Add a user to the watched list."""
    return user_watchlist_service.add_watched_user(user_id)


@inject_services("user_watchlist_service")
def remove_watched_user(
    user_id: str,
    user_watchlist_service: type[UserWatchlistService] = UserWatchlistService,
) -> bool:
    """Remove a user from the watched list."""
    return user_watchlist_service.remove_watched_user(user_id)


@inject_services("user_watchlist_service")
def add_pending_consent(
    user_id: str,
    requested_by: str,
    user_watchlist_service: type[UserWatchlistService] = UserWatchlistService,
) -> bool:
    """Add a user to pending consent."""
    return user_watchlist_service.add_pending_consent(user_id, requested_by)


@inject_services("user_watchlist_service")
def remove_pending_consent(
    user_id: str,
    user_watchlist_service: type[UserWatchlistService] = UserWatchlistService,
) -> bool:
    """Remove a user from pending consent."""
    return user_watchlist_service.remove_pending_consent(user_id)


@inject_services("user_watchlist_service")
def get_pending_consent(
    user_id: str,
    user_watchlist_service: type[UserWatchlistService] = UserWatchlistService,
) -> PendingConsent | None:
    """Get pending consent info for a user."""
    return user_watchlist_service.get_pending_consent(user_id)


@inject_services("user_watchlist_service")
def is_consent_pending(
    user_id: str,
    user_watchlist_service: type[UserWatchlistService] = UserWatchlistService,
) -> bool:
    """Check if consent is pending for a user."""
    return user_watchlist_service.is_consent_pending(user_id)


@inject_services("settings_service")
def get_notification_channel(
    settings_service: type[SettingsService] = SettingsService,
) -> str | None:
    """Get the configured notification channel ID."""
    return settings_service.get_notification_channel()


@inject_services("settings_service")
def set_notification_channel(
    channel_id: str,
    settings_service: type[SettingsService] = SettingsService,
) -> None:
    """Set the notification channel ID."""
    settings_service.set_notification_channel(channel_id)


@inject_services("settings_service")
def get_max_votes(
    settings_service: type[SettingsService] = SettingsService,
) -> int:
    """Get the max votes per voter setting (default 3)."""
    return settings_service.get_max_votes()


@inject_services("settings_service")
def set_max_votes(
    max_votes: int,
    settings_service: type[SettingsService] = SettingsService,
) -> None:
    """Set the max votes per voter."""
    settings_service.set_max_votes(max_votes)


@inject_services("settings_service")
def get_poll_day(
    settings_service: type[SettingsService] = SettingsService,
) -> str:
    """Get the day of week for polls (default 'mon')."""
    return settings_service.get_poll_day()


@inject_services("settings_service")
def set_poll_day(
    day: str,
    settings_service: type[SettingsService] = SettingsService,
) -> None:
    """Set the day of week for polls."""
    settings_service.set_poll_day(day)


@inject_services("settings_service")
def get_poll_hour(
    settings_service: type[SettingsService] = SettingsService,
) -> int:
    """Get the hour for polls (default 9)."""
    return settings_service.get_poll_hour()


@inject_services("settings_service")
def set_poll_hour(
    hour: int,
    settings_service: type[SettingsService] = SettingsService,
) -> None:
    """Set the hour for polls."""
    settings_service.set_poll_hour(hour)


@inject_services("settings_service")
def get_poll_duration_hours(
    settings_service: type[SettingsService] = SettingsService,
) -> int:
    """Get the poll duration in hours (default 24)."""
    return settings_service.get_poll_duration_hours()


@inject_services("settings_service")
def set_poll_duration_hours(
    hours: int,
    settings_service: type[SettingsService] = SettingsService,
) -> None:
    """Set the poll duration in hours."""
    settings_service.set_poll_duration_hours(hours)


@inject_services("settings_service")
def get_poll_duration_days(
    settings_service: type[SettingsService] = SettingsService,
) -> int:
    """Get the number of days to collect changes for polls (default 7)."""
    return settings_service.get_poll_duration_days()


@inject_services("settings_service")
def set_poll_duration_days(
    days: int,
    settings_service: type[SettingsService] = SettingsService,
) -> None:
    """Set the number of days to collect changes for polls."""
    settings_service.set_poll_duration_days(days)
