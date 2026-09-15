# Authoritative game server

Colyseus 0.16 runs the engine-independent rules at 30 fixed steps per second and
projects the result into Schema 3 state patches at 20 Hz. Run the documented root
commands from the project directory. The production entry is `dist/index.js`;
`dist/server.js` exports `createGameServer()` for the in-process network tests.

The default listener is `http://127.0.0.1:2567`. It serves the built client from
`apps/client/dist`, plus matchmaking and WebSockets on the same port. `/health`
returns `{ "ok": true, "service": "ctf" }` with no room or player information.
Only the built client directory is served; the reference directory is never a
static source. `HOST`, `PORT`, `CLIENT_DIST`, and `CTF_BASE_PATH` are configurable.
`ALLOWED_ORIGINS` optionally restricts WebSocket handshakes to comma-separated
browser origins. `RECONNECT_SECONDS` sets the reconnect grace, default 20 seconds.

## Client contract

Use the matching `colyseus.js` 0.16 SDK:

```ts
const room = await client.create('ctf', { nickname: 'Runner', practice: true });
// Multiplayer: omit practice, then share room.roomId or the client invite link.
const guest = await client.joinById(roomId, { nickname: 'Friend' });
room.send('input', { sequence: 1, moveX: 0, moveY: -1, tag: false });
room.send('start', {});   // Host, multiplayer lobby, at least one per team.
room.send('rematch', {}); // Host, finished match, connected roster on both teams.
```

Practice creates one human and three bots (2v2), then starts immediately. Bots
send ordinary movement/tag intents internally and obey player speed, safe zones,
jail, rescue, flag and cooldown rules. Their routing/defense is deliberately simple.

`players` is a Schema map keyed by session ID, with `id`, `nickname`, `team`, `x`,
`y`, `status`, `kills`, `deaths`, `captures`, `connected`, `bot`, `slot`, and
`tagReadyAt`. `flags` is keyed by `north`/`south`, with `owner`, `x`, `y`, `status`,
and `carrierId` (empty when absent). Top-level fields are `phase`, `round`,
`targetScore`, `northScore`, `southScore`, `hostId`, `practice`, `serverTime`,
`phaseEndsAt`, `lastPointWinner`, `lastPointReason`, and `endReason`. Time fields
are elapsed simulation seconds; world coordinates retain x-right/y-up. Import
`DEFAULT_CONFIG` from `@ctf/rules` to draw the geometry. The server sends a `notice`
message containing `{ message: string }` for rejected start/rematch actions.

## Prototype decisions and deterministic order

- The server balances teams with North winning equal-size ties. Each team has at
  most six players. Lobby join order assigns stable slots; leaving frees a slot.
  Players spawn 150 units apart horizontally within their safe territory.
- Start locks the roster; reconnect is the only way to reclaim an existing seat.
  The host transfers immediately to the first connected human slot on disconnect.
  Rematch resets scores/statistics using the surviving roster and starts directly.
- Each tick moves all players, then handles tag attempts, rescues, returning flag
  motion, pickups, and captures. Players act in ascending stable slot order. Tags
  select the closest eligible victim; ties use slot order. Tags precede rescues
  and captures, and an all-jailed point immediately ends that tick's round. If both
  flags could score simultaneously, the first eligible slot scores the one point.
  This is an explicit prototype tie policy, not a claim about Warcraft ordering.
- Every tag attempt, including a miss, consumes a one-second server cooldown.
  Multiple accepted tag messages before a tick collapse to one attempted action.
  A held tag intent is consumed once; clients must send another attempt to retry.
- Rounds pause for three seconds, freeze gameplay, reset flags/positions/cooldowns,
  and preserve match score/statistics. The first team to five points wins.
- On any disconnect, movement stops and carried flags immediately return from the
  last body position. Unexpected disconnects retain the same body/jail/team during
  the grace period. That body can still be tagged or rescued by connected players;
  it cannot move, rescue others, pick up a flag, or capture while absent. A reconnect
  restores connectivity without clearing jail or resetting sequence numbers.
  Explicit leave or grace expiry removes the player. An empty team finishes the
  match with an explicit disconnect reason and no awarded point.

## Input and timing bounds

Only the four input fields above are accepted. Inputs reject nonfinite values,
movement outside [-1, 1], nonboolean tags, unknown fields, and nonincreasing safe
integer sequences. Actor identity always comes from the authenticated socket.
One latest input and one latched tag bit per player are stored; no input queue
grows. Movement expires after 250 ms without a fresh accepted intent. A token
bucket allows 60 messages/second with a burst of 90; extra messages are discarded.
WebSocket frames are limited to 1 KiB. Command actions have a separate 500 ms gate.

The monotonic accumulator runs at most five catch-up steps and discards excess
lag, preventing a long pause from becoming a large teleport. Simulation speed is
independent of client message count. Pending intents are cleared at round reset.
Browser reconnection should persist the next sequence together with the SDK
`reconnectionToken`; the server keeps the previous accepted sequence.

The room owns no private untracked intervals. Colyseus clears simulation/patch
timers when disposing the last client room. Shutdown disconnects rooms, closes the
transport, and stops the server. There are no remotely accessible debug actions;
tests may position canonical state only via an in-process room reference.

Version-matched official references:
[rooms](https://0-16-x.docs.colyseus.io/room),
[Schema](https://0-16-x.docs.colyseus.io/state/schema), and
[WebSocket transport](https://0-16-x.docs.colyseus.io/server/transport/ws).
