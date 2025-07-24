FROM python:3.13-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN pip install uv

RUN --mount=type=bind,source=/src/usecases/db_incident_assistant/uv.lock,target=uv.lock \
    --mount=type=bind,source=/src/usecases/db_incident_assistant/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev


COPY /src/usecases/db_incident_assistant/app /app

COPY /src/usecases/db_incident_assistant /app/src/usecases/db_incident_assistant

COPY /src/modules/incident /app/src/modules/incident
COPY /src/modules/inventory /app/src/modules/inventory
COPY /src/modules/task /app/src/modules/task
COPY /src/modules/cmdb /app/src/modules/cmdb
COPY /src/modules/tools /app/src/modules/tools
COPY /src/tools /app/src/tools
COPY /src/llm /app/src/llm



EXPOSE 8000

RUN ls -la

CMD ["uv", "run", "uvicorn", "api:app", "--port", "8000", "--host", "0.0.0.0"]
