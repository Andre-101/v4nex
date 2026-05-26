import pytest

from app.core.errors import AppError, ErrorCode
from app.domain.bridge_status import BridgeStatus
from app.domain.state_machine import assert_valid_transition, can_transition


VALID_TRANSITIONS = [
    (BridgeStatus.DRAFT, BridgeStatus.VALIDATING),
    (BridgeStatus.VALIDATING, BridgeStatus.READY),
    (BridgeStatus.VALIDATING, BridgeStatus.ERROR),
    (BridgeStatus.READY, BridgeStatus.ACTIVE),
    (BridgeStatus.READY, BridgeStatus.ERROR),
    (BridgeStatus.ACTIVE, BridgeStatus.DISABLED),
    (BridgeStatus.ACTIVE, BridgeStatus.ERROR),
    (BridgeStatus.ERROR, BridgeStatus.VALIDATING),
    (BridgeStatus.DISABLED, BridgeStatus.VALIDATING),
]


@pytest.mark.parametrize(("from_status", "to_status"), VALID_TRANSITIONS)
def test_valid_transitions_pass(
    from_status: BridgeStatus,
    to_status: BridgeStatus,
) -> None:
    assert can_transition(from_status, to_status) is True
    assert_valid_transition(from_status, to_status)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (BridgeStatus.DRAFT, BridgeStatus.ACTIVE),
        (BridgeStatus.ACTIVE, BridgeStatus.READY),
    ],
)
def test_invalid_transitions_fail(
    from_status: BridgeStatus,
    to_status: BridgeStatus,
) -> None:
    assert can_transition(from_status, to_status) is False

    with pytest.raises(AppError) as exc_info:
        assert_valid_transition(from_status, to_status)

    assert exc_info.value.code == ErrorCode.INVALID_STATE_TRANSITION
