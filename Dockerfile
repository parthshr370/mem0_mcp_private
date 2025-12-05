FROM python:3.12-slim-bookworm AS base

FROM base AS builder
WORKDIR /app

# Copy source code
COPY . .

# Copy uv binary for fast installs
COPY --from=ghcr.io/astral-sh/uv:0.5.16 /uv /bin/uv

# Install dependencies inside a local venv
RUN export UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy && \
    if [ -f "uv.lock" ]; then \
      uv sync --frozen --no-dev; \
    else \
      uv sync --no-dev; \
    fi

FROM base
WORKDIR /app

# Bring in the pre-built virtualenv and sources
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PORT=8081

# Use Smithery CLI to inject runtime config/middleware
CMD ["smithery", "start"]
