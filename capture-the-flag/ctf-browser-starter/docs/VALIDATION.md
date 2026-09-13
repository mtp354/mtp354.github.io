# Validation record

Prepared 12 September 2026; commands executed in the working environment, not on the
owner's computer. No remote repository or hosting environment was changed.

## Stage 1 handoff (historical)

- Read-only extraction of 14 selected map members, with zero errors in that set.
  Original input and extracted members have recorded SHA-256 hashes.
- Static script index: 19,581 lines, 1,884 function definitions, 502 InitTrig definitions.
- Unit, item, and ability override parsing consumed each selected binary exactly,
  with no trailing bytes or missing record data in those files.
- `npm test`: **27 tests passed, 0 failed**. This script compiled the TypeScript rules
  then ran the built-in Node test runner. The captured output is TEST_OUTPUT.txt.
- `npm run typecheck`: passed with strict TypeScript checks.

The environment provided Node 22.16.0, npm 10.9.2, and TypeScript 5.8.3. These are
observed test-tool versions, not recommended up-to-date production runtime patches.

At handoff there was no installed lockfile, browser client, or network server. The
27 preserved rule tests and static map audit above are historical evidence, not
claims about the new runtime. `docs/TEST_OUTPUT.txt` captures that older test run.

## Stage 2 automated verification

On Windows with a project-local official Node.js 22.23.2 archive, npm 10.9.8,
TypeScript 5.8.3, Phaser 3.90.0, Colyseus 0.18.5 / SDK 0.18.2 / Schema 5.0.28,
Vite 8.3.0, and Playwright 1.63.0:

This machine had no system `node`/`npm` on PATH. PowerShell executions prepended
the ignored `.node/node-v22.23.2-win-x64` directory to PATH and used `npm.cmd`;
the table uses the portable `npm` command spelling for readability.

| Command or check | Actual result |
|---|---|
| `npm install --no-audit --no-fund` | Passed; installed 221 packages and generated retained `package-lock.json`. |
| `npm install --offline --no-audit --no-fund` | Passed after removing an unused development dependency and refreshing the lockfile. |
| `npm ci --offline --no-audit --no-fund` | Passed from the retained lockfile: clean reinstall of 221 packages. The first sandboxed attempt could not write npm's external cache temp directory; rerunning with approved cache access passed. |
| `npm test` | Passed: 28 tests, 0 failures (27 unchanged rules tests plus one full real-socket integration suite). |
| `npm run typecheck` | Passed: rules, server, and browser client. |
| `npm run build` | Passed: server JS and Vite static client. Vite reports a non-fatal 1.37 MB Phaser-containing JS chunk warning. |
| `npm run test:browser` | Passed: one Chromium Playwright test with **two actual browser contexts** plus two SDK teammates in the same room. Browser clicks and keyboard input caused server movement/tags; both contexts received HUD/arena changes. |
| `npm run dev` | Started the Node watcher and Vite; `GET /health` returned `{ "ok": true }` and `GET http://127.0.0.1:5173/` returned HTTP 200. |
| `npm run start:server` after build | Started the production Node entrypoint; `GET /health` returned `{ "ok": true }`. |
| PowerShell `$env:CTF_BASE_PATH='/games/ctf/'; $env:VITE_CTF_SERVER_URL='https://ctf.example.invalid'; npm.cmd run build` | Passed; generated asset URLs began `/games/ctf/assets/`. The example endpoint was build-only, never contacted. |
| `rg -l -i 'reference-private\|war3map\|\.w3x\|capture the flag advanced' apps/client/dist` and `git ls-files reference-private` | No matches / no tracked private paths. |
| `npm run install:browser` | Passed after Chromium had been installed into the project-local ignored directory. |

The network suite uses Colyseus SDK clients over actual sockets. It checks two-room
isolation; host start restriction; balanced team assignment; malformed, oversized,
spoof-shaped, and replayed input rejection; rate burst and stale intent behavior;
tagging, all-team jailbreak, dual flag possession, carrier drop, straight-line
return and interception, capture with own flag out, all-jailed scoring, intermission
freeze, and reset. It also checks a disconnected carrier and taggable absent body,
manual seat reclaim without duplication or jail clearing, host transfer, empty-team
abort without a score, twelve concurrent clients with six per side, thirteenth
client rejection, deterministic same-tick capture priority, and the first-to-five
match finish. The browser test
checks visible canvas/minimap/HUD, movement via keys, tags via Space, jailbreak,
both flags out, return/interception, scoring, round reset, and browser reload
reclaiming the same slot. Test-only position
setup was invoked directly inside the test process, never over a client message.

## Not yet verified or shipped

The twelve-client check is a socket smoke test, not a human 6v6 playtest or a load
benchmark. Human navigation, tagging feel, browser/device diversity, and a full
manual 6v6 checklist remain. No 50/100/200 ms latency simulation, prediction or
rewind policy, terrain/pathfinding, inherited Warcraft engine playtest, public
origin allowlist, production hosting, or Internet deployment has been done.
The original map's precise combat range, flag movement, first-round spawn details,
and trigger overlap remain unknown; implemented choices are labeled in
`docs/CORE_RULES.md`. The client currently sends a full serialized room projection
per changed patch and uses interpolation only, which is adequate for this local
prototype but has not been bandwidth-tuned. The private reference material stayed
outside Git and client assets.

## Manual reproduction

Run `npm ci`, `npm run dev`, open `http://127.0.0.1:5173/` twice, and create/join
one room using the invite link. Start from the host context. Click each arena to
focus, move with WASD/arrows, and press Space to tag a vulnerable opponent. A
1v1 last tag ends the round immediately by the all-jailed rule; use at least 2v2
to observe a jailbreak within an active round. `docs/6V6_CHECKLIST.md` records
the remaining human exercise. `npm run install:browser` installs the local test
Chromium before `npm run test:browser` on a fresh machine.
