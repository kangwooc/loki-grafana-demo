import logging

import requests
from django.conf import settings
from django.http import HttpRequest, JsonResponse

logger = logging.getLogger(__name__)


def hello(request: HttpRequest) -> JsonResponse:
    logger.info("Django received request")

    try:
        # requests library is auto-instrumented by RequestsInstrumentor,
        # so it automatically injects the W3C traceparent header here.
        resp = requests.get(f"{settings.FASTAPI_URL}/api/hello", timeout=5)
        resp.raise_for_status()
        fastapi_data = resp.json()
    except Exception as exc:
        logger.error("Failed to call FastAPI: %s", exc)
        fastapi_data = {"error": str(exc)}

    logger.info("Django request handled successfully")
    return JsonResponse({"django": "ok", "fastapi": fastapi_data})
