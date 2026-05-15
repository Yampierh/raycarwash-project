# Minimal image used by docker-compose for the rq-worker / rq-scheduler
# containers. The API itself still runs on the host with `uvicorn main:app`
# during development.

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install build deps for compiled wheels (cryptography, asyncpg) then drop them.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Source is mounted at runtime via docker-compose volumes, so we don't COPY it
# here — that keeps the image small and avoids rebuilds on every edit.
