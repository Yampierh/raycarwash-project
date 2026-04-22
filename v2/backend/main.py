from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.redis import close_redis_pool, get_redis_client
from app.db.session import AsyncSessionLocal, engine, get_db
from app.models.models import Base
from app.models import ledger as _ledger_models  # ensure ledger tables are registered
from app.routers.fare_router import router as fare_router
from app.routers.rides_router import router as rides_router
from app.ws.connection_manager import ConnectionManager
from app.ws.router import router as ws_router
from app.workers import assignment_worker, location_worker
from app.workers.ledger_seal_worker import run as ledger_seal_run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger   = logging.getLogger("raycarwash.v2")
settings = get_settings()


# ------------------------------------------------------------------ #
#  Lifespan                                                           #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("RayCarwash API v2 — starting")

    # ---- PostgreSQL ----
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Schema verified.")

    # ---- Redis ----
    redis_client: aioredis.Redis = get_redis_client()
    app.state.redis = redis_client
    logger.info("Redis client ready.")

    # ---- WebSocket manager (Redis Pub/Sub) ----
    app.state.ws_manager = ConnectionManager(redis_client)
    logger.info("WebSocket ConnectionManager (Redis Pub/Sub) ready.")

    # ---- Background workers ----
    worker_tasks = [
        asyncio.create_task(
            location_worker.run(redis_client, app.state.ws_manager),
            name="location_worker",
        ),
        asyncio.create_task(
            assignment_worker.run(redis_client),
            name="assignment_worker",
        ),
        asyncio.create_task(
            ledger_seal_run(),
            name="ledger_seal_worker",
        ),
    ]
    logger.info("Workers started: %s", [t.get_name() for t in worker_tasks])

    yield

    # ---- Shutdown ----
    for task in worker_tasks:
        task.cancel()
    await asyncio.gather(*worker_tasks, return_exceptions=True)

    await close_redis_pool()
    await engine.dispose()
    logger.info("Shutdown complete.")


# ------------------------------------------------------------------ #
#  Application factory                                                #
# ------------------------------------------------------------------ #

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        description=(
            "**RayCarwash API v2** — Uber-style architecture.\n\n"
            "Key changes from v1:\n"
            "- H3 hexagonal geospatial indexing (replaces Haversine O(N))\n"
            "- RAMEN push architecture (Fireball filter → Redis Pub/Sub)\n"
            "- Automatic detailer assignment engine (H3 k-ring → scoring → Redis lock)\n"
            "- Dynamic surge pricing via H3 supply counting\n"
            "- Append-only Payment Ledger (LedgerStore pattern)\n"
            "- Redis Streams as message queue (location_updates, assignment_queue)\n"
        ),
        docs_url="/docs"  if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        expose_headers=["X-Process-Time-Ms"],
    )

    app.include_router(fare_router)
    app.include_router(rides_router)
    app.include_router(ws_router)

    return app


app = create_application()


# ------------------------------------------------------------------ #
#  Middleware                                                          #
# ------------------------------------------------------------------ #

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = str(round((time.perf_counter() - start) * 1000, 2))
    return response


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    if request.url.path.startswith("/webhooks"):
        return await call_next(request)
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"code": "PAYLOAD_TOO_LARGE", "message": "Request body too large."},
                )
        except ValueError:
            pass
    return await call_next(request)


# ------------------------------------------------------------------ #
#  Health check                                                       #
# ------------------------------------------------------------------ #

@app.get("/health", tags=["Infrastructure"])
async def health_check() -> dict:
    db_ok    = False
    redis_ok = False

    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
            db_ok = True
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)

    try:
        await app.state.redis.ping()
        redis_ok = True
    except Exception as exc:
        logger.error("Redis health check failed: %s", exc)

    overall = "ok" if (db_ok and redis_ok) else "degraded"
    return {
        "status":       overall,
        "service":      settings.PROJECT_NAME,
        "version":      settings.API_VERSION,
        "db_reachable": db_ok,
        "redis_reachable": redis_ok,
    }
