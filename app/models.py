"""SQLAlchemy models for the profile picture tracker."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class ProfileChange(Base):
    """Record of a user's profile picture change."""

    __tablename__ = "profile_changes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str] = mapped_column(String(2048))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description_edited_by: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    description_edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notification_channel: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    notification_ts: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)


class Poll(Base):
    """Weekly poll for voting on profile pictures."""

    __tablename__ = "polls"

    poll_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended: Mapped[Optional[str]] = mapped_column(
        String(1), nullable=True
    )  # 'Y' if ended, NULL if active
    summary_message_ts: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    summary_message_channel: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )

    candidates: Mapped[List["PollCandidate"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan"
    )
    votes: Mapped[List["Vote"]] = relationship(
        back_populates="poll", cascade="all, delete-orphan"
    )


class PollCandidate(Base):
    """A user who is a candidate in a poll."""

    __tablename__ = "poll_candidates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    poll_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("polls.poll_id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str] = mapped_column(String(255))
    message_ts: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    message_channel: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        UniqueConstraint("poll_id", "user_id", name="uq_poll_candidate"),
        Index("ix_poll_candidates_poll_id", "poll_id"),
    )

    poll: Mapped["Poll"] = relationship(back_populates="candidates")
    pictures: Mapped[List["PollCandidatePicture"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class PollCandidatePicture(Base):
    """A profile picture for a poll candidate."""

    __tablename__ = "poll_candidate_pictures"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    poll_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("poll_candidates.id", ondelete="CASCADE")
    )
    avatar_url: Mapped[str] = mapped_column(String(2048))
    duration: Mapped[str] = mapped_column(String(32))
    week: Mapped[str] = mapped_column(String(16))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description_edited_by: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )
    description_edited_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_poll_candidate_pictures_candidate_id", "poll_candidate_id"),
    )

    candidate: Mapped["PollCandidate"] = relationship(back_populates="pictures")
    votes: Mapped[List["Vote"]] = relationship(
        back_populates="picture", cascade="all, delete-orphan"
    )


class Vote(Base):
    """A vote in a poll for a specific picture."""

    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    poll_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("polls.poll_id", ondelete="CASCADE")
    )
    voter_id: Mapped[str] = mapped_column(String(32))
    picture_id: Mapped[int] = mapped_column(
        ForeignKey("poll_candidate_pictures.id", ondelete="CASCADE")
    )
    voted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("poll_id", "voter_id", "picture_id", name="uq_vote_picture"),
        Index("ix_votes_poll_id", "poll_id"),
        Index("ix_votes_picture", "poll_id", "picture_id"),
        Index("ix_votes_voter", "poll_id", "voter_id"),
    )

    poll: Mapped["Poll"] = relationship(back_populates="votes")
    picture: Mapped["PollCandidatePicture"] = relationship(back_populates="votes")


class WatchedUser(Base):
    """A user who has consented to be watched for profile changes."""

    __tablename__ = "watched_users"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PendingConsent(Base):
    """A pending consent request for a user to be watched."""

    __tablename__ = "pending_consent"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    requested_by: Mapped[str] = mapped_column(String(32))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Setting(Base):
    """Application settings stored as key-value pairs."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(1024))
