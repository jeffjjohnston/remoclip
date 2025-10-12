from __future__ import annotations

import argparse
import json
import socket
import sys
from typing import Any, Dict, Optional

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

    def _payload(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"hostname": socket.gethostname()}
        if extra:
            payload.update(extra)
        return payload

    def copy(self, content: str, timeout: float = 5.0) -> Dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/copy",
            json=self._payload({"content": content}),
            headers=self._headers,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def paste(self, timeout: float = 5.0) -> str:
        response = requests.get(
            f"{self.base_url}/paste",
            json=self._payload(),
            headers=self._headers,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("content", "")

    def history(self, limit: Optional[int] = None, timeout: float = 5.0) -> Dict[str, Any]:
        extra: Dict[str, Any] = {}
        if limit is not None:
            extra["limit"] = limit
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

    args = parser.parse_args()
    config = load_config(args.config)
    client = RemoClipClient(config)

    try:
        if args.command in ("copy", "c"):
            content = sys.stdin.read()
            client.copy(content)
            sys.stdout.write(content)
        elif args.command in ("paste", "p"):
            content = client.paste()
            sys.stdout.write(content)
        elif args.command in ("history", "h"):
            if args.limit is not None and args.limit <= 0:
                raise ValueError("limit must be a positive integer")
            history = client.history(limit=args.limit)
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
