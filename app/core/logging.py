import json
import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON lines."""
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "path"):
            log_obj["path"] = record.path
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging():
    """Configure root logger to output structured JSON."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Remove default handlers to avoid duplicates
    root_logger.handlers = [handler]
    return logging.getLogger("ai_microservice")


logger = setup_logging()


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Injects a unique X-Request-ID header into every request and response.
    2. Logs structured JSON for every request with method, path, status, and duration.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        # Attach custom attributes for the JSON log formatter
        extra = {
            "request_id": request_id,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms
        }
        logger.info(
            f"{request.method} {request.url.path} HTTP/{request.scope.get('http_version', '1.1')} {response.status_code} - {duration_ms}ms",
            extra=extra
        )

        return response
