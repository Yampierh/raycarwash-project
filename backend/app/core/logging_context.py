from __future__ import annotations

import logging
from contextvars import ContextVar

# One ContextVar per asyncio Task — FastAPI creates one Task per HTTP request,
# so this is isolated per request. Default "-" distinguishes worker/startup
# logs from HTTP request logs in aggregators.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Injects current request_id into every log record on this handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class StaticFieldsFilter(logging.Filter):
    """Injects static service/env fields into every log record."""

    def __init__(self, service: str, env: str) -> None:
        super().__init__()
        self.service = service
        self.env = env

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self.service
        record.env = self.env
        return True
