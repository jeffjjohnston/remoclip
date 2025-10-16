# remoclip Contributor Guide

Welcome to **remoclip**, a pair of small Python CLIs that sync clipboard data over HTTP.
This document captures the project conventions you should follow when editing files in
this repository.

## Project overview
- `src/remoclip/` contains the application code (configuration loader, SQLAlchemy
  models, Flask server factory, and client CLI helpers) using the src/ layout.
- `tests/` exercises the public behaviours with pytest; add or update tests alongside
  any functional change.
- `docs/` holds the MkDocs content (landing page, usage guides, and API reference).
  Keep navigation up to date with `mkdocs.yaml` when you add new pages, and ensure
  examples reflect the current behaviour.
- The package targets **Python 3.10+** and uses standard library features available in
  that runtime.

## Development workflow
1. Create a virtual environment (any tool is fine) and install dependencies:
   ```bash
   uv sync --dev # preferred when available
   # or
   pip install -e .[test]
   ```
2. Run the full test suite with pytest. If you touch server code, include the `tests/test_server.py` cases.
3. Keep the default configuration path (`~/.remoclip.yaml`) and database location overridable via the existing helper functions; do not hard-code alternative paths.
4. When you add or change CLI flags or endpoints, update the README usage examples so they stay aligned with the behaviour.
5. Review the MkDocs documentation in `docs/` for relevant updates whenever you change functionality or user workflows; documentation should remain accurate and complete. Refer to the package as "remoclip", NOT RemoClip in all documentation.

## Coding conventions
- Keep modules fully type annotated; maintain the existing type hint style using `from __future__ import annotations`.
- Prefer small, pure helper functions and context managers (see `session_scope`) to keep request handlers tidy.
- The optional `security_token` travels in the `X-RemoClip-Token` header; keep it backwards compatible (missing token means no auth enforced) and update the config loader, server checks, and client headers together.
- Logging and error handling should be defensive but minimal—follow the pattern used in `server_cli.py` (log and return JSON error responses without leaking stack traces).
- When working with SQLAlchemy models, reuse the `session_scope` context manager instead of opening sessions manually.
- Avoid adding top-level side effects; CLIs should expose a `main()` entry point and be guarded by `if __name__ == "__main__":` when needed.

## Testing & QA
- Primary check: `pytest` from the project root.
- Address or acknowledge new warnings
- For changes to HTTP endpoints or CLI interfaces, include integration-style tests under `tests/` demonstrating the new behaviour.

Thank you for contributing!
