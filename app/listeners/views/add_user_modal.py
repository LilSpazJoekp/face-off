"""View handler for the add user modal submission."""

import logging
from typing import Any

from slack_bolt import Ack
from slack_sdk import WebClient

from ...app import app
from ...storage import (
    add_pending_consent,
    is_consent_pending,
    is_user_watched,
)
from ..events.app_home_opened import build_home_view

log = logging.getLogger(__name__)


@app.view("add_user_modal_submit")
def add_user_modal_callback(
    ack: Ack, body: dict[str, Any], client: WebClient, view: dict[str, Any]
) -> None:
    """Handle the add user modal submission."""
    requesting_user = body["user"]["id"]

    # Get the selected user from the modal
    values = view["state"]["values"]
    selected_user = values["user_select_block"]["user_select"]["selected_user"]

    # Check if user is already watched
    if is_user_watched(selected_user):
        ack(
            response_action="errors",
            errors={"user_select_block": "This user is already on the watch list."},
        )
        return

    # Check if consent is already pending
    if is_consent_pending(selected_user):
        ack(
            response_action="errors",
            errors={
                "user_select_block": "A consent request is already pending for this user."
            },
        )
        return

    # Acknowledge the modal submission
    ack()

    # Add to pending consent - user will see request in their Home tab
    added = add_pending_consent(selected_user, requesting_user)

    if added:
        log.info(f"Consent request created for {selected_user} by {requesting_user}")

    # Refresh the home view for the requesting user
    home_view = build_home_view(requesting_user)
    client.views_publish(user_id=requesting_user, view=home_view)
