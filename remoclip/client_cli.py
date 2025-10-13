from __future__ import annotations

import argparse
import json
import socket
import sys
from typing import Any

import requests

from .config import (
    DEFAULT_CONFIG_PATH,
    SECURITY_TOKEN_HEADER,
    RemoClipConfig,
    load_config,
)


class RemoClipClient:
    def __init__(self, config: RemoClipConfig):
        self.config = config
        self.base_url = f"http://{config.server}:{config.port}"
        self._headers = {}
        if config.security_token:
            self._headers[SECURITY_TOKEN_HEADER] = config.security_token

    def _payload(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"hostname": socket.gethostname()}
        if extra:
            payload.update(extra)
        return payload

    def copy(self, content: str, timeout: float = 5.0) -> dict[str, Any]:
        response = requests.post(
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
        response = requests.get(
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
        response = requests.get(
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
