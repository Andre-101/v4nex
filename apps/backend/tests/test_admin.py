from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.bridge_status import BridgeStatus
from app.domain.user_role import UserRole
from app.models.admin_audit_event import AdminAuditEvent
from app.models.bridge import Bridge
from app.models.user import User
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
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.bridge_limit = 5
        db.commit()
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


def promote_user_to_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        user.role = UserRole.ADMIN.value
        db.commit()


def admin_token(client: TestClient, email: str = "admin@example.com") -> str:
    token = register_and_login(client, email)
    promote_user_to_admin(email)
    return token


def test_reconcile_requires_auth(client: TestClient) -> None:
    response = client.post("/_v4nex/admin/reconcile-caddy")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_diagnostics_requires_auth(client: TestClient) -> None:
    response = client.get("/_v4nex/admin/diagnostics")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_no_public_admin_bootstrap_endpoint_exists(client: TestClient) -> None:
    response = client.post(
        "/_v4nex/admin/bootstrap-admin",
        json={"email": "admin@example.com", "password": "strong-password"},
    )

    assert response.status_code == 404


def test_reconcile_rejects_user_token(client: TestClient) -> None:
    token = register_and_login(client)

    response = client.post("/_v4nex/admin/reconcile-caddy", headers=auth_headers(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_diagnostics_rejects_user_token(client: TestClient) -> None:
    token = register_and_login(client)

    response = client.get("/_v4nex/admin/diagnostics", headers=auth_headers(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_reconcile_calls_caddy_with_only_active_routes(client: TestClient, monkeypatch) -> None:
    captured_routes = []
    token = admin_token(client)
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
    token = admin_token(client)
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
    assert body["rate_limit_enabled"] is True
    assert body["max_bridges_per_user"] == 5
    assert body["admin_endpoints_protected"] is True


def test_reconcile_creates_admin_audit_events(client: TestClient, monkeypatch) -> None:
    token = admin_token(client)
    monkeypatch.setattr(
        "app.services.caddy_reconciler.apply_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post("/_v4nex/admin/reconcile-caddy", headers=auth_headers(token))

    assert response.status_code == 200
    with SessionLocal() as db:
        actions = [event.action for event in db.query(AdminAuditEvent).order_by(AdminAuditEvent.created_at)]
    assert "ADMIN_RECONCILE_CADDY_STARTED" in actions
    assert "ADMIN_RECONCILE_CADDY_FINISHED" in actions


def test_diagnostics_creates_admin_audit_event_without_secrets(
    client: TestClient,
    monkeypatch,
) -> None:
    token = admin_token(client)
    monkeypatch.setattr("app.services.diagnostics.is_caddy_admin_reachable", lambda: True)

    response = client.get("/_v4nex/admin/diagnostics", headers=auth_headers(token))

    assert response.status_code == 200
    with SessionLocal() as db:
        event = db.query(AdminAuditEvent).filter_by(action="ADMIN_DIAGNOSTICS_VIEWED").one()
    serialized = str(event.event_metadata).lower()
    assert "secret" not in serialized
    assert "password" not in serialized
