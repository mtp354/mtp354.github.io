# Core rules audit and prototype contract

Prepared 12 September 2026. This is a **static audit of the core loop**, not a full
playtest or complete audit of all legacy triggers, characters, shops, or abilities.

## Evidence and confidence

The supplied file is `Capture the Flag advanced(1).w3x`, 1,427,780 bytes, SHA-256:

```text
9d5eba292f0cbc395bcdd46113d03d2bb178c8deced8e1196685471812974723
```

Its header names Capture the Flag v1.66b. A read-only extractor found the MPQ at
byte 512 and successfully extracted 14 selected data/script members. No member in
that selected set failed extraction. This is not a claim that every asset was extracted.
The unmodified `war3map.j` has 19,581 lines using Python splitlines, 1,884 function
definitions, and 502 `InitTrig_` definitions. Its SHA-256 is:

```text
b9c00d3de4a844d9d69af212d74d1038425b6d9c8d6b05e4b5c4fd4904c6b5b2
```

All source locations below refer to that exact `war3map.j` in
`reference-private/wc3/extracted/`. The companion pack also includes
`jass-index.json`, `regions.json`, parsed unit/item/ability overrides, and an
extraction manifest. Function names provide stable anchors when editor line endings differ.

Confidence labels: **verified** means explicitly visible in this source;
**inferred/unknown** means engine behavior or an untraced execution path remains;
**prototype choice** means a new decision, not an assertion about the old game.

## Source-verified core behavior

| ID | Behavior | Evidence |
|---|---|---|
| R01 | There are 12 player slots. Team counters initialize to six each and are adjusted for absent/leaving players. | `InitCustomPlayerSlots` L19225 onward; counter initialization L709–710; leave/absent-player logic around L17859–17960. |
| R02 | Main units receive home-side protection ability `A002`. Leaving the relevant side removes it; re-entry restores it. North also has an extra protected region. | `Trig_All_start_invulnerable_but_flags_Actions` L4445–4448; side triggers L4459–4591. |
| R03 | Tagging is implemented through Warcraft unit death, not a custom contact-collision event. The main hero's death creates a stationary jail representation, marks that player's jailed state, and updates kills/deaths. | North base-form handler L14730–14775; South handler L15857–15902. Numerous alternate-form copies exist and are not all individually audited. |
| R04 | A free teammate entering the enemy's jail revives all jailed teammates, not just one. They reappear at their own team's named jailbreak spawn point, not beside the rescuing player. | `Trig_one_jail_rescue_Conditions/Actions` L13748–13792; registration L13795–13800; South counterpart L13805–13857. |
| R05 | Enemy flag pickup uses a 200-unit proximity event for main player units. It hides the flag unit, transfers the flag item, and removes the Wind Walk buff `BOwk`. | `Trig_one_get_flag_*` L17044–17070 and `Trig_two_get_flag_*` L17075–17101. |
| R06 | Carrier death reveals the flag unit at the death position and issues a move order toward its home rectangle center. | North-carrier drop L17106–17129; South-carrier drop L17134–17157. Effective movement speed/pathfinding are not established by the order itself. |
| R07 | A main player carrying the enemy flag scores on entering their home-side region. No own-flag-home prerequisite appears in these capture conditions. | North capture condition L17276–17283 and event L17321–17326; South L17331 onward and L17376–17380. |
| R08 | A flag capture adds one team point and one personal capture. Jailing the entire opposing active team also adds one point. | Capture action L17302–17318; all-jailed predicates L14743–14745 and L15870–15872; score actions L17396–17402 and L17424–17430. |
| R09 | The match is first to a target number of points, not best-of-N rounds. Default target is 5; dialog choices set 3, 5, 7, 10, or 15. Another command sets 999, which is not literally infinity. | Default L727; dialog/actions L2464–2621; command L5005–5011; point threshold L17442–17460. |
| R10 | Between rounds, flags return home, dead heroes revive, players return to starts, cooldowns reset, mana refills, jailed state clears, and temporary effects/groups are cleaned up. | `Trig_reset_all_Actions` L17583–17657. This is a multi-step cinematic reset, not an instantaneous atomic transaction. |
| R11 | Entering the enemy deep side awards an eligible main player 200 gold; returning home restores eligibility. | Gold triggers L4597–4666; re-eligibility L4521–4524 and L4580–4583. Economy is deferred from the browser prototype. |

The `war3map.w3u` overrides for base runner `H000` set base HP to 1, base attack
damage to 1000, speed to 370, and attack cooldown to 1.0. These are **object overrides**,
not a complete proof of final effective engine stats after inherited attributes,
abilities, and gameplay constants. Its base object is `Hmkg`. The prototype directly
implements one-hit tagging instead of importing that unit or its combat engine.

## Important corrections to a generic CTF interpretation

### The center is not merely one zero-width line

Coordinates are Warcraft world coordinates: x increases right, y increases north.
The region definitions at L1061–1088 include:

| Region | x interval | y interval |
|---|---:|---:|
| North home side | -1408 to 2368 | -576 to 2656 |
| South home side | -1376 to 2368 | -3904 to -192 |
| Extra North safe region | -960 to 2368 | 2656 to 3040 |
| Jail in North territory (holds South) | 512 to 928 | 1472 to 1824 |
| Jail in South territory (holds North) | 480 to 928 | -2528 to -2176 |

The two main home regions overlap by 384 units in y, from -576 to -192, wherever
their x intervals also overlap. Their triggers therefore encode a central overlap
of protection, not the single line suggested by an oversimplified diagram.
The exact appearance/pathing of this area still needs an in-engine playtest.

North jailbreak revival is at (192, 576); South revival is at (192, -1344), from
centers of the named spawn rectangles. The rescuer is not teleported by that action.

### Returning flags are a distinct state

Use `HOME | CARRIED | RETURNING`, with an optional `DROPPED` state only if later
needed. Do not silently replace the explicit return-move order with a stationary
flag and a timer, or with touch-to-return by a friendly defender. Enemies can be
allowed to intercept the moving flag in the prototype; exact native range-event
re-entry behavior still needs Warcraft testing.

### Initial placement and reset placement differ

The preplaced flags at L861 and L884 are (704, 2432) and (704, -3136), while named
home rectangle centers used by return/reset are (-32, 2416) and (-32, -3200).
This difference is source-verified; whether it is visible in an actual first round
depends on the full startup/tutorial path, which has not been fully traced here.
The prototype explicitly normalizes initial positions to the reset-home centers.

## Explicit prototype choices already in the foundation

These are reversible development defaults, not confirmed original-map rules.

- Coordinates and named safe/jail regions retain the measured values. Protection
  is recomputed from current position, rather than reproducing possible stale
  ability state caused by old enter/leave-trigger ordering. Rectangle edges are inclusive.
- Initial flag locations use the reset-home centers from round one.
- Bounds are a provisional rectangle; obstacles, destructibles, unit collision
  bodies, Warcraft pathfinding, and exact playable-area edges are not reproduced.
- Movement uses WASD/arrows at 370 world units/s, normalized for diagonals. One
  explicit tag attempt selects a nearby valid enemy. Tag radius 120 is provisional;
  the old effective melee range was not established. The server must enforce a
  1-second cooldown. The pure `tryTag` helper intentionally does not own a clock.
- Returning flags move in a straight line at provisional speed 150 world units/s.
  This is not a claim about the inherited Warcraft flag unit's actual speed.
- Multiple players initially share a team spawn in the rules foundation. The
  browser/server implementation should add deterministic spread positions within
  safe territory; this is not the original twelve-start-location layout.
- Round scoring is atomic: one terminal result per round. The original's overlapping
  waits and triggers are not a behavior to reproduce. A short intermission will be
  implemented by the server. Statistics and match scores persist between rounds.
- A lobby may test with 1v1 or 2v2 as well as 6v6. Empty teams do not automatically
  count as all-jailed. Mid-match join, disconnect grace, and same-tick priorities
  must be implemented/documented in the server, not guessed from these helpers.

## Remaining Stage 1 work

### Implemented browser policies

The runnable server now implements spread spawns, fixed server steps, cooldowns,
three-second intermissions, balanced lobbies, locked match rosters, host transfer,
and a 20-second reconnect grace. Exact event order and same-tick tie handling are
documented in [the server contract](../apps/server/README.md#prototype-decisions-and-deterministic-order).
These remain explicit browser prototype choices, not additional map-source claims.

Solo practice adds three deterministic bots for an immediate 2v2 test. They use the
same movement, safety, tagging, jail and objective rules; their defense/flanking
behavior is new. They do not reproduce Warcraft AI. Multiplayer remains available
without bots and supports one to six players on each team.

### Original-map unknowns

The evidence is sufficient to build a core prototype, not to claim a faithful port
of every system. Still unverified: all alternate-character trigger differences,
actual flag speed/rooting/pathing, precise attack acquisition and range, first-round
flag startup, terrain obstructions, fog/visibility behavior, all spell/item effects,
round reset timing under concurrency, and full leaver handling. Do not infer these
from placeholder constants or general Warcraft knowledge. Test the original when
available, or keep each departure labeled.

Economy, abilities, skins, shops, gambling, admin/novelty commands, and the cinematic
tutorial are outside Stage 2. A public prototype should have original neutral UI text
and no imported Warcraft/third-party art, sounds, or character models.
