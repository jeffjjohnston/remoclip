from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

try:  # pragma: no cover - import guard
    import pyperclip  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - import guard
    pyperclip = None  # type: ignore[assignment]


class ClipboardBackend(Protocol):
    """Minimal interface for clipboard implementations."""

    def copy(self, text: str) -> None:
        """Persist *text* to the clipboard."""

    def paste(self) -> str:
        """Return the last persisted clipboard value."""


@dataclass
class PrivateClipboardBackend:
    """In-process clipboard implementation used for headless deployments."""

    _value: str = ""

    def copy(self, text: str) -> None:
        self._value = text

    def paste(self) -> str:
        return self._value


class SystemClipboardBackend:
    """Wrapper around :mod:`pyperclip` for system clipboard access."""

    def __init__(self) -> None:
        if pyperclip is None:
            raise RuntimeError("pyperclip is not available")

    def copy(self, text: str) -> None:
        assert pyperclip is not None  # for type checkers
        pyperclip.copy(text)

    def paste(self) -> str:
        assert pyperclip is not None  # for type checkers
        return str(pyperclip.paste())


def is_system_clipboard_available() -> bool:
    """Return ``True`` when the system clipboard backend can be constructed."""

    return pyperclip is not None


def warn_if_unavailable(logger: logging.Logger, backend: str) -> None:
    """Emit a warning that *backend* is unavailable."""

    logger.warning(
        "%s clipboard backend selected but pyperclip is not available; falling back to private backend",
        backend,
    )
