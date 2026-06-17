from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.domain.bridge_status import BridgeStatus
from app.domain.state_machine import assert_valid_transition
from app.models.admin_audit_event import AdminAuditEvent
from app.models.bridge import Bridge
from app.models.bridge_event import BridgeEvent
from app.models.user import User
from app.schemas.bridges import BridgeResponse
from app.services.audit import add_audit_event
from app.services.caddy_activation import disable_bridge_routes
from app.services.caddy_config import CaddyBridgeRoute
from app.services.caddy_reconciler import CaddyReconcileResult, reconcile_caddy_from_db
from app.services.diagnostics import build_diagnostics


router = APIRouter(prefix="/_v4nex/admin", tags=["admin"])


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    role: str
    is_active: bool
    bridge_limit: int
    bridges_used: int
    created_at: str
    updated_at: str


class AdminUserUpdateRequest(BaseModel):
    bridge_limit: int | None = None
    is_active: bool | None = None


class AdminBridgeResponse(BridgeResponse):
    owner_email: str
    user_id: str


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


def user_to_admin_response(db: Session, user: User) -> AdminUserResponse:
    bridges_used = db.scalar(select(func.count()).select_from(Bridge).where(Bridge.user_id == user.id))
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        bridge_limit=user.bridge_limit,
        bridges_used=bridges_used or 0,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat(),
    )


def bridge_to_admin_response(bridge: Bridge) -> AdminBridgeResponse:
    return AdminBridgeResponse(
        id=bridge.id,
        user_id=bridge.user_id,
        owner_email=bridge.user.email,
        subdomain=bridge.subdomain,
        public_url=bridge.public_url,
        target_ipv6=bridge.target_ipv6,
        target_port=bridge.target_port,
        status=BridgeStatus(bridge.status),
        last_tcp_validation_at=bridge.last_tcp_validation_at,
        last_tcp_validation_result=bridge.last_tcp_validation_result,
        last_heartbeat_at=bridge.last_heartbeat_at,
        last_heartbeat_result=bridge.last_heartbeat_result,
        activated_at=bridge.activated_at,
        disabled_at=bridge.disabled_at,
        created_at=bridge.created_at,
        updated_at=bridge.updated_at,
    )


def get_user_or_404(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(
            code=ErrorCode.USER_NOT_FOUND,
            message="User was not found.",
            details={"user_id": user_id},
        )
    return user


def get_bridge_or_404(db: Session, bridge_id: str) -> Bridge:
    bridge = db.get(Bridge, bridge_id)
    if bridge is None:
        raise AppError(
            code=ErrorCode.BRIDGE_NOT_FOUND,
            message="Bridge was not found.",
            details={"bridge_id": bridge_id},
        )
    return bridge


def bridge_to_caddy_route(bridge: Bridge) -> CaddyBridgeRoute:
    return CaddyBridgeRoute(
        subdomain=bridge.subdomain,
        public_domain=settings.public_domain,
        target_ipv6=bridge.target_ipv6,
        target_port=bridge.target_port,
    )


def active_routes_without_bridge(db: Session, bridge: Bridge) -> list[CaddyBridgeRoute]:
    active_bridges = db.scalars(
        select(Bridge)
        .where(Bridge.status == BridgeStatus.ACTIVE.value)
        .where(Bridge.id != bridge.id)
        .order_by(Bridge.created_at)
    ).all()
    return [bridge_to_caddy_route(active_bridge) for active_bridge in active_bridges]


def add_bridge_event(db: Session, bridge: Bridge, event_type: str, message: str, metadata: dict) -> None:
    db.add(
        BridgeEvent(
            bridge_id=bridge.id,
            event_type=event_type,
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


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> list[AdminUserResponse]:
    users = db.scalars(select(User).order_by(User.created_at)).all()
    return [user_to_admin_response(db, user) for user in users]


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user(
    user_id: str,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    return user_to_admin_response(db, get_user_or_404(db, user_id))


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> AdminUserResponse:
    user = get_user_or_404(db, user_id)
    updates = payload.model_dump(exclude_unset=True)

    if "bridge_limit" in updates:
        if payload.bridge_limit is None or payload.bridge_limit < 0:
            raise AppError(
                code=ErrorCode.INVALID_BRIDGE_LIMIT,
                message="Bridge limit must be zero or greater.",
                details={"bridge_limit": payload.bridge_limit},
            )
        previous_limit = user.bridge_limit
        user.bridge_limit = payload.bridge_limit
        add_audit_event(
            db,
            actor=current_user,
            target_user_id=user.id,
            action="USER_LIMIT_CHANGED",
            message="User bridge limit changed.",
            metadata={"previous_limit": previous_limit, "new_limit": user.bridge_limit},
        )

    if "is_active" in updates:
        if user.id == current_user.id and payload.is_active is False:
            raise AppError(
                code=ErrorCode.SELF_ACTION_NOT_ALLOWED,
                message="Admins cannot suspend themselves.",
            )
        previous_active = user.is_active
        user.is_active = bool(payload.is_active)
        if previous_active != user.is_active:
            add_audit_event(
                db,
                actor=current_user,
                target_user_id=user.id,
                action="USER_UNSUSPENDED" if user.is_active else "USER_SUSPENDED",
                message="User reactivated." if user.is_active else "User suspended.",
                metadata={},
            )

    db.commit()
    db.refresh(user)
    return user_to_admin_response(db, user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> Response:
    if user_id == current_user.id:
        raise AppError(
            code=ErrorCode.SELF_ACTION_NOT_ALLOWED,
            message="Admins cannot delete themselves.",
        )
    user = get_user_or_404(db, user_id)
    active_count = db.scalar(
        select(func.count())
        .select_from(Bridge)
        .where(Bridge.user_id == user.id)
        .where(Bridge.status == BridgeStatus.ACTIVE.value)
    )
    if active_count:
        raise AppError(
            code=ErrorCode.USER_HAS_ACTIVE_BRIDGES,
            message="User has active bridges. Disable them before deleting the user.",
            details={"user_id": user.id, "active_bridges": active_count},
        )

    add_audit_event(
        db,
        actor=current_user,
        target_user_id=user.id,
        action="USER_DELETED",
        message="User deleted.",
        metadata={"email": user.email},
    )
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/bridges", response_model=list[AdminBridgeResponse])
def list_all_bridges(
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> list[AdminBridgeResponse]:
    bridges = db.scalars(select(Bridge).order_by(Bridge.created_at)).all()
    return [bridge_to_admin_response(bridge) for bridge in bridges]


@router.get("/users/{user_id}/bridges", response_model=list[AdminBridgeResponse])
def list_user_bridges(
    user_id: str,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> list[AdminBridgeResponse]:
    user = get_user_or_404(db, user_id)
    return [bridge_to_admin_response(bridge) for bridge in user.bridges]


@router.post("/bridges/{bridge_id}/disable", response_model=AdminBridgeResponse)
def admin_disable_bridge(
    bridge_id: str,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> AdminBridgeResponse:
    bridge = get_bridge_or_404(db, bridge_id)
    assert_valid_transition(BridgeStatus(bridge.status), BridgeStatus.DISABLED)
    add_bridge_event(
        db,
        bridge,
        "CADDY_DISABLE_STARTED",
        "Admin Caddy disable started.",
        {"subdomain": bridge.subdomain, "target_port": bridge.target_port},
    )
    db.commit()
    db.refresh(bridge)

    result = disable_bridge_routes(active_routes_without_bridge(db, bridge))
    if not result.ok:
        assert_valid_transition(BridgeStatus.ACTIVE, BridgeStatus.ERROR)
        bridge.status = BridgeStatus.ERROR.value
        add_bridge_event(
            db,
            bridge,
            "CADDY_DISABLE_FAILED",
            result.message,
            {
                "error_code": result.error_code,
                "rollback_attempted": result.rollback_attempted,
                "rollback_ok": result.rollback_ok,
            },
        )
        db.commit()
        raise AppError(
            code=ErrorCode.CADDY_DISABLE_FAILED,
            message="Caddy disable failed. v4nex could not remove the dynamic route.",
            details={
                "error_code": result.error_code,
                "message": result.message,
                "rollback_attempted": result.rollback_attempted,
                "rollback_ok": result.rollback_ok,
            },
        )

    assert_valid_transition(BridgeStatus.ACTIVE, BridgeStatus.DISABLED)
    bridge.status = BridgeStatus.DISABLED.value
    bridge.disabled_at = datetime.now(UTC)
    add_bridge_event(
        db,
        bridge,
        "CADDY_DISABLE_PASSED",
        result.message,
        {"subdomain": bridge.subdomain},
    )
    add_audit_event(
        db,
        actor=current_user,
        target_user_id=bridge.user_id,
        bridge_id=bridge.id,
        action="ADMIN_BRIDGE_DISABLED",
        message="Admin disabled bridge.",
        metadata={"subdomain": bridge.subdomain},
    )
    db.commit()
    db.refresh(bridge)
    return bridge_to_admin_response(bridge)


@router.delete("/bridges/{bridge_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_bridge(
    bridge_id: str,
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> Response:
    bridge = get_bridge_or_404(db, bridge_id)
    if BridgeStatus(bridge.status) == BridgeStatus.ACTIVE:
        raise AppError(
            code=ErrorCode.INVALID_STATE_TRANSITION,
            message="This bridge is active. Disable it before deleting.",
            details={"bridge_id": bridge.id, "status": bridge.status},
        )
    add_audit_event(
        db,
        actor=current_user,
        target_user_id=bridge.user_id,
        bridge_id=bridge.id,
        action="ADMIN_BRIDGE_DELETED",
        message="Admin deleted bridge.",
        metadata={"subdomain": bridge.subdomain, "status": bridge.status},
    )
    db.delete(bridge)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
