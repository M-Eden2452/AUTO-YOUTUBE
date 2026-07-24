from __future__ import annotations

import os
import socket
from typing import Any


ALLOW_LIVE_ENV_VARS = ("AI_YOUTUBE_ALLOW_LIVE_TESTS", "AI_YOUTUBE_RUN_LIVE_TESTS")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}

_installed = False
_original_connect = socket.socket.connect
_original_create_connection = socket.create_connection
_original_getaddrinfo = socket.getaddrinfo
blocked_attempts: list[str] = []


class NetworkBlockedError(OSError):
    """Raised when an ordinary test attempts external network access."""


def live_tests_enabled() -> bool:
    return any(str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"} for name in ALLOW_LIVE_ENV_VARS)


def install_network_guard() -> None:
    global _installed
    if _installed or live_tests_enabled():
        return
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
    socket.create_connection = _guarded_create_connection  # type: ignore[assignment]
    socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]
    _installed = True


def uninstall_network_guard() -> None:
    global _installed
    socket.socket.connect = _original_connect  # type: ignore[method-assign]
    socket.create_connection = _original_create_connection  # type: ignore[assignment]
    socket.getaddrinfo = _original_getaddrinfo  # type: ignore[assignment]
    _installed = False


def _guarded_connect(self: socket.socket, address: Any) -> Any:
    host = _host_from_address(address)
    if _is_local_host(host):
        return _original_connect(self, address)
    _block(host, address)


def _guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> socket.socket:
    host = _host_from_address(address)
    if _is_local_host(host):
        return _original_create_connection(address, *args, **kwargs)
    _block(host, address)


def _guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
    if _is_local_host(str(host or "")):
        return _original_getaddrinfo(host, *args, **kwargs)
    _block(str(host or ""), host)


def _host_from_address(address: Any) -> str:
    if isinstance(address, tuple) and address:
        return str(address[0])
    return str(address or "")


def _is_local_host(host: str) -> bool:
    host = str(host or "").strip().lower().strip("[]")
    return host in LOCAL_HOSTS or host.startswith("127.")


def _block(host: str, address: Any) -> None:
    message = f"External network access is blocked during ordinary tests: {address!r}"
    blocked_attempts.append(str(host or address))
    raise NetworkBlockedError(message)

