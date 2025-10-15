from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import remoclip.config as config_module
from remoclip.clipboard import PrivateClipboardBackend
from remoclip.db import ClipboardEvent, session_scope
from remoclip.server_cli import create_app

ClientConfig = config_module.ClientConfig
RemoClipConfig = config_module.RemoClipConfig
ServerConfig = config_module.ServerConfig
SECURITY_TOKEN_HEADER = getattr(config_module, "SECURITY_TOKEN_HEADER", None)
assert SECURITY_TOKEN_HEADER is not None


def _make_config(
    tmp_path: Path,
    *,
    clipboard_backend: config_module.ClipboardBackendName = "private",
    security_token: str | None = None,
    allow_deletions: bool = False,
) -> RemoClipConfig:
    return RemoClipConfig(
        security_token=security_token,
        server=ServerConfig(
            host="127.0.0.1",
            port=5000,
            db=tmp_path / "db.sqlite",
            clipboard_backend=clipboard_backend,
            allow_deletions=allow_deletions,
        ),
        client=ClientConfig(url="http://127.0.0.1:5000"),
    )


@pytest.fixture
def app(tmp_path):
    config = _make_config(tmp_path)
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
    config = _make_config(tmp_path, security_token="shh")
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


def test_history_event_logs_request_metadata(client, app):
    client.post("/copy", json={"hostname": "test", "content": "hello"})
    client.post("/copy", json={"hostname": "test", "content": "world"})

    session_factory = app.config["SESSION_FACTORY"]

    def latest_history_event_content() -> str | None:
        with session_scope(session_factory) as session:
            entry = (
                session.query(ClipboardEvent)
                .filter(ClipboardEvent.action == "history")
                .order_by(ClipboardEvent.id.desc())
                .first()
            )
            if entry is None:
                return None
            return entry.content

    response = client.get("/history", json={"hostname": "test"})
    assert response.status_code == 200
    all_events = response.get_json()["history"]
    log_content = latest_history_event_content()
    assert log_content is not None
    payload = json.loads(log_content)
    assert payload["event_ids"] == [item["id"] for item in all_events]
    assert "limit" not in payload
    assert "id" not in payload

    response = client.get("/history", json={"hostname": "test", "limit": 1})
    assert response.status_code == 200
    limited_events = response.get_json()["history"]
    log_content = latest_history_event_content()
    assert log_content is not None
    payload = json.loads(log_content)
    assert payload["event_ids"] == [item["id"] for item in limited_events]
    assert payload["limit"] == 1
    assert "id" not in payload

    target_id = all_events[-1]["id"]
    response = client.get(
        "/history", json={"hostname": "test", "id": target_id}
    )
    assert response.status_code == 200
    specific_events = response.get_json()["history"]
    assert [item["id"] for item in specific_events] == [target_id]
    log_content = latest_history_event_content()
    assert log_content is not None
    payload = json.loads(log_content)
    assert payload["event_ids"] == [target_id]
    assert payload["id"] == target_id
    assert "limit" not in payload


def test_history_delete_requires_configuration(tmp_path):
    config = _make_config(tmp_path)
    application = create_app(config)
    application.config.update(TESTING=True)
    test_client = application.test_client()

    response = test_client.delete(
        "/history", json={"hostname": "test", "id": 1}
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "history deletions are disabled"


def test_history_delete_removes_event(tmp_path):
    config = _make_config(tmp_path, allow_deletions=True)
    application = create_app(config)
    application.config.update(TESTING=True)
    test_client = application.test_client()

    test_client.post("/copy", json={"hostname": "test", "content": "hello"})

    session_factory = application.config["SESSION_FACTORY"]
    with session_scope(session_factory) as session:
        copy_event_id = (
            session.query(ClipboardEvent.id)
            .filter(ClipboardEvent.action == "copy")
            .order_by(ClipboardEvent.id.desc())
            .scalar()
        )

    assert copy_event_id is not None

    response = test_client.delete(
        "/history", json={"hostname": "test", "id": copy_event_id}
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "deleted"

    with session_scope(session_factory) as session:
        deleted_event = session.get(ClipboardEvent, copy_event_id)
        assert deleted_event is None
        remaining_actions = [
            action for (action,) in session.query(ClipboardEvent.action).all()
        ]
        assert remaining_actions == []


def test_history_delete_missing_entry_returns_404(tmp_path):
    config = _make_config(tmp_path, allow_deletions=True)
    application = create_app(config)
    application.config.update(TESTING=True)
    test_client = application.test_client()

    response = test_client.delete(
        "/history", json={"hostname": "test", "id": 9999}
    )
    assert response.status_code == 404
    assert response.get_json()["error"] == "history entry not found"


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


def test_paste_specific_id_rejects_history_event(client, app):
    response = client.get("/history", json={"hostname": "test"})
    assert response.status_code == 200

    session_factory = app.config["SESSION_FACTORY"]
    with session_scope(session_factory) as session:
        history_event_id = (
            session.query(ClipboardEvent.id)
            .filter(ClipboardEvent.action == "history")
            .order_by(ClipboardEvent.id.desc())
            .scalar()
        )

    assert history_event_id is not None

    response = client.get(
        "/paste", json={"hostname": "test", "id": history_event_id}
    )
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["error"] == "history entry not found"


def test_private_backend_seeds_from_history(tmp_path):
    config = _make_config(tmp_path)
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

    config = _make_config(tmp_path, clipboard_backend="system")
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
