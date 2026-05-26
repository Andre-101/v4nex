from fastapi.testclient import TestClient


def test_register_success_returns_201(client: TestClient) -> None:
    response = client.post(
        "/_v4nex/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert "id" in response.json()


def test_register_does_not_return_password_hash(client: TestClient) -> None:
    response = client.post(
        "/_v4nex/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    assert response.status_code == 201
    assert "password_hash" not in response.json()


def test_duplicate_email_fails(client: TestClient) -> None:
    payload = {"email": "user@example.com", "password": "strong-password"}
    assert client.post("/_v4nex/auth/register", json=payload).status_code == 201

    response = client.post("/_v4nex/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_login_success_returns_access_token(client: TestClient) -> None:
    payload = {"email": "user@example.com", "password": "strong-password"}
    assert client.post("/_v4nex/auth/register", json=payload).status_code == 201

    response = client.post("/_v4nex/auth/login", json=payload)

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert isinstance(response.json()["access_token"], str)
    assert response.json()["access_token"]


def test_invalid_login_fails_without_revealing_reason(client: TestClient) -> None:
    assert (
        client.post(
            "/_v4nex/auth/register",
            json={"email": "user@example.com", "password": "strong-password"},
        ).status_code
        == 201
    )

    response = client.post(
        "/_v4nex/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
    assert response.json()["error"]["message"] == "Invalid credentials."
