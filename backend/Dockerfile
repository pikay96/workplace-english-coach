FROM ghcr.io/astral-sh/uv:0.11.18 AS uv
FROM python:3.12.12-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    UV_CONCURRENT_DOWNLOADS=4 UV_HTTP_TIMEOUT=120 \
    HF_HOME=/opt/models HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 OTEL_SDK_DISABLED=true \
    PATH=/app/.venv/bin:$PATH
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --no-install-project
COPY backend/app/voice/download_assets.py /tmp/download_assets.py
RUN python /tmp/download_assets.py
RUN groupadd --gid 10001 tutor && useradd --uid 10001 --gid tutor --create-home tutor \
    && chmod -R a+rX /opt/models
COPY --chown=tutor:tutor backend/app ./app
COPY --chown=tutor:tutor content ./content
ENV HF_HUB_OFFLINE=1
USER tutor
CMD ["python", "-m", "app.voice.agent"]
