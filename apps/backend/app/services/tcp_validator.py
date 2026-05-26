from dataclasses import dataclass
import socket
import time


TCP_OK = "TCP_OK"
TCP_TIMEOUT = "TCP_TIMEOUT"
TCP_CONNECTION_REFUSED = "TCP_CONNECTION_REFUSED"
TCP_UNREACHABLE = "TCP_UNREACHABLE"
TCP_DNS_ERROR = "TCP_DNS_ERROR"
TCP_UNKNOWN_ERROR = "TCP_UNKNOWN_ERROR"


@dataclass(frozen=True)
class TcpValidationResult:
    ok: bool
    error_code: str | None
    message: str
    latency_ms: int | None


def validate_tcp_connectivity(
    host: str,
    port: int,
    timeout_seconds: float = 3.0,
) -> TcpValidationResult:
    started_at = time.perf_counter()
    sock: socket.socket | None = None

    try:
        address_info = socket.getaddrinfo(
            host,
            port,
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
        )
        family, socktype, proto, _, sockaddr = address_info[0]

        sock = socket.socket(family, socktype, proto)
        sock.settimeout(timeout_seconds)
        sock.connect(sockaddr)

        return TcpValidationResult(
            ok=True,
            error_code=TCP_OK,
            message="TCP connectivity check succeeded.",
            latency_ms=_elapsed_ms(started_at),
        )
    except socket.gaierror:
        return TcpValidationResult(
            ok=False,
            error_code=TCP_DNS_ERROR,
            message="Could not resolve TCP target.",
            latency_ms=_elapsed_ms(started_at),
        )
    except TimeoutError:
        return TcpValidationResult(
            ok=False,
            error_code=TCP_TIMEOUT,
            message="TCP connectivity check timed out.",
            latency_ms=_elapsed_ms(started_at),
        )
    except ConnectionRefusedError:
        return TcpValidationResult(
            ok=False,
            error_code=TCP_CONNECTION_REFUSED,
            message="TCP connection was refused.",
            latency_ms=_elapsed_ms(started_at),
        )
    except OSError as exc:
        error_code = TCP_UNREACHABLE if _is_unreachable(exc) else TCP_UNKNOWN_ERROR
        return TcpValidationResult(
            ok=False,
            error_code=error_code,
            message=str(exc) or "TCP connectivity check failed.",
            latency_ms=_elapsed_ms(started_at),
        )
    finally:
        if sock is not None:
            sock.close()


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((time.perf_counter() - started_at) * 1000))


def _is_unreachable(exc: OSError) -> bool:
    unreachable_errnos = {
        10051,
        10064,
        101,
        113,
        118,
    }
    return exc.errno in unreachable_errnos
