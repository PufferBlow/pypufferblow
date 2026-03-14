from __future__ import annotations

__all__ = [
    "OptionsModel",
    "infer_scheme",
    "normalize_instance",
    "http_to_websocket_base",
]

from urllib.parse import urlparse

from pypufferblow.logging_utils import configure_sdk_logging


def _is_probably_local_host(host: str) -> bool:
    host = host.strip().lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    return (
        host.startswith("10.")
        or host.startswith("127.")
        or host.startswith("192.168.")
        or host.startswith("172.16.")
        or host.startswith("172.17.")
        or host.startswith("172.18.")
        or host.startswith("172.19.")
        or host.startswith("172.2")
        or host.startswith("172.30.")
        or host.startswith("172.31.")
    )


def infer_scheme(host: str, scheme: str | None = None) -> str:
    if scheme:
        return scheme.rstrip(":/").lower()
    return "http" if _is_probably_local_host(host) else "https"


def normalize_instance(
    *,
    instance: str | None = None,
    host: str | None = None,
    port: int | None = None,
    scheme: str | None = None,
) -> tuple[str, str, int | None, str]:
    raw_target = (instance or host or "127.0.0.1").strip()
    if not raw_target:
        raw_target = "127.0.0.1"

    has_explicit_scheme = "://" in raw_target
    parsed = urlparse(raw_target if has_explicit_scheme else f"//{raw_target}")
    normalized_host = parsed.hostname or raw_target.strip("/").split(":")[0]
    if parsed.port is not None:
        normalized_port = parsed.port
    elif has_explicit_scheme:
        normalized_port = None
    else:
        normalized_port = port
    normalized_scheme = infer_scheme(normalized_host, scheme or parsed.scheme or None)

    is_default_port = (
        normalized_port is None
        or (normalized_scheme == "http" and normalized_port == 80)
        or (normalized_scheme == "https" and normalized_port == 443)
    )
    port_suffix = "" if is_default_port else f":{normalized_port}"
    instance_url = f"{normalized_scheme}://{normalized_host}{port_suffix}"

    return normalized_scheme, normalized_host, normalized_port, instance_url


def http_to_websocket_base(instance_url: str) -> str:
    parsed = urlparse(instance_url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc or parsed.path
    return f"{ws_scheme}://{netloc}"


class OptionsModel:
    """
    Shared options model for SDK APIs.

    The preferred input for production and federated deployments is `instance`,
    for example `https://chat.example.org`. `host` and `port` remain supported
    for compatibility and local development.
    """

    def __init__(
        self,
        host: str | None = "127.0.0.1",
        port: int | None = 7575,
        username: str | None = None,
        password: str | None = None,
        scheme: str | None = None,
        instance: str | None = None,
        verbose: bool = False,
        log_level: str | int | None = None,
    ) -> None:
        """Initialize the instance."""
        resolved_scheme, resolved_host, resolved_port, instance_url = normalize_instance(
            instance=instance,
            host=host,
            port=port,
            scheme=scheme,
        )

        self.scheme = resolved_scheme
        self.host = resolved_host
        self.port = resolved_port
        self.username = username
        self.password = password
        self.instance = instance_url
        self.instance_url = instance_url
        self.api_base_url = instance_url
        self.ws_base_url = http_to_websocket_base(instance_url)
        self.verbose = verbose
        self.log_level = log_level or ("DEBUG" if verbose else None)

        if self.log_level is not None:
            configure_sdk_logging(self.log_level)
