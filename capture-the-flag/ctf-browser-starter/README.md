# Capture the Flag

A standalone browser prototype based on the core rules of your Warcraft III map.
Phaser draws the arena; a Colyseus server owns movement, tags, jails, flags and scores.
No Warcraft installation is needed.

## Play on Ubuntu

From the **website repository**:

```sh
./play-ctf.sh
```

The launcher installs a private Node.js runtime if needed, installs locked dependencies,
builds the game, starts the server, and opens **http://localhost:2567**. First launch
needs Internet access, `curl`, and `tar`; later launches reuse the installation. It
requires no `sudo` and makes no system-wide changes. Keep the terminal open while
playing; press Ctrl+C to stop. Use `--no-open` to skip opening the browser.

- **Play practice** starts immediately with bots. No account or room code needed.
- **Create game** opens a lobby. Copy the invite link into another browser tab, or
  share it with another player. The host starts when both teams have a player.
- Use **WASD / arrow keys** to move and **Space** to tag. Click the arena to control
  your runner. **Escape** releases controls; switching tabs stops movement.
- Bring the enemy flag back to your protected home territory to score. Tag enemies
  who are outside their safe territory. Enter the enemy jail to free all teammates.
  Jailing the whole enemy team also scores. First to five wins.

### Play with someone on the same network

```sh
./play-ctf.sh --lan
```

Open the host computer's local address (for example, `http://192.168.1.20:2567`)
on both computers, then create a game and copy its invite link. The server prints
local addresses when LAN mode is enabled. A `localhost` link works only on the
computer that created it. If Ubuntu's firewall blocks access, allow TCP port 2567
on your trusted local network. This is local network play, not public Internet hosting.

## Development

With Node.js 22+ installed, run these commands **inside this folder**. If you used
the Ubuntu launcher, first run `export PATH="$PWD/.runtime/node/bin:$PATH"`.

```sh
npm ci
npm run dev        # browser http://localhost:5173; game server 127.0.0.1:2567
npm test           # rules, simulation and actual WebSocket integration tests
npm run typecheck
npm run build
npm start          # built client + server at http://localhost:2567
```

`npm run dev` starts both processes and stops both on Ctrl+C. Production uses one
Node process serving the built client and WebSockets on the same port.

For browser checks, install Playwright's Chromium once with `npx playwright install
chromium`, then run `npm run test:browser`. Alternatively set `CHROME_PATH` to a local
Chrome/Chromium executable. The suite starts its own isolated server and browser
contexts. Test-only state setup runs inside the test process; there is no game cheat
endpoint or debug message.

### Configuration

| Variable | Default / purpose |
|---|---|
| `HOST` | `127.0.0.1`; use `0.0.0.0` for trusted LAN play |
| `PORT` | `2567` |
| `VITE_GAME_ENDPOINT` | Same origin in production; `/game` proxy during development. Override for a separate WebSocket host. |
| `VITE_BASE_PATH` | `/`; set when building for a nested static path such as `/games/ctf/` |
| `CTF_BASE_PATH` | `/`; set to match the built base path when serving a nested path through this server |
| `GAME_PROXY_TARGET` | `http://127.0.0.1:2567`, development only |
| `ALLOWED_ORIGINS` | Optional comma-separated browser origins for a future separately hosted server |
| `RECONNECT_SECONDS` | `20`; grace period to restore the same player after a connection drop |

Set server variables in your shell, for example `PORT=3000 npm start`. Vite variables
can be shell variables or live in `apps/client/.env.local`; rebuild after changing
them. Client variables are public configuration, never secrets. See
[WEBSITE_HOSTING.md](docs/WEBSITE_HOSTING.md) before a future deployment.

## Scope and evidence

The measured safe zones, center overlap, jails, home-side rescue, moving flag return
and scoring rules are retained. Movement controls, rectangle terrain, bot behavior
and network policies are prototype choices. This is not a complete terrain,
character, spell, or item port. See [CORE_RULES.md](docs/CORE_RULES.md),
[PROTOTYPE_PLAN.md](docs/PROTOTYPE_PLAN.md), and [VALIDATION.md](docs/VALIDATION.md).

The original map and companion archives are private reference inputs. They are not
served by this game or included in its builds. The surrounding Jekyll website excludes
the `capture-the-flag` source folder. Nothing is deployed or pushed by these commands.
