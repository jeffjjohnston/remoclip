from __future__ import annotations

import argparse
import json
import logging
from typing import Any
from datetime import datetime, timezone
from werkzeug.serving import WSGIRequestHandler, make_server

from flask import Flask, jsonify, request

from .config import (
    DEFAULT_CONFIG_PATH,
    SECURITY_TOKEN_HEADER,
    RemoClipConfig,
    load_config,
)
from .clipboard import (
    ClipboardBackend,
    PrivateClipboardBackend,
    SystemClipboardBackend,
    is_system_clipboard_available,
    warn_if_unavailable,
)
from .db import ClipboardEvent, create_session_factory, session_scope


class LoggingWSGIRequestHandler(WSGIRequestHandler):
    """WSGI request handler that forwards access logs to :mod:`logging`."""

    level_map = {
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }

    def log(self, type: str, message: str, *args: Any) -> None:  # pragma: no cover - IO heavy
        logger = logging.getLogger("werkzeug.server")
        level = self.level_map.get(type, logging.INFO)
        formatted = message % args if args else message
        logger.log(
            level,
            "%s - - [%s] %s",
            self.address_string(),
            self.log_date_time_string(),
            formatted,
        )

    def log_request(
        self, code: int | str = "-", size: int | str = "-"
    ) -> None:  # pragma: no cover - IO heavy
        super().log_request(code, size)


def serve(app: Flask, host: str, port: int) -> None:
    """Run *app* on *host*:*port* with structured logging."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.getLogger().setLevel(logging.INFO)
    logging.info("Listening on http://%s:%s", host, port)

    server = make_server(host, port, app, request_handler=LoggingWSGIRequestHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual interrupt
        logging.info("Shutting down")
    finally:
        server.server_close()


def create_app(config: RemoClipConfig) -> Flask:
    app = Flask(__name__)
    session_factory = create_session_factory(config.server.db_path)
    app.config["SESSION_FACTORY"] = session_factory

    logger = logging.getLogger(__name__)

    def _seed_clipboard_value() -> str:
        with session_scope(session_factory) as session:
            event = (
                session.query(ClipboardEvent)
                .filter(ClipboardEvent.action.in_(["copy", "paste"]))
                .order_by(ClipboardEvent.timestamp.desc())
                .first()
            )
            if event is not None:
                return event.content
        return ""

    def _create_clipboard_backend() -> ClipboardBackend:
        initial_value = _seed_clipboard_value()
        if config.server.clipboard_backend == "system":
            if is_system_clipboard_available():
                return SystemClipboardBackend()
            warn_if_unavailable(logger, "system")
        return PrivateClipboardBackend(_value=initial_value)

    clipboard_backend = _create_clipboard_backend()
    app.config["CLIPBOARD_BACKEND"] = clipboard_backend

    def _format_timestamp(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat().replace("+00:00", "Z")

    def _verify_token() -> Any | None:
        if not config.security_token:
            return None
        header = request.headers.get(SECURITY_TOKEN_HEADER)
        if header != config.security_token:
            return jsonify({"error": "invalid token"}), 401
        return None

    @app.before_request
    def _enforce_token() -> Any | None:
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

    def _parse_optional_positive_int(value: Any, field: str) -> int | None:
        if value is None:
            return None
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be an integer") from exc
        if number <= 0:
            raise ValueError(f"{field} must be positive")
        return number

    def _validate_payload(data: dict[str, Any], expect_content: bool) -> dict[str, Any]:
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
            clipboard_backend.copy(content)
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
            event_id = _parse_optional_positive_int(data.get("id"), "id")

            if event_id is not None:
                with session_scope(session_factory) as session:
                    event = (
                        session.query(ClipboardEvent)
                        .filter(
                            ClipboardEvent.id == event_id,
                            ClipboardEvent.action != "history",
                        )
                        .one_or_none()
                    )
                    if event is None:
                        return jsonify({"error": "history entry not found"}), 404
                    content = event.content
            else:
                content = clipboard_backend.paste()
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
            limit = _parse_optional_positive_int(data.get("limit"), "limit")
            event_id = _parse_optional_positive_int(data.get("id"), "id")

            with session_scope(session_factory) as session:
                if event_id is not None:
                    event = session.get(ClipboardEvent, event_id)
                    if event is None:
                        return jsonify({"error": "history entry not found"}), 404
                    events = [
                        {
                            "id": event.id,
                            "timestamp": _format_timestamp(event.timestamp),
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
                    if limit is not None:
                        query = query.limit(limit)
                    events = [
                        {
                            "id": item.id,
                            "timestamp": _format_timestamp(item.timestamp),
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
    parser = argparse.ArgumentParser(
        description="Run remoclip HTTP server.",
        epilog=(
            "Configure the clipboard backend in the YAML config file via the "
            "'clipboard_backend' option (system|private)."
        ),
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to configuration file (default: ~/.remoclip.yaml)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    app = create_app(config)

    serve(app, config.server.host, config.server.port)


if __name__ == "__main__":  # pragma: no cover
    main()
