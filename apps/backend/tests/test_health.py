from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_internal_health_returns_ok(client: TestClient) -> None:
    response = client.get("/_v4nex/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
