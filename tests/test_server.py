from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import remoclip.config as config_module
from remoclip.clipboard import PrivateClipboardBackend
from remoclip.server_cli import create_app

RemoClipConfig = config_module.RemoClipConfig
SECURITY_TOKEN_HEADER = getattr(config_module, "SECURITY_TOKEN_HEADER", None)
assert SECURITY_TOKEN_HEADER is not None


@pytest.fixture
def app(tmp_path):
    config = RemoClipConfig(
        server="127.0.0.1",
        port=5000,
        db=tmp_path / "db.sqlite",
        clipboard_backend="private",
    )
    application = create_app(config)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def clipboard_backend(app):
    backend = app.config.get("CLIPBOARD_BACKEND")
    assert isinstance(backend, PrivateClipboardBackend)
    return backend


@pytest.fixture
def secure_client(tmp_path):
    config = RemoClipConfig(
        server="127.0.0.1",
        port=5000,
        db=tmp_path / "db.sqlite",
        security_token="shh",
        clipboard_backend="private",
    )
    application = create_app(config)
    application.config.update(TESTING=True)
    return application.test_client()


def test_copy_paste_and_history_flow(client, clipboard_backend):
    response = client.post("/copy", json={"hostname": "test", "content": "hello"})
    assert response.status_code == 200
    assert clipboard_backend.paste() == "hello"

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


def test_history_excludes_history_events(client):
    client.post("/copy", json={"hostname": "test", "content": "hello"})
    client.get("/history", json={"hostname": "test"})

    response = client.get("/history", json={"hostname": "test"})
    assert response.status_code == 200
    history = response.get_json()["history"]
    assert history[0]["action"] == "copy"


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


def test_paste_specific_id(client, clipboard_backend):
    client.post("/copy", json={"hostname": "test", "content": "hello"})
    client.post("/copy", json={"hostname": "test", "content": "world"})

    response = client.get("/history", json={"hostname": "test"})
    events = response.get_json()["history"]
    target = events[1]

    clipboard_backend.copy("should not be returned")

    response = client.get(
        "/paste", json={"hostname": "test", "id": target["id"]}
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["content"] == target["content"] == "hello"


def test_paste_specific_id_not_found(client):
    response = client.get("/paste", json={"hostname": "test", "id": 12345})
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"] == "history entry not found"


def test_paste_specific_id_invalid(client):
    response = client.get("/paste", json={"hostname": "test", "id": -1})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "id must be positive"

    response = client.get("/paste", json={"hostname": "test", "id": "abc"})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "id must be an integer"


def test_private_backend_seeds_from_history(tmp_path):
    config = RemoClipConfig(
        server="127.0.0.1",
        port=5000,
        db=tmp_path / "db.sqlite",
        clipboard_backend="private",
    )
    first_app = create_app(config)
    first_app.config.update(TESTING=True)
    first_client = first_app.test_client()
    first_client.post("/copy", json={"hostname": "seed", "content": "persisted"})

    second_app = create_app(config)
    backend = second_app.config.get("CLIPBOARD_BACKEND")
    assert isinstance(backend, PrivateClipboardBackend)
    assert backend.paste() == "persisted"


def test_system_backend_falls_back_when_unavailable(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr("remoclip.clipboard.pyperclip", None, raising=False)
    caplog.set_level(logging.WARNING)

    config = RemoClipConfig(
        server="127.0.0.1",
        port=5000,
        db=tmp_path / "db.sqlite",
        clipboard_backend="system",
    )
    app = create_app(config)

    backend = app.config.get("CLIPBOARD_BACKEND")
    assert isinstance(backend, PrivateClipboardBackend)
    assert "falling back to private backend" in caplog.text


def test_history_invalid_parameters(client):
    response = client.get("/history", json={"hostname": "test", "limit": 0})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "limit must be positive"

    response = client.get("/history", json={"hostname": "test", "id": "oops"})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "id must be an integer"
