# remoclip

`remoclip` (**remo**te **clip**board) is a small tool for providing copy and paste clipboard functionality in the CLI - with a special emphasis on allowing access to your local machine's clipboard when connected to remote systems. The package provides two CLI scripts: `remoclip_server` and `remoclip`.

`remoclip` relies on the [`pyperclip`](https://github.com/asweigart/pyperclip) package to interface with the local clipboard on Linux, Mac, and Windows.

!!! warning
    **Please pay attention to these warnings in the documentation. Allowing remote access to your local machine's clipboard is dangerous if not properly secured. Use the `security_token` feature and keep its value secret.**


## Quick Start

Install with uv or pip:
```sh
$ uv tool install remoclip
# alternative:
# pip install remoclip
```

Create a security token (optional but **highly** recommended):
```sh
TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "security_token: $TOKEN" > ~/.remoclip.yaml 
```

Run the server:
```sh
$ remoclip_server
```

In a new shell, access your local clipboard:
```sh
$ echo Hello from remoclip. | remoclip copy
Hello from remoclip.
$ remoclip paste
Hello from remoclip.
```

Add `--strip` (or `-s`) to `remoclip copy` when you need to remove trailing newline
characters from the piped input before it reaches the clipboard.

Connect to a remote system:
```sh
# first copy the config file so the remote client uses the security token
$ scp ~/.remoclip.yaml user@myremotehost:~
# remoclip's default port is 35612
$ ssh -R 35612:127.0.0.1:35612 user@myremotehost
user@myremotehost$ uv tool install remoclip
user@myremotehost$ remoclip paste
Hello from remoclip.
user@myremotehost$ echo Hello from $(hostname) | remoclip copy
Hello from myremotehost
```
   
Now, back on your local system, paste the contents of your clipboard somewhere. It should contain:
```text
Hello from myremotehost
```

You can also use `remoclip paste` (or `remoclip p`) and `remoclip copy` (or `remoclip c`) locally, similar to the macOS `pbcopy` and `pbpaste` commands.

If you want to avoid exposing a port on the remote system, Unix domain sockets are also supported:

```sh
$ echo "Hello from my local machine." | remoclip copy
Hello from my local machine.
$ ssh -R /tmp/remoclip.sock:127.0.0.1:35612 user@myremotehost
user@myremotehost$ echo -e "\nclient:\n\tsocket: /tmp/remoclip.sock" >> ~/.remoclip.yaml
user@myremotehost$ remoclip paste
Hello from my local machine.
```

Unfortunately, SSH does not automatically clean up the socket file when you disconnect your session. You'll need to delete it manually before you initiate a new connection with the same socket:

```sh
$ ssh user@myremote rm /tmp/remoclip-user.sock
$ ssh -R /tmp/remoclip-user.sock:127.0.0.1:35612 user@myremotehost
```

## Documentation layout

- [Configuration](configuration.md) describes the YAML settings used by both CLIs
- [Usage](usage.md) describes some common setups 
- [Server](server.md) documents the `remoclip_server` HTTP server
- [Client](client.md) explains the `remoclip` client tool
- [Release History](releases.md) lists each released version
