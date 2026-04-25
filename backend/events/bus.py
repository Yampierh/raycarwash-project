"""
Simple in-process event bus.

Usage:
    from events.bus import bus

    # Subscribe
    @bus.on("appointment.status_changed")
    async def handle(payload: dict) -> None:
        ...

    # Publish
    await bus.emit("appointment.status_changed", {"appointment_id": str(appt.id), ...})

Design decisions:
- In-process only (no Kafka, no Redis pubsub for internal events).
- All handlers are async coroutines.
- Errors in handlers are logged but do not abort the caller.
- Ordered: handlers fire in registration order.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

_Handler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[_Handler]] = defaultdict(list)

    def on(self, event: str) -> Callable[[_Handler], _Handler]:
        """Decorator to register an async handler for an event name."""
        def decorator(fn: _Handler) -> _Handler:
            self._handlers[event].append(fn)
            return fn
        return decorator

    async def emit(self, event: str, payload: dict[str, Any]) -> None:
        """Fire all handlers registered for *event*. Errors are logged, not re-raised."""
        handlers = self._handlers.get(event, [])
        for handler in handlers:
            try:
                await handler(payload)
            except Exception:
                logger.exception("Event handler %s failed for event %r", handler.__name__, event)

    async def emit_all(self, events: list[tuple[str, dict[str, Any]]]) -> None:
        """Fire multiple events concurrently."""
        await asyncio.gather(*(self.emit(ev, payload) for ev, payload in events))


# Singleton — import and use directly: `from events.bus import bus`
bus = EventBus()
