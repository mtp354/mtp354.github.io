# Authoritative server

Colyseus 0.18 runs the `ctf` room. `GameRoom` owns the canonical rules `Match`,
validates input, advances a fixed-step simulation, and projects a synchronized
read-only snapshot into Colyseus Schema. Room IDs double as invite codes. Players
are assigned balanced teams by the server, up to six per side. `/health` returns
only `{ "ok": true }`.

Run `npm run dev` from the project root. For a built server, run
`npm run build` then `npm run start:server`. `CTF_PORT` defaults to 2567.
In-process test mutation is guarded by `CTF_TEST_HARNESS=1` and has no socket or
HTTP route. See `docs/PROTOTYPE_PLAN.md` for event order and disconnect policy.
