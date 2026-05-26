from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.core.config import settings
from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.models.admin_audit_event import AdminAuditEvent
from app.models.user import User
from app.services.caddy_reconciler import CaddyReconcileResult, reconcile_caddy_from_db
from app.services.diagnostics import build_diagnostics


router = APIRouter(prefix="/_v4nex/admin", tags=["admin"])


def add_admin_audit_event(
    db: Session,
    actor: User,
    action: str,
    message: str,
    metadata: dict,
) -> None:
    db.add(
        AdminAuditEvent(
            actor_user_id=actor.id,
            action=action,
            message=message,
            event_metadata=metadata,
        )
    )


@router.post("/reconcile-caddy")
def reconcile_caddy(
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    check_rate_limit(
        "admin.reconcile_caddy",
        current_user.id,
        max_requests=settings.rate_limit_strict_max_requests,
    )
    add_admin_audit_event(
        db,
        current_user,
        "ADMIN_RECONCILE_CADDY_STARTED",
        "Admin Caddy reconciliation started.",
        {},
    )
    db.commit()
    result: CaddyReconcileResult = reconcile_caddy_from_db(db)
    add_admin_audit_event(
        db,
        current_user,
        "ADMIN_RECONCILE_CADDY_FINISHED",
        "Admin Caddy reconciliation finished.",
        {
            "ok": result.ok,
            "active_routes_count": result.active_routes_count,
            "error_code": result.error_code,
            "rollback_attempted": result.rollback_attempted,
            "rollback_ok": result.rollback_ok,
        },
    )
    db.commit()
    return {
        "ok": result.ok,
        "active_routes_count": result.active_routes_count,
        "error_code": result.error_code,
        "message": result.message,
        "rollback_attempted": result.rollback_attempted,
        "rollback_ok": result.rollback_ok,
    }


@router.get("/diagnostics")
def diagnostics(
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> dict:
    add_admin_audit_event(
        db,
        current_user,
        "ADMIN_DIAGNOSTICS_VIEWED",
        "Admin diagnostics viewed.",
        {},
    )
    db.commit()
    return build_diagnostics(db)
