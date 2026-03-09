"""Handler for user profile change events."""

import logging

from ...app import app
from ...services.profile_change_service import ProfileChangeService

log = logging.getLogger(__name__)


@app.event("user_change")
def user_change_callback(event, client):
    """Handle user profile changes and detect profile picture updates."""
    user = event.get("user", {})
    ProfileChangeService.process_user_change(user, client)
