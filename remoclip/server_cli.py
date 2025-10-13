from __future__ import annotations

import argparse
import json
import logging
from typing import Any, Dict, Optional

import pyperclip
from flask import Flask, jsonify, request

from .config import (
    DEFAULT_CONFIG_PATH,
    SECURITY_TOKEN_HEADER,
    RemoClipConfig,
    load_config,
)
from .db import ClipboardEvent, create_session_factory, session_scope


def create_app(config: RemoClipConfig) -> Flask:
    app = Flask(__name__)
    session_factory = create_session_factory(config.db_path)
    app.config["SESSION_FACTORY"] = session_factory

    def _verify_token() -> Optional[Any]:
        if not config.security_token:
            return None
        header = request.headers.get(SECURITY_TOKEN_HEADER)
        if header != config.security_token:
            return jsonify({"error": "invalid token"}), 401
        return None

    @app.before_request
    def _enforce_token() -> Optional[Any]:
        return _verify_token()

    def _log_event(hostname: str, action: str, content: str) -> None:
        with session_scope(session_factory) as session:
            session.add(
                ClipboardEvent(
                    hostname=hostname,
                    action=action,
                    content=content,
                )
            )

    def _validate_payload(data: Dict[str, Any], expect_content: bool) -> Dict[str, Any]:
        if not data or "hostname" not in data:
            raise ValueError("JSON payload must include 'hostname'")
        if expect_content and "content" not in data:
            raise ValueError("JSON payload must include 'content'")
        return data

    @app.post("/copy")
    def copy_content():
        try:
            data = request.get_json(force=True, silent=False)
            payload = _validate_payload(data, expect_content=True)
            content = str(payload["content"])
            pyperclip.copy(content)
            _log_event(str(payload["hostname"]), "copy", content)
            return jsonify({"status": "ok"})
        except Exception as exc:  # pragma: no cover - defensive
            logging.exception("Failed to handle /copy request")
            return jsonify({"error": str(exc)}), 400

    @app.get("/paste")
    def paste_content():
        try:
            data = request.get_json(silent=True) or {}
            payload = _validate_payload(data, expect_content=False)
            content = pyperclip.paste()
            _log_event(str(payload["hostname"]), "paste", content)
            return jsonify({"content": content})
        except Exception as exc:  # pragma: no cover - defensive
            logging.exception("Failed to handle /paste request")
            return jsonify({"error": str(exc)}), 400

    @app.get("/history")
    def history():
        try:
            data = request.get_json(silent=True) or {}
            payload = _validate_payload(data, expect_content=False)
            limit_value = data.get("limit")
            limit = int(limit_value) if limit_value is not None else None
            id_value = data.get("id")
            event_id = int(id_value) if id_value is not None else None

            if limit is not None and limit <= 0:
                raise ValueError("limit must be positive")
            if event_id is not None and event_id <= 0:
                raise ValueError("id must be positive")

            with session_scope(session_factory) as session:
                if event_id is not None:
                    event = session.get(ClipboardEvent, event_id)
                    if event is None:
                        return jsonify({"error": "history entry not found"}), 404
                    events = [
                        {
                            "id": event.id,
                            "timestamp": event.timestamp.isoformat() + "Z",
                            "hostname": event.hostname,
                            "action": event.action,
                            "content": event.content,
                        }
                    ]
                else:
                    query = (
                        session.query(ClipboardEvent)
                        .filter(ClipboardEvent.action != "history")
                        .order_by(ClipboardEvent.timestamp.desc())
                    )
                    if limit is not None and limit > 0:
                        query = query.limit(limit)
                    events = [
                        {
                            "id": item.id,
                            "timestamp": item.timestamp.isoformat() + "Z",
                            "hostname": item.hostname,
                            "action": item.action,
                            "content": item.content,
                        }
                        for item in query.all()
                    ]
            _log_event(str(payload["hostname"]), "history", json.dumps(events))
            return jsonify({"history": events})
        except Exception as exc:  # pragma: no cover - defensive
            logging.exception("Failed to handle /history request")
            return jsonify({"error": str(exc)}), 400

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run remoclip HTTP server.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to configuration file (default: ~/.remoclip.yaml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    app = create_app(config)

    app.run(host=config.server, port=config.port, use_reloader=False)


if __name__ == "__main__":  # pragma: no cover
    main()
