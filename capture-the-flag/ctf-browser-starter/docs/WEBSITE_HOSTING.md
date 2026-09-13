# Later hosting on the owner's personal website

No hosting provider, current website framework, domain, or DNS access has been
established. Do not assume WordPress, GitHub Pages, Vercel, or a VPS. The prototype
should not require replacing the existing site.

## Two deployable pieces

The built Phaser/Vite client is static HTML/JavaScript/CSS plus original assets. It
can be served from a suitable static host, a subpath of the existing website, or a
separate game subdomain. Configure the Vite base path; do not hard-code `/assets/`.
Vite's official deployment guide distinguishes a production static build from its
local preview server.

The Colyseus server is a running authoritative Node process with live room state
and WebSocket connections. It needs hosting that supports that process model, not
merely a folder of static files. Generic short-lived request functions are not a
drop-in substitute. The website and server can run on different machines/providers.

Illustrative endpoint structure (not the owner's actual domain):

```text
https://example.com/games/ctf/       static browser client
wss://ctf-server.example.com        real-time game server
```

These are architecture examples, not created endpoints. A game subdomain is another
option if subpath integration is inconvenient. The existing academic/personal site
can simply link to the game initially; embedding is not required.

## Design for this now; deploy later

Keep a configurable client server-endpoint variable and a configurable asset base
path. In production use TLS/HTTPS/WSS, explicit origin checks, input/rate limits,
service health checks, room cleanup, graceful shutdown, and a process restart policy.
Match state is initially ephemeral: restarting the server ends active games unless
recovery is later implemented. Do not promise persistence from a room abstraction.

Do not put secrets in Vite/browser environment variables: client configuration is
public. Reconnect tokens are credentials; avoid logging them or putting them in
public screenshots. Review logs, costs, server region, and abuse controls before
public release. A room-capacity test is not a DDoS/security audit.

Before a deployment task, establish the actual website host/domain, available static
paths or subdomains, whether its plan permits a persistent Node/WebSocket server,
and the desired hosting budget. There is no need to resolve those facts to develop
and playtest locally.

Only publish the intended production client/server artifacts. Never upload the
starter ZIP or `reference-private/` to a public web directory. No deployment, paid
resource creation, repository publication, or DNS edits are authorized by this handoff.
See SOURCES.md for official deployment documentation checked for this design.
