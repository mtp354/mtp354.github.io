# Documentation sources

Checked 12 September 2026. Versions and interfaces should be rechecked at dependency
installation. The Warcraft gameplay evidence comes from the supplied file, not from
public descriptions of similarly named maps.

## Codex

Official local quickstart (the developers URL redirected to ChatGPT Learn during
verification), including opening a folder and selecting Codex:

```text
https://developers.openai.com/codex/quickstart
https://learn.chatgpt.com/docs/quickstart
```

Official CLI, repository instructions, and cloud setup:

```text
https://developers.openai.com/codex/cli
https://developers.openai.com/codex/guides/agents-md
https://developers.openai.com/codex/cloud
https://developers.openai.com/codex/environments/cloud-environment
```

AGENTS.md supplies durable per-project instructions. A cloud environment checks out
a connected repository; uncommitted/ignored local material is not part of that checkout.
The prepared project does not create a Codex task or move a chat automatically.

## Browser and multiplayer frameworks

```text
https://docs.phaser.io/phaser/getting-started/installation
https://docs.colyseus.io/
https://docs.colyseus.io/server
https://docs.colyseus.io/room
https://docs.colyseus.io/state
https://docs.colyseus.io/faq
https://docs.colyseus.io/deployment
https://vite.dev/guide/static-deploy.html
```

Phaser's installation documentation provides its TypeScript/browser setup. Colyseus
provides room isolation and server-owned synchronized state. Its current FAQ describes
netcode features, but game-specific protection/tagging policies still need deliberate
implementation and testing. Vite's deployment guide documents static production
output and explicitly says preview is not a production server.

## Archive implementation reference

The MPQ table/hash/sector organization was cross-checked against the original mpyq
implementation. No mpyq dependency or vendored source is required by the project;
the included extractor is a narrow standalone reader for the uploaded map.

```text
https://github.com/eagleflo/mpyq
https://raw.githubusercontent.com/eagleflo/mpyq/master/mpyq.py
```

The included tooling fails on unsupported archive modes. It is not a claim of full
MPQ/Warcraft compatibility and is not part of the eventual game runtime.

## Version-matched implementation references

Checked 12 September 2026 against the installed packages: Colyseus server
`0.18.5`, SDK `0.18.2`, Schema `5.0.28`; Phaser `3.90.0`; Vite `8.3.0`.
The Colyseus documentation shown here is explicitly marked **v0.18**. The
Schema 5 builder uses `schema()` with `t.*`, and the room exposes `messages`,
`onDrop`, `allowReconnection`, and `onReconnect` as used in the implementation.

- [Colyseus 0.18 server setup](https://docs.colyseus.io/recipes/setup-server-from-scratch-typescript)
- [Colyseus 0.18 rooms and message handling](https://docs.colyseus.io/room)
- [Colyseus 0.18 Schema builder](https://docs.colyseus.io/state/schema)
- [Colyseus 0.18 reconnection](https://docs.colyseus.io/room/reconnection)
- [Colyseus 0.18 HTTP routes](https://docs.colyseus.io/server/http-routes)
- [Phaser 3 npm installation and TypeScript types](https://docs.phaser.io/phaser/getting-started/installation)
- [Vite base and build-time environment variables](https://vite.dev/guide/env-and-mode)
