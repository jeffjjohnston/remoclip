# Server

The `remoclip_server` entry point runs a Flask application that exposes a small
HTTP API for clipboard operations. This page describes how to run the server,
what each endpoint does, and how logging and persistence work.

## Starting the server

```bash
remoclip_server --config ~/.remoclip.yaml
```

The command loads the configuration documented on the
[`configuration`](configuration.md) page and binds to the configured host and
port. On startup the server prints a banner such as:

```
INFO: Listening on http://127.0.0.1:35612
```

Access logs are streamed to standard output using a structured format that
includes the remote address, HTTP method, path, and response status. This makes
it easy to spot failing requests in real time.

## Clipboard backends

The server initialises a clipboard backend when it starts:

- **System backend** – integrates with the host clipboard via `pyperclip`. This
  is selected when `clipboard_backend: system` and `pyperclip` is available.
- **Private backend** – stores clipboard contents in memory. The server falls
  back to this backend automatically when the system clipboard is unavailable
  or when `clipboard_backend: private` is set.

Regardless of the backend, the service seeds the initial clipboard value from
the most recent event stored in the SQLite database so state survives restarts.

## Security token enforcement

When `security_token` is configured the server requires every request to include
an `X-RemoClip-Token` header with the matching value. Requests that omit the
header or provide the wrong token return an HTTP `401` response with a JSON error
message. Leave the configuration entry `null` to disable token checks.

## Usage scenarios

RemoClip is flexible enough to support a range of deployment patterns. The
following examples highlight common setups and the trade-offs to keep in mind.

### SSH forwarding options

When accessing a remote server over SSH you can expose the RemoClip HTTP
listener in two ways:

- **Local port forwarding** – Map the remote port to a localhost port on your
  workstation. This is a straightforward option when you control both ends and
  the port is not already occupied. Example:

  ```bash
  ssh -L 35612:127.0.0.1:35612 alice@devbox
  # RemoClip becomes reachable at http://127.0.0.1:35612 locally
  ```

- **Unix domain socket forwarding** – Request that SSH forward a remote socket
  path to a local port. This SSH feature lets you avoid colliding with other
  users who may also be running RemoClip instances on the same machine, because
  each user can bind to a dedicated socket file instead of competing for numbered
  ports. Example:

  ```bash
  ssh -L 35612:/tmp/remoclip-alice.sock alice@devbox
  # Remote socket /tmp/remoclip-alice.sock is exposed on localhost:35612
  ```

### Challenging cluster environments

High performance computing clusters sometimes require you to connect to a head
node via SSH and then open an interactive session on a compute node. In these
situations local port forwarding becomes cumbersome, because the final server is
no longer directly reachable from your workstation. A reliable alternative is to
launch a temporary [cloudflared](https://github.com/cloudflare/cloudflared)
tunnel on the machine that runs RemoClip. The tunnel should run alongside the
server and will publish it over a public HTTPS URL that any host can reach. When
you take this approach it is crucial to set and use the `security_token` so only
authorised clients can reach your clipboard data. For example:

```bash
cloudflared tunnel --url http://127.0.0.1:35612
# Outputs a https://... URL that forwards to your RemoClip server
```

### Headless servers

On single-purpose or headless servers the private clipboard backend pairs well
with RemoClip. Run the server with `clipboard_backend: private` to keep data in
process memory without depending on a GUI clipboard implementation. Combine this
with SSH forwarding or a tunnel, as described above, to access the clipboard from
your main workstation.

## HTTP endpoints

All endpoints accept and return JSON payloads. The `hostname` field is required
for auditing purposes.

!!! note
    The `GET` endpoints expect a small JSON document in the request body. The
    bundled RemoClip client takes care of this automatically, but custom
    integrations should remember to include the payload alongside the request.

### `POST /copy`

Set the clipboard to the supplied content. The request must include a payload in
the form:

```json
{
  "hostname": "alice",
  "content": "Hello from Alice"
}
```

Successful responses contain `{ "status": "ok" }`. The server writes a
`copy` event to the database and updates the configured clipboard backend.

### `GET /paste`

Return the current clipboard content. Clients may optionally include a JSON
payload to select a historic event:

```json
{
  "hostname": "bob",
  "id": 42
}
```

When `id` is provided the server returns the `content` of the matching history
entry. If the entry is not found the response is a `404` with an error message.
Without an `id` the service reads from the active clipboard backend. A matching
`paste` event is recorded in the database.

### `GET /history`

Return clipboard events in reverse chronological order. Clients may filter the
results by supplying `limit` or `id` fields in the JSON payload. The server
excludes prior `history` lookups so the response focuses on clipboard activity.
Responses look like:

```json
{
  "history": [
    {
      "id": 42,
      "timestamp": "2024-03-25T12:34:56Z",
      "hostname": "alice",
      "action": "copy",
      "content": "Hello from Alice"
    }
  ]
}
```

Every call stores a `history` event so you can audit when clients request
past entries.
