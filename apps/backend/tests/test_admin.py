from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.domain.bridge_status import BridgeStatus
from app.models.bridge import Bridge
from app.services.caddy_activation import CaddyActivationResult


def register_and_login(client: TestClient, email: str = "admin@example.com") -> str:
    password = "strong-password"
    assert client.post(
        "/_v4nex/auth/register",
        json={"email": email, "password": password},
    ).status_code == 201
    response = client.post(
        "/_v4nex/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_bridge(client: TestClient, token: str, subdomain: str):
    return client.post(
        "/_v4nex/bridges",
        headers=auth_headers(token),
        json={
            "subdomain": subdomain,
            "target_ipv6": "2606:4700:4700::1111",
            "target_port": 80,
        },
    )


def set_bridge_status(bridge_id: str, status: BridgeStatus) -> None:
    with SessionLocal() as db:
        bridge = db.get(Bridge, bridge_id)
        assert bridge is not None
        bridge.status = status.value
        db.commit()


def test_reconcile_requires_auth(client: TestClient) -> None:
    response = client.post("/_v4nex/admin/reconcile-caddy")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_diagnostics_requires_auth(client: TestClient) -> None:
    response = client.get("/_v4nex/admin/diagnostics")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_reconcile_calls_caddy_with_only_active_routes(client: TestClient, monkeypatch) -> None:
    captured_routes = []
    token = register_and_login(client)
    active_id = create_bridge(client, token, "active-one").json()["id"]
    draft_id = create_bridge(client, token, "draft-one").json()["id"]
    set_bridge_status(active_id, BridgeStatus.ACTIVE)
    set_bridge_status(draft_id, BridgeStatus.DRAFT)

    def fake_apply(routes):
        captured_routes.extend(routes)
        return CaddyActivationResult(True, "CADDY_OK", "ok", False, None)

    monkeypatch.setattr("app.services.caddy_reconciler.apply_bridge_routes", fake_apply)

    response = client.post("/_v4nex/admin/reconcile-caddy", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["active_routes_count"] == 1
    assert [route.subdomain for route in captured_routes] == ["active-one"]


def test_diagnostics_does_not_expose_secrets(client: TestClient, monkeypatch) -> None:
    token = register_and_login(client)
    monkeypatch.setattr("app.services.diagnostics.is_caddy_admin_reachable", lambda: True)

    response = client.get("/_v4nex/admin/diagnostics", headers=auth_headers(token))

    assert response.status_code == 200
    body = response.json()
    serialized = str(body)
    assert body["caddy_admin_reachable"] is True
    assert "jwt_secret" not in serialized.lower()
    assert "password" not in serialized.lower()
    assert "devpassword" not in serialized
    assert body["database_url_driver"] == "sqlite"
