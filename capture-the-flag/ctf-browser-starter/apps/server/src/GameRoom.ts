import { performance } from 'node:perf_hooks';
import { Room, type Client } from 'colyseus';
import { schema, t } from '@colyseus/schema';
import {
  DEFAULT_CONFIG, advanceReturningFlags, canTag, createMatch, distance,
  dropCarriedFlag, isSafe, movePlayer, nextRound, parseInput, playerById,
  startMatch, tryCapture, tryPickup, tryRescue, tryTag,
  type Input, type Match, type Player, type Team,
} from '@ctf/rules';

const GameState = schema({ snapshot: t.string().default('{}') }, 'CtfGameState');
type GameState = InstanceType<typeof GameState>;
const ZERO: Input = { sequence: 0, moveX: 0, moveY: 0, tag: false };
const TICK_HZ = readNumber('CTF_TICK_HZ', 30, 10, 60);
const PATCH_MS = readNumber('CTF_PATCH_MS', 50, 25, 250);
const GRACE_SECONDS = readNumber('CTF_RECONNECT_GRACE_SECONDS', 10, 1, 60);
const INTERMISSION_MS = readNumber('CTF_INTERMISSION_MS', 1500, 100, 10000);
const STALE_MS = 250;
const RATE_PER_SECOND = 45;
const RATE_BURST = 12;

function readNumber(key: string, fallback: number, min: number, max: number): number {
  const raw = process.env[key];
  const value = raw === undefined ? fallback : Number(raw);
  return Number.isFinite(value) && value >= min && value <= max ? value : fallback;
}

type Session = {
  name: string; connected: boolean; input: Input; pendingTag: boolean;
  lastSequence: number; lastInputAt: number; nextTagAt: number;
  tokens: number; tokenAt: number;
};

/** An in-process test handle, never exposed by any room message or HTTP route. */
export const testRooms = new Map<string, GameRoom>();

export class GameRoom extends Room<{ state: GameState }> {
  state = new GameState();
  maxClients = 12;
  patchRate = PATCH_MS;
  maxMessagesPerSecond = 100;
  canonical: Match = createMatch([]);
  private sessions = new Map<string, Session>();
  private joinOrder: string[] = [];
  private hostId = '';
  private endReason = '';
  private simulatedMs = 0;
  private roundEndsAt = 0;
  private shuttingDown = false;
  private lastWall = performance.now();
  private accumulator = 0;
  private readonly tickMs = 1000 / TICK_HZ;

  messages = {
    input: (client: Client, raw: unknown) => this.acceptInput(client, raw),
    start: (client: Client, raw: unknown) => this.acceptStart(client, raw),
  };

  onCreate(): void {
    this.publish();
    if (process.env.CTF_TEST_HARNESS === '1') testRooms.set(this.roomId, this);
    this.clock.setInterval(() => this.heartbeat(), this.tickMs / 2);
  }

  onAuth(_client: Client, options: unknown): boolean {
    if (this.canonical.phase !== 'lobby' || this.canonical.players.length >= 12) return false;
    if (typeof options !== 'object' || options === null || Array.isArray(options)) return false;
    const raw = options as Record<string, unknown>;
    if (Object.keys(raw).some(k => k !== 'nickname')) return false;
    return typeof raw.nickname === 'string' && raw.nickname.trim().length >= 1 &&
      raw.nickname.trim().length <= 18 && !/[\x00-\x1f\x7f]/.test(raw.nickname);
  }

  onJoin(client: Client, options: { nickname: string }): void {
    const north = this.canonical.players.filter(p => p.team === 'north').length;
    const south = this.canonical.players.length - north;
    const team: Team = north <= south ? 'north' : 'south';
    const slot = team === 'north' ? north : south;
    const spawn = spread(team, slot);
    this.canonical.players.push({
      id: client.sessionId, team, ...spawn, status: 'free', kills: 0, deaths: 0, captures: 0,
    });
    const now = performance.now();
    this.sessions.set(client.sessionId, {
      name: options.nickname.trim(), connected: true, input: ZERO, pendingTag: false,
      lastSequence: -1, lastInputAt: 0, nextTagAt: 0,
      tokens: RATE_BURST, tokenAt: now,
    });
    this.joinOrder.push(client.sessionId);
    if (!this.hostId) this.hostId = client.sessionId;
    this.publish();
  }

  onDrop(client: Client): void {
    const session = this.sessions.get(client.sessionId);
    if (!session) return;
    session.connected = false;
    session.input = ZERO;
    session.pendingTag = false;
    dropCarriedFlag(this.canonical, client.sessionId);
    if (!this.shuttingDown) this.allowReconnection(client, GRACE_SECONDS);
    this.publish();
  }

  onBeforeShutdown(): void {
    this.shuttingDown = true;
    super.onBeforeShutdown();
  }

  onReconnect(client: Client): void {
    const session = this.sessions.get(client.sessionId);
    if (!session) return;
    session.connected = true;
    session.input = ZERO;
    session.pendingTag = false;
    session.lastInputAt = 0;
    session.lastSequence = -1; // a new socket begins a new ordered input stream
    session.tokens = RATE_BURST;
    session.tokenAt = performance.now();
    this.publish();
  }

  onLeave(client: Client): void {
    const id = client.sessionId;
    dropCarriedFlag(this.canonical, id);
    this.sessions.delete(id);
    this.canonical.players = this.canonical.players.filter(p => p.id !== id);
    this.joinOrder = this.joinOrder.filter(value => value !== id);
    if (this.hostId === id) this.hostId = this.joinOrder[0] ?? '';
    if (this.canonical.phase !== 'lobby' && this.canonical.phase !== 'finished' &&
        (!this.canonical.players.some(p => p.team === 'north') ||
         !this.canonical.players.some(p => p.team === 'south'))) {
      this.canonical.phase = 'finished';
      this.endReason = 'disconnect';
    }
    this.publish();
  }

  onDispose(): void { testRooms.delete(this.roomId); }

  private acceptStart(client: Client, raw: unknown): void {
    if (client.sessionId !== this.hostId || this.canonical.phase !== 'lobby') return;
    if (raw !== null && (typeof raw !== 'object' || Array.isArray(raw) || Object.keys(raw).length !== 0)) return;
    if (startMatch(this.canonical)) {
      this.lock();
      this.clearInputs();
      this.publish();
    }
  }

  private acceptInput(client: Client, raw: unknown): void {
    const session = this.sessions.get(client.sessionId);
    if (!session || !session.connected || this.canonical.phase !== 'playing') return;
    let bytes = 0;
    try { bytes = Buffer.byteLength(JSON.stringify(raw)); } catch { return; }
    if (bytes > 160) return;
    const parsed = parseInput(raw);
    if (!parsed || parsed.sequence <= session.lastSequence) return;
    const now = performance.now();
    session.tokens = Math.min(RATE_BURST, session.tokens + (now - session.tokenAt) * RATE_PER_SECOND / 1000);
    session.tokenAt = now;
    if (session.tokens < 1) return;
    session.tokens--;
    session.lastSequence = parsed.sequence;
    session.input = parsed;
    session.lastInputAt = now;
    if (parsed.tag) session.pendingTag = true;
  }

  private heartbeat(): void {
    const now = performance.now();
    this.accumulator = Math.min(this.tickMs * 5, this.accumulator + Math.max(0, now - this.lastWall));
    this.lastWall = now;
    while (this.accumulator >= this.tickMs) {
      this.step();
      this.accumulator -= this.tickMs;
    }
    this.publish();
  }

  /** One fixed server tick. Also used by the in-process integration harness. */
  step(): void {
    this.simulatedMs += this.tickMs;
    if (this.canonical.phase === 'roundOver') {
      if (this.simulatedMs >= this.roundEndsAt && nextRound(this.canonical)) {
        this.respread();
        this.clearInputs();
      }
      return;
    }
    if (this.canonical.phase !== 'playing') return;
    const players = [...this.canonical.players].sort((a, b) => a.id.localeCompare(b.id));
    const wall = performance.now();
    for (const p of players) {
      const s = this.sessions.get(p.id);
      const input = s?.connected && wall - s.lastInputAt <= STALE_MS ? s.input : ZERO;
      movePlayer(this.canonical, p, input, this.tickMs / 1000);
    }
    for (const attacker of players) {
      const s = this.sessions.get(attacker.id);
      if (!s?.pendingTag) continue;
      s.pendingTag = false;
      if (!s.connected || this.simulatedMs < s.nextTagAt) continue;
      s.nextTagAt = this.simulatedMs + DEFAULT_CONFIG.tagCooldownSeconds * 1000;
      const target = players.filter(v => canTag(attacker, v))
        .sort((a, b) => distance(attacker, a) - distance(attacker, b) || a.id.localeCompare(b.id))[0];
      if (target) tryTag(this.canonical, attacker.id, target.id);
      if (this.canonical.phase !== 'playing') break;
    }
    if (this.canonical.phase === 'playing') {
      for (const p of players) if (this.sessions.get(p.id)?.connected) tryRescue(this.canonical, p.id);
      advanceReturningFlags(this.canonical, this.tickMs / 1000);
      for (const p of players) if (this.sessions.get(p.id)?.connected) tryPickup(this.canonical, p.id);
      for (const p of players) {
        if (this.sessions.get(p.id)?.connected && tryCapture(this.canonical, p.id)) break;
      }
    }
    if ((this.canonical as Match).phase === 'roundOver') {
      this.roundEndsAt = this.simulatedMs + INTERMISSION_MS;
      this.clearInputs();
    }
  }

  private clearInputs(): void {
    for (const s of this.sessions.values()) {
      s.input = ZERO;
      s.pendingTag = false;
      s.lastInputAt = 0;
      if (this.canonical.phase === 'playing' && this.canonical.round > 1) s.nextTagAt = 0;
    }
  }

  private respread(): void {
    for (const team of ['north', 'south'] as const) {
      this.canonical.players.filter(p => p.team === team)
        .sort((a, b) => this.joinOrder.indexOf(a.id) - this.joinOrder.indexOf(b.id))
        .forEach((p, slot) => Object.assign(p, spread(team, slot)));
    }
  }

  publish(): void {
    const m = this.canonical;
    const snapshot = {
      phase: m.phase, round: m.round, targetScore: m.targetScore,
      score: m.score, lastPoint: m.lastPoint, endReason: this.endReason,
      hostId: this.hostId,
      players: m.players.map(p => ({ ...p, name: this.sessions.get(p.id)?.name ?? '',
        connected: this.sessions.get(p.id)?.connected ?? false, safe: isSafe(p) })),
      flags: m.flags,
    };
    const json = JSON.stringify(snapshot);
    if (this.state.snapshot !== json) this.state.snapshot = json;
  }

  /** Local test process only. No client message can call this. */
  testOnlyMutate(callback: (match: Match) => void): void {
    if (process.env.CTF_TEST_HARNESS !== '1') throw new Error('Test harness disabled');
    callback(this.canonical);
    this.publish();
  }
}

function spread(team: Team, slot: number): Pick<Player, 'x' | 'y'> {
  const base = DEFAULT_CONFIG.spawn[team];
  return { x: base.x + (slot % 3 - 1) * 200, y: base.y + Math.floor(slot / 3) * 160 };
}
