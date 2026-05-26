from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.caddy_reconciler import CaddyReconcileResult, reconcile_caddy_from_db
from app.services.diagnostics import build_diagnostics


router = APIRouter(prefix="/_v4nex/admin", tags=["admin"])


@router.post("/reconcile-caddy")
def reconcile_caddy(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    result: CaddyReconcileResult = reconcile_caddy_from_db(db)
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
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return build_diagnostics(db)
