FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Have no clue why all of these are libs are necessary
# This is shamelessly stolen from one of my older projects
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    protobuf-compiler \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip uv

COPY pyproject.toml ./
COPY proto/ ./proto/
COPY src/ ./src/

RUN protoc \
    -I=./proto \
    --python_out=./generated \
    proto/v1/packet.proto

COPY generated/ ./src/vigmykd/generated/

ENV UV_SYSTEM_PYTHON=1
RUN uv pip install --system ".[dev]"

COPY LICENSE ./LICENSE


FROM python:3.11-slim-bookworm as runtime

WORKDIR /app

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=appuser:appuser resources/ /app/resources/
COPY --chown=appuser:appuser . /app/
COPY --chown=appuser:appuser keys/ ./keys/

# writing logs
RUN chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

# Default command will be overwritten by docker compose
CMD ["uvicorn", "vigmykd.entrypoint:app", "--host", "0.0.0.0", "--port", "8000"]