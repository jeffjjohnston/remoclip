## Usage scenarios

`remoclip` is flexible enough to support a range of deployment patterns. The
following examples highlight common setups.

### SSH forwarding

When accessing a remote server over SSH you can expose the `remoclip` server in two ways:

   - **Local port forwarding** – Map a remote port to the server's port. This is a straightforward option when you control both ends and the port is not already occupied. Example:
   ```bash
   ssh -L 35612:127.0.0.1:35612 alice@devbox
   # remoclip becomes reachable at http://127.0.0.1:35612 locally
   ```

   - **Unix domain socket forwarding** – SSH can forward a remote socket path to a local port. This feature lets you avoid colliding with other users who may also be running `remoclip` instances on the same machine, because each user can bind to a dedicated socket file instead of competing for numbered ports. Example:
   ```bash
   ssh -R /tmp/remoclip-alice.sock:127.0.0.1:35612 alice@devbox
   ```
   Ensure that the client is configured to use the socket:
   ```yaml title="~/.remoclip.yaml"
   client:
       socket: /tmp/remoclip-alice.sock
   ```

### Challenging cluster environments

High performance computing clusters generally require you to connect to a head node via SSH and then open an interactive session on a compute node. In these situations local port forwarding becomes cumbersome, because the final server is often not directly reachable from your workstation. A possible alternative is to launch a temporary [cloudflared](https://github.com/cloudflare/cloudflared) tunnel on your workstation. The tunnel can publish the `remoclip_server` localhost URL over a public HTTPS endpoint. When you take this approach it is crucial to set and use the `security_token` so only authorised clients can access your clipboard data. For example:

```bash
cloudflared tunnel --url http://127.0.0.1:35612
# Outputs a https://... URL that forwards to your remoclip server
```

Update your client configuration to use the Cloudflare tunnel URL:

```yaml title="~/.remoclip.yaml"
client:
    url: "https://..."
```

### Headless servers

If you want to run the `remoclip_server` on a system without a native clipboard, which is often a headless server, you can use the 
