import {
  DEFAULT_CONFIG, advanceReturningFlags, allJailedWinner, canTag, createMatch,
  distance, dropCarriedFlag, finishRound, movePlayer, nextRound, parseInput,
  startMatch, tryCapture, tryPickup, tryRescue, tryTag,
  type Config, type Input, type Match, type Team,
} from '@ctf/rules';
import { botInput } from './bots.js';

export const TICK_RATE = 30;
export const STEP_SECONDS = 1 / TICK_RATE;
export const STALE_INPUT_SECONDS = 0.25;
export const INTERMISSION_SECONDS = 3;
const INPUTS_PER_SECOND = 60;
const INPUT_BURST = 90;
const idleInput = (): Input => ({sequence: 0, moveX: 0, moveY: 0, tag: false});

export interface PlayerSession {
  nickname: string;
  slot: number;
  connected: boolean;
  bot: boolean;
  sequence: number;
  input: Input;
  receivedAt: number;
  pendingTag: boolean;
  tagReadyAt: number;
  tokens: number;
  tokenTime: number;
  commandReadyAt: number;
}

export function parseJoin(raw: unknown): {nickname: string; practice: boolean} | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const value = raw as Record<string, unknown>;
  if (Object.keys(value).some(key => !['nickname', 'practice'].includes(key))) return null;
  if (typeof value.nickname !== 'string' || value.nickname.length > 48) return null;
  if (value.practice !== undefined && typeof value.practice !== 'boolean') return null;
  const nickname = value.nickname.replace(/[\u0000-\u001f\u007f-\u009f]/g, '').trim().slice(0, 20);
  if (!nickname) return null;
  return {nickname, practice: value.practice === true};
}

/** Canonical state and timing. No sockets, Schema, or browser objects live here. */
export class GameSimulation {
  match: Match;
  readonly players = new Map<string, PlayerSession>();
  time = 0;
  phaseEndsAt = 0;
  hostId = '';
  endReason = '';

  constructor(
    readonly practice = false,
    readonly now: () => number = () => performance.now() / 1000,
    readonly config: Config = DEFAULT_CONFIG,
  ) {
    this.match = createMatch([], 5, config);
  }

  addPlayer(id: string, nickname: string, bot = false): boolean {
    if (this.match.phase !== 'lobby' || this.players.has(id) || this.players.size >= 12) return false;
    const north = this.match.players.filter(player => player.team === 'north').length;
    const south = this.match.players.filter(player => player.team === 'south').length;
    const team: Team = north <= south ? 'north' : 'south';
    const slots = new Set([...this.players.values()].map(player => player.slot));
    let slot = 0;
    while (slots.has(slot)) slot++;
    this.players.set(id, {
      nickname, slot, connected: true, bot, sequence: -1, input: idleInput(),
      receivedAt: -Infinity, pendingTag: false, tagReadyAt: 0,
      tokens: INPUT_BURST, tokenTime: this.now(), commandReadyAt: 0,
    });
    this.match.players.push({id, team, ...this.config.spawn[team], status: 'free', kills: 0, deaths: 0, captures: 0});
    if (!this.hostId && !bot) this.hostId = id;
    this.spreadSpawns();
    return true;
  }

  addPracticeBots(): void {
    this.addPlayer('bot-scout', 'Scout · bot', true);
    this.addPlayer('bot-ranger', 'Ranger · bot', true);
    this.addPlayer('bot-runner', 'Runner · bot', true);
  }

  orderedPlayers() {
    return [...this.match.players].sort((a, b) => this.players.get(a.id)!.slot - this.players.get(b.id)!.slot);
  }

  private spreadSpawns(): void {
    for (const team of ['north', 'south'] as const) {
      const members = this.orderedPlayers().filter(player => player.team === team);
      members.forEach((player, index) => {
        player.x = this.config.spawn[team].x + (index - (members.length - 1) / 2) * 150;
        player.y = this.config.spawn[team].y;
      });
    }
  }

  private resetInputs(): void {
    for (const session of this.players.values()) {
      session.input = idleInput();
      session.pendingTag = false;
      session.receivedAt = -Infinity;
      session.tagReadyAt = this.time;
    }
  }

  start(actorId: string): boolean {
    if (actorId !== this.hostId || this.match.phase !== 'lobby') return false;
    if (!(['north', 'south'] as const).every(team => this.match.players.some(player =>
      player.team === team && this.players.get(player.id)?.connected))) return false;
    if (!startMatch(this.match)) return false;
    this.resetInputs();
    return true;
  }

  rematch(actorId: string): boolean {
    if (actorId !== this.hostId || this.match.phase !== 'finished') return false;
    if (![...this.players.values()].every(player => player.connected)) return false;
    if (!(['north', 'south'] as const).every(team => this.match.players.some(player => player.team === team))) return false;
    const roster = this.match.players.map(({id, team}) => ({id, team}));
    this.match = createMatch(roster, this.match.targetScore, this.config);
    this.endReason = '';
    this.phaseEndsAt = 0;
    this.spreadSpawns();
    return this.start(actorId);
  }

  acceptInput(id: string, raw: unknown): boolean {
    const session = this.players.get(id);
    if (!session || !session.connected || session.bot) return false;
    const now = this.now();
    session.tokens = Math.min(INPUT_BURST, session.tokens + Math.max(0, now - session.tokenTime) * INPUTS_PER_SECOND);
    session.tokenTime = now;
    if (session.tokens < 1) return false;
    session.tokens--;
    const input = parseInput(raw);
    if (!input || input.sequence <= session.sequence) return false;
    session.sequence = input.sequence;
    if (this.match.phase !== 'playing') return false;
    session.input = input;
    session.receivedAt = now;
    session.pendingTag ||= input.tag;
    return true;
  }

  acceptCommand(id: string, raw: unknown): boolean {
    const session = this.players.get(id);
    if (!session || !session.connected || !raw || typeof raw !== 'object' || Array.isArray(raw) || Object.keys(raw).length) return false;
    const now = this.now();
    if (session.commandReadyAt > now) return false;
    session.commandReadyAt = now + 0.5;
    return true;
  }

  disconnect(id: string): void {
    const session = this.players.get(id);
    if (!session) return;
    session.connected = false;
    session.input = idleInput();
    session.pendingTag = false;
    session.receivedAt = -Infinity;
    dropCarriedFlag(this.match, id);
    if (this.hostId === id) this.transferHost();
  }

  reconnect(id: string): boolean {
    const session = this.players.get(id);
    if (!session) return false;
    session.connected = true;
    session.input = idleInput();
    session.pendingTag = false;
    session.receivedAt = -Infinity;
    if (!this.hostId) this.transferHost();
    return true;
  }

  private transferHost(): void {
    this.hostId = this.orderedPlayers().find(player => {
      const session = this.players.get(player.id)!;
      return session.connected && !session.bot;
    })?.id ?? '';
  }

  removePlayer(id: string): void {
    this.disconnect(id);
    this.players.delete(id);
    this.match.players = this.match.players.filter(player => player.id !== id);
    if (this.match.phase === 'lobby') {
      this.spreadSpawns();
      return;
    }
    if (this.match.phase === 'finished') return;
    if (!(['north', 'south'] as const).every(team => this.match.players.some(player => player.team === team))) {
      this.match.phase = 'finished';
      this.endReason = 'A team has no players left. Create a new game to continue.';
      this.phaseEndsAt = 0;
      this.resetInputs();
    } else {
      const winner = allJailedWinner(this.match);
      if (winner) finishRound(this.match, winner, 'allJailed');
      this.updatePhaseDeadline();
    }
  }

  /** One fixed step: slot-ordered movement, tags, rescue, returns, pickup, capture. */
  step(): void {
    this.time += STEP_SECONDS;
    if (this.match.phase === 'roundOver') {
      if (this.phaseEndsAt > 0 && this.time + 1e-9 >= this.phaseEndsAt) {
        nextRound(this.match, this.config);
        this.phaseEndsAt = 0;
        this.spreadSpawns();
        this.resetInputs();
      }
      return;
    }
    if (this.match.phase !== 'playing') return;
    const ordered = this.orderedPlayers();
    const now = this.now();
    const tickInputs = new Map<string, Input>();
    for (const player of ordered) {
      const session = this.players.get(player.id)!;
      let input = idleInput();
      if (session.bot) input = botInput(this.match, player, session.slot, this.config);
      else if (session.connected && now - session.receivedAt <= STALE_INPUT_SECONDS) {
        input = {...session.input, tag: session.pendingTag};
      }
      session.pendingTag = false;
      tickInputs.set(player.id, input);
      movePlayer(this.match, player, input, STEP_SECONDS, this.config);
    }
    for (const attacker of ordered) {
      const session = this.players.get(attacker.id)!;
      if (this.match.phase !== 'playing' || attacker.status !== 'free' || !tickInputs.get(attacker.id)?.tag || session.tagReadyAt > this.time + 1e-9) continue;
      // Misses consume cooldown too, so spamming cannot turn a held intent into continuous attacks.
      session.tagReadyAt = this.time + this.config.tagCooldownSeconds;
      const victim = ordered.filter(player => canTag(attacker, player, this.config))
        .sort((a, b) => distance(attacker, a) - distance(attacker, b) || this.players.get(a.id)!.slot - this.players.get(b.id)!.slot)[0];
      if (victim) tryTag(this.match, attacker.id, victim.id, this.config);
    }
    for (const player of ordered) if (this.players.get(player.id)!.connected) tryRescue(this.match, player.id, this.config);
    advanceReturningFlags(this.match, STEP_SECONDS, this.config);
    for (const player of ordered) if (this.players.get(player.id)!.connected) tryPickup(this.match, player.id, this.config);
    for (const player of ordered) if (this.players.get(player.id)!.connected) tryCapture(this.match, player.id, this.config);
    this.updatePhaseDeadline();
  }

  private updatePhaseDeadline(): void {
    if (this.match.phase === 'roundOver' && this.phaseEndsAt === 0) this.phaseEndsAt = this.time + INTERMISSION_SECONDS;
    if (this.match.phase === 'finished') this.phaseEndsAt = 0;
  }
}

/** Monotonic accumulator; discard excess lag after at most five catch-up steps. */
export class FixedStepLoop {
  private previous: number;
  private accumulator = 0;
  constructor(private readonly step: () => void, private readonly now: () => number = () => performance.now() / 1000) {
    this.previous = now();
  }
  advance(): number {
    const current = this.now();
    const elapsed = Math.max(0, current - this.previous);
    this.previous = current;
    this.accumulator = Math.min(this.accumulator + elapsed, STEP_SECONDS * 5);
    let count = 0;
    while (this.accumulator + 1e-9 >= STEP_SECONDS && count < 5) {
      this.accumulator -= STEP_SECONDS;
      this.step();
      count++;
    }
    return count;
  }
}
