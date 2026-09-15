import { Room, ServerError, type Client } from '@colyseus/core';
import { FixedStepLoop, GameSimulation, parseJoin, TICK_RATE } from './simulation.js';
import { FlagState, GameState, PlayerState } from './state.js';

/** A thin transport adapter; the rules state remains the sole gameplay authority. */
export class CtfRoom extends Room<GameState> {
  simulation!: GameSimulation;
  private shuttingDown = false;
  private disposed = false;
  private reconnectSeconds = 20;

  onCreate(options: unknown): void {
    const join = parseJoin(options);
    if (!join) throw new ServerError(400, 'Enter a nickname of up to 20 characters.');
    this.simulation = new GameSimulation(join.practice);
    this.maxClients = join.practice ? 1 : 12;
    this.setState(new GameState());
    this.setPatchRate(50);
    this.setSeatReservationTime(10);
    this.onMessage('input', (client, payload: unknown) => this.simulation.acceptInput(client.sessionId, payload));
    this.onMessage('start', (client, payload: unknown) => {
      if (!this.simulation.acceptCommand(client.sessionId, payload)) return;
      if (this.simulation.start(client.sessionId)) {
        void this.lock();
        this.projectState();
      } else client.send('notice', {message: 'The host can start once each team has a connected player.'});
    });
    this.onMessage('rematch', (client, payload: unknown) => {
      if (!this.simulation.acceptCommand(client.sessionId, payload)) return;
      if (this.simulation.rematch(client.sessionId)) this.projectState();
      else client.send('notice', {message: 'The host can play again when the match has finished and both teams are connected.'});
    });
    // Unknown message types never alter state or produce amplification replies.
    this.onMessage('*', () => {});
    const loop = new FixedStepLoop(() => this.simulation.step());
    this.setSimulationInterval(() => {
      if (this.disposed) return;
      loop.advance();
      this.projectState();
    }, 1000 / TICK_RATE);
    this.projectState();
  }

  onAuth(_client: Client, options: unknown): boolean {
    if (!parseJoin(options)) throw new ServerError(400, 'Choose a nickname before joining.');
    if (this.simulation.match.phase !== 'lobby') throw new ServerError(409, 'This game has started. Create a new game to play.');
    return true;
  }

  onJoin(client: Client, options: unknown): void {
    const join = parseJoin(options);
    if (!join || !this.simulation.addPlayer(client.sessionId, join.nickname)) throw new ServerError(409, 'This game is full or has already started.');
    if (this.simulation.practice) {
      this.simulation.addPracticeBots();
      this.simulation.start(client.sessionId);
      void this.lock();
    }
    this.projectState();
  }

  /** Server configuration, set by a subclass closure rather than untrusted options. */
  configureReconnect(seconds: number): void {
    this.reconnectSeconds = seconds;
  }

  async onLeave(client: Client, consented: boolean): Promise<void> {
    if (this.disposed) return;
    this.simulation.disconnect(client.sessionId);
    this.projectState();
    if (!consented && !this.shuttingDown) {
      // Colyseus 0.16 does not clear its native grace timer when shutdown rejects
      // the reconnection. Use its documented manual mode with a room-owned timer.
      const reconnection = this.allowReconnection(client, 'manual');
      const expiry = this.clock.setTimeout(() => reconnection.reject(), this.reconnectSeconds * 1000);
      try {
        await reconnection;
        if (this.disposed) return;
        this.simulation.reconnect(client.sessionId);
        this.projectState();
        return;
      } catch {
        // Grace expired: remove the retained body and explicitly finish empty-team matches.
      } finally {
        expiry.clear();
      }
    }
    if (this.disposed) return;
    this.simulation.removePlayer(client.sessionId);
    this.projectState();
  }

  onBeforeShutdown(): void {
    this.shuttingDown = true;
    void this.disconnect();
  }

  onDispose(): void {
    this.shuttingDown = true;
    this.disposed = true;
    this.simulation?.players.clear();
    // Colyseus owns and clears the simulation interval, patch interval, and room clock.
  }

  projectState(): void {
    if (this.disposed) return;
    const {match} = this.simulation;
    for (const id of this.state.players.keys()) if (!this.simulation.players.has(id)) this.state.players.delete(id);
    for (const player of match.players) {
      const session = this.simulation.players.get(player.id)!;
      let projected = this.state.players.get(player.id);
      if (!projected) {
        projected = new PlayerState();
        this.state.players.set(player.id, projected);
      }
      Object.assign(projected, player, {
        nickname: session.nickname, connected: session.connected, bot: session.bot,
        slot: session.slot, tagReadyAt: session.tagReadyAt,
      });
    }
    for (const owner of ['north', 'south'] as const) {
      let flag = this.state.flags.get(owner);
      if (!flag) {
        flag = new FlagState();
        this.state.flags.set(owner, flag);
      }
      Object.assign(flag, match.flags[owner], {carrierId: match.flags[owner].carrierId ?? ''});
    }
    Object.assign(this.state, {
      phase: match.phase, round: match.round, targetScore: match.targetScore,
      northScore: match.score.north, southScore: match.score.south,
      hostId: this.simulation.hostId, practice: this.simulation.practice,
      serverTime: this.simulation.time, phaseEndsAt: this.simulation.phaseEndsAt,
      lastPointWinner: match.lastPoint?.winner ?? '', lastPointReason: match.lastPoint?.reason ?? '',
      endReason: this.simulation.endReason,
    });
  }
}
