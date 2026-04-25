---
name: backend-async-workers
description: Background worker patterns for FastAPI async backends. Use when writing or modifying workers (location, assignment, ledger, cleanup). Workers run as asyncio Tasks attached to app.state.
depends_on:
  - architecture_orchestrator
  - system_contracts
  - failure_modes
  - websocket_realtime
  - infra-observability
preconditions:
  - Workers registered in app.state during lifespan
  - Workers handle asyncio.CancelledError gracefully
outputs:
  - asyncio.Task registered in lifespan
  - Redis pub/sub for cross-instance communication
conflicts:
  - Worker never re-raises inside infinite loop
  - Worker never crashes without backoff
  - Worker never ignores CancelledError
execution_priority: 2
---

# Async Background Workers

**Priority: HIGH**  
**Applies to:** Background worker implementation, async task design, polling loops

## Worker Architecture

Workers are `asyncio.Task` objects attached to `app.state` during the FastAPI lifespan:

```python
# main.py lifespan
app.state.location_worker_task = asyncio.create_task(location_worker(app.state))
app.state.assignment_worker_task = asyncio.create_task(assignment_worker(app.state))
app.state.ledger_seal_worker_task = asyncio.create_task(ledger_seal_worker(app.state))
app.state.token_cleanup_worker_task = asyncio.create_task(token_cleanup_worker(app.state))
```

Each worker:
- Runs as an infinite loop with sleep intervals
- Reads from Redis queues or polls the DB
- Emits results via WebSocket or updates DB state
- Handles graceful shutdown via cancellation

## Standard Worker Template

```python
import asyncio
import logging
from typing import Any

logger = logging.getLogger("raycarwash.worker")


async def location_worker(app_state: Any) -> None:
    """
    Polls for detailer GPS updates and broadcasts via WebSocket.
    Runs every LOCATION_POLL_INTERVAL seconds.
    """
    from app.core.config import get_settings
    settings = get_settings()
    interval = settings.LOCATION_POLL_INTERVAL

    while True:
        try:
            await asyncio.sleep(interval)
            await _broadcast_locations(app_state)
        except asyncio.CancelledError:
            logger.info("Location worker cancelled — shutting down")
            break
        except Exception as exc:
            logger.exception("Location worker error: %s", exc)
            await asyncio.sleep(5)  # Back off on error


async def _broadcast_locations(app_state: Any) -> None:
    # Worker logic here
    pass
```

## Shutdown Pattern

**Always handle `asyncio.CancelledError`** for graceful shutdown:

```python
async def my_worker(app_state: Any) -> None:
    while True:
        try:
            await asyncio.sleep(INTERVAL)
            await do_work(app_state)
        except asyncio.CancelledError:
            logger.info("Worker shutting down gracefully")
            break
        except Exception:
            logger.exception("Worker error, will retry")
            await asyncio.sleep(5)
```

Registered in lifespan:

```python
# Must be cleaned up in lifespan shutdown
for task_attr in ("location_worker_task", "assignment_worker_task"):
    task = getattr(app.state, task_attr, None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
```

## Worker Types

### 1. Polling Worker (Location)

```python
async def location_worker(app_state: Any) -> None:
    while True:
        try:
            locations = await _fetch_active_locations(app_state.db)
            await app_state.ws_manager.broadcast_locations(locations)
        except Exception as exc:
            logger.error("Location poll failed: %s", exc)
        await asyncio.sleep(settings.LOCATION_POLL_INTERVAL)
```

### 2. Event-Driven Worker (Assignment)

```python
async def assignment_worker(app_state: Any) -> None:
    """Waits for assignment events, sends offers, collects responses."""
    while True:
        try:
            event_key = await _wait_for_assignment_event(app_state.redis)
            appointment_id, detailer_id = _parse_key(event_key)
            await _process_assignment(appointment_id, detailer_id, app_state)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Assignment worker error")
```

### 3. Ledger Seal Worker (Daily Batch)

```python
async def ledger_seal_worker(app_state: Any) -> None:
    """Runs daily: hashes all ledger entries for a sealed date."""
    while True:
        try:
            await _seal_yesterday_entries(app_state.db)
        except Exception as exc:
            logger.error("Ledger seal failed: %s", exc)
        # Run once per day at midnight
        await _sleep_until_midnight()
```

### 4. Cleanup Worker (TTL)

```python
async def token_cleanup_worker(app_state: Any) -> None:
    """Removes expired refresh tokens every hour."""
    while True:
        try:
            deleted = await _cleanup_expired_tokens(app_state.db)
            if deleted:
                logger.info("Cleaned up %d expired tokens", deleted)
        except Exception as exc:
            logger.error("Token cleanup failed: %s", exc)
        await asyncio.sleep(3600)
```

## Redis Pub/Sub Pattern

Workers communicate via Redis channels:

```python
# Publishing worker
await redis.publish("channel:name", json.dumps(payload))

# Subscribing worker
async def listen_worker(app_state: Any) -> None:
    pubsub = app_state.redis.pubsub()
    await pubsub.subscribe("channel:name")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await handle_message(message["data"])
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("channel:name")
```

## Error Handling Rules

| Pattern | Use |
|---------|-----|
| `try/except/finally` around sleep | Ensures backoff on errors |
| Max retry with backoff | `await asyncio.sleep(2**attempt)` for exponential backoff |
| Never re-raise inside infinite loop | Use logger + backoff, not crash |
| Log worker errors at ERROR level | Alerting depends on log level |

## Anti-Patterns

```python
# ❌ BAD: No cancellation handling
async def worker():
    while True:
        await do_work()
        await asyncio.sleep(10)
# FastAPI shutdown waits forever

# ✅ GOOD: Graceful shutdown
async def worker():
    while True:
        try:
            await asyncio.sleep(10)
            await do_work()
        except asyncio.CancelledError:
            break

# ❌ BAD: No error backoff — crash loop on DB error
while True:
    await do_work()
    await asyncio.sleep(10)

# ✅ GOOD: Back off on errors
while True:
    try:
        await asyncio.sleep(10)
        await do_work()
    except Exception:
        await asyncio.sleep(30)

# ❌ BAD: No logger
# Errors silently lost

# ✅ GOOD: Structured logging
logger = logging.getLogger("raycarwash.worker")
logger.error("Worker failed: %s", exc)
```

## Success Criteria

- All workers handle `asyncio.CancelledError`
- Workers register their tasks in `app.state`
- Tasks are cancelled in lifespan shutdown
- Errors are logged, not re-raised
- Shutdown backoff implemented
- Redis used for cross-worker communication