FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

RUN uv sync --no-dev

CMD ["uv", "run", "-m", "app"]
