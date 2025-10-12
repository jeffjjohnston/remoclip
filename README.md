# remoclip

Remote clipboard utilities that sync clipboard contents over HTTP.

## Installation

```
pip install .
```

This provides two executables:

- `remoclip_server` – runs the HTTP server that manages the clipboard.
- `remoclip` – CLI client that interacts with a running server.

## Configuration

Both tools read the same YAML configuration file. By default this file lives at `~/.remoclip.yaml`:

```yaml
server: 127.0.0.1
port: 35612
db: ~/.remoclip.sqlite
```

- `server` and `port` describe where the server listens.
- `db` is the SQLite database path used for request logging.

Pass `--config /path/to/config.yaml` to either CLI to override the default path.

## Running the server

```
remoclip_server --config ~/.remoclip.yaml
```

The server exposes three JSON endpoints:

- `POST /copy` – set the clipboard. Payload includes `hostname` and `content`.
- `GET /paste` – retrieve the clipboard. Payload includes `hostname`.
- `GET /history` – retrieve prior clipboard events. Payload includes `hostname` and optional `limit`.

Each request is recorded in the configured SQLite database.

## Using the client

The client reads data from standard input and emits responses to standard output.

Copy local input to the remote clipboard (and echo it back):

```
echo "Hello" | remoclip copy
```

Paste the remote clipboard to your terminal:

```
remoclip paste
```

Fetch history as JSON, optionally limiting the number of entries:

```
remoclip history --limit 5
```

All client requests include the machine hostname for auditing on the server side.
