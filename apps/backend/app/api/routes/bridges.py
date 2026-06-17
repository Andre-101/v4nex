from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.core.rate_limit import check_rate_limit
from app.db.session import get_db
from app.domain.bridge_status import BridgeStatus
from app.domain.state_machine import assert_valid_transition
from app.domain.validators import validate_ipv6, validate_port, validate_subdomain
from app.models.bridge import Bridge
from app.models.bridge_event import BridgeEvent
from app.models.user import User
from app.schemas.bridges import BridgeCreateRequest, BridgeEventResponse, BridgeResponse, BridgeUpdateRequest
from app.services.caddy_activation import (
    CaddyActivationResult,
    activate_bridge_routes,
    disable_bridge_routes,
)
from app.services.audit import add_audit_event
from app.services.caddy_config import CaddyBridgeRoute
from app.services.tcp_validator import TcpValidationResult, validate_tcp_connectivity


router = APIRouter(prefix="/_v4nex/bridges", tags=["bridges"])


def bridge_to_response(bridge: Bridge) -> BridgeResponse:
    return BridgeResponse(
        id=bridge.id,
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


def event_to_response(event: BridgeEvent) -> BridgeEventResponse:
    return BridgeEventResponse(
        id=event.id,
        bridge_id=event.bridge_id,
        event_type=event.event_type,
        message=event.message,
        metadata=event.event_metadata,
        created_at=event.created_at,
    )


def get_owned_bridge(bridge_id: str, user: User, db: Session) -> Bridge:
    bridge = db.get(Bridge, bridge_id)
    if bridge is None or bridge.user_id != user.id:
        raise AppError(
            code=ErrorCode.BRIDGE_NOT_FOUND,
            message="Bridge was not found.",
            details={"bridge_id": bridge_id},
        )
    return bridge


def ensure_bridge_not_active(bridge: Bridge, action: str) -> None:
    if BridgeStatus(bridge.status) != BridgeStatus.ACTIVE:
        return

    message = (
        "This bridge is active. Disable it before editing."
        if action == "edit"
        else "This bridge is active. Disable it before deleting."
    )
    raise AppError(
        code=ErrorCode.INVALID_STATE_TRANSITION,
        message=message,
        details={
            "bridge_id": bridge.id,
            "status": bridge.status,
            "action": action,
        },
    )


def add_bridge_event(
    db: Session,
    bridge: Bridge,
    event_type: str,
    message: str,
    metadata: dict,
) -> None:
    db.add(
        BridgeEvent(
            bridge_id=bridge.id,
            event_type=event_type,
            message=message,
            event_metadata=metadata,
        )
    )


def validation_metadata(bridge: Bridge, result: TcpValidationResult | None = None) -> dict:
    metadata = {
        "target_ipv6": bridge.target_ipv6,
        "target_port": bridge.target_port,
    }
    if result is not None:
        metadata.update(
            {
                "error_code": result.error_code,
                "latency_ms": result.latency_ms,
            }
        )
    return metadata


def activation_metadata(
    bridge: Bridge,
    result: CaddyActivationResult | None = None,
) -> dict:
    metadata = {
        "subdomain": bridge.subdomain,
        "public_url": bridge.public_url,
        "target_ipv6": bridge.target_ipv6,
        "target_port": bridge.target_port,
    }
    if result is not None:
        metadata.update(
            {
                "error_code": result.error_code,
                "rollback_attempted": result.rollback_attempted,
                "rollback_ok": result.rollback_ok,
            }
        )
    return metadata


def bridge_to_caddy_route(bridge: Bridge) -> CaddyBridgeRoute:
    return CaddyBridgeRoute(
        subdomain=bridge.subdomain,
        public_domain=settings.public_domain,
        target_ipv6=bridge.target_ipv6,
        target_port=bridge.target_port,
    )


def active_routes_with_candidate(db: Session, bridge: Bridge) -> list[CaddyBridgeRoute]:
    active_bridges = db.scalars(
        select(Bridge)
        .where(Bridge.status == BridgeStatus.ACTIVE.value)
        .where(Bridge.id != bridge.id)
        .order_by(Bridge.created_at)
    ).all()
    return [bridge_to_caddy_route(active_bridge) for active_bridge in active_bridges] + [
        bridge_to_caddy_route(bridge)
    ]


def active_routes_without_bridge(db: Session, bridge: Bridge) -> list[CaddyBridgeRoute]:
    active_bridges = db.scalars(
        select(Bridge)
        .where(Bridge.status == BridgeStatus.ACTIVE.value)
        .where(Bridge.id != bridge.id)
        .order_by(Bridge.created_at)
    ).all()
    return [bridge_to_caddy_route(active_bridge) for active_bridge in active_bridges]


@router.get("", response_model=list[BridgeResponse])
def list_bridges(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BridgeResponse]:
    bridges = db.scalars(
        select(Bridge).where(Bridge.user_id == current_user.id).order_by(Bridge.created_at)
    ).all()
    return [bridge_to_response(bridge) for bridge in bridges]


@router.post("", response_model=BridgeResponse, status_code=status.HTTP_201_CREATED)
def create_bridge(
    payload: BridgeCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BridgeResponse:
    subdomain = validate_subdomain(payload.subdomain)
    target_ipv6 = validate_ipv6(payload.target_ipv6)
    target_port = validate_port(payload.target_port)
    bridge_count = db.scalar(
        select(func.count()).select_from(Bridge).where(Bridge.user_id == current_user.id)
    )
    if (bridge_count or 0) >= current_user.bridge_limit:
        raise AppError(
            code=ErrorCode.BRIDGE_LIMIT_REACHED,
            message="Bridge limit reached for this user.",
            details={
                "bridge_limit": current_user.bridge_limit,
                "bridges_used": bridge_count or 0,
            },
        )

    existing_bridge = db.scalar(select(Bridge).where(Bridge.subdomain == subdomain))
    if existing_bridge is not None:
        raise AppError(
            code=ErrorCode.SUBDOMAIN_ALREADY_EXISTS,
            message="Subdomain already exists.",
            details={"subdomain": subdomain},
        )

    public_url = f"https://{subdomain}.{settings.public_domain}"
    bridge = Bridge(
        user_id=current_user.id,
        subdomain=subdomain,
        public_url=public_url,
        target_ipv6=target_ipv6,
        target_port=target_port,
        status=BridgeStatus.DRAFT.value,
    )
    db.add(bridge)
    db.flush()

    db.add(
        BridgeEvent(
            bridge_id=bridge.id,
            event_type="BRIDGE_CREATED",
            message="Bridge created in DRAFT status.",
            event_metadata={},
        )
    )
    add_audit_event(
        db,
        actor=current_user,
        target_user_id=current_user.id,
        bridge_id=bridge.id,
        action="BRIDGE_CREATED",
        message="Bridge created.",
        metadata={"subdomain": bridge.subdomain, "target_port": bridge.target_port},
    )
    db.commit()
    db.refresh(bridge)

    return bridge_to_response(bridge)


@router.get("/{bridge_id}", response_model=BridgeResponse)
def get_bridge(
    bridge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BridgeResponse:
    return bridge_to_response(get_owned_bridge(bridge_id, current_user, db))


@router.patch("/{bridge_id}", response_model=BridgeResponse)
def update_bridge(
    bridge_id: str,
    payload: BridgeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BridgeResponse:
    bridge = get_owned_bridge(bridge_id, current_user, db)
    ensure_bridge_not_active(bridge, "edit")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return bridge_to_response(bridge)

    changed_fields: list[str] = []
    if "subdomain" in updates:
        subdomain = validate_subdomain(payload.subdomain or "")
        existing_bridge = db.scalar(
            select(Bridge)
            .where(Bridge.subdomain == subdomain)
            .where(Bridge.id != bridge.id)
        )
        if existing_bridge is not None:
            raise AppError(
                code=ErrorCode.SUBDOMAIN_ALREADY_EXISTS,
                message="Subdomain already exists.",
                details={"subdomain": subdomain},
            )
        if bridge.subdomain != subdomain:
            bridge.subdomain = subdomain
            bridge.public_url = f"https://{subdomain}.{settings.public_domain}"
            changed_fields.append("subdomain")

    if "target_ipv6" in updates:
        target_ipv6 = validate_ipv6(payload.target_ipv6 or "")
        if bridge.target_ipv6 != target_ipv6:
            bridge.target_ipv6 = target_ipv6
            changed_fields.append("target_ipv6")

    if "target_port" in updates:
        target_port = validate_port(payload.target_port)
        if bridge.target_port != target_port:
            bridge.target_port = target_port
            changed_fields.append("target_port")

    if changed_fields:
        bridge.status = BridgeStatus.DRAFT.value
        bridge.last_tcp_validation_at = None
        bridge.last_tcp_validation_result = None
        bridge.last_heartbeat_at = None
        bridge.last_heartbeat_result = None
        bridge.activated_at = None
        bridge.disabled_at = None
        add_bridge_event(
            db=db,
            bridge=bridge,
            event_type="BRIDGE_UPDATED",
            message="Bridge updated and reset to DRAFT status.",
            metadata={"changed_fields": changed_fields},
        )
        add_audit_event(
            db,
            actor=current_user,
            target_user_id=current_user.id,
            bridge_id=bridge.id,
            action="BRIDGE_UPDATED",
            message="Bridge updated.",
            metadata={"changed_fields": changed_fields},
        )
        db.commit()
        db.refresh(bridge)

    return bridge_to_response(bridge)


@router.delete("/{bridge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bridge(
    bridge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    bridge = get_owned_bridge(bridge_id, current_user, db)
    ensure_bridge_not_active(bridge, "delete")

    add_audit_event(
        db,
        actor=current_user,
        target_user_id=current_user.id,
        bridge_id=bridge.id,
        action="BRIDGE_DELETED",
        message="Bridge deleted.",
        metadata={"subdomain": bridge.subdomain, "status": bridge.status},
    )
    db.delete(bridge)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{bridge_id}/events", response_model=list[BridgeEventResponse])
def list_bridge_events(
    bridge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BridgeEventResponse]:
    bridge = get_owned_bridge(bridge_id, current_user, db)
    events = db.scalars(
        select(BridgeEvent)
        .where(BridgeEvent.bridge_id == bridge.id)
        .order_by(BridgeEvent.created_at)
    ).all()
    return [event_to_response(event) for event in events]


@router.post("/{bridge_id}/validate", response_model=BridgeResponse)
def validate_bridge(
    bridge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BridgeResponse:
    check_rate_limit(
        "bridges.validate",
        current_user.id,
        max_requests=settings.rate_limit_strict_max_requests,
    )
    bridge = get_owned_bridge(bridge_id, current_user, db)
    current_status = BridgeStatus(bridge.status)

    assert_valid_transition(current_status, BridgeStatus.VALIDATING)
    bridge.status = BridgeStatus.VALIDATING.value
    add_bridge_event(
        db=db,
        bridge=bridge,
        event_type="TCP_VALIDATION_STARTED",
        message="TCP validation started.",
        metadata=validation_metadata(bridge),
    )
    db.commit()
    db.refresh(bridge)

    result = validate_tcp_connectivity(bridge.target_ipv6, bridge.target_port)
    validated_at = datetime.now(UTC)

    if result.ok:
        assert_valid_transition(BridgeStatus.VALIDATING, BridgeStatus.READY)
        bridge.status = BridgeStatus.READY.value
        bridge.last_tcp_validation_at = validated_at
        bridge.last_tcp_validation_result = "OK"
        add_bridge_event(
            db=db,
            bridge=bridge,
            event_type="TCP_VALIDATION_PASSED",
            message=result.message,
            metadata=validation_metadata(bridge, result),
        )
        add_audit_event(
            db,
            actor=current_user,
            target_user_id=current_user.id,
            bridge_id=bridge.id,
            action="BRIDGE_VALIDATED",
            message="Bridge TCP validation passed.",
            metadata={"result": "OK"},
        )
        db.commit()
        db.refresh(bridge)
        return bridge_to_response(bridge)

    assert_valid_transition(BridgeStatus.VALIDATING, BridgeStatus.ERROR)
    bridge.status = BridgeStatus.ERROR.value
    bridge.last_tcp_validation_at = validated_at
    bridge.last_tcp_validation_result = "FAILED"
    add_bridge_event(
        db=db,
        bridge=bridge,
        event_type="TCP_VALIDATION_FAILED",
        message=result.message,
        metadata=validation_metadata(bridge, result),
    )
    add_audit_event(
        db,
        actor=current_user,
        target_user_id=current_user.id,
        bridge_id=bridge.id,
        action="BRIDGE_VALIDATED",
        message="Bridge TCP validation failed.",
        metadata={"result": "FAILED", "error_code": result.error_code},
    )
    db.commit()

    raise AppError(
        code=ErrorCode.TCP_VALIDATION_FAILED,
        message="TCP validation failed. v4nex could not reach the IPv6 service on the configured port.",
        details={
            "error_code": result.error_code,
            "message": result.message,
            "latency_ms": result.latency_ms,
            "target_port": bridge.target_port,
        },
    )


@router.post("/{bridge_id}/activate", response_model=BridgeResponse)
def activate_bridge(
    bridge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BridgeResponse:
    check_rate_limit(
        "bridges.activate",
        current_user.id,
        max_requests=settings.rate_limit_strict_max_requests,
    )
    bridge = get_owned_bridge(bridge_id, current_user, db)
    current_status = BridgeStatus(bridge.status)

    assert_valid_transition(current_status, BridgeStatus.ACTIVE)
    add_bridge_event(
        db=db,
        bridge=bridge,
        event_type="CADDY_ACTIVATION_STARTED",
        message="Caddy activation started.",
        metadata=activation_metadata(bridge),
    )
    db.commit()
    db.refresh(bridge)

    result = activate_bridge_routes(active_routes_with_candidate(db, bridge))
    if result.ok:
        assert_valid_transition(BridgeStatus.READY, BridgeStatus.ACTIVE)
        bridge.status = BridgeStatus.ACTIVE.value
        bridge.activated_at = datetime.now(UTC)
        add_bridge_event(
            db=db,
            bridge=bridge,
            event_type="CADDY_ACTIVATION_PASSED",
            message=result.message,
            metadata=activation_metadata(bridge, result),
        )
        add_audit_event(
            db,
            actor=current_user,
            target_user_id=current_user.id,
            bridge_id=bridge.id,
            action="BRIDGE_ACTIVATED",
            message="Bridge activated.",
            metadata={"subdomain": bridge.subdomain},
        )
        db.commit()
        db.refresh(bridge)
        return bridge_to_response(bridge)

    assert_valid_transition(BridgeStatus.READY, BridgeStatus.ERROR)
    bridge.status = BridgeStatus.ERROR.value
    add_bridge_event(
        db=db,
        bridge=bridge,
        event_type="CADDY_ACTIVATION_FAILED",
        message=result.message,
        metadata=activation_metadata(bridge, result),
    )
    db.commit()

    raise AppError(
        code=ErrorCode.CADDY_ACTIVATION_FAILED,
        message="Caddy activation failed. v4nex could not load the dynamic route.",
        details={
            "error_code": result.error_code,
            "message": result.message,
            "rollback_attempted": result.rollback_attempted,
            "rollback_ok": result.rollback_ok,
        },
    )


@router.post("/{bridge_id}/disable", response_model=BridgeResponse)
def disable_bridge(
    bridge_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BridgeResponse:
    check_rate_limit(
        "bridges.disable",
        current_user.id,
        max_requests=settings.rate_limit_strict_max_requests,
    )
    bridge = get_owned_bridge(bridge_id, current_user, db)
    current_status = BridgeStatus(bridge.status)

    assert_valid_transition(current_status, BridgeStatus.DISABLED)
    add_bridge_event(
        db=db,
        bridge=bridge,
        event_type="CADDY_DISABLE_STARTED",
        message="Caddy disable started.",
        metadata=activation_metadata(bridge),
    )
    db.commit()
    db.refresh(bridge)

    result = disable_bridge_routes(active_routes_without_bridge(db, bridge))
    if result.ok:
        assert_valid_transition(BridgeStatus.ACTIVE, BridgeStatus.DISABLED)
        bridge.status = BridgeStatus.DISABLED.value
        bridge.disabled_at = datetime.now(UTC)
        add_bridge_event(
            db=db,
            bridge=bridge,
            event_type="CADDY_DISABLE_PASSED",
            message=result.message,
            metadata=activation_metadata(bridge, result),
        )
        add_audit_event(
            db,
            actor=current_user,
            target_user_id=current_user.id,
            bridge_id=bridge.id,
            action="BRIDGE_DISABLED",
            message="Bridge disabled.",
            metadata={"subdomain": bridge.subdomain},
        )
        db.commit()
        db.refresh(bridge)
        return bridge_to_response(bridge)

    assert_valid_transition(BridgeStatus.ACTIVE, BridgeStatus.ERROR)
    bridge.status = BridgeStatus.ERROR.value
    add_bridge_event(
        db=db,
        bridge=bridge,
        event_type="CADDY_DISABLE_FAILED",
        message=result.message,
        metadata=activation_metadata(bridge, result),
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
