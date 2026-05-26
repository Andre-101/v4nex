import socket

from app.services import tcp_validator


class FakeSocket:
    def __init__(self, connect_error=None) -> None:
        self.connect_error = connect_error
        self.closed = False
        self.timeout = None

    def settimeout(self, timeout) -> None:
        self.timeout = timeout

    def connect(self, sockaddr) -> None:
        if self.connect_error is not None:
            raise self.connect_error

    def close(self) -> None:
        self.closed = True


def patch_getaddrinfo(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, family, type: [
            (socket.AF_INET6, socket.SOCK_STREAM, 0, "", ("::1", port, 0, 0))
        ],
    )


def test_tcp_validator_ok_closes_socket(monkeypatch) -> None:
    patch_getaddrinfo(monkeypatch)
    fake_socket = FakeSocket()
    monkeypatch.setattr(socket, "socket", lambda family, socktype, proto: fake_socket)

    result = tcp_validator.validate_tcp_connectivity("::1", 80)

    assert result.ok is True
    assert result.error_code == tcp_validator.TCP_OK
    assert result.latency_ms is not None
    assert fake_socket.closed is True


def test_tcp_validator_timeout(monkeypatch) -> None:
    patch_getaddrinfo(monkeypatch)
    fake_socket = FakeSocket(connect_error=TimeoutError())
    monkeypatch.setattr(socket, "socket", lambda family, socktype, proto: fake_socket)

    result = tcp_validator.validate_tcp_connectivity("::1", 80)

    assert result.ok is False
    assert result.error_code == tcp_validator.TCP_TIMEOUT
    assert fake_socket.closed is True


def test_tcp_validator_refused(monkeypatch) -> None:
    patch_getaddrinfo(monkeypatch)
    fake_socket = FakeSocket(connect_error=ConnectionRefusedError())
    monkeypatch.setattr(socket, "socket", lambda family, socktype, proto: fake_socket)

    result = tcp_validator.validate_tcp_connectivity("::1", 80)

    assert result.ok is False
    assert result.error_code == tcp_validator.TCP_CONNECTION_REFUSED
    assert fake_socket.closed is True
