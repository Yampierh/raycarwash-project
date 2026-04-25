# main.py  —  Composition Root  —  RayCarwash Sprint 4

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.redis import close_redis_pool, init_redis_pool
from app.workers.location_worker import location_worker
from app.workers.assignment_worker import assignment_worker
from app.workers.ledger_seal_worker import ledger_seal_worker
from app.workers.token_cleanup_worker import token_cleanup_worker

# Register ledger models with SQLAlchemy Base so create_all includes their tables
import app.models.ledger  # noqa: F401
from app.db.seed import seed_addons, seed_services, seed_service_categories, seed_specialties
from app.db.seed_rbac import seed_rbac
from app.db.detailer_seed import seed_detailers
from app.db.session import AsyncSessionLocal, engine, get_db
from app.models.models import AuditAction, Base, Role, User, UserRoleAssociation
from app.repositories.audit_repository import AuditRepository
from app.repositories.user_repository import UserRepository
from sqlalchemy import select

# ── All routers ──────────────────────────────────────────────────────
from app.routers.addon_router       import router as addon_router        # Sprint 5
from app.routers.fare_router        import router as fare_router          # v2
from app.routers.rides_router       import router as rides_router         # v2
from app.routers.appointment_router import router as appointment_router
from app.routers.auth_router        import router as auth_router
from app.routers.detailer_router    import router as detailer_router
from app.routers.matching_router    import router as matching_router      # Sprint 5
from app.routers.payment_router     import router as payment_router
from app.routers.review_router      import router as review_router
from app.routers.service_router     import router as service_router
from app.routers.vehicle_router     import router as vehicle_router
from app.routers.verification_router import router as verification_router  # Stripe Identity
from app.routers.webhook_router     import router as webhook_router  # Sprint 4
from app.routers.wellknown_router   import router as wellknown_router  # WebAuthn domain verification
from app.ws.connection_manager      import ConnectionManager
from app.ws.router                  import router as ws_router

from app.schemas.schemas import ErrorDetail, HealthResponse, UserCreate, UserRead
from app.services.auth import AuthService
from app.core.logging_context import RequestIdFilter, StaticFieldsFilter, request_id_var
from pythonjsonlogger import jsonlogger

# ── Logging ──────────────────────────────────────────────────────────
# settings is initialised first so we can derive env from DEBUG flag.
settings = get_settings()

_log_handler = logging.StreamHandler()
_log_handler.setFormatter(jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(service)s %(env)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    rename_fields={"levelname": "level", "asctime": "timestamp"},
))
_log_handler.addFilter(RequestIdFilter())
_log_handler.addFilter(StaticFieldsFilter(
    service="raycarwash-backend",
    env="development" if settings.DEBUG else "production",
))
logging.basicConfig(level=logging.INFO, handlers=[_log_handler])

logger = logging.getLogger("raycarwash")


# ── Lifespan ─────────────────────────────────────────────────────── #

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    STARTUP (in order):
      1. create_all — idempotent table creation for dev/test.
         PRODUCTION: remove create_all and run `alembic upgrade head`
         in CI/CD BEFORE deploying new app code.
      2. seed_rbac — create system roles (admin, detailer, client).
      3. seed_services — upsert 3-tier service catalogue.

    SHUTDOWN:
      - engine.dispose() flushes in-flight queries and releases all
        connections back to PostgreSQL gracefully.
    """
    logger.info("🚗  RayCarwash API — Sprint 5 — Fort Wayne, IN — starting")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✅  Schema verified.")

    async with AsyncSessionLocal() as seed_session:
        await seed_rbac(seed_session)
        logger.info("✅  RBAC roles seeded.")

    async with AsyncSessionLocal() as seed_session:
        await seed_service_categories(seed_session)
        logger.info("✅  Service categories seeded.")

    async with AsyncSessionLocal() as seed_session:
        await seed_specialties(seed_session)
        logger.info("✅  Specialties seeded.")

    async with AsyncSessionLocal() as seed_session:
        await seed_services(seed_session)
        logger.info("✅  Service catalogue seeded.")

    async with AsyncSessionLocal() as seed_session:
        await seed_addons(seed_session)
        logger.info("✅  Addon catalogue seeded.")

    async with AsyncSessionLocal() as seed_session:
        await seed_detailers(seed_session)
        logger.info("✅  Test detailers seeded.")

    # Redis pool — real Redis if available, else fakeredis in dev
    app.state.redis = await init_redis_pool(settings.REDIS_URL)

    # WebSocket connection manager backed by Redis Pub/Sub
    app.state.ws_manager = ConnectionManager(app.state.redis)
    logger.info("✅  WebSocket ConnectionManager ready.")

    # Shared state for assignment engine
    app.state.assignment_events    = {}   # {"{appt_id}:{detailer_id}": asyncio.Event}
    app.state.assignment_responses = {}   # {"{appt_id}:{detailer_id}": "accepted"|"declined"}

    # Background workers
    app.state.location_worker_task      = asyncio.create_task(location_worker(app.state))
    app.state.assignment_worker_task    = asyncio.create_task(assignment_worker(app.state))
    app.state.ledger_seal_worker_task   = asyncio.create_task(ledger_seal_worker(app.state))
    app.state.token_cleanup_worker_task = asyncio.create_task(token_cleanup_worker(app.state))
    logger.info("✅  Location + Assignment + LedgerSeal + TokenCleanup workers started.")

    yield

    for task_attr in ("location_worker_task", "assignment_worker_task", "ledger_seal_worker_task", "token_cleanup_worker_task"):
        task = getattr(app.state, task_attr, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    await close_redis_pool(app.state.redis)
    logger.info("🛑  Redis pool closed.")
    await engine.dispose()
    logger.info("🛑  Engine disposed. Shutdown complete.")


# ── App factory ──────────────────────────────────────────────────── #

def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        description=(
            "**RayCarwash** — Mobile Car Detailing Marketplace API.  \n"
            "Fort Wayne, IN · Sprint 4.\n\n"
            "Pricing: `estimated_price = ceil(base_price × SIZE_MULTIPLIER)`  \n"
            "Multipliers: Small ×1.0 | Medium ×1.2 | Large ×1.5 | **XL ×2.0**\n\n"
            "**Sprint 4 additions:**\n"
            "- Detailer onboarding: `POST/PATCH /api/v1/detailers/profile`\n"
            "- Detailer discovery: `GET /api/v1/detailers` with geo-filter\n"
            "- Stripe webhook: `POST /webhooks/stripe`\n"
            "- Cancellation policy: tiered auto-refunds on cancellation\n"
            "- Timezone-aware scheduling: detailer IANA timezone stored + used\n"
            "- Rate limiting: brute-force protection on `/auth/token`\n"
        ),
        docs_url="/docs"  if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ---- Rate limiter ----
    # Must be set on app.state BEFORE adding the exception handler.
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ---- Correlation ID middleware ----
    # Generates a unique X-Request-ID per request (or echoes the client-supplied
    # one). Stored in request_id_var (ContextVar) so every log line emitted
    # within this request's asyncio Task automatically carries it via
    # RequestIdFilter. Returned in the response header for client-side tracing.
    _req_log = logging.getLogger("raycarwash.request")

    @application.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        try:
            _req_log.info(
                "HTTP request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client": getattr(request.client, "host", "-"),
                },
            )
            response = await call_next(request)
            _req_log.info("HTTP response", extra={"status_code": response.status_code})
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_var.reset(token)

    # ---- CORS ----
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Process-Time-Ms", "X-Request-ID"],
    )

    # ---- Router registration order matters for prefix specificity ----
    # Webhook router first — no body parsing interference from other middleware
    application.include_router(wellknown_router)      # /.well-known/* (WebAuthn domain verification)
    application.include_router(webhook_router)        # /webhooks/*
    application.include_router(auth_router)           # /auth/*
    application.include_router(service_router)        # /api/v1/services/*
    application.include_router(addon_router)          # /api/v1/addons/*          Sprint 5
    application.include_router(matching_router)       # /api/v1/matching          Sprint 5
    application.include_router(vehicle_router)        # /api/v1/vehicles/*
    application.include_router(appointment_router)    # /api/v1/appointments/*
    application.include_router(detailer_router)       # /api/v1/detailers/*
    application.include_router(verification_router)   # /api/v1/detailers/verification/*
    application.include_router(fare_router)           # /api/v1/fares/*         v2
    application.include_router(rides_router)          # /api/v1/rides/*         v2
    application.include_router(ws_router)             # /ws/appointments/{id}
    application.include_router(payment_router)        # /api/v1/payments/*
    application.include_router(review_router)         # /api/v1/reviews/*

    return application


app = create_application()


# ── Middleware ───────────────────────────────────────────────────── #

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start    = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = str(
        round((time.perf_counter() - start) * 1000, 2)
    )
    return response


@app.middleware("http")
async def limit_request_body_size(request: Request, call_next):
    """
    Reject requests whose Content-Length exceeds MAX_REQUEST_BODY_BYTES
    BEFORE reading the body. This prevents memory exhaustion via payload
    flooding (DoS). The webhook endpoint is explicitly excluded because
    Stripe may send larger payloads.

    Note: Content-Length is advisory — clients can lie. The real guard is
    reading in chunks (done at the ASGI level by uvicorn), but this check
    catches well-behaved clients early and returns a clear 413 error.
    """
    if request.url.path.startswith("/webhooks"):
        # Stripe webhooks are exempt — they have their own signature guard.
        return await call_next(request)

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content=ErrorDetail(
                        code="PAYLOAD_TOO_LARGE",
                        message=(
                            f"Request body exceeds the maximum allowed size "
                            f"({settings.MAX_REQUEST_BODY_BYTES // (1024*1024)} MB)."
                        ),
                    ).model_dump(),
                )
        except ValueError:
            pass  # Malformed Content-Length — let uvicorn handle it

    return await call_next(request)


# ── Global exception handlers ────────────────────────────────────── #

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Convert PostgreSQL unique-constraint violations into clean 409 responses.
    Never leak raw SQL to the client (OWASP A09).
    """
    logger.warning("IntegrityError on %s: %s", request.url.path, exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorDetail(
            code="CONFLICT",
            message="A resource with these unique attributes already exists.",
        ).model_dump(),
    )


# ── Infrastructure ───────────────────────────────────────────────── #

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Infrastructure"],
    summary="Liveness probe for load balancers and Kubernetes readiness checks.",
)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """
    Returns status='ok' if both the API and the DB ping succeed.
    Returns status='degraded' (HTTP 200 still) if the DB ping fails —
    allows the orchestrator to decide whether to drain this pod.
    """
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("Health DB ping failed: %s", exc)

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        service=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        db_reachable=db_ok,
    )


# ── User registration ────────────────────────────────────────────── #
# Kept inline for MVP. Extract to app/routers/user_router.py in Sprint 5
# once admin-only endpoints (list users, deactivate) are needed.

@app.post(
    "/api/v1/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Users"],
    summary="Register a new CLIENT or DETAILER account.",
    responses={
        409: {"model": ErrorDetail, "description": "Email already registered."},
    },
)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """
    Open registration. ADMIN role is blocked at the schema layer.
    Password is bcrypt-hashed by AuthService — never stored in plaintext.

    After registering with role=detailer, call POST /api/v1/detailers/profile
    to complete onboarding and become discoverable.
    """
    user_repo = UserRepository(db)

    if await user_repo.email_exists(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorDetail(
                code="EMAIL_TAKEN",
                message=f"An account with '{payload.email}' already exists.",
            ).model_dump(),
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        password_hash=AuthService.hash_password(payload.password),
    )

    created = await user_repo.create(user)

    role_names = payload.role_names or ["client"]
    for role_name in role_names:
        if role_name == "admin":
            continue
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one_or_none()
        if role:
            user_role = UserRoleAssociation(
                user_id=created.id,
                role_id=role.id,
            )
            db.add(user_role)

    await db.commit()
    await db.refresh(created, ["user_roles"])

    await AuditRepository(db).log(
        action=AuditAction.USER_REGISTERED,
        entity_type="user",
        entity_id=str(created.id),
        actor_id=created.id,
        metadata={"roles": role_names},
    )

    logger.info("User registered | id=%s email=%s roles=%s",
                created.id, created.email, role_names)

    return UserRead.model_validate(created)
