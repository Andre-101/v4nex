import pytest

from app.services.caddy_activation import (
    CADDY_CONFIG_REJECTED,
    CADDY_CONFIG_SHAPE_UNSUPPORTED,
    CADDY_OK,
    CaddyActivationResult,
    activate_bridge_routes,
    disable_bridge_routes,
)
import app.services.caddy_activation as caddy_activation
from app.services.caddy_client import CaddyClientError
from app.services.caddy_config import (
    CaddyBridgeRoute,
    CaddyConfigShapeError,
    build_bridge_route,
    inject_bridge_routes,
    is_v4nex_dynamic_bridge_route,
)


def product_config() -> dict:
    return {
        "admin": {"listen": "0.0.0.0:2019"},
        "apps": {
            "http": {
                "servers": {
                    "public": {
                        "listen": [":80", ":443"],
                        "automatic_https": {},
                        "routes": [
                            {
                                "match": [
                                    {
                                        "host": ["v4nex.com"],
                                        "path": ["/_v4nex/*", "/health"],
                                    }
                                ],
                                "handle": [
                                    {
                                        "handler": "reverse_proxy",
                                        "upstreams": [{"dial": "backend:8000"}],
                                    }
                                ],
                            },
                            {
                                "match": [{"host": ["v4nex.com"]}],
                                "handle": [
                                    {
                                        "handler": "reverse_proxy",
                                        "upstreams": [{"dial": "frontend:80"}],
                                    }
                                ],
                            },
                            {
                                "handle": [
                                    {
                                        "handler": "reverse_proxy",
                                        "upstreams": [{"dial": "frontend:80"}],
                                    }
                                ],
                            },
                        ],
                    }
                }
            },
            "tls": {"automation": {"policies": [{"subjects": ["v4nex.com", "*.v4nex.com"]}]}},
        },
    }


class FakeCaddyClient:
    def __init__(
        self,
        current_config: dict | None = None,
        fail_load: bool = False,
        fail_rollback: bool = False,
    ) -> None:
        self.current_config = current_config or product_config()
        self.fail_load = fail_load
        self.fail_rollback = fail_rollback
        self.load_calls = []

    def get_current_config(self) -> dict:
        return self.current_config

    def load_config(self, config: dict) -> None:
        self.load_calls.append(config)
        if len(self.load_calls) == 1 and self.fail_load:
            raise CaddyClientError("rejected")
        if len(self.load_calls) == 2 and self.fail_rollback:
            raise CaddyClientError("rollback failed")


def route(subdomain: str = "demo", port: int = 80) -> CaddyBridgeRoute:
    return CaddyBridgeRoute(
        subdomain=subdomain,
        public_domain="v4nex.com",
        target_ipv6="2606:4700:4700::1111",
        target_port=port,
    )


def routes(config: dict) -> list[dict]:
    return config["apps"]["http"]["servers"]["public"]["routes"]


def test_build_bridge_route_rejects_malicious_subdomain() -> None:
    malicious_route = CaddyBridgeRoute(
        subdomain="demo\nreverse_proxy evil:80",
        public_domain="v4nex.com",
        target_ipv6="2606:4700:4700::1111",
        target_port=80,
    )

    with pytest.raises(Exception) as exc_info:
        build_bridge_route(malicious_route)

    assert exc_info.value.__class__.__name__ == "AppError"


def test_is_v4nex_dynamic_bridge_route_detects_only_bridge_routes() -> None:
    bridge_route = build_bridge_route(route())

    assert is_v4nex_dynamic_bridge_route(bridge_route, "v4nex.com") is True
    assert is_v4nex_dynamic_bridge_route(routes(product_config())[0], "v4nex.com") is False
    assert is_v4nex_dynamic_bridge_route(routes(product_config())[1], "v4nex.com") is False


def test_inject_bridge_routes_preserves_admin_config() -> None:
    config = inject_bridge_routes(product_config(), [route()])

    assert config["admin"]["listen"] == "0.0.0.0:2019"


def test_inject_bridge_routes_preserves_listen_existing() -> None:
    config = inject_bridge_routes(product_config(), [route()])

    assert config["apps"]["http"]["servers"]["public"]["listen"] == [":80", ":443"]


def test_inject_bridge_routes_does_not_create_8080_listener() -> None:
    config = inject_bridge_routes(product_config(), [route()])

    assert ":8080" not in config["apps"]["http"]["servers"]["public"]["listen"]


def test_inject_bridge_routes_does_not_disable_automatic_https() -> None:
    config = inject_bridge_routes(product_config(), [route()])

    assert config["apps"]["http"]["servers"]["public"]["automatic_https"] == {}
    assert config["apps"]["http"]["servers"]["public"]["automatic_https"] != {"disable": True}


def test_inject_bridge_routes_preserves_base_domain_route() -> None:
    config = inject_bridge_routes(product_config(), [route()])

    assert any("v4nex.com" in route_item.get("match", [{}])[0].get("host", []) for route_item in routes(config))


def test_inject_bridge_routes_preserves_health_and_api_routes() -> None:
    config = inject_bridge_routes(product_config(), [route()])

    assert any(
        "/health" in route_item.get("match", [{}])[0].get("path", [])
        and "/_v4nex/*" in route_item.get("match", [{}])[0].get("path", [])
        for route_item in routes(config)
    )


def test_inject_bridge_routes_inserts_bridge_before_frontend_catch_all() -> None:
    config = inject_bridge_routes(product_config(), [route()])
    route_items = routes(config)
    bridge_index = next(
        index for index, route_item in enumerate(route_items) if is_v4nex_dynamic_bridge_route(route_item, "v4nex.com")
    )
    catch_all_index = next(index for index, route_item in enumerate(route_items) if "match" not in route_item)

    assert bridge_index < catch_all_index


def test_inject_bridge_routes_replaces_previous_dynamic_routes_without_duplicates() -> None:
    config = product_config()
    config["apps"]["http"]["servers"]["public"]["routes"].insert(0, build_bridge_route(route("demo")))

    next_config = inject_bridge_routes(config, [route("demo"), route("second", 8080)])
    dynamic_routes = [
        route_item
        for route_item in routes(next_config)
        if is_v4nex_dynamic_bridge_route(route_item, "v4nex.com")
    ]

    assert len(dynamic_routes) == 2
    assert [route_item["match"][0]["host"][0] for route_item in dynamic_routes] == [
        "demo.v4nex.com",
        "second.v4nex.com",
    ]


def test_inject_bridge_routes_fails_safe_without_http_servers() -> None:
    with pytest.raises(CaddyConfigShapeError):
        inject_bridge_routes({"apps": {"http": {"servers": {}}}}, [route()])


def test_caddy_activation_ok() -> None:
    client = FakeCaddyClient()

    result = activate_bridge_routes([route()], client=client)

    assert result == CaddyActivationResult(True, CADDY_OK, "Caddy config loaded successfully.", False, None)
    assert len(client.load_calls) == 1
    assert "admin" in client.load_calls[0]
    assert client.load_calls[0]["apps"]["http"]["servers"]["public"]["listen"] == [":80", ":443"]


def test_caddy_activation_does_not_load_when_inject_fails() -> None:
    client = FakeCaddyClient(current_config={"apps": {"http": {"servers": {}}}})

    result = activate_bridge_routes([route()], client=client)

    assert result.ok is False
    assert result.error_code == CADDY_CONFIG_SHAPE_UNSUPPORTED
    assert result.rollback_attempted is False
    assert client.load_calls == []


def test_caddy_activation_rolls_back_when_load_fails() -> None:
    client = FakeCaddyClient(fail_load=True)

    result = activate_bridge_routes([route()], client=client)

    assert result.ok is False
    assert result.error_code == CADDY_CONFIG_REJECTED
    assert result.rollback_attempted is True
    assert result.rollback_ok is True
    assert client.load_calls[-1] == product_config()


def test_caddy_disable_rolls_back_when_load_fails() -> None:
    client = FakeCaddyClient(fail_load=True)

    result = disable_bridge_routes([route()], client=client)

    assert result.ok is False
    assert result.error_code == CADDY_CONFIG_REJECTED
    assert result.rollback_attempted is True
    assert result.rollback_ok is True
    assert client.load_calls[-1] == product_config()


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
