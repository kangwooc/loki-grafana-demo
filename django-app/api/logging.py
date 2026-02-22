import json
import logging

from opentelemetry import trace


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
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)
