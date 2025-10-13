from __future__ import annotations

import argparse
import json
import socket
import sys
from http.client import HTTPConnection
from pathlib import Path
from typing import Any

from urllib.parse import quote, urlsplit

import requests
from requests import Response, Session as RequestsSession

from .config import (
    DEFAULT_CONFIG_PATH,
    SECURITY_TOKEN_HEADER,
    RemoClipConfig,
    load_config,
)


class _UnixSocketHTTPConnection(HTTPConnection):
    def __init__(self, socket_path: str, timeout: float | None):
        super().__init__("localhost", timeout=timeout)
        self._socket_path = socket_path

    def connect(self) -> None:  # pragma: no cover - exercised indirectly by session
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.timeout is not None:
            sock.settimeout(self.timeout)
        sock.connect(self._socket_path)
        self.sock = sock


class _UnixSocketResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class UnixSocketSession:
    def __init__(self, socket_path: Path):
        self._socket_path = str(socket_path)

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_payload: dict[str, Any] | None,
        headers: dict[str, str] | None,
        timeout: float,
    ) -> _UnixSocketResponse:
        body: bytes | None = None
        request_headers = dict(headers or {})
        if json_payload is not None:
            body = json.dumps(json_payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")
        parsed = urlsplit(url)
        request_path = parsed.path or "/"
        if parsed.query:
            request_path = f"{request_path}?{parsed.query}"
        connection = _UnixSocketHTTPConnection(self._socket_path, timeout)
        try:
            connection.request(method.upper(), request_path, body=body, headers=request_headers)
            response = connection.getresponse()
            raw_data = response.read()
            status = response.status
            reason = response.reason
            headers_map = dict(response.getheaders())
        except OSError as exc:  # pragma: no cover - connection issues are exceptional
            raise requests.RequestException(str(exc)) from exc
        finally:
            connection.close()

        if status >= 400:
            http_response = Response()
            http_response.status_code = status
            http_response.reason = reason
            http_response.headers = headers_map
            http_response._content = raw_data
            raise requests.HTTPError(f"{status} {reason}", response=http_response)

        payload: dict[str, Any]
        if raw_data:
            payload = json.loads(raw_data.decode("utf-8"))
        else:
            payload = {}
        return _UnixSocketResponse(status, payload)

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str] | None,
        timeout: float,
    ) -> _UnixSocketResponse:
        return self._request(
            "POST",
            url,
            json_payload=json,
            headers=headers,
            timeout=timeout,
        )

    def get(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str] | None,
        timeout: float,
    ) -> _UnixSocketResponse:
        return self._request(
            "GET",
            url,
            json_payload=json,
            headers=headers,
            timeout=timeout,
        )


class RemoClipClient:
    def __init__(self, config: RemoClipConfig):
        self.config = config
        socket_path = config.socket_path
        if socket_path is not None:
            encoded_path = quote(str(socket_path), safe="")
            self.base_url = f"http+unix://{encoded_path}"
            session = UnixSocketSession(socket_path)
        else:
            self.base_url = f"http://{config.server}:{config.port}"
            session = RequestsSession()
        self._session = session
        self._headers = {}
        if config.security_token:
            self._headers[SECURITY_TOKEN_HEADER] = config.security_token

    def _payload(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"hostname": socket.gethostname()}
        if extra:
            payload.update(extra)
        return payload

    def copy(self, content: str, timeout: float = 5.0) -> dict[str, Any]:
        response = self._session.post(
            f"{self.base_url}/copy",
            json=self._payload({"content": content}),
            headers=self._headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def paste(self, event_id: int | None = None, timeout: float = 5.0) -> str:
        extra: dict[str, Any] | None = None
        if event_id is not None:
            extra = {"id": event_id}
        response = self._session.get(
            f"{self.base_url}/paste",
            json=self._payload(extra),
            headers=self._headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("content", "")

    def history(
        self,
        limit: int | None = None,
        event_id: int | None = None,
        timeout: float = 5.0,
    ) -> dict[str, Any]:
        extra: dict[str, Any] = {}
        if limit is not None:
            extra["limit"] = limit
        if event_id is not None:
            extra["id"] = event_id
        response = self._session.get(
            f"{self.base_url}/history",
            json=self._payload(extra),
            headers=self._headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="remoclip client CLI")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to configuration file (default: ~/.remoclip.yaml)",
    )
    parser.add_argument(
        "command",
        choices=["copy", "c", "paste", "p", "history", "h"],
        help="Action to perform on the remote clipboard",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit for history entries (only for history command)",
    )
    parser.add_argument(
        "--id",
        type=int,
        help="Retrieve a specific entry by id (available for paste and history commands)",
    )

    args = parser.parse_args()
    config = load_config(args.config)
    client = RemoClipClient(config)

    try:
        if args.command in ("copy", "c"):
            content = sys.stdin.read()
            client.copy(content)
            sys.stdout.write(content)
        elif args.command in ("paste", "p"):
            if args.id is not None and args.id <= 0:
                raise ValueError("id must be a positive integer")
            content = client.paste(event_id=args.id)
            sys.stdout.write(content)
        elif args.command in ("history", "h"):
            if args.limit is not None and args.limit <= 0:
                raise ValueError("limit must be a positive integer")
            if args.id is not None and args.id <= 0:
                raise ValueError("id must be a positive integer")
            history = client.history(limit=args.limit, event_id=args.id)
            json.dump(history, sys.stdout, indent=2)
            sys.stdout.write("\n")
    except requests.RequestException as exc:
        sys.stderr.write(f"Request failed: {exc}\n")
        sys.exit(1)
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(2)


if __name__ == "__main__":  # pragma: no cover
    main()
