"""View handler for the poll schedule modal."""

import logging

from ...app import app
from ...storage import set_poll_day, set_poll_hour, set_poll_duration_hours
from ..events.app_home_opened import build_home_view

log = logging.getLogger(__name__)


@app.view("poll_schedule_modal_submit")
def poll_schedule_modal_callback(ack, body, client, view, context):
    """Handle the poll schedule modal submission."""
    # Import here to avoid circular import
    from ...scheduler import reschedule_poll

    ack()

    user_id = body["user"]["id"]

    # Get the selected values from the modal
    values = view["state"]["values"]
    selected_day = values["poll_day_block"]["poll_day_select"]["selected_option"][
        "value"
    ]
    selected_hour = int(
        values["poll_hour_block"]["poll_hour_select"]["selected_option"]["value"]
    )
    selected_duration = int(
        values["poll_duration_block"]["poll_duration_select"]["selected_option"][
            "value"
        ]
    )

    # Save the settings
    set_poll_day(selected_day)
    set_poll_hour(selected_hour)
    set_poll_duration_hours(selected_duration)

    # Reschedule the poll with new settings
    scheduler = context.get("scheduler")
    if scheduler:
        reschedule_poll(scheduler)

    log.info(
        f"Poll schedule updated by {user_id}: day={selected_day}, hour={selected_hour}, duration={selected_duration}h"
    )

    # Refresh the home view
    home_view = build_home_view(user_id)
    client.views_publish(user_id=user_id, view=home_view)
