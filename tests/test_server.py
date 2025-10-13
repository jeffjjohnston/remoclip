from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import remoclip.config as config_module
from remoclip.server_cli import create_app

RemoClipConfig = config_module.RemoClipConfig
SECURITY_TOKEN_HEADER = getattr(config_module, "SECURITY_TOKEN_HEADER", None)
assert SECURITY_TOKEN_HEADER is not None


@pytest.fixture
def in_memory_clipboard(monkeypatch):
    clipboard: Dict[str, str] = {"value": ""}

    def fake_copy(value: str) -> None:
        clipboard["value"] = value

    def fake_paste() -> str:
        return clipboard["value"]

    monkeypatch.setattr("remoclip.server_cli.pyperclip.copy", fake_copy)
    monkeypatch.setattr("remoclip.server_cli.pyperclip.paste", fake_paste)

    return clipboard


@pytest.fixture
def app(tmp_path, in_memory_clipboard):
    config = RemoClipConfig(server="127.0.0.1", port=5000, db=tmp_path / "db.sqlite")
    application = create_app(config)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def secure_client(tmp_path, in_memory_clipboard):
    config = RemoClipConfig(
        server="127.0.0.1",
        port=5000,
        db=tmp_path / "db.sqlite",
        security_token="shh",
    )
    application = create_app(config)
    application.config.update(TESTING=True)
    return application.test_client()


def test_copy_paste_and_history_flow(client, in_memory_clipboard):
    response = client.post("/copy", json={"hostname": "test", "content": "hello"})
    assert response.status_code == 200
    assert in_memory_clipboard["value"] == "hello"

    response = client.get("/paste", json={"hostname": "test"})
    assert response.status_code == 200
    assert response.get_json()["content"] == "hello"

    response = client.get("/history", json={"hostname": "test"})
    assert response.status_code == 200
    history = response.get_json()["history"]
    actions = [item["action"] for item in history]
    assert actions == ["paste", "copy"]


def test_history_limit_parameter(client):
    client.post("/copy", json={"hostname": "test", "content": "hello"})
    client.post("/copy", json={"hostname": "test", "content": "world"})

    response = client.get("/history", json={"hostname": "test", "limit": 1})
    assert response.status_code == 200
    history = response.get_json()["history"]
    assert len(history) == 1
    assert history[0]["content"] == "world"


def test_history_specific_id(client):
    client.post("/copy", json={"hostname": "test", "content": "hello"})
    client.post("/copy", json={"hostname": "test", "content": "world"})

    response = client.get("/history", json={"hostname": "test"})
    assert response.status_code == 200
    events = response.get_json()["history"]
    assert len(events) >= 2
    # Second element corresponds to the first copy action ("hello")
    target = events[1]
    assert target["content"] == "hello"

    response = client.get(
        "/history", json={"hostname": "test", "id": target["id"]}
    )
    assert response.status_code == 200
    history = response.get_json()["history"]
    assert len(history) == 1
    assert history[0]["id"] == target["id"]
    assert history[0]["content"] == "hello"


def test_history_specific_id_not_found(client):
    response = client.get("/history", json={"hostname": "test", "id": 999})
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"] == "history entry not found"


def test_security_token_required(secure_client):
    response = secure_client.post(
        "/copy",
        json={"hostname": "test", "content": "secret"},
    )
    assert response.status_code == 401

    response = secure_client.post(
        "/copy",
        json={"hostname": "test", "content": "secret"},
        headers={SECURITY_TOKEN_HEADER: "shh"},
    )
    assert response.status_code == 200
