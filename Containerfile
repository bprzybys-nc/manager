FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

EXPOSE 9123/tcp

RUN --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ADD . /app
RUN uv sync --frozen --no-dev

ENV AZURE_OPENAI_API_KEY="***"
ENV AZURE_OPENAI_ENDPOINT="https://***"

ENV SLACK_BOT_TOKEN="xoxb-***"
ENV SLACK_APP_TOKEN="xapp-***"
ENV SLACK_CHANNEL_NAME="project-harbinger"

ENV LANGFUSE_HOST="http://***"
ENV LANGFUSE_PUBLIC_KEY="pk-***"
ENV LANGFUSE_SECRET_KEY="sk-****"

ENV PROMETHEUS_ADDRESS="http://localhost:9090"
ENV METRICS_DIR="metrics"

ENV MONGO_DB_URI="mongodb://localhost:27017"
ENV SYSAIDMIN_DB_NAME="sysaidmin"
ENV CHECKPOINT_COLLECTION_NAME="checkpoints"

ENV CELERY_BROKER_URL="redis://localhost:6379/0"

ENV MANAGER_API_ADDRESS="http://localhost:9123"

ENTRYPOINT ["uv", "run"]

CMD ["uvicorn", "main:app", "--port", "9123", "--host", "0.0.0.0"]
