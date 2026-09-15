# Browser client

Phaser 3.90 + TypeScript + Vite 6.4, using the Colyseus 0.16 SDK. Run the root
`npm run dev` to start the client and authoritative server together; open
<http://localhost:5173>. The client renders shapes and text only.

- **Play practice** creates a 2v2 game with three bots and starts immediately.
- **Create a game** opens a lobby; **Copy invite link** gives friends a direct
  `?room=CODE` link that joins automatically. Names are optional and remembered.
- The host starts once both teams have a connected player. Teams are assigned by
  the server. Matches admit at most twelve players and lock their roster on start.
- WASD/arrows move; Space attempts a tag; Escape releases keyboard controls.
  Losing window focus or hiding the tab immediately clears movement. Click the
  arena or **Resume controls** to regain controls; the match continues while away.
- Refreshing the same tab attempts to restore its saved session during the server's
  reconnect window. The per-tab token is stored in sessionStorage, never in invites.
  Sequence numbers remain monotonic across refresh. New tabs do not intentionally
  share the identity token.

The camera follows your player; the sidebar map shows the full arena, both flags,
both jails, and every player. The central overlap protects both teams. Team,
protection/jail state, objective, tag cooldown, scores, and player statistics remain
visible outside the canvas. Names and server text are rendered as text.

## Configuration

Set environment variables before running Vite/building:

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_GAME_ENDPOINT` | Same origin | Absolute game server endpoint, e.g. `wss://game.example.com` |
| `VITE_BASE_PATH` | `/` | Client asset base, e.g. `/games/ctf/` |
| `GAME_PROXY_TARGET` | `http://127.0.0.1:2567` | Development-only backend proxy target |

Development sends HTTP matchmaking and WebSocket traffic through Vite's `/game`
proxy, so LAN invites use the same reachable address/port as the page. Open the
page using the host's LAN address before copying an invite for another computer.
`localhost` links work only on the host's own computer.

Production assumes the built client is served alongside the game server. A static
website on a separate origin must build with `VITE_GAME_ENDPOINT` pointing to its
persistent backend. Client assets never contain private Warcraft reference files.
The top-level README describes the production server and supported base-path setup.

## API references

- [Phaser 3.90 source: BaseCamera](https://github.com/phaserjs/phaser/blob/v3.90.0/src/cameras/2d/BaseCamera.js)
- [Phaser Scale Manager](https://docs.phaser.io/phaser/concepts/scale-manager)
- [Vite 6 base configuration](https://v6.vite.dev/config/shared-options#base)
- [Vite 6 development proxy](https://v6.vite.dev/config/server-options#server-proxy)
- Colyseus 0.16.22's installed `colyseus.js/lib/Client.d.ts` and `Room.d.ts` verify
  `joinById`, `create`, `reconnect(reconnectionToken)`, `room.onStateChange`,
  `room.onMessage`, and `room.onLeave`. No 0.17/0.18 automatic reconnection or input
  APIs are used.

This prototype uses authoritative snapshots with short visual interpolation, no
client prediction or latency compensation. It currently requires a keyboard.
