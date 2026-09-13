# Capture the Flag — standalone browser project

A local project handoff for Codex. Prepared 12 September 2026.

**Current status:** core map evidence reviewed, a TypeScript rules foundation written,
and 27 automated tests passing. **The browser client and multiplayer server have not
yet been implemented.** Their concrete build task is in `CODEX_FIRST_TASK.md`.

## Start in Codex

1. Extract `ctf-browser-starter.zip`.
2. For local source verification, extract `ctf-private-reference.zip` beside it so
   its contents merge into `ctf-browser-starter/reference-private/`. These files are
   intentionally excluded from Git and browser builds.
3. Open the `ctf-browser-starter` folder in Codex's local environment (desktop or IDE),
   or run the Codex CLI from that directory. Read/paste `CODEX_FIRST_TASK.md`.

The files are the handoff; do not depend on this chat or its attachments appearing
automatically in another environment. Local development is the simplest first path.
A cloud Codex environment instead needs a connected repository containing the source
and docs. Ignored local reference files will not magically appear in that environment.
Core build work can proceed from the specification; do not publish the old map just to
make it available to an agent.

## Run the existing checks

Install Node.js with npm (Node 22 or newer), then in this folder:

```sh
npm install
npm test
npm run typecheck
```

The handoff was tested with preinstalled Node 22.16.0 and TypeScript 5.8.3. A fresh
npm dependency installation was not performed in the handoff environment. Codex
should install dependencies, create `package-lock.json`, and retest from a clean
checkout. The pinned compiler version is a tested baseline, not a claim of latest.

There is deliberately **no `npm run dev` yet**. That is a required deliverable of
Codex's first implementation task. The Python reference tools use only the standard
library; they are not required to run the game or the TypeScript tests.

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
| `apps/client/`, `apps/server/` | Reserved implementation locations; currently briefs only |

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
