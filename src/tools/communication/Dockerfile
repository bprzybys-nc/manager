FROM python:3.13-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN pip install uv

RUN --mount=type=bind,source=/src/tools/communication/uv.lock,target=uv.lock \
    --mount=type=bind,source=/src/tools/communication/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY /src/tools/communication /app/src/tools/communication
COPY /src/modules/incident /app/src/modules/incident
COPY /src/modules/inventory /app/src/modules/inventory
COPY /src/modules/task /app/src/modules/task
COPY /src/modules/cmdb /app/src/modules/cmdb
COPY /src/tools/communication/app /app


EXPOSE 8002

RUN ls -la

CMD ["uv", "run", "uvicorn", "api:app", "--port", "8002", "--host", "0.0.0.0"]
