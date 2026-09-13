We are turning my old Warcraft III Capture the Flag custom map into a standalone
in-browser multiplayer game, eventually accessible from my personal website.
Continue from this folder rather than starting from a generic CTF template.

Read AGENTS.md, README.md, docs/CORE_RULES.md, docs/PROTOTYPE_PLAN.md, and
 docs/VALIDATION.md, then inspect packages/rules. The current project contains only
an audited core specification and a tested rules foundation. It does NOT already
contain a working browser client or multiplayer server.

Implement the first playable zero-art prototype using Phaser + TypeScript + Vite
in apps/client and Colyseus + Node/TypeScript in apps/server. Keep the pure rules in
packages/rules. Use the current official documentation for the compatible versions
you actually install and retain a lockfile. Do not discard the existing rules tests.

Start with a local lobby that assigns teams on the server, supports a room/invite
code, and lets the host start once each team has a player. Up to six players per
team. Render simple shapes, safe regions, jails, flags, player labels, and a score HUD.
Use WASD/arrows for movement and Space for a server-validated tag attempt; this is a
prototype control change, not Warcraft's original click-to-move combat.

Implement the complete core loop: safe home territory including the measured
central overlap, vulnerability away from home, tagging, imprisonment, all-team
jailbreak at the enemy jail with home-side revival, enemy flag pickup, moving flag
return after a tag, interception of a returning flag, scoring on reaching home
territory without requiring our own flag home, all-opponents-jailed scoring,
first-to-five matches, and an atomic round reset. Treat unresolved original-engine
behavior and all proposed defaults exactly as labeled in docs/CORE_RULES.md.

The server alone owns state and time. Validate session ownership and input payloads,
reject stale/replayed sequences, normalize movement, enforce tag cooldowns, cap
input rate and size, expire stale inputs, and freeze play outside the active phase.
Use a fixed-step loop with a bounded catch-up accumulator. Document event ordering
and same-tick scoring policy. Handle disconnects without orphaned flags, duplicate
scores, an immortal disconnected player, or an empty-team automatic win.

Deliver root npm run dev, npm test, npm run typecheck, and npm run build commands.
Verify two browser contexts in one room; test actual WebSocket state synchronization,
not merely the pure functions. Add integration tests for duplicate inputs, room
capacity, disconnected carriers, and round reset. Then run a 12-client network smoke
test. Attempt a browser smoke test with Playwright when available and record whether
it really ran. Keep any test-only teleport/state injection unavailable in production.

No accounts, database, art imports, economy, classes, wards, other abilities, or
public deployment in this task. Keep the server endpoint and client base path
configurable. Do not change my website or publish the reference-private directory.

Work in small local commits. Actually implement and run the prototype; do not stop
after writing another plan. At the end give exact run commands, test results, and
remaining limitations, including anything blocked by the environment.
