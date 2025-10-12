from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULT_CONFIG_PATH = Path("~/.remoclip.yaml").expanduser()

DEFAULT_CONFIG: Dict[str, Any] = {
    "server": "127.0.0.1",
    "port": 35612,
    "db": "~/.remoclip.sqlite",
}


@dataclass(frozen=True)
class RemoClipConfig:
    server: str
    port: int
    db: Path

    @property
    def db_path(self) -> Path:
        return self.db.expanduser()


def load_config(path: Optional[str] = None) -> RemoClipConfig:
    """Load configuration from YAML file, filling in defaults."""
    config_path = Path(path).expanduser() if path else DEFAULT_CONFIG_PATH
    data: Dict[str, Any] = DEFAULT_CONFIG.copy()

    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text()) or {}
        for key in DEFAULT_CONFIG:
            if key in loaded and loaded[key] is not None:
                data[key] = loaded[key]

    return RemoClipConfig(
        server=str(data["server"]),
        port=int(data["port"]),
        db=Path(str(data["db"])),
    )
