import pytest
from fastapi.testclient import TestClient

from app.db import session


def sample(body: str, line_start: str) -> float:
    """Valeur d'une série dans la sortie texte de /metrics."""
    for line in body.splitlines():
        if line.startswith(line_start):
            return float(line.rsplit(" ", 1)[1])
    return 0.0


def test_metrics_count_requests_by_route_template(
    client: TestClient, auth: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(session, "check_database", lambda: True)
    health = 'kidai_http_requests_total{method="GET",route="/health",status="200"}'
    child = 'kidai_http_requests_total{method="PATCH",route="/api/children/{child_id}"'
    before = client.get("/metrics").text

    client.get("/health")
    client.get("/health")
    client.patch("/api/children/123", json={"name": "Lina"}, headers=auth)

    body = client.get("/metrics").text
    assert sample(body, health) == sample(before, health) + 2
    # Gabarit de la route, pas l'identifiant
    assert child in body
    assert "/api/children/123" not in body


def test_metrics_ignore_metrics_and_group_unknown_paths(client: TestClient) -> None:
    client.get("/nexiste/pas/42")

    body = client.get("/metrics").text
    assert 'route="unmatched",status="404"' in body
    assert "/nexiste" not in body
    assert 'route="/metrics"' not in body


def test_latency_histogram_has_buckets_up_to_30_seconds(client: TestClient) -> None:
    client.get("/nexiste")

    body = client.get("/metrics").text
    bucket = 'kidai_http_request_duration_seconds_bucket{le="%s",method="GET",route="unmatched"}'
    assert bucket % "5.0" in body
    assert bucket % "30.0" in body
