# remoclip Documentation

`remoclip` (**remo**te **clip**board) is a small tool for providing copy and paste clipboard functionality in the CLI - with a special emphasis on allowing access to your local machine's clipboard when connected to remote systems.

Here's a quick example:

   1. Install with uv or pip
   ```sh
   $ uv tool install remoclip
   # alternative:
   # pip install remoclip
   ```

   2. Create a security token (optional but **highly** recommended)
   ```sh
   TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   echo "security_token: $TOKEN" > ~/.remoclip.yaml 
   ```

   3. Run the server
   ```sh
   $ remoclip_server
   ```

   4. Access your local clipboard
   ```sh
   $ echo Hello from remoclip. | remoclip copy
   $ remoclip paste
   ```

   5. Connect to a remote system
   ```sh
   # first copy the config file so the remote client uses the security token
   $ scp ~/.remoclip.yaml user@myremotehost:~
   # remoclip's default port is 35612
   $ ssh -R 35612:127.0.0.1:35612 user@myremotehost
   user@myremotehost$ uv install remoclip
   user@myremotehost$ remoclip paste
   Hello from remoclip.
   user@myremotehost$ echo Hello from $(hostname) | remoclip copy
   ```
   
   6. Now, back on your local system:
   ```sh
   $ remoclip paste
   Hello from myremotehost
   ```

If you want to avoid exposing a port on the remote system, Unix domain sockets are also supported:

```sh
$ ssh -R /tmp/remoclip.sock:127.0.0.1:35612 user@myremotehost
user@myremotehost$ echo "socket: /tmp/remoclip.sock" >> ~/.remoclip.yaml
user@myremotehost$ remoclip paste
Hello from myremotehost
```

Unfortunately, SSH does not automatically clean up the socket file when you disconnect your session. You'll need to delete it manually before you initiate a new connect with the socket:

```sh
$ ssh user@myremote rm /tmp/remoclip.sock
$ ssh -R /tmp/remoclip.sock:127.0.0.1:35612 user@myremotehost
```

## Features

- **Clipboard synchronisation:** copy text from one machine and paste it from
  another via the RemoClip HTTP API.
- **History tracking:** every clipboard interaction is written to a SQLite
  database so you can review or retrieve past entries.
- **Flexible transport:** communicate over TCP or a Unix domain socket, making
  remoclip a good fit for local, remote, or tunnelled workflows.
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
