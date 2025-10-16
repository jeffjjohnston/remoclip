from __future__ import annotations

import io
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import remoclip.config as config_module
import remoclip.client_cli as client_cli

from remoclip.client_cli import RemoClipClient

ClientConfig = config_module.ClientConfig
RemoClipConfig = config_module.RemoClipConfig
ServerConfig = config_module.ServerConfig
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
        self.delete_calls: list[dict[str, Any]] = []

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

    def delete(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float = 0,
    ) -> DummyResponse:
        payload = {"url": url, "json": json, "headers": headers or {}, "timeout": timeout}
        self.delete_calls.append(payload)
        return DummyResponse({"status": "deleted"})


def test_client_includes_security_token(monkeypatch):
    session = RecordingSession()
    monkeypatch.setattr("remoclip.client_cli.RequestsSession", lambda: session)

    config = RemoClipConfig(
        security_token="secret",
        server=ServerConfig(
            host="example.com",
            port=1234,
            db=Path("/tmp/db.sqlite"),
        ),
        client=ClientConfig(url="http://example.com:1234"),
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

    client.delete_history(8)
    assert session.delete_calls[-1]["headers"][SECURITY_TOKEN_HEADER] == "secret"
    assert session.delete_calls[-1]["json"]["id"] == 8


def test_client_without_token_uses_empty_headers(monkeypatch):
    session = RecordingSession()
    monkeypatch.setattr("remoclip.client_cli.RequestsSession", lambda: session)

    config = RemoClipConfig(
        security_token=None,
        server=ServerConfig(
            host="example.com",
            port=1234,
            db=Path("/tmp/db.sqlite"),
        ),
        client=ClientConfig(url="http://example.com:1234"),
    )
    client = RemoClipClient(config)

    client.copy("hello")
    assert session.post_calls[-1]["headers"] == {}


def test_client_uses_configured_url(monkeypatch):
    session = RecordingSession()
    monkeypatch.setattr("remoclip.client_cli.RequestsSession", lambda: session)

    config = RemoClipConfig(
        security_token=None,
        server=ServerConfig(
            host="secure.example.com",
            port=8443,
            db=Path("/tmp/db.sqlite"),
        ),
        client=ClientConfig(url="https://secure.example.com:8443"),
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
        security_token=None,
        server=ServerConfig(
            host="example.com",
            port=1234,
            db=Path("/tmp/db.sqlite"),
        ),
        client=ClientConfig(
            url="http://example.com:1234",
            socket=socket_path,
        ),
    )

    client = RemoClipClient(config)

    assert client.base_url == f"http+unix://{quote(str(socket_path), safe='')}"
    assert client._session is session
    assert captured_path["path"] == socket_path


def test_copy_command_preserves_newlines_by_default(monkeypatch, capsys):
    recorded: dict[str, Any] = {}

    monkeypatch.setattr(client_cli, "load_config", lambda path: object())

    class DummyClient:
        def __init__(self, config: Any) -> None:
            recorded["config"] = config

        def copy(self, content: str, timeout: float = 5.0) -> None:
            recorded["content"] = content

    monkeypatch.setattr(client_cli, "RemoClipClient", DummyClient)
    monkeypatch.setattr(client_cli.sys, "stdin", io.StringIO("hello\n\n"))
    monkeypatch.setattr(client_cli.sys, "argv", ["remoclip", "copy"])

    client_cli.main()

    captured = capsys.readouterr()
    assert recorded["content"] == "hello\n\n"
    assert captured.out == "hello\n\n"
    assert captured.err == ""


def test_copy_command_strips_newlines_when_requested(monkeypatch, capsys):
    recorded: dict[str, Any] = {}

    monkeypatch.setattr(client_cli, "load_config", lambda path: object())

    class DummyClient:
        def __init__(self, config: Any) -> None:
            recorded["config"] = config

        def copy(self, content: str, timeout: float = 5.0) -> None:
            recorded["content"] = content

    monkeypatch.setattr(client_cli, "RemoClipClient", DummyClient)
    monkeypatch.setattr(client_cli.sys, "stdin", io.StringIO("hello\n\n"))
    monkeypatch.setattr(client_cli.sys, "argv", ["remoclip", "copy", "--strip"])

    client_cli.main()

    captured = capsys.readouterr()
    assert recorded["content"] == "hello"
    assert captured.out == "hello"
    assert captured.err == ""


def test_strip_option_rejected_for_non_copy_commands(monkeypatch, capsys):
    monkeypatch.setattr(client_cli, "load_config", lambda path: object())

    class DummyClient:
        def __init__(self, config: Any) -> None:
            self.config = config

    monkeypatch.setattr(client_cli, "RemoClipClient", DummyClient)
    monkeypatch.setattr(client_cli.sys, "argv", ["remoclip", "paste", "--strip"])

    with pytest.raises(SystemExit) as excinfo:
        client_cli.main()

    assert excinfo.value.code == 2
    captured = capsys.readouterr()
    assert "--strip can only be used with the copy command" in captured.err
