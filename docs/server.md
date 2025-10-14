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
