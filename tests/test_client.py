from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import quote
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import remoclip.config as config_module

from remoclip.client_cli import RemoClipClient

RemoClipConfig = config_module.RemoClipConfig
SECURITY_TOKEN_HEADER = getattr(config_module, "SECURITY_TOKEN_HEADER", None)
assert SECURITY_TOKEN_HEADER is not None


class DummyResponse:
    def __init__(self, payload: dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class RecordingSession:
    def __init__(self) -> None:
        self.post_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float = 0,
    ) -> DummyResponse:
        payload = {"url": url, "json": json, "headers": headers or {}, "timeout": timeout}
        self.post_calls.append(payload)
        return DummyResponse({"status": "ok"})

    def get(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float = 0,
    ) -> DummyResponse:
        payload = {"url": url, "json": json, "headers": headers or {}, "timeout": timeout}
        self.get_calls.append(payload)
        if url.endswith("/paste"):
            return DummyResponse({"content": "value"})
        return DummyResponse({"history": []})


def test_client_includes_security_token(monkeypatch):
    session = RecordingSession()
    monkeypatch.setattr("remoclip.client_cli.RequestsSession", lambda: session)

    config = RemoClipConfig(
        server="example.com",
        port=1234,
        db=Path("/tmp/db.sqlite"),
        security_token="secret",
    )
    client = RemoClipClient(config)

    client.copy("hello")
    assert session.post_calls[-1]["headers"][SECURITY_TOKEN_HEADER] == "secret"

    client.paste()
    assert session.get_calls[-1]["headers"][SECURITY_TOKEN_HEADER] == "secret"
    assert SECURITY_TOKEN_HEADER not in session.get_calls[-1]["json"]

    client.paste(event_id=7)
    assert session.get_calls[-1]["headers"][SECURITY_TOKEN_HEADER] == "secret"
    assert session.get_calls[-1]["json"]["id"] == 7

    client.history()
    assert session.get_calls[-1]["headers"][SECURITY_TOKEN_HEADER] == "secret"
    assert "id" not in session.get_calls[-1]["json"]

    client.history(event_id=5)
    assert session.get_calls[-1]["headers"][SECURITY_TOKEN_HEADER] == "secret"
    assert session.get_calls[-1]["json"]["id"] == 5


def test_client_without_token_uses_empty_headers(monkeypatch):
    session = RecordingSession()
    monkeypatch.setattr("remoclip.client_cli.RequestsSession", lambda: session)

    config = RemoClipConfig(
        server="example.com",
        port=1234,
        db=Path("/tmp/db.sqlite"),
    )
    client = RemoClipClient(config)

    client.copy("hello")
    assert session.post_calls[-1]["headers"] == {}


def test_client_uses_https_when_configured(monkeypatch):
    session = RecordingSession()
    monkeypatch.setattr("remoclip.client_cli.RequestsSession", lambda: session)

    config = RemoClipConfig(
        server="secure.example.com",
        port=8443,
        db=Path("/tmp/db.sqlite"),
        use_https=True,
    )

    client = RemoClipClient(config)

    client.paste()

    assert client.base_url == "https://secure.example.com:8443"
    assert session.get_calls[-1]["url"] == "https://secure.example.com:8443/paste"


def test_client_prefers_unix_socket_when_configured(monkeypatch, tmp_path):
    socket_path = tmp_path / "remoclip.sock"
    session = RecordingSession()

    captured_path: dict[str, Path] = {}

    def fake_unix_session(path: Path) -> RecordingSession:
        captured_path["path"] = path
        return session

    monkeypatch.setattr("remoclip.client_cli.UnixSocketSession", fake_unix_session)
    monkeypatch.setattr(
        "remoclip.client_cli.RequestsSession",
        lambda: (_ for _ in ()).throw(AssertionError("HTTP session should not be created")),
    )

    config = RemoClipConfig(
        server="example.com",
        port=1234,
        db=Path("/tmp/db.sqlite"),
        socket=socket_path,
    )

    client = RemoClipClient(config)

    assert client.base_url == f"http+unix://{quote(str(socket_path), safe='')}"
    assert client._session is session
    assert captured_path["path"] == socket_path
