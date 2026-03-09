"""Actions for handling consent requests from the app home."""

import logging
from typing import Any

from slack_bolt import Ack
from slack_sdk import WebClient

from ...app import app
from ...storage import (
    add_watched_user,
    is_consent_pending,
    remove_pending_consent,
)
from ..events.app_home_opened import build_home_view

log = logging.getLogger(__name__)


@app.action("consent_accept")
def consent_accept_callback(ack: Ack, body: dict[str, Any], client: WebClient) -> None:
    """Handle user accepting the consent request from the home tab."""
    ack()

    user_id = body["user"]["id"]

    # Verify this user has a pending consent
    if not is_consent_pending(user_id):
        log.warning(f"No pending consent for user {user_id}")
        return

    # Add user to watched list
    added = add_watched_user(user_id)

    if added:
        log.info(f"User {user_id} accepted consent and was added to watch list")

    # Refresh user's home view to show updated status
    view = build_home_view(user_id)
    client.views_publish(user_id=user_id, view=view)


@app.action("consent_decline")
def consent_decline_callback(ack: Ack, body: dict[str, Any], client: WebClient) -> None:
    """Handle user declining the consent request from the home tab."""
    ack()

    user_id = body["user"]["id"]

    # Remove from pending consent
    remove_pending_consent(user_id)

    log.info(f"User {user_id} declined consent request")

    # Refresh user's home view to show updated status
    view = build_home_view(user_id)
    client.views_publish(user_id=user_id, view=view)
