"""Service for managing application settings."""

from ..database import get_db
from ..models import Setting


class SettingsService:
    """Service for managing application settings."""

    @staticmethod
    def get_setting(key: str, default: str | None = None) -> str | None:
        """Get a setting value by key.

        :param key: The setting key.
        :param default: Default value if setting not found.

        :returns: The setting value or default.

        """
        with get_db() as db:
            if setting := db.query(Setting).filter(Setting.key == key).first():
                return setting.value
            return default

    @staticmethod
    def set_setting(key: str, value: str) -> None:
        """Set a setting value.

        :param key: The setting key.
        :param value: The value to store.

        """
        with get_db() as db:
            setting = db.query(Setting).filter(Setting.key == key).first()
            if setting:
                setting.value = value
            else:
                setting = Setting(key=key, value=value)
                db.add(setting)

    @staticmethod
    def get_notification_channel() -> str | None:
        """Get the configured notification channel ID.

        :returns: The Slack channel ID, or None if not configured.

        """
        return SettingsService.get_setting("notification_channel")

    @staticmethod
    def set_notification_channel(channel_id: str) -> None:
        """Set the notification channel ID.

        :param channel_id: The Slack channel ID.

        """
        SettingsService.set_setting("notification_channel", channel_id)

    @staticmethod
    def get_max_votes() -> int:
        """Get the max votes per voter setting.

        :returns: Maximum number of votes allowed per voter (default 3).

        """
        value = SettingsService.get_setting("max_votes")
        return int(value) if value else 3

    @staticmethod
    def set_max_votes(max_votes: int) -> None:
        """Set the max votes per voter.

        :param max_votes: Maximum number of votes allowed.

        """
        SettingsService.set_setting("max_votes", str(max_votes))

    @staticmethod
    def get_poll_day() -> str:
        """Get the day of week for polls.

        :returns: Day abbreviation (e.g., 'mon', 'tue'). Default 'mon'.

        """
        return SettingsService.get_setting("poll_day", "mon")

    @staticmethod
    def set_poll_day(day: str) -> None:
        """Set the day of week for polls.

        :param day: Day abbreviation (e.g., 'mon', 'tue', 'wed').

        """
        SettingsService.set_setting("poll_day", day)

    @staticmethod
    def get_poll_hour() -> int:
        """Get the hour for polls.

        :returns: Hour in 24-hour format (default 9).

        """
        value = SettingsService.get_setting("poll_hour")
        return int(value) if value else 9

    @staticmethod
    def set_poll_hour(hour: int) -> None:
        """Set the hour for polls.

        :param hour: Hour in 24-hour format (0-23).

        """
        SettingsService.set_setting("poll_hour", str(hour))

    @staticmethod
    def get_poll_duration_hours() -> int:
        """Get the poll duration in hours.

        :returns: Duration in hours (default 24).

        """
        value = SettingsService.get_setting("poll_duration_hours")
        return int(value) if value else 24

    @staticmethod
    def set_poll_duration_hours(hours: int) -> None:
        """Set the poll duration in hours.

        :param hours: Duration in hours.

        """
        SettingsService.set_setting("poll_duration_hours", str(hours))

    @staticmethod
    def get_poll_duration_days() -> int:
        """Get the number of days to collect changes for polls.

        :returns: Number of days (default 7).

        """
        value = SettingsService.get_setting("poll_duration_days")
        return int(value) if value else 7

    @staticmethod
    def set_poll_duration_days(days: int) -> None:
        """Set the number of days to collect changes for polls.

        :param days: Number of days.

        """
        SettingsService.set_setting("poll_duration_days", str(days))
