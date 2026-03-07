#!/usr/bin/env python3

import logging
import os

from slack_bolt.adapter.socket_mode import SocketModeHandler

from .app import app
from .scheduler import start_scheduler

log = logging.getLogger(__name__)

# Start the weekly poll scheduler

scheduler = start_scheduler(app)
log.info("Face Off started!")

handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))

try:
    handler.start()
except KeyboardInterrupt:
    log.info("Shutting down...")
    scheduler.shutdown()
