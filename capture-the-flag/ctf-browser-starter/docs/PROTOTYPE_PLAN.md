# Stage 2: first browser multiplayer build

Implemented September 2026. This document retains the design and acceptance
contract; see VALIDATION.md for actual results and remaining manual checks.

## One outcome

Two real browser contexts join the same server room and complete movement → tag →
jail → jailbreak → flag pickup → return/capture → score → reset. The same architecture
must admit twelve players. Local success is not a claim of Internet playability or
competitive-quality netcode.

## Architecture

```text
apps/client        Phaser + TypeScript + Vite; rendering, input, interpolation
       |           authoritative snapshots/state patches down; input intent up
       | WSS       (WS acceptable on localhost only)
apps/server        Colyseus + Node/TypeScript; room lifecycle and fixed-step simulation
       |
packages/rules     framework-independent state and transition helpers
```

Selected frameworks: Phaser for a browser-first 2D renderer; Colyseus for rooms,
server-authoritative state synchronization, and a matching client SDK. Official
references are recorded in SOURCES.md. Pin a mutually compatible dependency set
and lockfile in Codex; do not assume every tutorial matches the version installed.
Use Tiled later, when obstacles and authored maps warrant it. The initial geometry
is declarative configuration, not a visual-editor dependency.

The rules helpers mutate only server-owned state. Their use on a client for display
or prediction does not confer authority. A Schema adapter should project the
canonical state rather than creating a separate competing implementation of rules.

## Browser and room behavior

Use a small lobby with room code/invite URL, nickname (length-capped and rendered
as text), connection status, server-assigned balanced teams, and a Start control
restricted to the current host. Enforce six slots per team and twelve total.
Starting needs at least one connected player on each team. Lock the active roster
for the first build; reconnects reclaim existing slots, not new identities. Host
transfer/room disposal must work when a host leaves before the match.

Render the whole arena or a readable camera view with a small minimap; label safe
areas and the central overlap. Show North/South score, target, phase, local jail
state, flag carriers, and a compact personal-stat list. Graphics are shapes and
text. Input is WASD/arrows plus Space for a tag attempt. Restore input focus cleanly;
blur/hidden-tab behavior must stop movement. Escape should release input focus.

A bare rectangle arena is acceptable, but it must not be described as a faithful
terrain port. Add deterministic per-slot safe spawn offsets rather than stacking
all six players at exactly the same point.

## Server safeguards and simulation contract

Only `sequence`, `moveX`, `moveY`, and `tag` arrive in movement messages. Room joins
and host start are distinct validated commands. Derive the actor from the socket's
session, never an arbitrary supplied player ID. Reject NaN/infinity, unknown fields,
invalid ranges, repeated/out-of-order sequence numbers, and oversized messages.
Use bounded per-session rate limits and never accumulate an unbounded input queue.
A client sending more messages must not move faster or tag more often.

Start with a 30 Hz fixed simulation step and an appropriate state patch rate, both
configurable. Use a monotonic-clock accumulator with bounded catch-up; do not run
one arbitrary frame delta as if it were a fixed tick. Movement consumes one bounded
latest-input state per simulation tick. Drop stale movement intent after a short
configured timeout. The server, not a client timestamp, controls cooldowns and time.

The server must decide and document event order: input/movement, tag attempts,
rescue, objective interactions, scoring, and round phase. The existing atomic
helpers block a second committed point but do not resolve competing simultaneous
proposals. Add a deterministic, documented policy and tests before calling the
network loop complete. Do not depend on WebSocket callback order or array insertion
order without explicitly treating that as a provisional gameplay choice.

A practical initial disconnect policy is a short configurable reconnect grace:
zero the absent player's inputs; drop carried flags immediately; retain the player's
team/jail/body state while disconnected so leaving is not an invulnerability trick.
On grace expiry, remove the player from the active roster. If a team becomes empty,
end/abort the match with an explicit disconnect reason rather than silently award
an all-jailed point. Prevent reconnect from clearing jail or duplicating an entity.
This is a new browser policy and may differ from Warcraft; record it as such.

## Latency is a real gameplay concern

Instant tags at protection boundaries are sensitive to latency even with twelve
players. Colyseus supplies infrastructure; it does not automatically make the game's
hit decisions fair. Initial local milestone may use authoritative movement with
remote interpolation. Later test 50/100/200 ms round-trip conditions, then introduce
local prediction/reconciliation and a deliberately chosen tag-validation/rewind
policy as needed. Never add a generic rewind option without specifying how it
interacts with safe zones, jailbreak teleports, round resets, and flag possession.
Do not send hidden information if invisibility/fog is added in a later milestone.

## Deliverable commands

After the implementation, root commands should include:

```sh
npm install        # initially create a lockfile, thereafter use npm ci
npm run dev        # starts both client and server
npm test           # rules + server/integration suites
npm run typecheck
npm run build      # production client and server artifacts
```

Document the actual localhost port(s), endpoint environment variable, and base-path
configuration. Keep production start separate from Vite's development/preview server.
A `/health` endpoint should report service health without exposing private room data.

## Acceptance checks

| Layer | Required evidence |
|---|---|
| Existing foundation | All 27 rule tests and strict compilation remain passing. |
| Network | Two actual SDK clients in one room receive synchronized authoritative state; two rooms do not share state. |
| Input abuse | Duplicate sequences, actor spoof attempts, rate bursts, malformed payloads, and huge movement values cannot alter authoritative rules. |
| Lifecycle | Disconnected carriers drop flags; a returning user does not duplicate a slot or clear jail; a last-member disconnect is handled explicitly. |
| Browser | Two browser contexts can visibly play the core loop. A human test or actual browser automation is required; a source review is not a browser test. |
| Rules integration | Jailbreak revives at home; both flags may be out; all-jailed and capture cannot double-score; phases freeze movement and tag handling. |
| Capacity | Twelve real network clients can join/configure a match; a thirteenth is rejected or directed to another lobby. This is a smoke test, not a scalability benchmark. |
| Build | Clean install + production build succeeds; no private reference assets occur in client output; endpoint/base path are configurable. |

Keep any integration-test state injection in test harnesses, not remotely accessible
production messages or an accidentally enabled debug endpoint. Public hosting,
accounts, persistence, abilities, economy, cosmetics, and mobile controls are later tasks.
