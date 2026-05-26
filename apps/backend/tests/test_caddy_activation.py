from app.services.caddy_activation import (
    CADDY_CONFIG_REJECTED,
    CADDY_OK,
    CaddyActivationResult,
    activate_bridge_routes,
    disable_bridge_routes,
)
import app.services.caddy_activation as caddy_activation
from app.services.caddy_client import CaddyClientError
from app.services.caddy_config import CaddyBridgeRoute, build_caddy_config


class FakeCaddyClient:
    def __init__(self, fail_load: bool = False, fail_rollback: bool = False) -> None:
        self.fail_load = fail_load
        self.fail_rollback = fail_rollback
        self.load_calls = []

    def get_current_config(self) -> dict:
        return {"previous": True}

    def load_config(self, config: dict) -> None:
        self.load_calls.append(config)
        if len(self.load_calls) == 1 and self.fail_load:
            raise CaddyClientError("rejected")
        if len(self.load_calls) == 2 and self.fail_rollback:
            raise CaddyClientError("rollback failed")


def route() -> CaddyBridgeRoute:
    return CaddyBridgeRoute(
        subdomain="demo",
        public_domain="v4nex.com",
        target_ipv6="2606:4700:4700::1111",
        target_port=80,
    )


def test_caddy_activation_ok() -> None:
    client = FakeCaddyClient()

    result = activate_bridge_routes([route()], client=client)

    assert result == CaddyActivationResult(True, CADDY_OK, "Caddy config loaded successfully.", False, None)
    assert len(client.load_calls) == 1


def test_caddy_activation_rolls_back_when_load_fails() -> None:
    client = FakeCaddyClient(fail_load=True)

    result = activate_bridge_routes([route()], client=client)

    assert result.ok is False
    assert result.error_code == CADDY_CONFIG_REJECTED
    assert result.rollback_attempted is True
    assert result.rollback_ok is True
    assert client.load_calls[-1] == {"previous": True}


def test_caddy_disable_rolls_back_when_load_fails() -> None:
    client = FakeCaddyClient(fail_load=True)

    result = disable_bridge_routes([route()], client=client)

    assert result.ok is False
    assert result.error_code == CADDY_CONFIG_REJECTED
    assert result.rollback_attempted is True
    assert result.rollback_ok is True
    assert client.load_calls[-1] == {"previous": True}


def test_caddy_config_renderer_rejects_malicious_subdomain() -> None:
    malicious_route = CaddyBridgeRoute(
        subdomain="demo\nreverse_proxy evil:80",
        public_domain="v4nex.com",
        target_ipv6="2606:4700:4700::1111",
        target_port=80,
    )

    try:
        build_caddy_config([malicious_route])
    except Exception as exc:
        assert exc.__class__.__name__ == "AppError"
    else:
        raise AssertionError("malicious subdomain was accepted")


def test_caddy_config_preserves_admin_api() -> None:
    config = build_caddy_config([route()])

    assert config["admin"]["listen"] == "0.0.0.0:2019"


def test_caddy_config_disables_automatic_https_for_dev() -> None:
    config = build_caddy_config([route()])

    assert config["apps"]["http"]["servers"]["srv0"]["automatic_https"] == {"disable": True}


class FakeLock:
    def __init__(self) -> None:
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.exited = True


def test_caddy_apply_uses_local_lock(monkeypatch) -> None:
    fake_lock = FakeLock()
    monkeypatch.setattr(caddy_activation, "_caddy_config_lock", fake_lock)

    result = activate_bridge_routes([route()], client=FakeCaddyClient())

    assert result.ok is True
    assert fake_lock.entered is True
    assert fake_lock.exited is True
