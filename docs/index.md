# RemoClip Documentation

RemoClip synchronises clipboard contents between machines using a small HTTP
service and a terminal client. This documentation is organised for [MkDocs],
so each page in the `docs/` directory becomes part of the site navigation.

## Features

- **Clipboard synchronisation:** copy text from one machine and paste it from
  another via the RemoClip HTTP API.
- **Shared configuration:** both the server and client load settings from the
  same YAML file, making it easy to keep hosts aligned.
- **History tracking:** every clipboard interaction is written to a SQLite
  database so you can review or retrieve past entries.
- **Flexible transport:** communicate over TCP or a Unix domain socket, making
  RemoClip a good fit for local, remote, or tunnelled workflows.
- **Optional security token:** configure a shared secret to require callers to
  present an `X-RemoClip-Token` header before requests are accepted.

## Project layout

- [`configuration`](configuration.md) describes the YAML settings used by both
  CLIs.
- [`server`](server.md) documents the Flask application and HTTP endpoints.
- [`client`](client.md) explains the terminal interface that drives the server.

## Quick start

1. Install the project in an isolated environment:
   ```bash
   uv sync  # or: pip install -e .[test]
   ```
2. (Optional) Create `~/.remoclip.yaml` to override the built-in defaults. The
   [`configuration`](configuration.md) page documents every available option so
   you can tailor connectivity, persistence, and security to your environment.
3. Start the server:
   ```bash
   remoclip_server --config ~/.remoclip.yaml
   ```
4. Interact with the clipboard from another terminal:
   ```bash
   echo "Hello" | remoclip copy
   remoclip paste
   ```

[MkDocs]: https://www.mkdocs.org/
