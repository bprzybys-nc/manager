FROM python:3.13-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN pip install uv
RUN --mount=type=bind,source=/src/tools/cmd_exec/uv.lock,target=uv.lock \
    --mount=type=bind,source=/src/tools/cmd_exec/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

    
COPY /src/modules/inventory /app/src/modules/inventory
COPY /src/modules/task /app/src/modules/task
COPY /src/modules/cmdb /app/src/modules/cmdb
COPY /src/modules/incident /app/src/modules/incident
COPY /src/modules/tools /app/src/modules/tools


COPY /src/tools/cmd_exec /app/src/tools/cmd_exec
COPY /src/tools/cmd_exec/app /app


EXPOSE 8003


CMD ["uv", "run", "uvicorn", "api:app", "--port", "8003", "--host", "0.0.0.0"]