import { createEndpoint, createRouter, defineRoom, defineServer } from 'colyseus';
import { pathToFileURL } from 'node:url';
import { GameRoom } from './GameRoom.js';

const health = createEndpoint('/health', { method: 'GET', metadata: { scope: 'http' } }, async () => ({ ok: true }));

export function createGameServer() {
  return defineServer({
    rooms: { ctf: defineRoom(GameRoom) },
    routes: createRouter({ health }),
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const port = Number(process.env.CTF_PORT ?? 2567);
  if (!Number.isSafeInteger(port) || port < 1 || port > 65535) throw new Error('Invalid CTF_PORT');
  createGameServer().listen(port);
}
