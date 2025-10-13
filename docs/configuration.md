# Configuration

Both `remoclip` (the client) and `remoclip_server` (the server) load a shared
YAML configuration file. By default this file lives at `~/.remoclip.yaml`, but
both CLIs accept a `--config` flag so you can supply an alternate path.

```yaml
server: 127.0.0.1
port: 35612
db: ~/.remoclip.sqlite
security_token: null
socket: null
clipboard_backend: system
```

## Settings

| Key | Type | Description |
| --- | ---- | ----------- |
| `server` | string | Hostname or IP address that the server binds to when listening for HTTP requests. |
| `port` | integer | TCP port the server uses when `socket` is not configured. |
| `db` | path | Location of the SQLite database used to persist clipboard events. The directory is created automatically if it does not exist. |
| `security_token` | string or `null` | Optional shared secret. When set, both the client and server send the token in the `X-RemoClip-Token` HTTP header. Requests with a missing or incorrect token receive a `401` response. |
| `socket` | path or `null` | Path to a Unix domain socket used by the client. When provided, the client prefers this socket while the server continues to bind to `server`/`port`. Leave `null` to send requests over TCP. |
| `clipboard_backend` | `system` or `private` | Selects how clipboard contents are stored on the server. The `system` backend uses the host clipboard via `pyperclip`. The `private` backend keeps data in memory so RemoClip can run on headless hosts without clipboard access. |

## Clipboard backend behaviour

When the configuration requests the `system` backend but the `pyperclip`
dependency is unavailable, the server logs a warning and falls back to the
`private` backend. This ensures copy and paste requests continue to work even on
minimal systems.

If you explicitly select the `private` backend, clipboard contents stay within
the RemoClip process. The most recent value is seeded from the database during
startup so history survives server restarts.

## Database location

The SQLite database records every `copy`, `paste`, and `history` action. Each
record includes the hostname, action, timestamp, and the content that was
transferred. This audit trail powers the history API and is valuable when you
need to retrieve earlier clipboard entries.

The database file defaults to `~/.remoclip.sqlite`. You can change the path to
store data alongside other application state or to point at a shared volume.
