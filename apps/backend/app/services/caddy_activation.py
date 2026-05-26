from dataclasses import dataclass

from app.services.caddy_client import CaddyAdminClient, CaddyClientError
from app.services.caddy_config import CaddyBridgeRoute, build_caddy_config


CADDY_OK = "CADDY_OK"
CADDY_ADMIN_UNREACHABLE = "CADDY_ADMIN_UNREACHABLE"
CADDY_CONFIG_REJECTED = "CADDY_CONFIG_REJECTED"
CADDY_ROLLBACK_FAILED = "CADDY_ROLLBACK_FAILED"
CADDY_UNKNOWN_ERROR = "CADDY_UNKNOWN_ERROR"


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
        caddy_client.load_config(build_caddy_config(routes))
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
