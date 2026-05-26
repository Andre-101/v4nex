from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import clear_rate_limits
from app.db.session import SessionLocal
from app.domain.user_role import UserRole
from app.models.user import User


def test_register_success_returns_201(client: TestClient) -> None:
    response = client.post(
        "/_v4nex/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"
    assert "id" in response.json()


def test_registered_user_defaults_to_user_role(client: TestClient) -> None:
    response = client.post(
        "/_v4nex/auth/register",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    assert response.status_code == 201
    with SessionLocal() as db:
        user = db.get(User, response.json()["id"])
        assert user is not None
        assert user.role == UserRole.USER.value


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


def test_rate_limit_exceeded_returns_standard_error(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_max_requests", 1)
    payload = {"email": "rate@example.com", "password": "strong-password"}

    assert client.post("/_v4nex/auth/register", json=payload).status_code == 201
    response = client.post("/_v4nex/auth/register", json=payload)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_rate_limit_state_can_be_cleared(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_max_requests", 1)
    first_payload = {"email": "first@example.com", "password": "strong-password"}
    second_payload = {"email": "first@example.com", "password": "strong-password"}
    assert client.post("/_v4nex/auth/register", json=first_payload).status_code == 201
    assert client.post("/_v4nex/auth/register", json=second_payload).status_code == 429

    clear_rate_limits()
    response = client.post(
        "/_v4nex/auth/register",
        json={"email": "second@example.com", "password": "strong-password"},
    )

    assert response.status_code == 201
