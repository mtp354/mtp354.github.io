# Project: standalone browser Capture the Flag

## Read first
Read README.md, docs/CORE_RULES.md, docs/PROTOTYPE_PLAN.md, and docs/VALIDATION.md.
The user wants a standalone in-browser multiplayer game, eventually hosted through
his personal website. The old Warcraft III map is a design reference, not the runtime.
This repository currently contains a tested TypeScript rules foundation, NOT a
working Phaser client or Colyseus server. Implement those next; do not merely plan them.

## Development decisions
- Phaser + TypeScript + Vite client; Colyseus + Node/TypeScript authoritative server.
- Keep gameplay rules independent of Phaser, DOM, sockets, and Colyseus Schema.
- Validate dependency/API compatibility against official version-matched docs.
  Install compatible versions and commit a lockfile. Do not mix Colyseus 0.16 examples
  with newer APIs. The existing compiler is pinned to the version tested at handoff;
  updating it is allowed with successful checks.
- Browser messages express intent only. Server assigns identity/team and owns time,
  motion, tags, jail, flag ownership, scores, cooldowns, and round transitions.
- The pure helpers are NOT a complete security boundary. The server must enforce
  session ownership, sequence monotonicity, message rate/size, cooldowns, stale-input
  expiry, fixed timestep, round-phase gates, and deterministic event ordering.
- Distinguish source-verified facts, inherited-engine unknowns, and new prototype
  choices. Document every gameplay departure. Prior chat summaries are not authority.
- Use source line references in docs/CORE_RULES.md and the private JASS index when
  checking old behavior. Never execute JASS or unknown map scripts.

## Scope
First deliver two browser tabs in one room playing the complete basic CTF/jail loop.
Then verify 12 network clients and a 6v6 manual checklist. Shapes and labels only.
Do not add accounts, databases, shops, gold, gambling, cosmetics, wards, blink,
invisibility, imported assets, public matchmaking, or website deployment yet.
Use WASD/arrows + explicit tag action as a documented prototype control scheme.
Keep game endpoint and client base path configurable for later website hosting.
Do not re-platform the user's personal website.

## Source and publication boundaries
reference-private/ is user-supplied reference material, intentionally ignored by Git.
The companion reference ZIP contains the old .w3x and extracted code/object data.
Do not put these in client assets, public/, dist/, a public repository, or a deployment.
Do not reproduce old offensive strings or named third-party character art.
Open-source engine choice does not set the licensing of this game's own code.
Do not deploy, create paid resources, publish a repository, change DNS, or access
website credentials without a separate explicit user request.

## Verify
Run npm install once; generate and retain package-lock.json. Then run:
- npm test
- npm run typecheck
After implementing client/server, provide npm run dev and npm run build, network
integration tests, and preferably a two-browser-context Playwright smoke test.
Record exact commands/results and remaining failures in docs/VALIDATION.md.
Do not describe the prototype as playable until the browser/network loop was tested.
Commit small, reviewable local milestones. Do not push remote changes implicitly.
