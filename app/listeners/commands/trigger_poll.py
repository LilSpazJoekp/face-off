"""Command to manually trigger the weekly poll."""

from slack_bolt import Ack, Respond

from ...app import app


@app.command("/trigger-poll")
def trigger_poll_callback(ack: Ack, respond: Respond, client) -> None:
    """Manually trigger the weekly poll."""
    from ...scheduler import create_weekly_poll

    ack()
    created = create_weekly_poll(client, manual=True)

    if created:
        respond("Poll triggered! Check the notification channel.")
    else:
        respond("No updates to vote on this week.")
