import pytest

from app.core.errors import AppError, ErrorCode
from app.domain.validators import validate_ipv6, validate_port, validate_subdomain


def test_valid_subdomain_passes() -> None:
    assert validate_subdomain("demo-123") == "demo-123"


def test_uppercase_subdomain_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_subdomain("Demo")

    assert exc_info.value.code == ErrorCode.INVALID_SUBDOMAIN


def test_subdomain_with_initial_hyphen_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_subdomain("-demo")

    assert exc_info.value.code == ErrorCode.INVALID_SUBDOMAIN


def test_reserved_subdomain_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_subdomain("admin")

    assert exc_info.value.code == ErrorCode.RESERVED_SUBDOMAIN


def test_valid_ipv6_passes() -> None:
    assert validate_ipv6("2606:4700:4700::1111") == "2606:4700:4700::1111"


def test_empty_ipv6_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_ipv6("")

    assert exc_info.value.code == ErrorCode.INVALID_IPV6


def test_documentation_ipv6_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_ipv6("2001:db8::1")

    assert exc_info.value.code == ErrorCode.INVALID_IPV6


def test_port_80_passes() -> None:
    assert validate_port(80) == 80


def test_port_8080_passes() -> None:
    assert validate_port(8080) == 8080


def test_port_22_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_port(22)

    assert exc_info.value.code == ErrorCode.INVALID_PORT
    assert exc_info.value.details == {"target_port": 22, "allowed_ports": [80, 8080]}


def test_port_2019_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_port(2019)

    assert exc_info.value.code == ErrorCode.INVALID_PORT


def test_port_5432_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_port(5432)

    assert exc_info.value.code == ErrorCode.INVALID_PORT


def test_port_65536_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_port(65536)

    assert exc_info.value.code == ErrorCode.INVALID_PORT


def test_port_0_fails() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_port(0)

    assert exc_info.value.code == ErrorCode.INVALID_PORT
