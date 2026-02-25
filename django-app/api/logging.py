import json
import logging

from opentelemetry import trace

logger = logging.getLogger(__name__)


class OtelJsonFormatter(logging.Formatter):
    """JSON log formatter that injects the current OpenTelemetry trace_id and span_id."""

    def format(self, record: logging.LogRecord) -> str:
        span = trace.get_current_span()
        ctx = span.get_span_context()

        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "django-app",
            # trace_id and span_id allow Grafana to link logs → Tempo traces
            "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else "",
            "span_id": format(ctx.span_id, "016x") if ctx.is_valid else "",
            # request context (populated by RequestLoggingMiddleware)
            "path": getattr(record, "path", ""),
            "method": getattr(record, "method", ""),
            "status_code": getattr(record, "status_code", ""),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


class RequestLoggingMiddleware:
    """Django middleware that emits one structured log line per HTTP request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        level = logging.ERROR if response.status_code >= 500 else logging.INFO
        logger.log(
            level,
            "HTTP request",
            extra={
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
            },
        )
        return response
