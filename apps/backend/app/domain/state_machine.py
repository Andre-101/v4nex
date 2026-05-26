from app.core.errors import AppError, ErrorCode
from app.domain.bridge_status import BridgeStatus


VALID_TRANSITIONS: frozenset[tuple[BridgeStatus, BridgeStatus]] = frozenset(
    {
        (BridgeStatus.DRAFT, BridgeStatus.VALIDATING),
        (BridgeStatus.VALIDATING, BridgeStatus.READY),
        (BridgeStatus.VALIDATING, BridgeStatus.ERROR),
        (BridgeStatus.READY, BridgeStatus.ACTIVE),
        (BridgeStatus.READY, BridgeStatus.ERROR),
        (BridgeStatus.ACTIVE, BridgeStatus.DISABLED),
        (BridgeStatus.ACTIVE, BridgeStatus.ERROR),
        (BridgeStatus.ERROR, BridgeStatus.VALIDATING),
        (BridgeStatus.DISABLED, BridgeStatus.VALIDATING),
    }
)


def can_transition(from_status: BridgeStatus, to_status: BridgeStatus) -> bool:
    return (from_status, to_status) in VALID_TRANSITIONS


def assert_valid_transition(
    from_status: BridgeStatus,
    to_status: BridgeStatus,
) -> None:
    if can_transition(from_status, to_status):
        return

    raise AppError(
        code=ErrorCode.INVALID_STATE_TRANSITION,
        message=f"Invalid bridge state transition: {from_status} -> {to_status}.",
        details={
            "from_status": from_status.value,
            "to_status": to_status.value,
        },
    )
