"""Handler for ending a poll."""

import logging
from collections.abc import Mapping
from typing import Any

from slack_bolt import Ack
from slack_sdk import WebClient

from ...app import app
from ...storage import end_poll, get_poll

log = logging.getLogger(__name__)


def _value(record: Any, key: str) -> Any:
    """Get a field from either a model object or mapping."""
    if isinstance(record, Mapping):
        return record.get(key)
    return getattr(record, key, None)


@app.action("end_poll")
def end_poll_callback(ack: Ack, body: dict[str, Any], client: WebClient) -> None:
    """End a poll and update the summary message."""
    # Import here to avoid circular import
    from ...scheduler import build_summary_blocks, update_poll_user_messages

    ack()

    poll_id = body["actions"][0]["value"]

    # End the poll
    success = end_poll(poll_id)
    if not success:
        log.error(f"Failed to end poll {poll_id}")
        return

    log.info(f"Poll {poll_id} ended by {body['user']['id']}")

    # Update all user messages to remove vote buttons
    update_poll_user_messages(client, poll_id, ended=True)

    # Update the summary message with final results
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
            log.exception("Error updating poll summary after ending")
