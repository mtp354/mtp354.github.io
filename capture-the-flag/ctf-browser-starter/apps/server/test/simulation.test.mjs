import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_CONFIG } from '@ctf/rules';
import { FixedStepLoop, GameSimulation, INTERMISSION_SECONDS, STEP_SECONDS, parseJoin } from '../dist/simulation.js';

function fixture(count = 4) {
  let now = 0;
  const game = new GameSimulation(false, () => now);
  for (let i = 0; i < count; i++) assert.equal(game.addPlayer(`p${i}`, `Player ${i}`), true);
  assert.equal(game.start('p0'), true);
  const sequences = new Map();
  return {
    game,
    p: id => game.match.players.find(player => player.id === id),
    input(id, values = {}) {
      const sequence = (sequences.get(id) ?? 0) + 1;
      sequences.set(id, sequence);
      return game.acceptInput(id, {sequence, moveX: 0, moveY: 0, tag: false, ...values});
    },
    tick(count = 1) {
      for (let i = 0; i < count; i++) { now += STEP_SECONDS; game.step(); }
    },
    advance(seconds) { now += seconds; },
  };
}

test('join options are bounded text with no actor/team or unexpected fields', () => {
  assert.deepEqual(parseJoin({nickname: '  Test\u0000 person  '}), {nickname: 'Test person', practice: false});
  assert.equal(parseJoin({nickname: 'Player', team: 'north'}), null);
  assert.equal(parseJoin({nickname: ' '.repeat(20)}), null);
  assert.equal(parseJoin({nickname: 'x'.repeat(49)}), null);
  assert.equal(parseJoin({nickname: 'Player', practice: 'true'}), null);
});

test('balanced twelve-player lobby, safe spread, host authorization, and locked active roster', () => {
  const game = new GameSimulation();
  for (let i = 0; i < 12; i++) assert.equal(game.addPlayer(`p${i}`, `Player ${i}`), true);
  assert.equal(game.addPlayer('thirteenth', 'Too late'), false);
  assert.equal(game.match.players.filter(player => player.team === 'north').length, 6);
  assert.equal(new Set(game.match.players.filter(player => player.team === 'north').map(player => player.x)).size, 6);
  assert.equal(game.start('p1'), false);
  assert.equal(game.start('p0'), true);
  game.removePlayer('p11');
  assert.equal(game.addPlayer('newcomer', 'Too late'), false);
});

test('invalid, spoofed, duplicate, and out-of-order intents cannot change the latest accepted input', () => {
  const {game, input} = fixture();
  assert.equal(input('p0', {moveX: 1}), true);
  const accepted = {...game.players.get('p0').input};
  for (const payload of [
    {...accepted, sequence: 2, playerId: 'p1'},
    {...accepted, sequence: 2, moveX: Infinity},
    {...accepted, sequence: 2, moveY: NaN},
    {...accepted, sequence: 2, moveX: 1.1},
    {...accepted, sequence: 2, tag: 1},
    {...accepted, sequence: 0},
    {...accepted, sequence: 1},
  ]) assert.equal(game.acceptInput('p0', payload), false);
  assert.equal(game.acceptInput('missing', accepted), false);
  assert.deepEqual(game.players.get('p0').input, accepted);
});

test('a burst is bounded and never produces more than one movement step; old intent expires', () => {
  const {game, p, input, tick, advance} = fixture();
  const origin = {x: p('p0').x, y: p('p0').y};
  let accepted = 0;
  for (let i = 0; i < 1000; i++) if (input('p0', {moveX: 1, moveY: 1})) accepted++;
  assert.equal(accepted, 90);
  tick();
  assert.ok(Math.abs(Math.hypot(p('p0').x - origin.x, p('p0').y - origin.y) - DEFAULT_CONFIG.speed * STEP_SECONDS) < 1e-8);
  const stopped = {x: p('p0').x, y: p('p0').y};
  advance(0.3);
  tick(3);
  assert.deepEqual({x: p('p0').x, y: p('p0').y}, stopped);
});

test('tag attempts consume a one-second cooldown including misses and cannot tag safe players', () => {
  const {game, p, input, tick} = fixture();
  Object.assign(p('p0'), {x: 0, y: 100});
  Object.assign(p('p1'), {x: 0, y: 150});
  assert.equal(input('p0', {tag: true}), true);
  tick();
  assert.equal(p('p1').status, 'jailed');
  Object.assign(p('p3'), {x: 0, y: 150});
  input('p0', {tag: true});
  tick();
  assert.equal(p('p3').status, 'free');
  tick(29);
  input('p0', {tag: true});
  tick();
  assert.equal(p('p3').status, 'jailed');
  assert.equal(game.match.lastPoint.reason, 'allJailed');

  const safe = fixture();
  Object.assign(safe.p('p0'), {x: 0, y: -400});
  Object.assign(safe.p('p1'), {x: 0, y: -400});
  safe.input('p0', {tag: true});
  safe.tick();
  assert.equal(safe.p('p1').status, 'free');
  assert.ok(safe.game.players.get('p0').tagReadyAt > safe.game.time);
});

test('tags win same-tick conflicts before rescues and captures, with one point total', () => {
  const {game, p, input, tick} = fixture(2);
  Object.assign(p('p0'), {x: 0, y: 100});
  Object.assign(p('p1'), {x: 0, y: 150});
  Object.assign(game.match.flags.south, {status: 'carried', carrierId: 'p0', x: 0, y: 100});
  input('p0', {tag: true});
  tick();
  assert.deepEqual(game.match.score, {north: 1, south: 0});
  assert.deepEqual(game.match.lastPoint, {winner: 'north', reason: 'allJailed'});
  assert.equal(p('p0').captures, 0);
});

test('simultaneous captures resolve in stable slot order even if canonical array is reordered', () => {
  const {game, p, tick} = fixture();
  Object.assign(game.match.flags.south, {status: 'carried', carrierId: 'p0', x: p('p0').x, y: p('p0').y});
  Object.assign(game.match.flags.north, {status: 'carried', carrierId: 'p1', x: p('p1').x, y: p('p1').y});
  game.match.players.reverse();
  tick();
  assert.deepEqual(game.match.score, {north: 1, south: 0});
  assert.equal(game.match.lastPoint.reason, 'capture');
});

test('jailbreak returns every teammate home without teleporting the rescuer', () => {
  const {game, p, tick} = fixture(6);
  Object.assign(p('p0'), {status: 'jailed', x: 700, y: -2300});
  Object.assign(p('p2'), {status: 'jailed', x: 700, y: -2300});
  Object.assign(p('p4'), {x: 600, y: -2300});
  tick();
  for (const id of ['p0', 'p2']) {
    assert.equal(p(id).status, 'free');
    assert.equal(p(id).x, DEFAULT_CONFIG.rescueSpawn.north.x);
    assert.equal(p(id).y, DEFAULT_CONFIG.rescueSpawn.north.y);
  }
  assert.equal(p('p4').x, 600);
  assert.equal(p('p4').y, -2300);
  assert.deepEqual(game.match.score, {north: 0, south: 0});
});

test('round intermission freezes intent, resets positions/cooldowns, and preserves stats', () => {
  const {game, p, input, tick} = fixture();
  Object.assign(game.match.flags.south, {status: 'carried', carrierId: 'p0', x: p('p0').x, y: p('p0').y});
  tick();
  assert.equal(game.match.phase, 'roundOver');
  const x = p('p0').x;
  assert.equal(input('p0', {moveX: 1, tag: true}), false);
  tick(15);
  assert.equal(p('p0').x, x);
  tick(Math.ceil(INTERMISSION_SECONDS / STEP_SECONDS));
  assert.equal(game.match.phase, 'playing');
  assert.equal(game.match.round, 2);
  assert.equal(p('p0').captures, 1);
  assert.deepEqual(game.match.score, {north: 1, south: 0});
  assert.equal(game.match.flags.south.status, 'home');
  assert.equal(game.players.get('p0').pendingTag, false);
});

test('disconnect drops a carrier immediately, retains a taggable body, and reconnect preserves jail', () => {
  const {game, p, input, tick} = fixture();
  Object.assign(p('p0'), {x: 0, y: -1000});
  Object.assign(p('p1'), {x: 0, y: -1000});
  Object.assign(game.match.flags.south, {status: 'carried', carrierId: 'p0', x: 0, y: -1000});
  game.disconnect('p0');
  assert.equal(game.match.flags.south.status, 'returning');
  assert.equal(game.match.flags.south.carrierId, null);
  assert.equal(game.hostId, 'p1');
  input('p1', {tag: true});
  tick();
  assert.equal(p('p0').status, 'jailed');
  assert.equal(game.reconnect('p0'), true);
  assert.equal(p('p0').status, 'jailed');
  assert.equal(game.match.players.length, 4);
  assert.equal(game.hostId, 'p1');
});

test('a disconnected body cannot rescue teammates or pick up a returning flag', () => {
  const {game, p, tick} = fixture();
  Object.assign(p('p0'), {x: 600, y: -2300});
  Object.assign(p('p2'), {status: 'jailed', x: 700, y: -2300});
  game.disconnect('p0');
  Object.assign(game.match.flags.south, {status: 'returning', carrierId: null, x: 600, y: -2300});
  tick();
  assert.equal(p('p2').status, 'jailed');
  assert.equal(game.match.flags.south.status, 'returning');
});

test('last team member expiry finishes explicitly without inventing a point', () => {
  const {game} = fixture(2);
  game.removePlayer('p1');
  assert.equal(game.match.phase, 'finished');
  assert.match(game.endReason, /no players left/);
  assert.deepEqual(game.match.score, {north: 0, south: 0});
  assert.equal(game.rematch('p0'), false);
});

test('only host can rematch a finished match and scores/statistics reset', () => {
  const {game, p, tick} = fixture();
  game.match.targetScore = 1;
  Object.assign(game.match.flags.south, {status: 'carried', carrierId: 'p0', x: p('p0').x, y: p('p0').y});
  tick();
  assert.equal(game.match.phase, 'finished');
  assert.equal(game.rematch('p1'), false);
  assert.equal(game.rematch('p0'), true);
  assert.equal(game.match.phase, 'playing');
  assert.deepEqual(game.match.score, {north: 0, south: 0});
  assert.equal(p('p0').captures, 0);
});

test('practice bots advance through the same fixed speed and cooldown rules', () => {
  let now = 0;
  const game = new GameSimulation(true, () => now);
  game.addPlayer('human', 'Player');
  game.addPracticeBots();
  assert.equal(game.start('human'), true);
  assert.equal(game.players.size, 4);
  const before = game.match.players.map(player => ({...player}));
  now += STEP_SECONDS;
  game.step();
  for (const bot of game.match.players.filter(player => player.id !== 'human')) {
    const old = before.find(player => player.id === bot.id);
    assert.ok(Math.hypot(bot.x - old.x, bot.y - old.y) <= DEFAULT_CONFIG.speed * STEP_SECONDS + 1e-8);
  }
  assert.notEqual(game.match.players[1].y, before[1].y);
});

test('practice bots can finish a full match instead of stalling at an objective', () => {
  let now = 0;
  const game = new GameSimulation(true, () => now);
  game.addPlayer('human', 'Player');
  game.addPracticeBots();
  game.start('human');
  for (let i = 0; i < 30 * 180 && game.match.phase !== 'finished'; i++) {
    now += STEP_SECONDS;
    game.step();
  }
  assert.equal(game.match.phase, 'finished');
  assert.equal(Math.max(game.match.score.north, game.match.score.south), 5);
  assert.ok(game.match.players.some(player => player.id !== 'human' && player.captures > 0));
});

test('fixed monotonic accumulator bounds catch-up and does not retain a lag backlog', () => {
  let now = 0;
  let steps = 0;
  const loop = new FixedStepLoop(() => steps++, () => now);
  now = STEP_SECONDS / 2;
  assert.equal(loop.advance(), 0);
  now = STEP_SECONDS;
  assert.equal(loop.advance(), 1);
  now = 100;
  assert.equal(loop.advance(), 5);
  assert.equal(loop.advance(), 0);
  now += STEP_SECONDS;
  assert.equal(loop.advance(), 1);
  assert.equal(steps, 7);
});
