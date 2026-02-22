import os

from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "api"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource({"service.name": os.getenv("OTEL_SERVICE_NAME", "django-app")})
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

        # DjangoInstrumentor creates spans for each HTTP request
        DjangoInstrumentor().instrument()
        # RequestsInstrumentor injects W3C traceparent header into outgoing HTTP calls
        RequestsInstrumentor().instrument()
