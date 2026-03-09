"""Service for sending Slack notifications."""

import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

log = logging.getLogger(__name__)


class NotificationService:
    """Service for sending Slack notifications and managing messages."""

    def __init__(self, client: WebClient) -> None:
        """Initialize the notification service.

        :param client: The Slack client instance.

        """
        self.client = client

    def join_channel(self, channel_id: str) -> bool:
        """Join a Slack channel.

        :param channel_id: The channel ID to join.

        :returns: True if successful, False otherwise.

        """
        try:
            self.client.conversations_join(channel=channel_id)
        except SlackApiError:
            log.exception(f"Failed to join channel {channel_id}")
            return False
        else:
            return True

    def post_message(
        self,
        channel: str,
        text: str,
        blocks: list | None = None,
        metadata: dict | None = None,
    ) -> dict | None:
        """Post a message to a channel.

        :param channel: The channel ID to post to.
        :param text: Fallback text for the message.
        :param blocks: Optional Block Kit blocks.
        :param metadata: Optional message metadata.

        :returns: API response dict containing 'ts', or None on failure.

        """
        try:
            kwargs = {
                "channel": channel,
                "text": text,
            }
            if blocks:
                kwargs["blocks"] = blocks
            if metadata:
                kwargs["metadata"] = metadata

            result = self.client.chat_postMessage(**kwargs)
            return {"ts": result["ts"], "channel": result["channel"]}
        except SlackApiError:
            log.exception(f"Failed to post message to {channel}")
            return None

    def update_message(
        self,
        channel: str,
        ts: str,
        text: str,
        blocks: list | None = None,
    ) -> bool:
        """Update an existing message.

        :param channel: The channel ID containing the message.
        :param ts: The message timestamp.
        :param text: Updated fallback text.
        :param blocks: Optional updated Block Kit blocks.

        :returns: True if successful, False otherwise.

        """
        try:
            kwargs = {
                "channel": channel,
                "ts": ts,
                "text": text,
            }
            if blocks:
                kwargs["blocks"] = blocks

            self.client.chat_update(**kwargs)
        except SlackApiError:
            log.exception(f"Failed to update message in {channel}")
            return False
        else:
            return True

    def post_ephemeral(
        self,
        channel: str,
        user: str,
        text: str,
        blocks: list | None = None,
    ) -> bool:
        """Post an ephemeral message visible only to one user.

        :param channel: The channel ID to post to.
        :param user: The user ID who will see the message.
        :param text: The message text.
        :param blocks: Optional Block Kit blocks.

        :returns: True if successful, False otherwise.

        """
        try:
            kwargs = {
                "channel": channel,
                "user": user,
                "text": text,
            }
            if blocks:
                kwargs["blocks"] = blocks

            self.client.chat_postEphemeral(**kwargs)
        except SlackApiError:
            log.exception(f"Failed to post ephemeral to {user} in {channel}")
            return False
        else:
            return True

    def open_view(self, trigger_id: str, view: dict) -> bool:
        """Open a modal view.

        :param trigger_id: The trigger ID from user interaction.
        :param view: The view definition.

        :returns: True if successful, False otherwise.

        """
        try:
            self.client.views_open(trigger_id=trigger_id, view=view)
        except SlackApiError:
            log.exception("Failed to open view")
            return False
        else:
            return True

    def update_view(self, view_id: str, view: dict) -> bool:
        """Update an existing modal view.

        :param view_id: The view ID to update.
        :param view: The updated view definition.

        :returns: True if successful, False otherwise.

        """
        try:
            self.client.views_update(view_id=view_id, view=view)
        except SlackApiError:
            log.exception(f"Failed to update view {view_id}")
            return False
        else:
            return True

    def publish_home_tab(self, user_id: str, view: dict) -> bool:
        """Publish the app home tab for a user.

        :param user_id: The user ID to publish for.
        :param view: The home tab view definition.

        :returns: True if successful, False otherwise.

        """
        try:
            self.client.views_publish(user_id=user_id, view=view)
        except SlackApiError:
            log.exception(f"Failed to publish home tab for {user_id}")
            return False
        else:
            return True

    def send_direct_message(
        self,
        user_id: str,
        text: str,
        blocks: list | None = None,
    ) -> dict | None:
        """Send a direct message to a user.

        :param user_id: The user ID to message.
        :param text: The message text.
        :param blocks: Optional Block Kit blocks.

        :returns: API response dict with 'ts' and 'channel', or None on failure.

        """
        try:
            # Open a DM channel with the user
            response = self.client.conversations_open(users=[user_id])
            channel_id = response["channel"]["id"]

            return self.post_message(channel_id, text, blocks)
        except SlackApiError:
            log.exception(f"Failed to send DM to {user_id}")
            return None
