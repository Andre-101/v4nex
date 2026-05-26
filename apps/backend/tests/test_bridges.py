from fastapi.testclient import TestClient


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
