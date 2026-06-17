from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.domain.bridge_status import BridgeStatus
from app.domain.user_role import UserRole
from app.models.admin_audit_event import AdminAuditEvent
from app.models.bridge import Bridge
from app.models.user import User
from app.services.caddy_activation import CaddyActivationResult


PASSWORD = "strong-password"


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(client: TestClient, email: str) -> dict:
    response = client.post("/_v4nex/auth/register", json={"email": email, "password": PASSWORD})
    assert response.status_code == 201
    return response.json()


def login(client: TestClient, email: str) -> str:
    response = client.post("/_v4nex/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()["access_token"]


def set_user(email: str, *, role: UserRole | None = None, bridge_limit: int | None = None, is_active: bool | None = None) -> User:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        if role is not None:
            user.role = role.value
        if bridge_limit is not None:
            user.bridge_limit = bridge_limit
        if is_active is not None:
            user.is_active = is_active
        db.commit()
        db.refresh(user)
        return user


def create_bridge(client: TestClient, token: str, subdomain: str = "quotaone"):
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


def admin_token(client: TestClient) -> str:
    register(client, "admin@example.com")
    set_user("admin@example.com", role=UserRole.ADMIN, bridge_limit=5)
    return login(client, "admin@example.com")


def test_registered_users_default_to_user_active_with_bridge_limit_one(client: TestClient) -> None:
    body = register(client, "user@example.com")

    assert body["role"] == "USER"
    assert body["bridge_limit"] == 1
    assert body["is_active"] is True


def test_bridge_limit_zero_blocks_creation(client: TestClient) -> None:
    register(client, "user@example.com")
    set_user("user@example.com", bridge_limit=0)
    token = login(client, "user@example.com")

    response = create_bridge(client, token)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BRIDGE_LIMIT_REACHED"


def test_bridge_limit_one_allows_one_and_blocks_second(client: TestClient) -> None:
    register(client, "user@example.com")
    set_user("user@example.com", bridge_limit=1)
    token = login(client, "user@example.com")

    assert create_bridge(client, token, "firstone").status_code == 201
    response = create_bridge(client, token, "secondone")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BRIDGE_LIMIT_REACHED"


def test_delete_bridge_frees_quota(client: TestClient) -> None:
    register(client, "user@example.com")
    set_user("user@example.com", bridge_limit=1)
    token = login(client, "user@example.com")
    bridge_id = create_bridge(client, token, "firstone").json()["id"]

    assert client.delete(f"/_v4nex/bridges/{bridge_id}", headers=auth_headers(token)).status_code == 204
    response = create_bridge(client, token, "secondone")

    assert response.status_code == 201


def test_user_token_cannot_access_admin(client: TestClient) -> None:
    register(client, "user@example.com")
    token = login(client, "user@example.com")

    response = client.get("/_v4nex/admin/users", headers=auth_headers(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_list_users_and_change_bridge_limit(client: TestClient) -> None:
    token = admin_token(client)
    user = set_user("admin@example.com", bridge_limit=1)

    list_response = client.get("/_v4nex/admin/users", headers=auth_headers(token))
    patch_response = client.patch(
        f"/_v4nex/admin/users/{user.id}",
        headers=auth_headers(token),
        json={"bridge_limit": 3},
    )

    assert list_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["bridge_limit"] == 3


def test_admin_suspends_and_reactivates_user(client: TestClient) -> None:
    admin = admin_token(client)
    register(client, "user@example.com")
    user = set_user("user@example.com")
    user_token = login(client, "user@example.com")

    suspend = client.patch(
        f"/_v4nex/admin/users/{user.id}",
        headers=auth_headers(admin),
        json={"is_active": False},
    )
    private_response = client.get("/_v4nex/bridges", headers=auth_headers(user_token))
    login_response = client.post("/_v4nex/auth/login", json={"email": "user@example.com", "password": PASSWORD})
    reactivate = client.patch(
        f"/_v4nex/admin/users/{user.id}",
        headers=auth_headers(admin),
        json={"is_active": True},
    )

    assert suspend.status_code == 200
    assert private_response.status_code == 403
    assert private_response.json()["error"]["code"] == "USER_INACTIVE"
    assert login_response.status_code == 403
    assert login_response.json()["error"]["code"] == "USER_INACTIVE"
    assert reactivate.status_code == 200
    assert reactivate.json()["is_active"] is True


def test_admin_cannot_self_suspend_or_self_delete(client: TestClient) -> None:
    token = admin_token(client)
    admin_user = set_user("admin@example.com")

    suspend = client.patch(
        f"/_v4nex/admin/users/{admin_user.id}",
        headers=auth_headers(token),
        json={"is_active": False},
    )
    delete = client.delete(f"/_v4nex/admin/users/{admin_user.id}", headers=auth_headers(token))

    assert suspend.status_code == 409
    assert suspend.json()["error"]["code"] == "SELF_ACTION_NOT_ALLOWED"
    assert delete.status_code == 409
    assert delete.json()["error"]["code"] == "SELF_ACTION_NOT_ALLOWED"


def test_delete_user_blocked_when_active_bridge_exists(client: TestClient) -> None:
    admin = admin_token(client)
    register(client, "user@example.com")
    set_user("user@example.com", bridge_limit=2)
    user = set_user("user@example.com")
    user_token = login(client, "user@example.com")
    bridge_id = create_bridge(client, user_token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)

    response = client.delete(f"/_v4nex/admin/users/{user.id}", headers=auth_headers(admin))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USER_HAS_ACTIVE_BRIDGES"


def test_delete_user_without_active_bridges_cascades_non_active_bridges(client: TestClient) -> None:
    admin = admin_token(client)
    register(client, "user@example.com")
    set_user("user@example.com", bridge_limit=2)
    user = set_user("user@example.com")
    user_token = login(client, "user@example.com")
    bridge_id = create_bridge(client, user_token).json()["id"]

    response = client.delete(f"/_v4nex/admin/users/{user.id}", headers=auth_headers(admin))

    assert response.status_code == 204
    with SessionLocal() as db:
        assert db.get(User, user.id) is None
        assert db.get(Bridge, bridge_id) is None


def test_reserved_subdomains_are_blocked(client: TestClient) -> None:
    register(client, "user@example.com")
    set_user("user@example.com", bridge_limit=2)
    token = login(client, "user@example.com")

    response = create_bridge(client, token, "support")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RESERVED_SUBDOMAIN"


def test_audit_events_created_for_register_bridge_and_limit_change(client: TestClient) -> None:
    admin = admin_token(client)
    register(client, "user@example.com")
    user = set_user("user@example.com", bridge_limit=2)
    token = login(client, "user@example.com")
    assert create_bridge(client, token, "auditone").status_code == 201
    assert (
        client.patch(
            f"/_v4nex/admin/users/{user.id}",
            headers=auth_headers(admin),
            json={"bridge_limit": 3},
        ).status_code
        == 200
    )

    with SessionLocal() as db:
        actions = [event.action for event in db.query(AdminAuditEvent).order_by(AdminAuditEvent.created_at)]

    assert "USER_REGISTERED" in actions
    assert "BRIDGE_CREATED" in actions
    assert "USER_LIMIT_CHANGED" in actions


def test_admin_can_disable_other_users_active_bridge(client: TestClient, monkeypatch) -> None:
    admin = admin_token(client)
    register(client, "user@example.com")
    set_user("user@example.com", bridge_limit=2)
    user_token = login(client, "user@example.com")
    bridge_id = create_bridge(client, user_token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)
    monkeypatch.setattr(
        "app.api.routes.admin.disable_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(f"/_v4nex/admin/bridges/{bridge_id}/disable", headers=auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["status"] == "DISABLED"
    with SessionLocal() as db:
        actions = [event.action for event in db.query(AdminAuditEvent).order_by(AdminAuditEvent.created_at)]
    assert "ADMIN_BRIDGE_DISABLED" in actions


def test_admin_can_delete_allowed_bridge_of_other_user(client: TestClient) -> None:
    admin = admin_token(client)
    register(client, "user@example.com")
    set_user("user@example.com", bridge_limit=2)
    user_token = login(client, "user@example.com")
    bridge_id = create_bridge(client, user_token).json()["id"]

    response = client.delete(f"/_v4nex/admin/bridges/{bridge_id}", headers=auth_headers(admin))

    assert response.status_code == 204
    with SessionLocal() as db:
        assert db.get(Bridge, bridge_id) is None
