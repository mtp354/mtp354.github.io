import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';
import { Client } from 'colyseus.js';
import { matchMaker } from '@colyseus/core';
import { createGameServer } from '../../apps/server/dist/server.js';

const service = await createGameServer({ port: 0, host: '127.0.0.1', reconnectSeconds: 20 });
try {
  const sdk = new Client(service.url);
  const host = await sdk.create('ctf', { nickname: 'Host' });
  const guest = await sdk.joinById(host.roomId, { nickname: 'Guest' });
  const local = matchMaker.getLocalRoomById(host.roomId);
  let guestClosed = false;
  guest.onLeave(() => { guestClosed = true; });
  host.connection.close(1000);
  const deadline = performance.now() + 3000;
  while (local.simulation.players.get(host.sessionId)?.connected !== false && performance.now() < deadline) await delay(10);
  assert.equal(local.simulation.players.get(host.sessionId)?.connected, false);
  assert.equal(local.simulation.players.size, 2, 'the disconnected slot is still reserved');
  await service.close();
  const closedDeadline = performance.now() + 3000;
  while (!guestClosed && performance.now() < closedDeadline) await delay(10);
  assert.equal(guestClosed, true);
  assert.equal(service.httpServer.listening, false);
  assert.equal(matchMaker.getLocalRoomById(host.roomId), undefined);
  await delay(100);
  console.log('shutdown complete');
} finally {
  await service.close();
}
