# Browser client

Phaser 3 + TypeScript + Vite render the arena, minimap, labels, lobby, and HUD.
The client sends only movement direction, a sequence number, and an explicit tag
attempt. Server snapshots are authoritative; the client interpolates displayed
positions but does not predict hits. Run `npm run dev` at the project root.

`VITE_CTF_SERVER_URL` sets the Colyseus endpoint at Vite build time (default
`http://127.0.0.1:2567`). `CTF_BASE_PATH` sets Vite's asset base path (default `/`).
The output is `apps/client/dist`. No private map material is needed or copied.
