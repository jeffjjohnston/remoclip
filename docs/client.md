# Client

The `remoclip` executable provides a terminal-friendly interface for interacting
with a running `remoclip_server`. It reads from standard input, writes responses to
standard output, and surfaces errors on standard error.

## Command overview

```bash
remoclip --config ~/.remoclip.yaml <command> [options]
```

The `command` argument selects the operation to perform. Short aliases are also
available.

| Command | Alias | Description |
| ------- | ----- | ----------- |
| `copy` | `c` | Read stdin, send the content to the server, and echo the value locally. |
| `paste` | `p` | Retrieve the latest clipboard value (or a specific history entry) and print it to stdout. |
| `history` | `h` | Fetch clipboard history as formatted JSON and write it to stdout. |

Common options:

- `--config PATH` – location of the YAML configuration file (defaults to
  `~/.remoclip.yaml`).
- `--limit N` – restrict the number of entries returned by `history`.
- `--id N` – request a particular history entry for `paste` or `history`.
- `--delete` – remove a specific history entry when combined with `--id`.
- `-s`/`--strip` – remove trailing newline characters before copying (copy command only).

Invalid values for `--limit` or `--id` cause the client to exit with code `2`
and a descriptive error message.

!!! tip
    Provide positive integers for `--limit` and `--id`. The CLI validates the
    values before sending a request so mistakes fail fast with a helpful error.

## Transport selection

The client chooses how to talk to the server based on the loaded
configuration:

- When `socket` is set to a Unix domain socket path the client connects over that
  socket using an HTTP-over-UDS adapter.
- Otherwise it targets the configured `client.url` using standard HTTP(S)
  requests via the `requests` library. Switch the URL to `https://` when a TLS
  terminator sits in front of the remoclip server.

In both cases the client includes the local machine hostname in every request.
If `security_token` is configured the client transparently attaches it via the
`X-RemoClip-Token` header.

## Exit codes and errors

Network or HTTP-level issues raise a `RequestException`. The CLI reports the
failure and exits with status code `1` so scripts can detect the problem. Value
validation errors exit with status code `2`. Successful operations exit with
status code `0`.

## Examples

```text title="notes.txt"
Aloha!
```

Copy the contents of a file to the server's clipboard (and echo it back):

```bash
$ cat notes.txt | remoclip copy
Aloha!
```

Paste the most recent clipboard value from the server:

```bash
$ remoclip paste
Aloha!
```

Retrieve the last two history entries as JSON:

```bash
$ remoclip history --limit 2
```

```json
{
  "history": [
    {
      "action": "paste",
      "content": "Aloha!\n",
      "hostname": "example-host",
      "id": 2,
      "timestamp": "2025-10-15T17:07:52.467966Z"
    },
    {
      "action": "copy",
      "content": "Aloha!\n",
      "hostname": "example-host",
      "id": 1,
      "timestamp": "2025-10-15T17:07:38.963020Z"
    }
  ]
}
```

Retrieve a single history entry as JSON:

```bash
$ remoclip history --id 2
```

```json
{
  "history": [
    {
      "action": "paste",
      "content": "Aloha!\n",
      "hostname": "example-host",
      "id": 2,
      "timestamp": "2025-10-15T17:07:52.467966Z"
    }
  ]
}
```

Paste the contents of a previous history entry:

```bash
$ echo "Hello!" | remoclip copy
Hello!
$ remoclip paste
Hello!
$ remoclip paste --id 2
Aloha!
```

As `remoclip` reads and writes from standard in and standard out, it can be used with pipes to avoid a lot of manual copying and pasting. 

