import json
import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# ---------------------------------------------------------------------------
# OpenTelemetry initialisation – must happen before the app is created so
# that FastAPIInstrumentor can wrap the app correctly.
# ---------------------------------------------------------------------------
resource = Resource({"service.name": os.getenv("OTEL_SERVICE_NAME", "fastapi-app")})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
            insecure=True,
        )
    )
)
trace.set_tracer_provider(provider)


# ---------------------------------------------------------------------------
# JSON structured logging with trace_id / span_id injection
# ---------------------------------------------------------------------------
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
            "service": "fastapi-app",
            # trace_id and span_id allow Grafana to link logs → Tempo traces
            "trace_id": format(ctx.trace_id, "032x") if ctx.is_valid else "",
            "span_id": format(ctx.span_id, "016x") if ctx.is_valid else "",
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


_handler = logging.StreamHandler()
_handler.setFormatter(OtelJsonFormatter())
logging.root.setLevel(logging.INFO)
logging.root.handlers = [_handler]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="FastAPI Demo")

# Instrument after app creation; propagates the incoming W3C traceparent header
# so this service's spans are children of the Django span.
FastAPIInstrumentor().instrument_app(app)


@app.get("/api/hello")
def hello():
    logger.info("FastAPI received request")
    return {"fastapi": "ok"}
