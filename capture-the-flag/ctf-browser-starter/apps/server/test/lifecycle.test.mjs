import test from 'node:test';
import assert from 'node:assert/strict';
import { CtfRoom } from '../dist/room.js';
import { GameState } from '../dist/state.js';
import { GameSimulation } from '../dist/simulation.js';

// Deliberately control the promise boundary without sockets: shutdown may dispose
// a room before a pending reconnection settles in Colyseus 0.16.
for (const outcome of ['resolve', 'reject']) {
  test(`a reconnection ${outcome} after disposal does not mutate or reproject cleared players`, async () => {
    const room = new CtfRoom();
    room.simulation = new GameSimulation();
    room.simulation.addPlayer('p0', 'Player');
    room.setState(new GameState());
    room.projectState();
    let settle;
    room.allowReconnection = () => new Promise((resolve, reject) => { settle = outcome === 'resolve' ? resolve : reject; });
    const leaving = room.onLeave({sessionId: 'p0'}, false);
    assert.equal(room.simulation.players.get('p0').connected, false);
    room.onDispose();
    settle();
    await assert.doesNotReject(leaving);
    assert.equal(room.simulation.players.size, 0);
    assert.ok(room.clock.delayed.every(timer => !timer.active), 'reconnection expiry no longer holds a live timer');
    assert.doesNotThrow(() => room.projectState());
    await assert.doesNotReject(room.onLeave({sessionId: 'p0'}, true));
  });
}

test('disposal is safe when invalid creation options prevented simulation initialization', () => {
  const room = new CtfRoom();
  assert.throws(() => room.onCreate({nickname: ''}));
  assert.doesNotThrow(() => room.onDispose());
});
