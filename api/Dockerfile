FROM ghcr.io/astral-sh/uv:0.13.7 AS uv

FROM python:3.15.2-slim

COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app/api

# Dependencies first, so code changes reuse this layer. The dev group is kept for `pytest`.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

COPY . .
# Read by the seed command from ../samples (settings.SAMPLES_DIR).
COPY --from=samples . /app/samples

RUN useradd --system --create-home app && mkdir /data && chown app /data /app/api
USER app

EXPOSE 8000
# TD-10: migrate and seed (idempotent) on every start. TD-4: one worker, so there is exactly one sweeper.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed && exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 1 --threads 8"]
