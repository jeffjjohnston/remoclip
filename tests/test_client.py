from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import remoclip.config as config_module

from remoclip.client_cli import RemoClipClient

RemoClipConfig = config_module.RemoClipConfig
SECURITY_TOKEN_HEADER = getattr(config_module, "SECURITY_TOKEN_HEADER", None)
assert SECURITY_TOKEN_HEADER is not None


class DummyResponse:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload


def test_client_includes_security_token(monkeypatch):
    captured: Dict[str, Any] = {}

    def fake_post(url: str, json: Dict[str, Any], headers=None, timeout: float = 0):
        captured["post"] = headers
        return DummyResponse({"status": "ok"})

    def fake_get(url: str, json: Dict[str, Any], headers=None, timeout: float = 0):
        key = "paste" if url.endswith("/paste") else "history"
        captured[key] = {"headers": headers, "json": json}
        payload = {"content": "value"} if key == "paste" else {"history": []}
        return DummyResponse(payload)

    monkeypatch.setattr("remoclip.client_cli.requests.post", fake_post)
    monkeypatch.setattr("remoclip.client_cli.requests.get", fake_get)

    config = RemoClipConfig(
        server="example.com",
        port=1234,
        db=Path("/tmp/db.sqlite"),
        security_token="secret",
    )
    client = RemoClipClient(config)

    client.copy("hello")
    assert captured["post"][SECURITY_TOKEN_HEADER] == "secret"

    client.paste()
    assert captured["paste"]["headers"][SECURITY_TOKEN_HEADER] == "secret"
    assert SECURITY_TOKEN_HEADER not in captured["paste"]["json"]

    client.history()
    assert captured["history"]["headers"][SECURITY_TOKEN_HEADER] == "secret"
    assert "id" not in captured["history"]["json"]

    client.history(event_id=5)
    assert captured["history"]["headers"][SECURITY_TOKEN_HEADER] == "secret"
    assert captured["history"]["json"]["id"] == 5


def test_client_without_token_uses_empty_headers(monkeypatch):
    captured: Dict[str, Dict[str, str]] = {}

    def fake_post(url: str, json: Dict[str, Any], headers=None, timeout: float = 0):
        captured["post"] = headers
        return DummyResponse({"status": "ok"})

    monkeypatch.setattr("remoclip.client_cli.requests.post", fake_post)

    config = RemoClipConfig(
        server="example.com",
        port=1234,
        db=Path("/tmp/db.sqlite"),
    )
    client = RemoClipClient(config)

    client.copy("hello")
    assert captured["post"] == {}
