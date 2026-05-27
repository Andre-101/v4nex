from copy import deepcopy
from dataclasses import dataclass
from ipaddress import IPv6Address, ip_address
from typing import Any

from app.core.config import settings
from app.domain.validators import validate_subdomain


class CaddyConfigShapeError(Exception):
    pass


@dataclass(frozen=True)
class CaddyBridgeRoute:
    subdomain: str
    public_domain: str
    target_ipv6: str
    target_port: int


def build_bridge_route(route: CaddyBridgeRoute) -> dict[str, Any]:
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


def build_caddy_config(routes: list[CaddyBridgeRoute]) -> dict[str, Any]:
    raise CaddyConfigShapeError(
        "Full Caddy config generation is disabled. Dynamic bridge routes must be injected into the live config."
    )


def is_v4nex_dynamic_bridge_route(route: dict[str, Any], public_domain: str) -> bool:
    if _route_matches_protected_paths(route):
        return False

    hosts = _route_hosts(route)
    if not hosts:
        return False

    expected_suffix = f".{public_domain}"
    if not all(host.endswith(expected_suffix) and host != public_domain for host in hosts):
        return False

    return any(_is_ipv6_reverse_proxy_handler(handler) for handler in route.get("handle", []))


def inject_bridge_routes(
    current_config: dict[str, Any],
    routes: list[CaddyBridgeRoute],
) -> dict[str, Any]:
    next_config = deepcopy(current_config)
    public_domain = _public_domain_for(routes)
    server = _find_public_http_server(next_config, public_domain)

    existing_routes = server.get("routes")
    if not isinstance(existing_routes, list):
        raise CaddyConfigShapeError("Public Caddy HTTP server does not expose a routes list.")

    preserved_routes = [
        route
        for route in existing_routes
        if not is_v4nex_dynamic_bridge_route(route, public_domain)
    ]
    bridge_routes = [build_bridge_route(route) for route in routes]
    insert_at = _frontend_catch_all_index(preserved_routes)

    server["routes"] = [
        *preserved_routes[:insert_at],
        *bridge_routes,
        *preserved_routes[insert_at:],
    ]
    return next_config


def _public_domain_for(routes: list[CaddyBridgeRoute]) -> str:
    if routes:
        return routes[0].public_domain
    return settings.public_domain


def _find_public_http_server(config: dict[str, Any], public_domain: str) -> dict[str, Any]:
    servers = (
        config.get("apps", {})
        .get("http", {})
        .get("servers", {})
    )
    if not isinstance(servers, dict) or not servers:
        raise CaddyConfigShapeError("Caddy config does not contain HTTP servers.")

    candidates: list[dict[str, Any]] = []
    for server in servers.values():
        if not isinstance(server, dict):
            continue
        routes = server.get("routes")
        if not isinstance(routes, list):
            continue
        if any(_route_has_host(route, public_domain) for route in routes):
            candidates.append(server)

    if len(candidates) != 1:
        raise CaddyConfigShapeError("Could not safely identify exactly one public Caddy HTTP server.")
    return candidates[0]


def _frontend_catch_all_index(routes: list[dict[str, Any]]) -> int:
    for index, route in enumerate(routes):
        if "match" not in route and _route_has_reverse_proxy(route):
            return index
    return len(routes)


def _route_hosts(route: dict[str, Any]) -> list[str]:
    hosts: list[str] = []
    matchers = route.get("match", [])
    if not isinstance(matchers, list):
        return hosts

    for matcher in matchers:
        if not isinstance(matcher, dict):
            continue
        matcher_hosts = matcher.get("host", [])
        if isinstance(matcher_hosts, str):
            hosts.append(matcher_hosts)
        elif isinstance(matcher_hosts, list):
            hosts.extend(host for host in matcher_hosts if isinstance(host, str))
    return hosts


def _route_has_host(route: dict[str, Any], host: str) -> bool:
    return host in _route_hosts(route)


def _route_matches_protected_paths(route: dict[str, Any]) -> bool:
    matchers = route.get("match", [])
    if not isinstance(matchers, list):
        return False

    for matcher in matchers:
        if not isinstance(matcher, dict):
            continue
        paths = matcher.get("path", [])
        if isinstance(paths, str):
            paths = [paths]
        if not isinstance(paths, list):
            continue
        for path in paths:
            if path == "/health" or path == "/_v4nex/*":
                return True
    return False


def _route_has_reverse_proxy(route: dict[str, Any]) -> bool:
    return any(
        isinstance(handler, dict) and handler.get("handler") == "reverse_proxy"
        for handler in route.get("handle", [])
    )


def _is_ipv6_reverse_proxy_handler(handler: dict[str, Any]) -> bool:
    if not isinstance(handler, dict) or handler.get("handler") != "reverse_proxy":
        return False

    upstreams = handler.get("upstreams", [])
    if not isinstance(upstreams, list):
        return False

    return any(_is_bracketed_ipv6_dial(upstream.get("dial")) for upstream in upstreams if isinstance(upstream, dict))


def _is_bracketed_ipv6_dial(dial: str | None) -> bool:
    if not isinstance(dial, str) or not dial.startswith("[") or "]:" not in dial:
        return False

    host = dial[1:dial.index("]:")]
    try:
        return isinstance(ip_address(host), IPv6Address)
    except ValueError:
        return False
