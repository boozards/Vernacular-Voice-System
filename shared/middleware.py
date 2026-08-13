import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from prometheus_client import Counter, Histogram
from shared.logging import correlation_id_var

# Prometheus Metrics Definitions
HTTP_REQUESTS_TOTAL = Counter(
    "voicekart_http_requests_total",
    "Total HTTP Requests",
    ["service", "method", "endpoint", "status_code"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "voicekart_http_request_duration_seconds",
    "HTTP Request Latency in seconds",
    ["service", "method", "endpoint"]
)

E2E_RESPONSE_LATENCY = Histogram(
    "voicekart_e2e_response_latency_seconds",
    "End-to-end response latency in seconds",
    ["language"]
)


class CorrelationAndMetricsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        token = correlation_id_var.set(correlation_id)

        start_time = time.time()
        endpoint = request.url.path

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            response.headers["X-Correlation-ID"] = correlation_id

            HTTP_REQUESTS_TOTAL.labels(
                service=self.service_name,
                method=request.method,
                endpoint=endpoint,
                status_code=response.status_code
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                service=self.service_name,
                method=request.method,
                endpoint=endpoint
            ).observe(duration)

            return response

        finally:
            correlation_id_var.reset(token)
