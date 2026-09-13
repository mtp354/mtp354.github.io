# Handoff validation

Prepared 12 September 2026; commands executed in the working environment, not on the
owner's computer. No remote repository or hosting environment was changed.

## Passed

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

## Not done / not claimed

A fresh `npm install` was not performed. The checks used preinstalled Node and the
compiler; Codex should install dependencies, generate a lockfile, and rerun the checks
from a clean checkout. There is no fabricated lockfile and no bundled node_modules.

No Phaser/Vite browser client, Colyseus room/server, browser rendering, WebSocket
integration, prediction/reconciliation, latency test, twelve-client test, production
build, Internet deployment, or original Warcraft playtest has been completed.
`apps/client` and `apps/server` currently contain implementation briefs only.

The existing helpers do not enforce network identity, per-client rate limits,
cooldown time, sequence monotonicity, reconnection, production origin checks, or
same-tick conflict resolution. Their input parser is not a substitute for those
server controls. Movement/return physics and some constants are explicitly provisional.

Stage 1 covers core rules and known unknowns, not all 502 triggers or every imported
object. Stage 2 is started through the testable rules foundation; a playable browser
prototype is the next Codex deliverable.

## Update after Codex implementation

Record commands, tool/dependency versions, results, browser/network evidence,
known failures, and manual reproduction steps here. Keep automated rule tests,
network tests, browser tests, and human gameplay/balance assessments distinct.
