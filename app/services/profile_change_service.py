"""Service for managing profile picture changes."""

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytz

from ..database import get_db
from ..models import ProfileChange

CT_TIMEZONE = pytz.timezone("America/Chicago")


class ProfileChangeService:
    """Service for tracking and managing user profile picture changes."""

    @staticmethod
    def _coerce_datetime(value: datetime | str | None) -> datetime | None:
        """Normalize datetime-like values from model fields or legacy dict payloads."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    @staticmethod
    def _extract_timestamps(
        change: ProfileChange | Mapping[str, Any],
    ) -> tuple[datetime, datetime | None]:
        """Return (start, end) datetimes from either a model instance or mapping."""
        if isinstance(change, ProfileChange):
            return change.timestamp, change.ended_at

        start = ProfileChangeService._coerce_datetime(change.get("timestamp"))
        end = ProfileChangeService._coerce_datetime(change.get("ended_at"))
        if start is None:
            raise ValueError("Change timestamp is required")
        return start, end

    @staticmethod
    def record_change(user_id: str, display_name: str, avatar_url: str) -> str | None:
        """Record a profile picture change.

        :param user_id: The Slack user ID.
        :param display_name: The user's display name.
        :param avatar_url: URL to the new profile picture.

        :returns: The change_id if this is a new change, None if duplicate.

        """
        now = datetime.now(UTC)

        with get_db() as db:
            existing = (
                db.query(ProfileChange)
                .filter(
                    ProfileChange.user_id == user_id,
                    ProfileChange.avatar_url == avatar_url,
                )
                .first()
            )
            if existing:
                return None

            db.query(ProfileChange).filter(
                ProfileChange.user_id == user_id,
                ProfileChange.ended_at.is_(None),
            ).update({"ended_at": now})

            change_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
            db.add(
                ProfileChange(
                    id=change_id,
                    user_id=user_id,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    timestamp=now,
                    ended_at=None,
                )
            )

        return change_id

    @staticmethod
    def get_change(change_id: str) -> ProfileChange | None:
        """Get a single profile change by ID.

        :param change_id: The unique change identifier.

        :returns: ProfileChange model, or None if not found.

        """
        with get_db() as db:
            return db.query(ProfileChange).filter(ProfileChange.id == change_id).first()

    @staticmethod
    def get_change_duration(change: ProfileChange | Mapping[str, Any]) -> str:
        """Calculate and format the duration a profile picture was used.

        :param change: ProfileChange model instance or mapping containing timestamp fields.

        :returns: Formatted duration string (e.g., "2d 5h" or "45m").

        """
        start, ended_at = ProfileChangeService._extract_timestamps(change)
        end = ended_at or datetime.now(CT_TIMEZONE)

        if start.tzinfo is None:
            start = CT_TIMEZONE.localize(start)
        if end.tzinfo is None:
            end = CT_TIMEZONE.localize(end)

        duration = end - start
        days = duration.days
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60

        if days > 0:
            return f"{days}d {hours}h"
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @staticmethod
    def get_changes_by_week() -> dict[str, list[ProfileChange]]:
        """Get all changes organized by week.

        :returns: Dictionary with week keys (YYYY-WXX) mapping to change models.

        """
        with get_db() as db:
            changes = db.query(ProfileChange).all()

        weeks: dict[str, list[ProfileChange]] = {}
        for change in changes:
            week_key = change.timestamp.strftime("%Y-W%W")
            weeks.setdefault(week_key, []).append(change)
        return weeks

    @staticmethod
    def get_sorted_weeks() -> list[str]:
        """Get list of week keys sorted from newest to oldest.

        :returns: List of week key strings sorted in descending order.

        """
        return sorted(ProfileChangeService.get_changes_by_week().keys(), reverse=True)

    @staticmethod
    def get_changes_by_user(
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> dict[str, list[ProfileChange]]:
        """Get changes grouped by user, optionally filtered by date range.

        :param since: Only include changes after this datetime.
        :param until: Only include changes before this datetime.

        :returns: Dictionary mapping user_id to ProfileChange model lists.

        """
        with get_db() as db:
            query = db.query(ProfileChange)
            if since is not None:
                query = query.filter(ProfileChange.timestamp >= since)
            if until is not None:
                query = query.filter(ProfileChange.timestamp < until)
            changes = query.order_by(ProfileChange.timestamp.desc()).all()

        users: dict[str, list[ProfileChange]] = {}
        for change in changes:
            users.setdefault(change.user_id, []).append(change)
        return users

    @staticmethod
    def get_weekly_changes(since_days: int = 7) -> list[ProfileChange]:
        """Get profile changes from the past N days.

        :param since_days: Number of days to look back (default 7).

        :returns: List of ProfileChange model instances.

        """
        now = datetime.now(CT_TIMEZONE)
        cutoff = now - timedelta(days=since_days)

        with get_db() as db:
            return (
                db.query(ProfileChange)
                .filter(ProfileChange.timestamp > cutoff)
                .order_by(ProfileChange.timestamp.desc())
                .all()
            )

    @staticmethod
    def clear_old_changes(days_old: int = 7) -> None:
        """Remove changes older than N days.

        :param days_old: Age threshold in days (default 7).

        """
        now = datetime.now(CT_TIMEZONE)
        cutoff = now - timedelta(days=days_old)

        with get_db() as db:
            db.query(ProfileChange).filter(ProfileChange.timestamp <= cutoff).delete()

    @staticmethod
    def update_description(change_id: str, description: str, edited_by: str) -> bool:
        """Update a profile change's description.

        :param change_id: The change identifier.
        :param description: The new description text.
        :param edited_by: User ID of who made the edit.

        :returns: True if successful, False if change not found.

        """
        now = datetime.now(CT_TIMEZONE)
        cleaned_description = description.strip()

        with get_db() as db:
            change = (
                db.query(ProfileChange).filter(ProfileChange.id == change_id).first()
            )
            if not change:
                return False

            if cleaned_description:
                change.description = cleaned_description
                change.description_edited_by = edited_by
                change.description_edited_at = now
            else:
                change.description = None
                change.description_edited_by = None
                change.description_edited_at = None

        return True

    @staticmethod
    def save_notification_ts(change_id: str, channel: str, message_ts: str) -> bool:
        """Save the notification message timestamp for a profile change.

        :param change_id: The change identifier.
        :param channel: The Slack channel ID.
        :param message_ts: The message timestamp.

        :returns: True if successful, False if change not found.

        """
        with get_db() as db:
            change = (
                db.query(ProfileChange).filter(ProfileChange.id == change_id).first()
            )
            if not change:
                return False

            change.notification_channel = channel
            change.notification_ts = message_ts

        return True

    @staticmethod
    def get_notification_info(change_id: str) -> ProfileChange | None:
        """Get the profile change containing notification metadata.

        :param change_id: The change identifier.

        :returns: ProfileChange model with notification fields populated, or None.

        """
        with get_db() as db:
            change = (
                db.query(ProfileChange).filter(ProfileChange.id == change_id).first()
            )
            if not change or not change.notification_ts:
                return None
            return change
