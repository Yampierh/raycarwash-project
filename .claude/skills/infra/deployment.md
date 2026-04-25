---
name: infra-deployment
description: Deployment and environment management for FastAPI backends. Use when deploying, configuring environment variables, or managing Docker containers.
depends_on:
  - architecture_orchestrator
preconditions:
  - Environment variables defined
outputs:
  - Docker image or deployment config
  - Startup sequence verified
conflicts:
  - Never commit secrets to .env file
  - Never run create_all() in production
execution_priority: 3
---

# Deployment

**Priority: HIGH**  
**Applies to:** Deployment, Docker, environment configuration, startup

## Environment Variables

### Required

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
SECRET_KEY=<32+ character secret>
DEBUG=false
```

### Stripe (Required in Production)

```env
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Optional

```env
# Database
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_IDENTIFY=10/minute
RATE_LIMIT_TOKEN=10/minute

# App
APP_BASE_URL=https://api.yourapp.com
ALLOWED_ORIGINS=https://yourapp.com

# Cancellation
CANCELLATION_FULL_REFUND_HOURS=24
CANCELLATION_PARTIAL_REFUND_HOURS=2
CANCELLATION_PARTIAL_REFUND_PERCENT=50

# Workers
LOCATION_POLL_INTERVAL=10
ASSIGNMENT_TIMEOUT_SECONDS=60
```

## Startup Sequence

```
1. PostgreSQL online
2. Redis online
3. Alembic migrations: alembic upgrade head
4. FastAPI starts
   a. create_all() — DEV ONLY, disabled in production
   b. Seed RBAC roles
   c. Seed service catalog
   d. Seed test data (dev only)
   e. Init Redis pool
   f. Start workers (asyncio.create_task)
5. Ready
```

## Production Checklist

- [ ] `DEBUG=false`
- [ ] `alembic upgrade head` run in CI/CD before deploy
- [ ] `create_all()` removed from startup in production
- [ ] Seed functions guarded with `if settings.DEBUG`
- [ ] `SECRET_KEY` from secrets manager (not env file)
- [ ] Stripe keys from environment (not .env)
- [ ] CORS origins set to production domain only

## Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run migrations first
RUN alembic upgrade head

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Anti-Patterns

```dockerfile
# ❌ BAD: create_all() in production
# This will try to create tables on every startup
# May conflict with Alembic migrations

# ✅ GOOD: create_all() guarded
if settings.DEBUG:
    await conn.run_sync(Base.metadata.create_all)

# ❌ BAD: Secrets in .env file
SECRET_KEY=mysecretkey123  # committed to git

# ✅ GOOD: Secrets from environment or secrets manager
SECRET_KEY=${SECRET_KEY}
```

## Success Criteria

- `DEBUG=false` in production
- Migrations run via CI/CD, not at startup
- Seed data only runs in DEBUG mode
- Secrets managed via environment, not .env