# Capture the Flag — standalone browser project

A local, playable zero-art prototype built from the audited Warcraft III map rules.
The Phaser/Vite browser client and Colyseus server are implemented. The original map
remains a private design reference, not a runtime dependency. Two browser contexts
and a 12-client socket smoke test have passed; human 6v6 play and latency
testing remain.

## Run locally

Install Node.js 22 or newer. From this folder:

```sh
npm ci
npm run dev
```

Open `http://127.0.0.1:5173/`. Create a room, copy its invite link, and open it in
another browser context. The server listens at `http://127.0.0.1:2567/` and exposes
`/health`. The first player hosts and can start when both teams have a player. Click
the arena to focus controls: WASD/arrows move, Space attempts a tag, Escape releases
controls. The HUD and minimap show scores, jails, players, and flags. These controls
and the rectangle terrain are explicit prototype choices, not old-map behavior.

Checks and production artifacts:

```sh
npm test              # 27 preserved rules tests + real-socket integration test
npm run typecheck
npm run build         # apps/client/dist and apps/server/dist
npm run install:browser  # once, downloads Chromium under .playwright-browsers/
npm run test:browser  # two browser contexts, real client/server gameplay loop
npm run start:server  # production Node server, after build
```

`npm run build` creates static client files; serve `apps/client/dist` with any static
HTTP server and run `npm run start:server` separately. Vite's development server
and preview command are not production hosting. Nothing is deployed by these commands.

`CTF_PORT` changes the server port (default `2567`). Set `VITE_CTF_SERVER_URL` to the
server's public HTTPS origin when building a client away from localhost; its default
is `http://127.0.0.1:2567`. Set `CTF_BASE_PATH` at build time for a nested client URL,
for example `/games/ctf/` (default `/`). The server also accepts validated
`CTF_TICK_HZ`, `CTF_PATCH_MS`, `CTF_RECONNECT_GRACE_SECONDS`, and
`CTF_INTERMISSION_MS` environment settings; defaults are 30 Hz, 50 ms, 10 seconds,
and 1500 ms. A published HTTPS page requires an HTTPS/WSS game endpoint.

## Files

| Path | Purpose |
|---|---|
| `AGENTS.md` | Durable project constraints and instructions for coding agents |
| `CODEX_FIRST_TASK.md` | First implementation prompt and completion conditions |
| `docs/CORE_RULES.md` | Source-backed original behavior, unknowns, and prototype choices |
| `docs/PROTOTYPE_PLAN.md` | Client/server architecture, networking work, acceptance tests |
| `docs/WEBSITE_HOSTING.md` | Later static-client / persistent-server deployment split |
| `docs/VALIDATION.md` | What has and has not actually been tested |
| `packages/rules/src/index.ts` | Engine-independent state and transition helpers |
| `packages/rules/test/core.test.mjs` | Automated rule tests |
| `tools/` | Read-only MPQ extraction and source indexing |
| `apps/client/`, `apps/server/` | Phaser/Vite client and authoritative Colyseus room |
| `apps/server/test/network.test.mjs` | Actual SDK socket and 12-client smoke tests |
| `tests/browser.spec.ts` | Two-browser Playwright gameplay loop |

## Reproduce the private audit

With the original map saved at the companion archive's location:

```sh
python tools/extract_reference.py "reference-private/wc3/Capture the Flag advanced(1).w3x"
python tools/audit_reference.py reference-private/wc3/extracted
```

The extractor only supports the legacy MPQ features needed for this supplied map.
Unsupported encryption/compression fails explicitly. It is not a universal map parser.
Extraction preserves script bytes and records SHA-256 hashes. No map script is run.

## Boundaries

This is a new implementation, not a Warcraft map converter. Phaser/Colyseus are the
selected frameworks; the game does not need a Warcraft installation to run once built.
The main starter archive contains no Warcraft models, textures, audio, preview art,
or original map archive. The separate private reference archive is not a deployable.
The code's public licensing and final game name remain decisions for the owner.
Nothing has been deployed or pushed to a remote repository.
