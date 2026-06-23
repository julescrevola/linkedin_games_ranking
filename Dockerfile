# Build the application in the `/linkedin_games_ranking` directory
FROM ghcr.io/astral-sh/uv:trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Omit development dependencies
ENV UV_NO_DEV=1

# Configure the Python directory so it is consistent
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

# Install Python before the project for caching
RUN uv python install 3.11

# Set working directory
WORKDIR /linkedin_games_ranking

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Copy app files to the container
COPY . /linkedin_games_ranking
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Build frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Use a final image without uv
FROM debian:trixie-slim

# Copy the Python version
COPY --from=builder /python /python

# Copy the application from the builder
COPY --from=builder --chown=nonroot:nonroot /linkedin_games_ranking /linkedin_games_ranking

# Copy built frontend to static directory
COPY --from=frontend-builder /app/dist /linkedin_games_ranking/static

# Place executables in the environment at the front of the path
ENV PATH="/linkedin_games_ranking/.venv/bin:$PATH"

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Use `/linkedin_games_ranking` as the working directory
WORKDIR /linkedin_games_ranking

# Expose the port FastAPI runs on
EXPOSE 8000

# Start the FastAPI application with Uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
