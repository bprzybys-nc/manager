# Use an official Python runtime as a parent image
FROM python:3.13-slim

WORKDIR /app

# Set environment variables for uv to optimize performance
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install uv, the fast Python package installer
RUN pip install uv

# Install dependencies using uv sync with build mounts for better caching.
# This requires building with a context that includes the specified source files.
RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev

# Copy the application code into the container
COPY app/ ./app

# Expose the port the app runs on
EXPOSE 8004

# Run the application using uv run
# The application module is 'app.api'
CMD ["uv", "run", "uvicorn", "app.api:app", "--port", "8004", "--host", "0.0.0.0"]
