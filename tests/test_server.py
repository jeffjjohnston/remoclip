from __future__ import annotations

from typing import Dict

import pytest

from remoclip.config import RemoClipConfig
from remoclip.server_cli import create_app


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
