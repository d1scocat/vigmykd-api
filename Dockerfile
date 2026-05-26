FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Have no clue why all of these are libs are necessary
# This is shamelessly stolen from one of my older projects
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip uv

COPY pyproject.toml ./

ENV UV_SYSTEM_PYTHON=1
RUN uv pip install --system ".[dev]"


FROM python:3.11-slim-bookworm as runtime

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser
USER appuser

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser keys/ ./keys/

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

# Default command will be overwritten by docker compose
CMD ["uvicorn", "src.entrypoint:app", "--host", "0.0.0.0", "--port", "8000"]