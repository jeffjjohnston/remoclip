# remoclip Documentation

`remoclip` (**remo**te **clip**board) is a small tool for providing copy and paste clipboard functionality in the CLI - with a special emphasis on allowing access to your local machine's clipboard when connected to remote systems. The package provides two CLI scripts: `remoclip_server` and `remoclip`.

Here's a quick example:

   1. Install with uv or pip:
   ```sh
   $ uv tool install remoclip
   # alternative:
   # pip install remoclip
   ```

   2. Create a security token (optional but **highly** recommended):
   ```sh
   TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
   echo "security_token: $TOKEN" > ~/.remoclip.yaml 
   ```

   3. Run the server
   ```sh
   $ remoclip_server
   ```

   4. In a new shell, access your local clipboard:
   ```sh
   $ echo Hello from remoclip. | remoclip copy
   Hello from remoclip.
   $ remoclip paste
   Hello from remoclip.
   ```

   5. Connect to a remote system:
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
user@myremotehost$ echo -e "client:\n\tsocket: /tmp/remoclip.sock" >> ~/.remoclip.yaml
user@myremotehost$ remoclip paste
Hello from myremotehost
```

Unfortunately, SSH does not automatically clean up the socket file when you disconnect your session. You'll need to delete it manually before you initiate a new connection with the socket:

```sh
$ ssh user@myremote rm /tmp/remoclip.sock
$ ssh -R /tmp/remoclip.sock:127.0.0.1:35612 user@myremotehost
```

## Documentation layout

- [Configuration](configuration.md) describes the YAML settings used by both
  CLIs.
- [Usage](usage.md) describes some common setups 
- [Server](server.md) documents the `remoclip_server` HTTP server
- [Client](client.md) explains the `remoclip` client tool

