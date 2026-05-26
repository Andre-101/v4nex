import ipaddress
import re

from app.core.config import settings
from app.core.errors import AppError, ErrorCode


RESERVED_SUBDOMAINS: frozenset[str] = frozenset(
    {
        "www",
        "api",
        "admin",
        "panel",
        "login",
        "dashboard",
        "status",
        "mail",
        "smtp",
        "ftp",
        "ssh",
        "root",
        "support",
        "billing",
        "docs",
        "dev",
        "test",
        "_v4nex",
    }
)

SUBDOMAIN_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])$")
DOCUMENTATION_IPV6_NETWORK = ipaddress.ip_network("2001:db8::/32")
DEFAULT_ALLOWED_TARGET_PORTS = frozenset({80, 8080})


def validate_subdomain(subdomain: str) -> str:
    if subdomain in RESERVED_SUBDOMAINS:
        raise AppError(
            code=ErrorCode.RESERVED_SUBDOMAIN,
            message="This subdomain is reserved.",
            details={"subdomain": subdomain},
        )

    if not SUBDOMAIN_PATTERN.fullmatch(subdomain):
        raise AppError(
            code=ErrorCode.INVALID_SUBDOMAIN,
            message=(
                "Subdomain must be 3 to 40 characters and use only lowercase "
                "letters, numbers, and hyphens. It cannot start or end with a hyphen."
            ),
            details={"subdomain": subdomain},
        )

    return subdomain


def validate_ipv6(target_ipv6: str) -> str:
    if not target_ipv6:
        raise AppError(
            code=ErrorCode.INVALID_IPV6,
            message="IPv6 address cannot be empty.",
        )

    try:
        ip = ipaddress.ip_address(target_ipv6)
    except ValueError as exc:
        raise AppError(
            code=ErrorCode.INVALID_IPV6,
            message="Invalid IPv6 address.",
            details={"target_ipv6": target_ipv6},
        ) from exc

    if ip.version != 6:
        raise AppError(
            code=ErrorCode.INVALID_IPV6,
            message="Target address must be IPv6.",
            details={"target_ipv6": target_ipv6},
        )

    if ip in DOCUMENTATION_IPV6_NETWORK:
        raise AppError(
            code=ErrorCode.INVALID_IPV6,
            message="Documentation IPv6 ranges are not accepted for the MVP.",
            details={"target_ipv6": target_ipv6},
        )

    return target_ipv6


def validate_port(target_port: int) -> int:
    allowed_ports = frozenset(settings.allowed_target_ports) or DEFAULT_ALLOWED_TARGET_PORTS
    details = {
        "target_port": target_port,
        "allowed_ports": sorted(allowed_ports),
    }

    if target_port < 1 or target_port > 65535:
        raise AppError(
            code=ErrorCode.INVALID_PORT,
            message=(
                "Target port is not allowed. "
                f"Allowed ports: {', '.join(str(port) for port in sorted(allowed_ports))}."
            ),
            details=details,
        )

    if target_port not in allowed_ports:
        raise AppError(
            code=ErrorCode.INVALID_PORT,
            message=(
                "Target port is not allowed. "
                f"Allowed ports: {', '.join(str(port) for port in sorted(allowed_ports))}."
            ),
            details=details,
        )

    return target_port
