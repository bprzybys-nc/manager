FROM python:3.13-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN pip install uv
RUN --mount=type=bind,source=/src/tools/db_servers_cmdb/uv.lock,target=uv.lock \
    --mount=type=bind,source=/src/tools/db_servers_cmdb/pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY /src/modules/tools /app/src/modules/tools
COPY /src/tools/db_servers_cmdb /app/src/tools/db_servers_cmdb

COPY /src/tools/db_servers_cmdb/app /app


EXPOSE 8001

CMD ["uv", "run", "uvicorn", "api:app", "--port", "8001", "--host", "0.0.0.0"]
