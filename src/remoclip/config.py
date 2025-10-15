from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml

DEFAULT_CONFIG_PATH = Path("~/.remoclip.yaml").expanduser()

SECURITY_TOKEN_HEADER = "X-RemoClip-Token"


ClipboardBackendName = Literal["system", "private"]


DEFAULT_CONFIG: dict[str, Any] = {
    "security_token": None,
    "server": {
        "host": "127.0.0.1",
        "port": 35612,
        "db": "~/.remoclip.sqlite",
        "clipboard_backend": "system",
    },
    "client": {
        "url": "http://127.0.0.1:35612",
        "socket": None,
    },
}


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    db: Path
    clipboard_backend: ClipboardBackendName = "system"

    @property
    def db_path(self) -> Path:
        return self.db.expanduser()


@dataclass(frozen=True)
class ClientConfig:
    url: str
    socket: Path | None = None

    @property
    def socket_path(self) -> Path | None:
        if self.socket is None:
            return None
        return self.socket.expanduser()


@dataclass(frozen=True)
class RemoClipConfig:
    security_token: str | None
    server: ServerConfig
    client: ClientConfig


def load_config(path: str | None = None) -> RemoClipConfig:
    """Load configuration from YAML file, filling in defaults."""
    config_path = Path(path).expanduser() if path else DEFAULT_CONFIG_PATH
    data = _merge(DEFAULT_CONFIG, _load_yaml(config_path))

    server_config = data["server"]
    client_config = data["client"]

    server = ServerConfig(
        host=str(server_config["host"]),
        port=int(server_config["port"]),
        db=Path(str(server_config["db"])),
        clipboard_backend=_normalize_clipboard_backend(
            server_config.get("clipboard_backend")
        ),
    )

    socket_value = client_config.get("socket")
    if socket_value in (None, ""):
        socket_path = None
    else:
        socket_path = Path(str(socket_value))

    client = ClientConfig(
        url=str(client_config["url"]),
        socket=socket_path,
    )

    security_token = data.get("security_token")
    if security_token is not None:
        security_token = str(security_token)

    return RemoClipConfig(
        security_token=security_token,
        server=server,
        client=client,
    )


def _normalize_clipboard_backend(value: Any) -> ClipboardBackendName:
    backend = str(value or "system").lower()
    if backend not in ("system", "private"):
        raise ValueError(
            "clipboard_backend must be either 'system' or 'private'"
        )
    return backend  # type: ignore[return-value]


def _merge(defaults: Mapping[str, Any], overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    if overrides is None:
        return {key: _clone(value) for key, value in defaults.items()}

    merged: dict[str, Any] = {}
    for key, default_value in defaults.items():
        if key not in overrides or overrides[key] is None:
            merged[key] = _clone(default_value)
            continue
        override_value = overrides[key]
        if isinstance(default_value, Mapping) and isinstance(override_value, Mapping):
            merged[key] = _merge(default_value, override_value)
        else:
            merged[key] = override_value
    for key, value in overrides.items():
        if key not in merged and value is not None:
            merged[key] = value
    return merged


def _clone(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _clone(v) for k, v in value.items()}
    return value


def _load_yaml(path: Path) -> Mapping[str, Any] | None:
    if not path.exists():
        return None
    loaded = yaml.safe_load(path.read_text())
    if loaded is None:
        return None
    if not isinstance(loaded, Mapping):
        raise TypeError("Configuration file must contain a mapping at the top level")
    return loaded
