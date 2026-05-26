from dataclasses import dataclass
from typing import Any

from app.domain.validators import validate_subdomain


@dataclass(frozen=True)
class CaddyBridgeRoute:
    subdomain: str
    public_domain: str
    target_ipv6: str
    target_port: int


def build_caddy_config(routes: list[CaddyBridgeRoute]) -> dict[str, Any]:
    return {
        "admin": {
            "listen": "0.0.0.0:2019",
        },
        "apps": {
            "http": {
                "servers": {
                    "srv0": {
                        "listen": [":8080"],
                        "routes": [
                            *[_bridge_route(route) for route in routes],
                            _backend_route(),
                            _frontend_route(),
                        ],
                    }
                }
            }
        }
    }


def _bridge_route(route: CaddyBridgeRoute) -> dict[str, Any]:
    subdomain = validate_subdomain(route.subdomain)
    host = f"{subdomain}.{route.public_domain}"
    upstream = f"[{route.target_ipv6}]:{route.target_port}"
    return {
        "match": [{"host": [host]}],
        "handle": [
            {
                "handler": "reverse_proxy",
                "upstreams": [{"dial": upstream}],
            }
        ],
    }


def _backend_route() -> dict[str, Any]:
    return {
        "match": [{"path": ["/_v4nex/*", "/health"]}],
        "handle": [
            {
                "handler": "reverse_proxy",
                "upstreams": [{"dial": "backend:8000"}],
            }
        ],
    }


def _frontend_route() -> dict[str, Any]:
    return {
        "handle": [
            {
                "handler": "reverse_proxy",
                "upstreams": [{"dial": "frontend:5173"}],
            }
        ]
    }
