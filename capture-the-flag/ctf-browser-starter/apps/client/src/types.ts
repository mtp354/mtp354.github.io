import type { Team } from '@ctf/rules';

export interface PlayerView {
  id: string;
  nickname: string;
  team: Team;
  x: number;
  y: number;
  status: 'free' | 'jailed';
  kills: number;
  deaths: number;
  captures: number;
  connected: boolean;
  bot: boolean;
  slot: number;
  tagReadyAt: number;
}
export interface FlagView {
  owner: Team;
  x: number;
  y: number;
  status: 'home' | 'carried' | 'returning';
  carrierId: string;
}
export interface SyncedMap<T> {
  get(key: string): T | undefined;
  forEach(callback: (value: T, key: string) => void): void;
  values(): IterableIterator<T>;
}
export interface GameState {
  players: SyncedMap<PlayerView>;
  flags: SyncedMap<FlagView>;
  phase: 'lobby' | 'playing' | 'roundOver' | 'finished';
  round: number;
  targetScore: number;
  northScore: number;
  southScore: number;
  hostId: string;
  practice: boolean;
  serverTime: number;
  phaseEndsAt: number;
  lastPointWinner: string;
  lastPointReason: string;
  endReason: string;
}
