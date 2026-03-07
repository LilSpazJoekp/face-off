# Face Off

A Slack bot that highlights daily profile picture changes with voting and commentary.

## Setup

### Create a Slack App

1. Open [https://api.slack.com/apps/new](https://api.slack.com/apps/new) and choose "From an app manifest"
2. Choose the workspace you want to install the application to
3. Copy the contents of [manifest.json](./manifest.json) into the text box that says `*Paste your manifest code here*` (within the JSON tab) and click *Next*
4. Review the configuration and click *Create*
5. Click *Install to Workspace* and *Allow* on the screen that follows. You'll then be redirected to the App Configuration dashboard.

### Environment Variables

1. From your app's configuration page, click **OAuth & Permissions** and copy the **Bot User OAuth Token** (`SLACK_BOT_TOKEN`).
2. Click **Basic Information** and create an app-level token with the `connections:write` scope (`SLACK_APP_TOKEN`).
3. Copy the example env file and fill in your values:

```sh
cp .env.example .env
```

## Running

### Docker (recommended)

```sh
docker compose up
```

This starts the bot and a PostgreSQL database.

### Local development

```sh
uv sync
uv run python -m app
```

## Project Structure

```
app/
  __main__.py          # Entry point
  app.py               # Slack Bolt app initialization
  database.py          # Database session management
  models.py            # SQLAlchemy models
  scheduler.py         # Poll scheduling
  log_config.py        # Colored logging setup
  services/            # Business logic
  listeners/
    actions/           # Button clicks, menu selections
    commands/          # Slash commands (/trigger-poll, /watched-users)
    events/            # Slack events (profile changes, app home)
    views/             # Modal submissions
tests/                 # Unit tests
```

## Development

```sh
uv sync --dev
uv run pytest
uv run ruff check .
```
