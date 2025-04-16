# See https://docs.astral.sh/uv/guides/integration/docker
FROM python:3.10-slim-bookworm

ENV UV_LINK_MODE=copy

# Speeds up the build and reduces the image size dramatically
# --mount=type=cache,target=/root/.cache/uv

# Install dependencies

# https://stackoverflow.com/a/64604562/1504082: Use python3-dev libpq-dev to fix the
# Error: pg_config executable not found issue

RUN --mount=from=ghcr.io/astral-sh/uv:0.5.2,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    apt-get update \
    && apt-get install -y --no-install-recommends python3-dev libpq-dev gcc \
    && uv sync --frozen --no-install-project \
    && apt-get purge -y --auto-remove gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the project into the image
ADD app/ /app

WORKDIR /

ENV PATH="/.venv/bin/:$PATH"

ARG GIT_COMMIT
ENV GIT_COMMIT=$GIT_COMMIT

# Presuming there is a `my_app` command provided by the project
CMD ["python", "-m", "app.main"]
