from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("~/.remoclip.yaml").expanduser()

SECURITY_TOKEN_HEADER = "X-RemoClip-Token"


DEFAULT_CONFIG: dict[str, Any] = {
    "server": "127.0.0.1",
    "port": 35612,
    "db": "~/.remoclip.sqlite",
    "security_token": None,
    "socket": None,
}


@dataclass(frozen=True)
class RemoClipConfig:
    server: str
    port: int
    db: Path
    security_token: str | None = None
    socket: Path | None = None

    @property
    def db_path(self) -> Path:
        return self.db.expanduser()

    @property
    def socket_path(self) -> Path | None:
        if self.socket is None:
            return None
        return self.socket.expanduser()


def load_config(path: str | None = None) -> RemoClipConfig:
    """Load configuration from YAML file, filling in defaults."""
    config_path = Path(path).expanduser() if path else DEFAULT_CONFIG_PATH
    data: dict[str, Any] = DEFAULT_CONFIG.copy()

    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text()) or {}
        for key in DEFAULT_CONFIG:
            if key in loaded and loaded[key] is not None:
                data[key] = loaded[key]

    socket_value = data.get("socket")
    if socket_value in (None, ""):
        socket_path = None
    else:
        socket_path = Path(str(socket_value))

    return RemoClipConfig(
        server=str(data["server"]),
        port=int(data["port"]),
        db=Path(str(data["db"])),
        security_token=(
            str(data["security_token"])
            if data.get("security_token") is not None
            else None
        ),
        socket=socket_path,
    )
