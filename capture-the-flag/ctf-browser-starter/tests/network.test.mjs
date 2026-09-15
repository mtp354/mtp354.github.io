import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { setTimeout as delay } from 'node:timers/promises';
import { Client } from 'colyseus.js';
import { matchMaker } from '@colyseus/core';
import { createGameServer } from '../apps/server/dist/server.js';
import { DEFAULT_CONFIG, center } from '../packages/rules/dist/index.js';

// These are real HTTP matchmaking + WebSocket clients. Position injection is
// deliberately confined to this in-process harness; production exposes no cheat
// message or debug endpoint. All actions and observations use the normal wire API.
let service;
before(async () => {
  service = await createGameServer({ port: 0, host: '127.0.0.1', reconnectSeconds: 1 });
}, { timeout: 10000 });
after(async () => { await service?.close(); }, { timeout: 5000 });

async function until(predicate, description, timeout = 4000) {
  const deadline = performance.now() + timeout;
  while (performance.now() < deadline) {
    if (predicate()) return;
    await delay(15);
  }
  assert.fail(`Timed out waiting for ${description}`);
}

async function roster(t, count = 2, options = {}) {
  const sdk = new Client(service.url);
  const active = new Set();
  t.after(async () => {
    await Promise.allSettled([...active].map(room => room.leave(true)));
  });
  const host = await sdk.create('ctf', { nickname: 'Player 1', ...options });
  host.onMessage('notice', () => {});
  active.add(host);
  const rooms = [host];
  for (let i = 1; i < count; i++) {
    const room = await sdk.joinById(host.roomId, { nickname: `Player ${i + 1}` });
    room.onMessage('notice', () => {});
    active.add(room);
    rooms.push(room);
  }
  await until(() => rooms.every(room => room.state.players?.has(room.sessionId) && room.state.players.size >= count), 'initial synchronized roster');
  const local = matchMaker.getLocalRoomById(host.roomId);
  assert(local, 'the room is owned by this test process');
  const player = room => local.simulation.match.players.find(p => p.id === room.sessionId);
  const byTeam = team => rooms.filter(room => player(room).team === team);
  const position = (room, x, y) => {
    Object.assign(player(room), { x, y });
    local.projectState();
  };
  const start = async () => {
    host.send('start', {});
    await until(() => rooms.every(room => room.state.phase === 'playing'), 'all clients to start');
  };
  const reconnect = async (room, onDisconnected = () => {}) => {
    const token = room.reconnectionToken;
    const id = room.sessionId;
    active.delete(room);
    // 4000 means an intentional Colyseus leave; 1000 closes only the socket.
    room.connection.close(1000);
    await until(() => local.simulation.players.get(id)?.connected === false, 'disconnect acknowledgement');
    onDisconnected();
    const resumed = await sdk.reconnect(token);
    active.add(resumed);
    await until(() => resumed.state.players?.get(id)?.connected === true, 'reconnected state');
    assert.equal(resumed.sessionId, id);
    return resumed;
  };
  return { sdk, active, rooms, host, local, player, byTeam, position, start, reconnect };
}

const input = (room, sequence, moveX = 0, moveY = 0, tag = false) =>
  room.send('input', { sequence, moveX, moveY, tag });
const point = p => ({ x: p.x, y: p.y });

test('real clients synchronize movement, enforce the host, and isolate rooms', { timeout: 12000 }, async t => {
  const a = await roster(t, 2);
  const b = await roster(t, 1);
  assert.notEqual(a.host.roomId, b.host.roomId);
  assert.equal(a.host.state.hostId, a.host.sessionId);
  assert.equal(a.host.state.players.size, 2);
  assert.equal(b.host.state.players.size, 1);
  assert.equal(a.host.state.players.has(b.host.sessionId), false);
  const original = point(a.player(a.host));
  input(a.host, 1, 1);
  a.rooms[1].send('start', {});
  await delay(160);
  assert.equal(a.local.simulation.match.phase, 'lobby');
  assert.deepEqual(point(a.player(a.host)), original, 'movement is frozen in the lobby');
  await a.start();
  input(a.host, 2, 1);
  await until(() => a.rooms.every(room => room.state.players.get(a.host.sessionId).x > original.x + 10), 'movement on both sockets');
  input(a.host, 3);
  await delay(100);
  assert.equal(a.host.state.players.get(a.host.sessionId).x, a.rooms[1].state.players.get(a.host.sessionId).x);
  assert.equal(b.host.state.phase, 'lobby');
  assert.equal(b.host.state.northScore + b.host.state.southScore, 0);
});

test('nicknames, spoofed actors, invalid input, sequences, rate bursts, and stale input are bounded', { timeout: 12000 }, async t => {
  const g = await roster(t, 2, { nickname: '  Alice\u0000\n' + 'x'.repeat(30) });
  const nickname = g.host.state.players.get(g.host.sessionId).nickname;
  assert(nickname.length > 0 && nickname.length <= 24, 'nickname has a short server-enforced cap');
  assert.equal(/[\u0000-\u001f\u007f]/u.test(nickname), false);
  await assert.rejects(g.sdk.joinById(g.host.roomId, { nickname: 'x'.repeat(1000) }));
  await assert.rejects(g.sdk.joinById(g.host.roomId, { nickname: 'Spoof', team: 'north', id: g.host.sessionId }));
  await g.start();
  const me = g.player(g.host);
  const other = g.player(g.rooms[1]);
  const meStart = point(me);
  const otherStart = point(other);
  input(g.host, 10, 1);
  await until(() => me.x > meStart.x + 10, 'valid movement');
  input(g.host, 11);
  await delay(90);
  const stopped = point(me);
  for (const payload of [
    { sequence: 11, moveX: 1, moveY: 0, tag: false },
    { sequence: 9, moveX: 1, moveY: 0, tag: false },
    { sequence: 100, moveX: 1, moveY: 0, tag: false, id: other.id },
    { sequence: 100, moveX: 1, moveY: 0, tag: false, x: 999999 },
    { sequence: 100, moveX: 1e12, moveY: 0, tag: false },
    { sequence: 100, moveX: NaN, moveY: 0, tag: false },
    { sequence: 100, moveX: 0, moveY: Infinity, tag: false },
    { sequence: -1, moveX: 1, moveY: 0, tag: false },
    { sequence: 12.5, moveX: 1, moveY: 0, tag: false },
    { sequence: 100, moveX: 1, moveY: 0, tag: 1 },
    null,
    [],
    'move right',
  ]) g.host.send('input', payload);
  await delay(200);
  assert.deepEqual(point(me), stopped);
  assert.deepEqual(point(other), otherStart, 'a client cannot select another actor');
  input(g.host, 12, 1);
  await until(() => me.x > stopped.x + 5, 'valid sequence after rejected messages');
  input(g.host, 13);
  await delay(100);
  const burstStart = point(me);
  const timeStart = g.local.simulation.time;
  for (let sequence = 1000; sequence < 1300; sequence++) input(g.host, sequence, 1, 1);
  await delay(180);
  const elapsed = g.local.simulation.time - timeStart;
  const moved = Math.hypot(me.x - burstStart.x, me.y - burstStart.y);
  assert(moved > 0, 'the burst contains valid movement');
  assert(moved <= DEFAULT_CONFIG.speed * elapsed + 0.01, 'message frequency cannot accelerate movement');
  assert(g.local.simulation.players.get(me.id).sequence < 1299, 'the input burst exceeds the per-session rate limit');
  await delay(900);
  const stale = point(me);
  await delay(180);
  assert.deepEqual(point(me), stale, 'movement expires when packets stop');
});

test('health exposes only service status and oversized frames cannot change the world', { timeout: 10000 }, async t => {
  const health = await fetch(`${service.url}/health`);
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { ok: true, service: 'ctf' });
  const g = await roster(t, 2);
  await g.start();
  const original = point(g.player(g.host));
  let closeCode;
  g.host.onLeave(code => { closeCode = code; });
  g.host.send('input', { sequence: 1, moveX: 1, moveY: 0, tag: false, junk: 'x'.repeat(2048) });
  await until(() => closeCode !== undefined, 'oversized frame to close the socket');
  g.active.delete(g.host);
  assert.equal(closeCode, 1009, 'WebSocket message-too-large close code');
  assert.deepEqual(point(g.player(g.host)), original);
  assert.equal(g.local.simulation.match.score.north + g.local.simulation.match.score.south, 0);
  assert.equal((await fetch(`${service.url}/health`)).status, 200, 'the server stays healthy');
});

test('sockets complete tag, jail, rescue, two flag pickups, capture, freeze, and round reset', { timeout: 14000 }, async t => {
  const g = await roster(t, 4);
  await g.start();
  const [north, rescuer] = g.byTeam('north');
  const [defender, southCarrier] = g.byTeam('south');
  g.position(north, 0, -1100);
  g.position(defender, 20, -1100);
  input(defender, 1, 0, 0, true);
  await until(() => g.rooms.every(room => room.state.players.get(north.sessionId).status === 'jailed'), 'network jail');
  assert.equal(g.player(north).deaths, 1);
  assert.equal(g.player(defender).kills, 1);
  assert.deepEqual(point(g.player(north)), center(DEFAULT_CONFIG.jail.south));
  input(north, 1, 1, 1, true);
  await delay(120);
  assert.deepEqual(point(g.player(north)), center(DEFAULT_CONFIG.jail.south), 'jailed input is ignored');
  input(north, 2);
  await delay(50);
  g.position(rescuer, 704, -2352);
  await until(() => g.host.state.players.get(north.sessionId).status === 'free', 'jailbreak');
  assert.deepEqual(point(g.player(north)), DEFAULT_CONFIG.rescueSpawn.north);
  assert.deepEqual(point(g.player(rescuer)), { x: 704, y: -2352 }, 'the rescuer stays in place');
  g.position(north, DEFAULT_CONFIG.flagHome.south.x, DEFAULT_CONFIG.flagHome.south.y);
  g.position(southCarrier, DEFAULT_CONFIG.flagHome.north.x, DEFAULT_CONFIG.flagHome.north.y);
  await until(() => g.rooms.every(room => room.state.flags.get('south').carrierId === north.sessionId && room.state.flags.get('north').carrierId === southCarrier.sessionId), 'both flags carried');
  g.position(north, 0, -580);
  input(north, 3, 0, 1);
  await until(() => g.rooms.every(room => room.state.phase === 'roundOver'), 'capture on home-side entry');
  assert.equal(g.host.state.northScore, 1);
  assert.equal(g.host.state.southScore, 0);
  assert.equal(g.host.state.lastPointReason, 'capture');
  assert.equal(g.player(north).captures, 1);
  const frozen = point(g.player(north));
  input(north, 4, 1, 1, true);
  input(defender, 2, 1, 1, true);
  await delay(150);
  assert.deepEqual(point(g.player(north)), frozen, 'intermission freezes movement');
  assert.equal(g.local.simulation.match.score.north + g.local.simulation.match.score.south, 1);
  await until(() => g.rooms.every(room => room.state.round === 2 && room.state.phase === 'playing'), 'automatic next round', 4500);
  assert.equal(g.host.state.northScore, 1);
  assert.equal(g.host.state.players.get(north.sessionId).captures, 1);
  assert.equal(g.host.state.players.get(north.sessionId).deaths, 1);
  for (const flag of g.host.state.flags.values()) assert.equal(flag.status, 'home');
  for (const p of g.host.state.players.values()) assert.equal(p.status, 'free');
  assert.equal(new Set(g.byTeam('north').map(room => `${g.player(room).x},${g.player(room).y}`)).size, 2, 'spawn positions are spread');
});

test('tag cooldown prevents rapid repeats and all-jailed awards exactly one point', { timeout: 10000 }, async t => {
  const g = await roster(t, 4);
  await g.start();
  const [attacker] = g.byTeam('north');
  const [first, second] = g.byTeam('south');
  g.position(attacker, 0, 448);
  g.position(first, 20, 448);
  g.position(second, 80, 448);
  input(attacker, 1, 0, 0, true);
  await until(() => g.host.state.players.get(first.sessionId).status === 'jailed', 'nearest eligible victim');
  input(attacker, 2, 0, 0, true);
  await delay(180);
  assert.equal(g.player(second).status, 'free');
  assert.equal(g.player(attacker).kills, 1);
  assert.equal(g.local.simulation.match.phase, 'playing');
  await delay(1050);
  input(attacker, 3, 0, 0, true);
  await until(() => g.host.state.phase === 'roundOver', 'all-jailed point');
  assert.equal(g.host.state.lastPointReason, 'allJailed');
  assert.equal(g.host.state.northScore, 1);
  assert.equal(g.host.state.southScore, 0);
  assert.equal(g.player(attacker).kills, 2);
  for (let seq = 4; seq < 15; seq++) input(attacker, seq, 0, 0, true);
  await delay(120);
  assert.equal(g.local.simulation.match.score.north, 1);
});

test('disconnect drops a carried flag and reconnection preserves identity, slot, and jail', { timeout: 12000 }, async t => {
  const g = await roster(t, 4);
  await g.start();
  let [north] = g.byTeam('north');
  const [defender] = g.byTeam('south');
  const originalId = north.sessionId;
  const originalSlot = g.host.state.players.get(originalId).slot;
  g.position(north, DEFAULT_CONFIG.flagHome.south.x, DEFAULT_CONFIG.flagHome.south.y);
  await until(() => g.local.simulation.match.flags.south.carrierId === originalId, 'flag pickup before disconnect');
  g.position(north, 0, -1500);
  north = await g.reconnect(north, () => {
    assert.equal(g.local.simulation.match.flags.south.status, 'returning');
    assert.equal(g.local.simulation.match.flags.south.carrierId, null);
  });
  assert.equal(north.state.players.size, 4);
  assert.equal(north.state.players.get(originalId).slot, originalSlot);
  assert.equal(g.local.simulation.match.players.filter(p => p.id === originalId).length, 1);
  g.position(defender, g.player(north).x + 20, g.player(north).y);
  input(defender, 1, 0, 0, true);
  await until(() => north.state.players.get(originalId).status === 'jailed', 'jail before reconnect');
  north = await g.reconnect(north);
  assert.equal(north.state.players.get(originalId).status, 'jailed');
  assert.equal(north.state.players.get(originalId).deaths, 1);
  assert.equal(north.state.players.size, 4);
  input(north, 99, 1, 1, true);
  await delay(140);
  assert.deepEqual(point(g.player(north)), center(DEFAULT_CONFIG.jail.south));
});

test('host transfer permits starting, active joins are locked, and expired empty teams end explicitly', { timeout: 10000 }, async t => {
  const g = await roster(t, 2);
  const successor = g.rooms[1];
  await g.host.leave(true);
  g.active.delete(g.host);
  await until(() => successor.state.hostId === successor.sessionId && successor.state.players.size === 1, 'host transfer');
  const newcomer = await g.sdk.joinById(successor.roomId, { nickname: 'Replacement' });
  g.active.add(newcomer);
  await until(() => newcomer.state.players?.size === 2, 'replacement player');
  successor.send('start', {});
  await until(() => successor.state.phase === 'playing', 'new host starts');
  await assert.rejects(g.sdk.joinById(successor.roomId, { nickname: 'Too late' }));
  const lostId = newcomer.sessionId;
  newcomer.connection.close(1000);
  g.active.delete(newcomer);
  await until(() => successor.state.phase === 'finished', 'grace expiry ends match', 4500);
  assert.equal(successor.state.players.has(lostId), false);
  assert.match(successor.state.endReason, /disconnect|empty|no players left/i);
  assert.equal(successor.state.northScore + successor.state.southScore, 0, 'disconnect does not silently award points');
});

test('twelve WebSocket clients form 6v6, while a thirteenth cannot join', { timeout: 15000 }, async t => {
  const g = await roster(t, 12);
  await until(() => g.rooms.every(room => room.state.players.size === 12), 'twelve synchronized rosters');
  assert.equal(g.byTeam('north').length, 6);
  assert.equal(g.byTeam('south').length, 6);
  assert.equal(new Set([...g.host.state.players.values()].map(p => p.slot)).size, 12);
  await assert.rejects(g.sdk.joinById(g.host.roomId, { nickname: 'Player 13' }));
  await g.start();
  assert.equal(g.local.simulation.match.players.length, 12);
});

test('a practice room supplies moving opponents and accepts normal human input', { timeout: 10000 }, async t => {
  const g = await roster(t, 1, { practice: true });
  await until(() => [...g.host.state.players.values()].some(p => p.bot), 'practice bots');
  if (g.host.state.phase === 'lobby') await g.start();
  assert.equal(g.host.state.practice, true);
  const human = g.player(g.host);
  const bots = g.local.simulation.match.players.filter(p => g.local.simulation.players.get(p.id).bot);
  assert(bots.some(p => p.team !== human.team));
  const previous = new Map(bots.map(p => [p.id, point(p)]));
  const humanStart = point(human);
  input(g.host, 1, 1);
  await until(() => g.host.state.players.get(human.id).x > humanStart.x + 10, 'practice human movement');
  await until(() => bots.some(p => Math.hypot(p.x - previous.get(p.id).x, p.y - previous.get(p.id).y) > 10), 'autonomous practice movement');
});
