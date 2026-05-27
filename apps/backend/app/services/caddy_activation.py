from dataclasses import dataclass
import threading

from app.services.caddy_client import CaddyAdminClient, CaddyClientError
from app.services.caddy_config import (
    CaddyBridgeRoute,
    CaddyConfigShapeError,
    inject_bridge_routes,
)


CADDY_OK = "CADDY_OK"
CADDY_ADMIN_UNREACHABLE = "CADDY_ADMIN_UNREACHABLE"
CADDY_CONFIG_SHAPE_UNSUPPORTED = "CADDY_CONFIG_SHAPE_UNSUPPORTED"
CADDY_CONFIG_REJECTED = "CADDY_CONFIG_REJECTED"
CADDY_ROLLBACK_FAILED = "CADDY_ROLLBACK_FAILED"
CADDY_UNKNOWN_ERROR = "CADDY_UNKNOWN_ERROR"

_caddy_config_lock = threading.Lock()


@dataclass(frozen=True)
class CaddyActivationResult:
    ok: bool
    error_code: str | None
    message: str
    rollback_attempted: bool
    rollback_ok: bool | None


def activate_bridge_routes(
    routes: list[CaddyBridgeRoute],
    client: CaddyAdminClient | None = None,
) -> CaddyActivationResult:
    return apply_bridge_routes(routes, client=client)


def disable_bridge_routes(
    routes: list[CaddyBridgeRoute],
    client: CaddyAdminClient | None = None,
) -> CaddyActivationResult:
    return apply_bridge_routes(routes, client=client)


def apply_bridge_routes(
    routes: list[CaddyBridgeRoute],
    client: CaddyAdminClient | None = None,
) -> CaddyActivationResult:
    with _caddy_config_lock:
        return _apply_bridge_routes_unlocked(routes, client=client)


def _apply_bridge_routes_unlocked(
    routes: list[CaddyBridgeRoute],
    client: CaddyAdminClient | None = None,
) -> CaddyActivationResult:
    caddy_client = client or CaddyAdminClient()

    try:
        previous_config = caddy_client.get_current_config()
    except CaddyClientError as exc:
        return CaddyActivationResult(
            ok=False,
            error_code=CADDY_ADMIN_UNREACHABLE,
            message=str(exc) or "Caddy Admin API is unreachable.",
            rollback_attempted=False,
            rollback_ok=None,
        )

    try:
        next_config = inject_bridge_routes(previous_config, routes)
    except CaddyConfigShapeError as exc:
        return CaddyActivationResult(
            ok=False,
            error_code=CADDY_CONFIG_SHAPE_UNSUPPORTED,
            message=str(exc) or "Caddy config shape is not supported for safe dynamic injection.",
            rollback_attempted=False,
            rollback_ok=None,
        )
    except Exception as exc:
        return CaddyActivationResult(
            ok=False,
            error_code=CADDY_UNKNOWN_ERROR,
            message=str(exc) or "Unexpected Caddy config injection error.",
            rollback_attempted=False,
            rollback_ok=None,
        )

    try:
        caddy_client.load_config(next_config)
    except CaddyClientError as exc:
        rollback_ok = _attempt_rollback(caddy_client, previous_config)
        return CaddyActivationResult(
            ok=False,
            error_code=CADDY_CONFIG_REJECTED if rollback_ok else CADDY_ROLLBACK_FAILED,
            message=str(exc) or "Caddy rejected the generated config.",
            rollback_attempted=True,
            rollback_ok=rollback_ok,
        )
    except Exception as exc:
        rollback_ok = _attempt_rollback(caddy_client, previous_config)
        return CaddyActivationResult(
            ok=False,
            error_code=CADDY_UNKNOWN_ERROR if rollback_ok else CADDY_ROLLBACK_FAILED,
            message=str(exc) or "Unexpected Caddy activation error.",
            rollback_attempted=True,
            rollback_ok=rollback_ok,
        )

    return CaddyActivationResult(
        ok=True,
        error_code=CADDY_OK,
        message="Caddy config loaded successfully.",
        rollback_attempted=False,
        rollback_ok=None,
    )


def _attempt_rollback(client: CaddyAdminClient, previous_config: dict) -> bool:
    try:
        client.load_config(previous_config)
        return True
    except CaddyClientError:
        return False
