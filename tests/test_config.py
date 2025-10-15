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

    assert loaded.security_token is None
    assert loaded.server.host == config.DEFAULT_CONFIG["server"]["host"]
    assert loaded.server.port == config.DEFAULT_CONFIG["server"]["port"]
    assert loaded.server.db_path == Path(
        config.DEFAULT_CONFIG["server"]["db"]
    ).expanduser()
    assert loaded.server.clipboard_backend == config.DEFAULT_CONFIG["server"][
        "clipboard_backend"
    ]
    assert loaded.server.allow_deletions is False
    assert loaded.client.url == config.DEFAULT_CONFIG["client"]["url"]
    assert loaded.client.socket is None


def test_load_config_overrides_defaults(tmp_path):
    config_file = tmp_path / "custom.yaml"
    config_file.write_text(
        textwrap.dedent(
            """
            security_token: secret
            server:
                host: example.com
                port: 4000
                db: ~/custom.sqlite
                clipboard_backend: private
                allow_deletions: true
            client:
                url: https://example.com:4000
                socket: /tmp/remoclip.sock
            """
        ).strip()
    )

    loaded = config.load_config(str(config_file))

    assert loaded.security_token == "secret"
    assert loaded.server.host == "example.com"
    assert loaded.server.port == 4000
    assert loaded.server.db_path == Path("~/custom.sqlite").expanduser()
    assert loaded.server.clipboard_backend == "private"
    assert loaded.server.allow_deletions is True
    assert loaded.client.url == "https://example.com:4000"
    assert loaded.client.socket_path == Path("/tmp/remoclip.sock")
