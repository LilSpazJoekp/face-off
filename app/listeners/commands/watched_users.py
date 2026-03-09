"""Command to show watched users."""

from slack_bolt import Ack, Respond

from ...app import app
from ...storage import get_watched_users

app.command("/watched-users")


def watched_users_callback(ack: Ack, respond: Respond) -> None:
    """Show the list of watched users."""
    ack()

    watched_user_ids = get_watched_users()

    if watched_user_ids:
        user_list = ", ".join([f"<@{uid}>" for uid in watched_user_ids])
        respond(f"Currently watching: {user_list}")
    else:
        respond("No users are being watched. Add users from the app's Home tab.")
