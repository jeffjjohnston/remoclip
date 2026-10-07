# Release history

This page lists each released version of remoclip and the changes it contains. Install the latest release from [PyPI](https://pypi.org/project/remoclip/) with `uv tool install remoclip` or `pip install remoclip`. To upgrade an existing installation, use `uv tool upgrade remoclip` or `pip install --upgrade remoclip`.

## 1.0.0

**Released on**: 2025-10-17

This was the first release of remoclip. It contains two command-line tools: `remoclip_server` and `remoclip`.

### Server (`remoclip_server`)

- An HTTP API with the endpoints `POST /copy`, `GET /paste`, `GET /history` and `DELETE /history`. Refer to [Server](server.md) for the request and response formats.
- Two clipboard backends:
    - `system` uses the host clipboard through [`pyperclip`](https://github.com/asweigart/pyperclip) on Linux, macOS and Windows.
    - `private` keeps the clipboard in memory, for headless hosts that have no clipboard. When the server starts, it loads the last clipboard value from the database.
- A SQLite database records each `copy`, `paste` and `history` action with the hostname, timestamp and content.
- An optional `security_token`. When you set it, the server rejects requests that do not have the correct `X-RemoClip-Token` header with an HTTP `401` response.
- The `server.allow_deletions` setting controls whether clients can delete history entries. Deletions are disabled by default.

### Client (`remoclip`)

- The commands `copy` (`c`), `paste` (`p`) and `history` (`h`). They read from standard input and write to standard output, so you can use them in pipes, as you use `pbcopy` and `pbpaste` on macOS.
- `paste --id N` gets an earlier history entry. `history --limit N` and `history --id N` filter the history output.
- `history --delete --id N` deletes a history entry from the server database.
- `copy --strip` (`-s`) removes trailing newline characters before the content goes to the clipboard.
- The client connects with HTTP or HTTPS through `client.url`, or through a Unix domain socket through `client.socket`. A socket lets you forward the connection over SSH without opening a TCP port on the remote host.
- Exit codes: `0` for success, `1` for network or HTTP errors and `2` for incorrect `--limit` or `--id` values.

### Configuration

- The server and the client use the same YAML file, `~/.remoclip.yaml`. You can supply a different file with `--config`. Refer to [Configuration](configuration.md) for all settings and their default values.
