# Human 6v6 playtest checklist — pending

The automated socket suite already joined twelve real SDK clients (six per team).
This checklist is for a separate **human browser playtest**, not a claim that one
has happened. Run `npm ci`, `npm run dev`, and open `http://127.0.0.1:5173/` in
twelve browser contexts or machines that can reach the configured server. Create
one room, share its invite URL, and confirm six blue North and six orange South
slots. A thirteenth join should fail. The host starts after both sides have players.

- [ ] Each player can focus the arena, move with WASD/arrows, and see other players
      and the minimap update. Blur, hidden tab, and Escape stop movement intent.
- [ ] Both teams appear protected in the measured central overlap. A player in
      enemy territory can be tagged once per second by a nearby free opponent.
- [ ] A tagged player appears jailed and cannot move/tag. A free teammate entering
      the enemy jail frees **all** jailed allies at the named home-side spawn.
- [ ] Either side can carry the enemy flag. Both flags can be away at once. Tag a
      carrier: their flag should move back toward home and be interceptable.
- [ ] A carrier scores on entering their own safe territory even while their own
      flag is away. Score and personal capture update once; the round freezes,
      resets, and preserves statistics.
- [ ] Jailing the entire opposing active team scores once. Continue until five
      points and verify the match remains finished.
- [ ] Disconnect a carrier and confirm an immediate flag drop. Reconnect within
      the grace window and confirm the same slot/team/jail state. If a team empties
      permanently, confirm a disconnect finish with no automatic point.
- [ ] Record subjective navigation, visibility, tag fairness, and performance,
      especially with 50/100/200 ms round-trip delay, in a separate playtest log.

Use neutral nicknames and shapes only; do not add or publish private map assets.
