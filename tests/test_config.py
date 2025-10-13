import textwrap
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from remoclip import config


def test_load_config_uses_defaults_when_file_missing(tmp_path, monkeypatch):
    fake_default = tmp_path / "config.yaml"
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", fake_default)

    loaded = config.load_config()

    assert loaded.server == config.DEFAULT_CONFIG["server"]
    assert loaded.port == config.DEFAULT_CONFIG["port"]
    assert loaded.db_path == Path(config.DEFAULT_CONFIG["db"]).expanduser()
    assert loaded.security_token is None
    assert loaded.socket is None


def test_load_config_overrides_defaults(tmp_path):
    config_file = tmp_path / "custom.yaml"
    config_file.write_text(
        textwrap.dedent(
            """
            server: example.com
            port: 4000
            db: ~/custom.sqlite
            security_token: secret
            socket: /tmp/remoclip.sock
            """
        ).strip()
    )

    loaded = config.load_config(str(config_file))

    assert loaded.server == "example.com"
    assert loaded.port == 4000
    assert loaded.db_path == Path("~/custom.sqlite").expanduser()
    assert loaded.security_token == "secret"
    assert loaded.socket_path == Path("/tmp/remoclip.sock")
