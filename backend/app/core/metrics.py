"""Métriques Prometheus de l'API sur /metrics (lues par Prometheus, affichées par Grafana).

Le libellé `route` est le gabarit de la route (« /api/children/{child_id} ») et non le chemin
réel : sinon chaque identifiant créerait une nouvelle série.
"""

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.routing import Match

METRICS_PATH = "/metrics"
UNMATCHED = "unmatched"

REQUESTS = Counter(
    "kidai_http_requests_total", "Requêtes HTTP traitées", ["method", "route", "status"]
)
LATENCY = Histogram(
    "kidai_http_request_duration_seconds",
    "Durée de traitement des requêtes HTTP",
    ["method", "route"],
    # Jusqu'à 30 s : une réponse du LLM local peut prendre plusieurs secondes (cible P90 < 5 s).
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 30),
)


def route_of(request: Request) -> str:
    for route in request.app.router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", UNMATCHED)
    return UNMATCHED


async def track_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    route = route_of(request)
    if route == METRICS_PATH:
        return await call_next(request)
    start = time.perf_counter()
    status = 500  # si l'application lève une exception
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        LATENCY.labels(request.method, route).observe(time.perf_counter() - start)
        REQUESTS.labels(request.method, route, str(status)).inc()


def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
