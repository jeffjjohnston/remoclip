# Configuration

Both `remoclip` (the client) and `remoclip_server` (the server) load a shared
YAML configuration file. By default this file lives at `~/.remoclip.yaml`, but
both CLIs accept a `--config` flag so you can supply an alternate path.

```yaml
security_token: null

server:
    host: 127.0.0.1
    port: 35612
    db: ~/.remoclip.sqlite
    clipboard_backend: system
    allow_deletions: false

client:
    url: "http://127.0.0.1:35612"
    socket: null
```

## Settings

| Key | Type | Description |
| --- | ---- | ----------- |
| `security_token` | string or `null` | Optional shared secret. When set, both the client and server send the token in the `X-RemoClip-Token` HTTP header. Requests with a missing or incorrect token receive a `401` response. |
| `server.host` | string | Hostname or IP address that the server binds to when listening for HTTP requests. |
| `server.port` | integer | TCP port the server uses when `client.socket` is not configured. |
| `server.db` | path | Location of the SQLite database used to persist clipboard events. The directory is created automatically if it does not exist. |
| `server.clipboard_backend` | `system` or `private` | Selects how clipboard contents are stored on the server. The `system` backend uses the host clipboard via `pyperclip`. The `private` backend keeps data in memory so RemoClip can run on headless hosts without clipboard access. |
| `server.allow_deletions` | boolean | When `true`, clients may delete clipboard history entries via the API. The default `false` value keeps the audit trail intact. |
| `client.url` | string | Base URL the client uses for HTTP(S) requests. Switch to an `https://` URL when a reverse proxy terminates TLS in front of the RemoClip server. |
| `client.socket` | path or `null` | Path to a Unix domain socket used by the client. When provided, the client prefers this socket while the server continues to bind to `server.host`/`server.port`. Leave `null` to send requests over TCP. |

## HTTPS support

Set `client.url` to an `https://` address when the remoclip server is exposed
via a TLS terminator such as a reverse proxy. 

## Database location

The SQLite database records every `copy`, `paste`, and `history` action. Each record includes the hostname, action, timestamp, and the content that was transferred. This audit trail powers the history API and is valuable when you need to retrieve earlier clipboard entries. The database file defaults to `~/.remoclip.sqlite` and is configurable.
