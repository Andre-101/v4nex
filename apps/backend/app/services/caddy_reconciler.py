from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.domain.bridge_status import BridgeStatus
from app.models.bridge import Bridge
from app.services.caddy_activation import CaddyActivationResult, apply_bridge_routes
from app.services.caddy_config import CaddyBridgeRoute


@dataclass(frozen=True)
class CaddyReconcileResult:
    ok: bool
    active_routes_count: int
    error_code: str | None
    message: str
    rollback_attempted: bool
    rollback_ok: bool | None


def active_bridge_routes_from_db(db: Session) -> list[CaddyBridgeRoute]:
    bridges = db.scalars(
        select(Bridge)
        .where(Bridge.status == BridgeStatus.ACTIVE.value)
        .order_by(Bridge.created_at)
    ).all()
    return [
        CaddyBridgeRoute(
            subdomain=bridge.subdomain,
            public_domain=settings.public_domain,
            target_ipv6=bridge.target_ipv6,
            target_port=bridge.target_port,
        )
        for bridge in bridges
    ]


def reconcile_caddy_from_db(db: Session) -> CaddyReconcileResult:
    routes = active_bridge_routes_from_db(db)
    result: CaddyActivationResult = apply_bridge_routes(routes)
    return CaddyReconcileResult(
        ok=result.ok,
        active_routes_count=len(routes),
        error_code=result.error_code,
        message=result.message,
        rollback_attempted=result.rollback_attempted,
        rollback_ok=result.rollback_ok,
    )
