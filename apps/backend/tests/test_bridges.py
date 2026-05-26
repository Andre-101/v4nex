from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.domain.bridge_status import BridgeStatus
from app.models.bridge import Bridge
from app.core.config import settings
from app.services.caddy_activation import CaddyActivationResult
from app.services.tcp_validator import TcpValidationResult


def register_and_login(client: TestClient, email: str) -> str:
    password = "strong-password"
    assert (
        client.post(
            "/_v4nex/auth/register",
            json={"email": email, "password": password},
        ).status_code
        == 201
    )
    response = client.post(
        "/_v4nex/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_bridge(client: TestClient, token: str, subdomain: str = "demo"):
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


def test_create_bridge_without_token_fails_401(client: TestClient) -> None:
    response = client.post(
        "/_v4nex/bridges",
        json={
            "subdomain": "demo",
            "target_ipv6": "2606:4700:4700::1111",
            "target_port": 80,
        },
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_create_bridge_with_valid_token_returns_draft(client: TestClient) -> None:
    token = register_and_login(client, "user@example.com")

    response = create_bridge(client, token)

    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"
    assert response.json()["subdomain"] == "demo"


def test_create_bridge_builds_public_url(client: TestClient) -> None:
    token = register_and_login(client, "user@example.com")

    response = create_bridge(client, token)

    assert response.status_code == 201
    assert response.json()["public_url"] == "https://demo.v4nex.com"


def test_create_bridge_with_reserved_subdomain_fails(client: TestClient) -> None:
    token = register_and_login(client, "user@example.com")

    response = create_bridge(client, token, subdomain="admin")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "RESERVED_SUBDOMAIN"


def test_create_bridge_with_invalid_ipv6_fails(client: TestClient) -> None:
    token = register_and_login(client, "user@example.com")

    response = client.post(
        "/_v4nex/bridges",
        headers=auth_headers(token),
        json={"subdomain": "demo", "target_ipv6": "not-ipv6", "target_port": 80},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_IPV6"


def test_create_bridge_with_port_443_fails(client: TestClient) -> None:
    token = register_and_login(client, "user@example.com")

    response = client.post(
        "/_v4nex/bridges",
        headers=auth_headers(token),
        json={
            "subdomain": "demo",
            "target_ipv6": "2606:4700:4700::1111",
            "target_port": 443,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_PORT"


def test_create_bridge_with_duplicate_subdomain_fails(client: TestClient) -> None:
    token = register_and_login(client, "user@example.com")
    assert create_bridge(client, token).status_code == 201

    response = create_bridge(client, token)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBDOMAIN_ALREADY_EXISTS"


def test_bridge_quota_allows_until_limit(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_bridges_per_user", 2)
    token = register_and_login(client, "user@example.com")

    assert create_bridge(client, token, subdomain="first").status_code == 201
    assert create_bridge(client, token, subdomain="second").status_code == 201


def test_bridge_quota_blocks_additional_bridge(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_bridges_per_user", 2)
    token = register_and_login(client, "user@example.com")
    assert create_bridge(client, token, subdomain="first").status_code == 201
    assert create_bridge(client, token, subdomain="second").status_code == 201

    response = create_bridge(client, token, subdomain="third")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BRIDGE_QUOTA_EXCEEDED"


def test_bridge_quota_is_per_user(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "max_bridges_per_user", 1)
    first_token = register_and_login(client, "first@example.com")
    second_token = register_and_login(client, "second@example.com")
    assert create_bridge(client, first_token, subdomain="first").status_code == 201

    response = create_bridge(client, second_token, subdomain="second")

    assert response.status_code == 201


def test_list_bridges_returns_only_authenticated_users_bridges(client: TestClient) -> None:
    first_token = register_and_login(client, "first@example.com")
    second_token = register_and_login(client, "second@example.com")
    assert create_bridge(client, first_token, subdomain="first").status_code == 201
    assert create_bridge(client, second_token, subdomain="second").status_code == 201

    response = client.get("/_v4nex/bridges", headers=auth_headers(first_token))

    assert response.status_code == 200
    assert [bridge["subdomain"] for bridge in response.json()] == ["first"]


def test_bridge_detail_for_other_user_is_not_accessible(client: TestClient) -> None:
    first_token = register_and_login(client, "first@example.com")
    second_token = register_and_login(client, "second@example.com")
    bridge_id = create_bridge(client, first_token, subdomain="first").json()["id"]

    response = client.get(
        f"/_v4nex/bridges/{bridge_id}",
        headers=auth_headers(second_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BRIDGE_NOT_FOUND"


def test_bridge_events_returns_bridge_created(client: TestClient) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]

    response = client.get(
        f"/_v4nex/bridges/{bridge_id}/events",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["event_type"] == "BRIDGE_CREATED"


def test_validate_without_token_fails_401(client: TestClient) -> None:
    response = client.post("/_v4nex/bridges/some-id/validate")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_validate_own_draft_bridge_tcp_ok_changes_to_ready(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.validate_tcp_connectivity",
        lambda host, port: TcpValidationResult(True, "TCP_OK", "ok", 12),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/validate",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "READY"


def test_validate_own_draft_bridge_tcp_fail_changes_to_error(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.validate_tcp_connectivity",
        lambda host, port: TcpValidationResult(False, "TCP_TIMEOUT", "timeout", 3000),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/validate",
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TCP_VALIDATION_FAILED"

    detail = client.get(f"/_v4nex/bridges/{bridge_id}", headers=auth_headers(token))
    assert detail.json()["status"] == "ERROR"


def test_validate_other_users_bridge_returns_not_found(
    client: TestClient,
    monkeypatch,
) -> None:
    first_token = register_and_login(client, "first@example.com")
    second_token = register_and_login(client, "second@example.com")
    bridge_id = create_bridge(client, first_token, subdomain="first").json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.validate_tcp_connectivity",
        lambda host, port: TcpValidationResult(True, "TCP_OK", "ok", 12),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/validate",
        headers=auth_headers(second_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BRIDGE_NOT_FOUND"


def test_validate_active_bridge_returns_invalid_state_transition(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.validate_tcp_connectivity",
        lambda host, port: TcpValidationResult(True, "TCP_OK", "ok", 12),
    )
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/validate",
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_validate_creates_started_and_passed_events(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.validate_tcp_connectivity",
        lambda host, port: TcpValidationResult(True, "TCP_OK", "ok", 12),
    )

    assert (
        client.post(f"/_v4nex/bridges/{bridge_id}/validate", headers=auth_headers(token)).status_code
        == 200
    )
    events = client.get(f"/_v4nex/bridges/{bridge_id}/events", headers=auth_headers(token))
    event_types = [event["event_type"] for event in events.json()]

    assert "TCP_VALIDATION_STARTED" in event_types
    assert "TCP_VALIDATION_PASSED" in event_types


def test_validate_fail_creates_failed_event(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.validate_tcp_connectivity",
        lambda host, port: TcpValidationResult(False, "TCP_TIMEOUT", "timeout", 3000),
    )

    assert (
        client.post(f"/_v4nex/bridges/{bridge_id}/validate", headers=auth_headers(token)).status_code
        == 422
    )
    events = client.get(f"/_v4nex/bridges/{bridge_id}/events", headers=auth_headers(token))
    event_types = [event["event_type"] for event in events.json()]

    assert "TCP_VALIDATION_STARTED" in event_types
    assert "TCP_VALIDATION_FAILED" in event_types


def test_validate_ok_updates_last_tcp_validation_result(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.validate_tcp_connectivity",
        lambda host, port: TcpValidationResult(True, "TCP_OK", "ok", 12),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/validate",
        headers=auth_headers(token),
    )

    assert response.json()["last_tcp_validation_result"] == "OK"


def test_validate_fail_updates_last_tcp_validation_result(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.validate_tcp_connectivity",
        lambda host, port: TcpValidationResult(False, "TCP_TIMEOUT", "timeout", 3000),
    )

    client.post(f"/_v4nex/bridges/{bridge_id}/validate", headers=auth_headers(token))
    detail = client.get(f"/_v4nex/bridges/{bridge_id}", headers=auth_headers(token))

    assert detail.json()["last_tcp_validation_result"] == "FAILED"


def test_activate_without_token_fails_401(client: TestClient) -> None:
    response = client.post("/_v4nex/bridges/some-id/activate")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_activate_other_users_bridge_returns_not_found(
    client: TestClient,
    monkeypatch,
) -> None:
    first_token = register_and_login(client, "first@example.com")
    second_token = register_and_login(client, "second@example.com")
    bridge_id = create_bridge(client, first_token, subdomain="first").json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.READY)
    monkeypatch.setattr(
        "app.api.routes.bridges.activate_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/activate",
        headers=auth_headers(second_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BRIDGE_NOT_FOUND"


def test_activate_draft_bridge_returns_invalid_state_transition(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.activate_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/activate",
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_activate_ready_bridge_with_caddy_ok_becomes_active(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.READY)
    monkeypatch.setattr(
        "app.api.routes.bridges.activate_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/activate",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_activate_ready_bridge_with_caddy_fail_becomes_error(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.READY)
    monkeypatch.setattr(
        "app.api.routes.bridges.activate_bridge_routes",
        lambda routes: CaddyActivationResult(
            False,
            "CADDY_CONFIG_REJECTED",
            "rejected",
            True,
            True,
        ),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/activate",
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CADDY_ACTIVATION_FAILED"

    detail = client.get(f"/_v4nex/bridges/{bridge_id}", headers=auth_headers(token))
    assert detail.json()["status"] == "ERROR"


def test_activate_ok_updates_activated_at(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.READY)
    monkeypatch.setattr(
        "app.api.routes.bridges.activate_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/activate",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["activated_at"] is not None


def test_activate_ok_creates_started_and_passed_events(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.READY)
    monkeypatch.setattr(
        "app.api.routes.bridges.activate_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    assert (
        client.post(f"/_v4nex/bridges/{bridge_id}/activate", headers=auth_headers(token)).status_code
        == 200
    )
    events = client.get(f"/_v4nex/bridges/{bridge_id}/events", headers=auth_headers(token))
    event_types = [event["event_type"] for event in events.json()]

    assert "CADDY_ACTIVATION_STARTED" in event_types
    assert "CADDY_ACTIVATION_PASSED" in event_types


def test_activate_fail_creates_started_and_failed_events(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.READY)
    monkeypatch.setattr(
        "app.api.routes.bridges.activate_bridge_routes",
        lambda routes: CaddyActivationResult(False, "CADDY_CONFIG_REJECTED", "rejected", True, True),
    )

    assert (
        client.post(f"/_v4nex/bridges/{bridge_id}/activate", headers=auth_headers(token)).status_code
        == 409
    )
    events = client.get(f"/_v4nex/bridges/{bridge_id}/events", headers=auth_headers(token))
    event_types = [event["event_type"] for event in events.json()]

    assert "CADDY_ACTIVATION_STARTED" in event_types
    assert "CADDY_ACTIVATION_FAILED" in event_types


def test_activate_fail_returns_rollback_details(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.READY)
    monkeypatch.setattr(
        "app.api.routes.bridges.activate_bridge_routes",
        lambda routes: CaddyActivationResult(False, "CADDY_CONFIG_REJECTED", "rejected", True, False),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/activate",
        headers=auth_headers(token),
    )

    details = response.json()["error"]["details"]
    assert details["error_code"] == "CADDY_CONFIG_REJECTED"
    assert details["rollback_attempted"] is True
    assert details["rollback_ok"] is False


def test_disable_without_token_fails_401(client: TestClient) -> None:
    response = client.post("/_v4nex/bridges/some-id/disable")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_disable_other_users_bridge_returns_not_found(
    client: TestClient,
    monkeypatch,
) -> None:
    first_token = register_and_login(client, "first@example.com")
    second_token = register_and_login(client, "second@example.com")
    bridge_id = create_bridge(client, first_token, subdomain="first").json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/disable",
        headers=auth_headers(second_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "BRIDGE_NOT_FOUND"


def test_disable_draft_bridge_returns_invalid_state_transition(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/disable",
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_disable_ready_bridge_returns_invalid_state_transition(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.READY)
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/disable",
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_disable_active_bridge_with_caddy_ok_becomes_disabled(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/disable",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "DISABLED"


def test_disable_active_bridge_with_caddy_fail_becomes_error(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(False, "CADDY_CONFIG_REJECTED", "rejected", True, True),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/disable",
        headers=auth_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CADDY_DISABLE_FAILED"

    detail = client.get(f"/_v4nex/bridges/{bridge_id}", headers=auth_headers(token))
    assert detail.json()["status"] == "ERROR"


def test_disable_ok_updates_disabled_at(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/disable",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["disabled_at"] is not None


def test_disable_ok_creates_started_and_passed_events(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(True, "CADDY_OK", "ok", False, None),
    )

    assert (
        client.post(f"/_v4nex/bridges/{bridge_id}/disable", headers=auth_headers(token)).status_code
        == 200
    )
    events = client.get(f"/_v4nex/bridges/{bridge_id}/events", headers=auth_headers(token))
    event_types = [event["event_type"] for event in events.json()]

    assert "CADDY_DISABLE_STARTED" in event_types
    assert "CADDY_DISABLE_PASSED" in event_types


def test_disable_fail_creates_started_and_failed_events(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(False, "CADDY_CONFIG_REJECTED", "rejected", True, True),
    )

    assert (
        client.post(f"/_v4nex/bridges/{bridge_id}/disable", headers=auth_headers(token)).status_code
        == 409
    )
    events = client.get(f"/_v4nex/bridges/{bridge_id}/events", headers=auth_headers(token))
    event_types = [event["event_type"] for event in events.json()]

    assert "CADDY_DISABLE_STARTED" in event_types
    assert "CADDY_DISABLE_FAILED" in event_types


def test_disable_fail_returns_rollback_details(
    client: TestClient,
    monkeypatch,
) -> None:
    token = register_and_login(client, "user@example.com")
    bridge_id = create_bridge(client, token).json()["id"]
    set_bridge_status(bridge_id, BridgeStatus.ACTIVE)
    monkeypatch.setattr(
        "app.api.routes.bridges.disable_bridge_routes",
        lambda routes: CaddyActivationResult(False, "CADDY_CONFIG_REJECTED", "rejected", True, False),
    )

    response = client.post(
        f"/_v4nex/bridges/{bridge_id}/disable",
        headers=auth_headers(token),
    )

    details = response.json()["error"]["details"]
    assert details["error_code"] == "CADDY_CONFIG_REJECTED"
    assert details["rollback_attempted"] is True
    assert details["rollback_ok"] is False


def test_disable_routes_exclude_disabled_bridge_and_keep_other_active(
    client: TestClient,
    monkeypatch,
) -> None:
    captured_routes = []
    token = register_and_login(client, "user@example.com")
    first_id = create_bridge(client, token, subdomain="first").json()["id"]
    second_id = create_bridge(client, token, subdomain="second").json()["id"]
    set_bridge_status(first_id, BridgeStatus.ACTIVE)
    set_bridge_status(second_id, BridgeStatus.ACTIVE)

    def fake_disable(routes):
        captured_routes.extend(routes)
        return CaddyActivationResult(True, "CADDY_OK", "ok", False, None)

    monkeypatch.setattr("app.api.routes.bridges.disable_bridge_routes", fake_disable)

    response = client.post(
        f"/_v4nex/bridges/{first_id}/disable",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert [route.subdomain for route in captured_routes] == ["second"]
