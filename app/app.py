import logging
import os
import sys
from collections.abc import Callable
from typing import Any

from slack_bolt import App

from .database import run_migrations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


# Initialization - disable token verification in test mode
_testing = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")

# Run database migrations (skip in tests — they use in-memory SQLite)
if not _testing:
    run_migrations()


# Initialization - disable token verification in test mode
_testing = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    token_verification_enabled=not _testing,
)


# Middleware to inject scheduler into context
@app.middleware
def inject_scheduler(context: dict[str, Any], next_: Callable[[], None]) -> None:
    context["scheduler"] = getattr(app, "scheduler", None)
    next_()
