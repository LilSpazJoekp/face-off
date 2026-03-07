"""Service for managing watched users and consent."""

from datetime import datetime

import pytz

from ..database import get_db
from ..models import PendingConsent, WatchedUser

CT_TIMEZONE = pytz.timezone("America/Chicago")


class UserWatchlistService:
    """Service for managing user consent and the watched users list."""

    @staticmethod
    def get_watched_users() -> list[str]:
        """Get list of user IDs who have consented to be watched.

        :returns: List of Slack user ID strings.

        """
        with get_db() as db:
            users = db.query(WatchedUser).all()
            return [user.user_id for user in users]

    @staticmethod
    def is_user_watched(user_id: str) -> bool:
        """Check if a user is in the watched list.

        :param user_id: The Slack user ID to check.

        :returns: True if user is being watched, False otherwise.

        """
        return user_id in UserWatchlistService.get_watched_users()

    @staticmethod
    def add_watched_user(user_id: str) -> bool:
        """Add a user to the watched list.

        :param user_id: The Slack user ID to add.

        :returns: True if added, False if already exists.

        """
        if UserWatchlistService.is_user_watched(user_id):
            return False

        now = datetime.now(CT_TIMEZONE)
        with get_db() as db:
            db.add(WatchedUser(user_id=user_id, added_at=now))

        UserWatchlistService.remove_pending_consent(user_id)
        return True

    @staticmethod
    def remove_watched_user(user_id: str) -> bool:
        """Remove a user from the watched list.

        :param user_id: The Slack user ID to remove.

        :returns: True if removed, False if not found.

        """
        if not UserWatchlistService.is_user_watched(user_id):
            return False

        with get_db() as db:
            db.query(WatchedUser).filter(WatchedUser.user_id == user_id).delete()

        return True

    @staticmethod
    def add_pending_consent(user_id: str, requested_by: str) -> bool:
        """Add a user to pending consent.

        :param user_id: The Slack user ID to request consent from.
        :param requested_by: The Slack user ID who requested.

        :returns: True if added, False if already pending or watched.

        """
        if UserWatchlistService.is_user_watched(user_id):
            return False
        if UserWatchlistService.is_consent_pending(user_id):
            return False

        now = datetime.now(CT_TIMEZONE)
        with get_db() as db:
            db.add(
                PendingConsent(
                    user_id=user_id,
                    requested_by=requested_by,
                    requested_at=now,
                )
            )

        return True

    @staticmethod
    def remove_pending_consent(user_id: str) -> bool:
        """Remove a user from pending consent.

        :param user_id: The Slack user ID to remove.

        :returns: True if removed, False if not found.

        """
        if not UserWatchlistService.is_consent_pending(user_id):
            return False

        with get_db() as db:
            db.query(PendingConsent).filter(PendingConsent.user_id == user_id).delete()

        return True

    @staticmethod
    def get_pending_consent(user_id: str) -> PendingConsent | None:
        """Get pending consent info for a user.

        :param user_id: The Slack user ID to check.

        :returns: PendingConsent model, or None if not pending.

        """
        with get_db() as db:
            return (
                db.query(PendingConsent)
                .filter(PendingConsent.user_id == user_id)
                .first()
            )

    @staticmethod
    def is_consent_pending(user_id: str) -> bool:
        """Check if consent is pending for a user.

        :param user_id: The Slack user ID to check.

        :returns: True if consent is pending, False otherwise.

        """
        return UserWatchlistService.get_pending_consent(user_id) is not None
