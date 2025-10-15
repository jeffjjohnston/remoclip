# remoclip

`remoclip` (**remo**te **clip**board) is a small tool for providing copy and paste clipboard functionality in the CLI - with a special emphasis on allowing access to your local machine's clipboard when connected to remote systems. The package provides two CLI scripts: `remoclip_server` and `remoclip`.

## Documentation

See the full documentation at [remoclip.newmatter.net](https://remoclip.newmatter.net).

## Quick Start

```
pip install .
```

This provides two executables:

- `remoclip_server` – runs the HTTP server that manages the clipboard.
- `remoclip` – CLI client that interacts with a running server.

## Configuration

Both tools read the same YAML configuration file. By default this file lives at `~/.remoclip.yaml`:

```yaml
security_token: null

server:
    host: 127.0.0.1
    port: 35612
    db: ~/.remoclip.sqlite
    clipboard_backend: system

client:
    url: "http://127.0.0.1:35612"
    socket: null
```

- `security_token` is an optional shared secret; when set, both the client and server
  send it in the `X-RemoClip-Token` HTTP header. Leave it `null` (or omit the key) to
  disable the check.
- `server.host` and `server.port` describe where the server listens.
- `server.db` is the SQLite database path used for request logging.
- `server.clipboard_backend` selects how the server stores clipboard data. The default
  `system` value uses the host clipboard via `pyperclip`. Set the field to `private`
  to keep clipboard contents in-process for headless deployments.
- `client.url` controls how the client reaches the server. Switch it to an `https://`
  URL when a TLS terminator or reverse proxy handles encryption.
- `client.socket` is an optional Unix domain socket path for the client. When provided,
  the client defaults to communicating over that socket while the server continues to
  use the TCP host and port. This allows the same configuration to be used for both
  tools even when an SSH tunnel exposes the server as a socket (for example,
  `ssh -R /tmp/remoclip.sock:localhost:35612 remotehost`).

Pass `--config /path/to/config.yaml` to either CLI to override the default path.

## Running the server

```
remoclip_server --config ~/.remoclip.yaml
```

On startup the server prints a banner such as `INFO: Listening on http://127.0.0.1:35612`
and then streams structured access logs to standard output. Each request line follows
the common log format (including the remote address and HTTP version) and status codes
are colourised so you can spot redirects, client errors, and server errors at a glance.

When the server runs with the `private` clipboard backend it keeps clipboard contents in
memory and seeds them from the most recent copy or paste event in the database so state
survives restarts. If the configuration requests the `system` backend but `pyperclip`
is unavailable, the server logs a warning and falls back to the private backend so
clipboard operations continue to work.

The server exposes three JSON endpoints:

- `POST /copy` – set the clipboard. Payload includes `hostname` and `content`.
- `GET /paste` – retrieve the clipboard. Payload includes `hostname`.
- `GET /history` – retrieve prior clipboard events. Payload includes `hostname` and optional `limit` or `id`.

Each request is recorded in the configured SQLite database. When a `security_token` is
configured, requests that omit or use an incorrect token receive `401` responses.

## Using the client

The client reads data from standard input and emits responses to standard output.

Copy local input to the remote clipboard (and echo it back):

```
echo "Hello" | remoclip copy
```

Paste the remote clipboard to your terminal, optionally requesting a specific history entry:

```
remoclip paste
remoclip paste --id 42
```

Fetch history as JSON, optionally limiting the number of entries or retrieving a specific event:

```
remoclip history --limit 5
remoclip history --id 42
```

All client requests include the machine hostname for auditing on the server side.
If the configuration provides a `security_token`, the client automatically attaches it
using the `X-RemoClip-Token` header so the server accepts the request.
