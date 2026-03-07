"""Service for managing polls and voting."""

from collections.abc import Mapping
from datetime import datetime
from typing import TypedDict

import pytz
from sqlalchemy.orm import selectinload

from ..dependencies import inject_services
from ..database import get_db
from ..models import Poll, PollCandidate, PollCandidatePicture, ProfileChange, Vote
from .profile_change_service import ProfileChangeService
from .settings_service import SettingsService

CT_TIMEZONE = pytz.timezone("America/Chicago")


class PictureInput(TypedDict, total=False):
    """Input shape for creating poll candidate pictures."""

    avatar_url: str
    duration: str
    week: str
    timestamp: datetime | str
    description: str | None
    description_edited_by: str | None
    description_edited_at: datetime | str | None


class UserPollInput(TypedDict):
    """Input shape for a poll candidate and their pictures."""

    user_id: str
    display_name: str
    pictures: list[PictureInput]


class PollService:
    """Service for managing profile picture polls and votes."""

    @staticmethod
    def _coerce_datetime(value: datetime | str | None) -> datetime | None:
        """Normalize datetime values from typed payloads."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    @staticmethod
    def create_poll(
        poll_id: str,
        users: Mapping[str, UserPollInput | list[ProfileChange]],
        ends_at: datetime | None = None,
    ) -> Poll:
        """Create a new poll with users as candidates.

        :param poll_id: Unique identifier for the poll.
        :param users: User payload keyed by user_id.
        :param ends_at: Optional datetime when the poll should end.

        :returns: Poll model instance.

        """
        now = datetime.now(CT_TIMEZONE)

        with get_db() as db:
            poll = Poll(poll_id=poll_id, created_at=now, ends_at=ends_at)
            db.add(poll)
            db.flush()

            for user_id, user_data in users.items():
                if isinstance(user_data, list):
                    if not user_data:
                        continue
                    display_name = user_data[0].display_name
                    pictures: list[PictureInput] = [
                        {
                            "avatar_url": change.avatar_url,
                            "duration": ProfileChangeService.get_change_duration(
                                change
                            ),
                            "week": change.timestamp.strftime("%Y-W%W"),
                            "timestamp": change.timestamp,
                            "description": change.description,
                            "description_edited_by": change.description_edited_by,
                            "description_edited_at": change.description_edited_at,
                        }
                        for change in user_data
                    ]
                else:
                    display_name = user_data["display_name"]
                    pictures = user_data.get("pictures", [])

                candidate = PollCandidate(
                    poll_id=poll_id,
                    user_id=user_id,
                    display_name=display_name,
                )
                db.add(candidate)
                db.flush()

                for pic in pictures:
                    timestamp = PollService._coerce_datetime(pic.get("timestamp"))
                    if timestamp is None:
                        continue

                    db.add(
                        PollCandidatePicture(
                            poll_candidate_id=candidate.id,
                            avatar_url=pic["avatar_url"],
                            duration=pic["duration"],
                            week=pic["week"],
                            timestamp=timestamp,
                            description=pic.get("description"),
                            description_edited_by=pic.get("description_edited_by"),
                            description_edited_at=PollService._coerce_datetime(
                                pic.get("description_edited_at")
                            ),
                        )
                    )

        created_poll = PollService.get_poll(poll_id)
        if created_poll is None:
            raise RuntimeError(f"Poll {poll_id} was not persisted")
        return created_poll

    @staticmethod
    def get_poll(poll_id: str) -> Poll | None:
        """Get poll data by ID.

        :param poll_id: The poll identifier.

        :returns: Poll model with candidates/pictures/votes eagerly loaded.

        """
        with get_db() as db:
            poll = (
                db.query(Poll)
                .options(
                    selectinload(Poll.candidates).selectinload(PollCandidate.pictures),
                    selectinload(Poll.votes),
                )
                .filter(Poll.poll_id == poll_id)
                .first()
            )

        if poll is None:
            return None

        for candidate in poll.candidates:
            candidate.pictures.sort(key=lambda picture: picture.timestamp, reverse=True)
        poll.candidates.sort(key=lambda candidate: candidate.display_name.lower())
        return poll

    @staticmethod
    def end_poll(poll_id: str) -> bool:
        """End a poll, preventing further votes.

        :param poll_id: The poll identifier.

        :returns: True if successful, False if poll not found.

        """
        with get_db() as db:
            poll = db.query(Poll).filter(Poll.poll_id == poll_id).first()
            if not poll:
                return False
            poll.ended = "Y"
        return True

    @staticmethod
    def is_poll_ended(poll_id: str) -> bool:
        """Check if a poll has ended.

        :param poll_id: The poll identifier.

        :returns: True if poll has ended or doesn't exist, False otherwise.

        """
        with get_db() as db:
            poll = db.query(Poll).filter(Poll.poll_id == poll_id).first()
            if not poll:
                return True
            return poll.ended == "Y"

    @staticmethod
    def get_active_polls_with_end_time() -> list[Poll]:
        """Get all active polls that have an ends_at time set.

        :returns: List of active Poll model instances.

        """
        with get_db() as db:
            return (
                db.query(Poll)
                .filter(Poll.ended.is_(None), Poll.ends_at.isnot(None))
                .order_by(Poll.ends_at.asc())
                .all()
            )

    @staticmethod
    @inject_services("settings_service")
    def record_vote(
        poll_id: str,
        voter_id: str,
        picture_id: int,
        settings_service: type[SettingsService] = SettingsService,
    ) -> bool:
        """Record a vote for a specific picture.

        :param poll_id: The poll identifier.
        :param voter_id: The Slack user ID of the voter.
        :param picture_id: The picture ID to vote for.

        :returns: True if vote was recorded, False if at max votes or already voted.

        """
        now = datetime.now(CT_TIMEZONE)
        max_votes = settings_service.get_max_votes()

        with get_db() as db:
            poll = db.query(Poll).filter(Poll.poll_id == poll_id).first()
            if not poll or poll.ended == "Y":
                return False

            existing_vote = (
                db.query(Vote)
                .filter(
                    Vote.poll_id == poll_id,
                    Vote.voter_id == voter_id,
                    Vote.picture_id == picture_id,
                )
                .first()
            )
            if existing_vote:
                return False

            voter_vote_count = (
                db.query(Vote)
                .filter(Vote.poll_id == poll_id, Vote.voter_id == voter_id)
                .count()
            )
            if voter_vote_count >= max_votes:
                return False

            db.add(
                Vote(
                    poll_id=poll_id,
                    voter_id=voter_id,
                    picture_id=picture_id,
                    voted_at=now,
                )
            )

        return True

    @staticmethod
    def remove_vote(poll_id: str, voter_id: str, picture_id: int) -> bool:
        """Remove a vote for a specific picture (toggle off).

        :param poll_id: The poll identifier.
        :param voter_id: The Slack user ID of the voter.
        :param picture_id: The picture ID to remove vote from.

        :returns: True if vote was removed, False if not found.

        """
        with get_db() as db:
            result = (
                db.query(Vote)
                .filter(
                    Vote.poll_id == poll_id,
                    Vote.voter_id == voter_id,
                    Vote.picture_id == picture_id,
                )
                .delete()
            )
            return result > 0

    @staticmethod
    def has_voted_for_picture(poll_id: str, voter_id: str, picture_id: int) -> bool:
        """Check if a voter has voted for a specific picture.

        :param poll_id: The poll identifier.
        :param voter_id: The Slack user ID of the voter.
        :param picture_id: The picture ID to check.

        :returns: True if voter has voted for the picture, False otherwise.

        """
        with get_db() as db:
            vote = (
                db.query(Vote)
                .filter(
                    Vote.poll_id == poll_id,
                    Vote.voter_id == voter_id,
                    Vote.picture_id == picture_id,
                )
                .first()
            )
            return vote is not None

    @staticmethod
    def get_vote_counts(poll_id: str) -> dict[int, int]:
        """Get vote counts for each picture in a poll.

        :param poll_id: The poll identifier.

        :returns: Dictionary mapping picture_id to vote count.

        """
        with get_db() as db:
            pictures = (
                db.query(PollCandidatePicture)
                .join(PollCandidate)
                .filter(PollCandidate.poll_id == poll_id)
                .all()
            )
            counts = {picture.id: 0 for picture in pictures}

            votes = db.query(Vote).filter(Vote.poll_id == poll_id).all()
            for vote in votes:
                if vote.picture_id in counts:
                    counts[vote.picture_id] += 1
            return counts

    @staticmethod
    def get_picture_vote_count(poll_id: str, picture_id: int) -> int:
        """Get vote count for a specific picture.

        :param poll_id: The poll identifier.
        :param picture_id: The picture ID.

        :returns: Number of votes for the picture.

        """
        with get_db() as db:
            return (
                db.query(Vote)
                .filter(Vote.poll_id == poll_id, Vote.picture_id == picture_id)
                .count()
            )

    @staticmethod
    def get_user_total_votes(poll_id: str, user_id: str) -> int:
        """Get total votes across all pictures for a specific user in the poll.

        :param poll_id: The poll identifier.
        :param user_id: The user whose pictures to count votes for.

        :returns: Total number of votes for the user's pictures.

        """
        with get_db() as db:
            return (
                db.query(Vote)
                .join(PollCandidatePicture)
                .join(PollCandidate)
                .filter(
                    Vote.poll_id == poll_id,
                    PollCandidate.user_id == user_id,
                )
                .count()
            )

    @staticmethod
    def get_voter_votes(poll_id: str, voter_id: str) -> list[int]:
        """Get list of picture_ids the voter has voted for.

        :param poll_id: The poll identifier.
        :param voter_id: The Slack user ID of the voter.

        :returns: List of picture IDs.

        """
        with get_db() as db:
            votes = (
                db.query(Vote)
                .filter(Vote.poll_id == poll_id, Vote.voter_id == voter_id)
                .all()
            )
            return [vote.picture_id for vote in votes]

    @staticmethod
    @inject_services("settings_service")
    def get_voter_remaining_votes(
        poll_id: str,
        voter_id: str,
        settings_service: type[SettingsService] = SettingsService,
    ) -> int:
        """Get how many more votes the voter can cast.

        :param poll_id: The poll identifier.
        :param voter_id: The Slack user ID of the voter.

        :returns: Number of remaining votes.

        """
        max_votes = settings_service.get_max_votes()
        current_votes = len(PollService.get_voter_votes(poll_id, voter_id))
        return max(0, max_votes - current_votes)

    @staticmethod
    def get_all_pictures_with_votes(
        poll_id: str,
    ) -> list[tuple[PollCandidatePicture, str, str, int]]:
        """Get all poll pictures with vote counts, sorted by votes descending.

        :param poll_id: The poll identifier.

        :returns: List of (picture, user_id, display_name, vote_count) tuples.

        """
        with get_db() as db:
            candidates = (
                db.query(PollCandidate)
                .options(selectinload(PollCandidate.pictures))
                .filter(PollCandidate.poll_id == poll_id)
                .all()
            )

            votes = db.query(Vote).filter(Vote.poll_id == poll_id).all()
            vote_counts: dict[int, int] = {}
            for vote in votes:
                vote_counts[vote.picture_id] = vote_counts.get(vote.picture_id, 0) + 1

        pictures_with_votes: list[tuple[PollCandidatePicture, str, str, int]] = []
        for candidate in candidates:
            for picture in candidate.pictures:
                pictures_with_votes.append(
                    (
                        picture,
                        candidate.user_id,
                        candidate.display_name,
                        vote_counts.get(picture.id, 0),
                    )
                )

        pictures_with_votes.sort(key=lambda pair: pair[3], reverse=True)
        return pictures_with_votes

    @staticmethod
    def save_poll_message_ts(
        poll_id: str,
        user_id: str,
        channel: str,
        message_ts: str,
    ) -> bool:
        """Save the message timestamp for a user's poll message.

        :param poll_id: The poll identifier.
        :param user_id: The Slack user ID.
        :param channel: The Slack channel ID.
        :param message_ts: The message timestamp.

        :returns: True if successful, False if candidate not found.

        """
        with get_db() as db:
            candidate = (
                db.query(PollCandidate)
                .filter(
                    PollCandidate.poll_id == poll_id, PollCandidate.user_id == user_id
                )
                .first()
            )
            if not candidate:
                return False

            candidate.message_ts = message_ts
            candidate.message_channel = channel

        return True

    @staticmethod
    def save_poll_summary_ts(poll_id: str, channel: str, message_ts: str) -> bool:
        """Save the message timestamp for a poll's summary message.

        :param poll_id: The poll identifier.
        :param channel: The Slack channel ID.
        :param message_ts: The message timestamp.

        :returns: True if successful, False if poll not found.

        """
        with get_db() as db:
            poll = db.query(Poll).filter(Poll.poll_id == poll_id).first()
            if not poll:
                return False

            poll.summary_message_ts = message_ts
            poll.summary_message_channel = channel

        return True

    @staticmethod
    def get_candidate_message_info(poll_id: str, user_id: str) -> PollCandidate | None:
        """Get the candidate record containing message ts/channel information.

        :param poll_id: The poll identifier.
        :param user_id: The Slack user ID.

        :returns: PollCandidate model with message metadata, or None if missing.

        """
        with get_db() as db:
            candidate = (
                db.query(PollCandidate)
                .filter(
                    PollCandidate.poll_id == poll_id, PollCandidate.user_id == user_id
                )
                .first()
            )
            if not candidate or not candidate.message_ts:
                return None
            return candidate

    @staticmethod
    def get_picture(picture_id: int) -> PollCandidatePicture | None:
        """Get a single picture by ID.

        :param picture_id: The picture identifier.

        :returns: PollCandidatePicture model, or None if not found.

        """
        with get_db() as db:
            return (
                db.query(PollCandidatePicture)
                .options(selectinload(PollCandidatePicture.candidate))
                .filter(PollCandidatePicture.id == picture_id)
                .first()
            )

    @staticmethod
    def update_picture_description(
        picture_id: int, description: str, edited_by: str
    ) -> bool:
        """Update a picture's description.

        :param picture_id: The picture identifier.
        :param description: The new description text.
        :param edited_by: User ID of who made the edit.

        :returns: True if successful, False if picture not found.

        """
        now = datetime.now(CT_TIMEZONE)
        cleaned_description = description.strip()

        with get_db() as db:
            picture = (
                db.query(PollCandidatePicture)
                .filter(PollCandidatePicture.id == picture_id)
                .first()
            )
            if not picture:
                return False

            if cleaned_description:
                picture.description = cleaned_description
                picture.description_edited_by = edited_by
                picture.description_edited_at = now
            else:
                picture.description = None
                picture.description_edited_by = None
                picture.description_edited_at = None

        return True
