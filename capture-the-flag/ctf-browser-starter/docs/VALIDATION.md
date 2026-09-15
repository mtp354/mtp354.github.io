# Playable prototype validation

Validated on Ubuntu on 15 September 2026. No deployment, remote push, accounts,
paid services, or Warcraft runtime were used.

## Environment and pinned dependencies

- Private Linux Node.js **22.23.2** runtime, downloaded from nodejs.org and verified
  against its official SHA-256 list. No system Node installation was available.
- TypeScript **5.8.3**, Phaser **3.90.0**, Vite **6.4.3**.
- Colyseus core **0.16.26**, WebSocket transport **0.16.5**, Schema **3.0.76**,
  matching JavaScript SDK **0.16.22**.
- Playwright **1.62.1**, using the installed `/opt/google/chrome/chrome` in isolated
  headless contexts. The in-app Browser integration had no connected browser.
- Exact dependencies and integrity hashes retained in `package-lock.json`.

## Automated coverage

Final clean-install results:

| Command | Result |
|---|---|
| `./play-ctf.sh --no-open` from website root | Passed: private runtime selected, `npm ci` installed all 67 packages, build passed, production game started on port 2567. |
| `npm test` | **56 passed, 0 failed**, 10.3 seconds; exact output in TEST_OUTPUT.txt. |
| `npm run typecheck` | Passed for rules, server and client. |
| `npm run build` | Passed for rules, server and Vite browser bundle. |
| `CHROME_PATH=/opt/google/chrome/chrome npm run test:browser` | **1 passed, 0 failed**, two browser contexts, 11.3 seconds after build; no browser errors or shutdown errors. |

Invalid-join and oversized-frame cases intentionally produce rejection messages in
the network-test output. Those cases assert the rejections and pass.

| Layer | Evidence |
|---|---|
| Original rules | 27 existing rule tests retained and passing. |
| Server simulation/lifecycle | 19 tests: fixed steps, bounded catch-up, normalized movement, sequences, malformed input, rate limiting, stale intent, cooldowns, same-tick priority, jail/rescue, both flags out, scoring/reset/rematch, disconnects, spawn spacing, bots completing a match, and disposal races. |
| Real WebSockets | 9 cases use the actual SDK and server: synchronized state, room isolation, host authority, hostile input, full objective loop, tag cooldown/all-jailed scoring, disconnect/reconnect/grace expiry, host transfer, 12 players with 13th rejected, health and oversized-frame enforcement, solo practice. Some cases cover multiple related behaviors. |
| Shutdown | A separate child-process test verifies active sockets and a pending 20-second reconnect grace close without leaked handles, errors, or a long process-exit delay. |
| Browser | Two isolated browser contexts autojoin one room, move by keyboard, tag, observe jail, rescue, pick up a flag, score, reset, refresh/reconnect into the same seat, and move again. The suite then enters one-click practice and checks three bots. Browser JavaScript errors fail the test. |
| Development path | `npm run dev` started both processes; isolated Chrome joined practice through Vite's `/game` HTTP/WebSocket proxy. Ctrl+C stopped both. |
| Nested static path | Built with `VITE_BASE_PATH=/games/ctf/` and joined practice in Chrome from a server mounted at `/games/ctf/`. |
| Asset boundary | Client output contains only HTML/CSS/JavaScript. Checked for private-reference paths, map archives, and original map scripts; none are included. Jekyll excludes the source/reference folder. |

Network and browser fixtures sometimes position players through an **in-process**
server reference to reach a scenario quickly. There are no production teleport
messages, debug endpoints, or exposed browser game-state controls. Keyboard movement,
tag intent, joining, snapshots, reconnect and all resulting rules still cross actual
WebSockets. This proves the loop works; it is not a human balance assessment.

Browser screenshots are generated locally in ignored `test-results/`. Visual review
confirmed the arena, camera, minimap, scoreboard, player labels, and join screens.

## Reproduce

From the game project directory with Node.js 22+ on PATH:

```sh
npm ci
npm test
npm run typecheck
npm run build
CHROME_PATH=/opt/google/chrome/chrome npm run test:browser
```

Without an installed Chrome, run `npx playwright install chromium` once, then omit
`CHROME_PATH`. The game itself does not require Playwright or any browser download;
open it using your regular browser.

From the website root, `./play-ctf.sh` performs installation/build/start and opens
`http://localhost:2567/`. `./play-ctf.sh --lan` enables local-network play after stopping
an existing loopback-only server. `--no-open` leaves browser opening to you. See the
[README](../README.md) for controls, invites, and environment variables.

## Fixes found during validation

- Development server must start in its own directory so TypeScript loads the legacy
  decorator configuration required by Schema 3.
- Disposed rooms must not resume delayed `onLeave` work and project cleared metadata.
- Colyseus 0.16's numeric reconnect timeout can leave a native timer alive during
  shutdown. The room uses documented manual reconnection plus its own clock timeout
  and clears that timeout on completion.
- Browser cleanup must close SDK clients before closing the server.
- The launcher uses the configured nested base path, and does not pretend a running
  loopback server has switched to LAN mode.

## Still manual / not claimed

- A human six-versus-six playtest has not happened. Twelve SDK clients is a capacity
  smoke test, not evidence of balanced gameplay or Internet-scale performance.
- Two physical computers on a LAN have not been tested; firewall/router behavior
  depends on the user's network. Development and production HTTP/WebSockets worked
  on localhost, and the server supports listening on all interfaces for LAN use.
- No 50/100/200 ms network-latency study, prediction/reconciliation, or lag compensation.
- No mobile touch controls, terrain obstacles/pathfinding, classes, abilities,
  economy, imported art/audio, persistence, or public deployment.
- Bots are simple deterministic practice partners. They obey the rules but are not
  a recreation of Warcraft AI or a substitute for human opponents.
- Original map extraction/source evidence remains in CORE_RULES.md. The old map was
  not executed or playtested; source-unknown behaviors remain explicitly unknown.
