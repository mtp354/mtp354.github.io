import Phaser from 'phaser';
import { DEFAULT_CONFIG as config, isSafe, opposite, type Rect, type Team } from '@ctf/rules';
import type { GameState, PlayerView } from './types';

const colors = { north: 0x63d8df, south: 0xf4af70 };
const cssColors = { north: '#63d8df', south: '#f4af70' };
const worldWidth = config.bounds.maxX - config.bounds.minX;
const worldHeight = config.bounds.maxY - config.bounds.minY;
const wx = (x: number) => x - config.bounds.minX;
const wy = (y: number) => config.bounds.maxY - y;
const teamName = (team: Team) => team === 'north' ? 'NORTH' : 'SOUTH';

export interface ArenaSource {
  state: () => GameState | undefined;
  localId: () => string;
}

class ArenaScene extends Phaser.Scene {
  private drawing!: Phaser.GameObjects.Graphics;
  private labels = new Map<string, Phaser.GameObjects.Text>();
  private positions = new Map<string, { x: number; y: number; status: string }>();
  private cameraReady = false;
  private mapLabels: Phaser.GameObjects.Text[] = [];

  constructor(private source: ArenaSource) { super('arena'); }

  create() {
    this.cameras.main.setBackgroundColor('#0b171e');
    this.cameras.main.setBounds(0, 0, worldWidth, worldHeight);
    const g = this.add.graphics();
    g.fillStyle(0x101f27).fillRect(0, 0, worldWidth, worldHeight);
    for (const team of ['north', 'south'] as const) {
      for (const rect of config.safe[team]) this.rectangle(g, rect, colors[team], 0.065);
    }
    // The measured home regions overlap; both teams are protected in this band.
    const overlap = { minX: -1376, maxX: 2368, minY: -576, maxY: -192 };
    this.rectangle(g, overlap, 0xcbe5bd, 0.07);
    g.lineStyle(2, 0x8da7a7, 0.22);
    for (let x = 0; x <= worldWidth; x += 256) g.lineBetween(x, 0, x, worldHeight);
    for (let y = 0; y <= worldHeight; y += 256) g.lineBetween(0, y, worldWidth, y);
    g.lineStyle(3, 0xcbe5bd, 0.3);
    g.lineBetween(0, wy(-192), worldWidth, wy(-192));
    g.lineBetween(0, wy(-576), worldWidth, wy(-576));
    this.mapLabel('BOTH TEAMS SAFE', wx(800), wy(-384), '#adc3b4', 25);
    for (const team of ['north', 'south'] as const) {
      const jail = config.jail[team];
      this.rectangle(g, jail, colors[opposite(team)], 0.13);
      g.lineStyle(5, colors[opposite(team)], 0.7);
      g.strokeRect(wx(jail.minX), wy(jail.maxY), jail.maxX - jail.minX, jail.maxY - jail.minY);
      for (let x = jail.minX + 65; x < jail.maxX; x += 70) {
        g.lineBetween(wx(x), wy(jail.maxY), wx(x), wy(jail.minY));
      }
      this.mapLabel(`${teamName(opposite(team))} JAIL`, wx((jail.minX + jail.maxX) / 2), wy(jail.maxY) - 55, cssColors[opposite(team)], 28);
      this.mapLabel(`${teamName(team)} TERRITORY`, wx(-20), wy(team === 'north' ? 1100 : -1700), cssColors[team], 35);
      const home = config.flagHome[team];
      g.lineStyle(4, colors[team], 0.25).strokeCircle(wx(home.x), wy(home.y), config.pickupRadius);
      this.mapLabel(`${teamName(team)} FLAG`, wx(home.x), wy(home.y) + 150, cssColors[team], 27);
    }
    g.lineStyle(8, 0x60777c, 0.5).strokeRect(0, 0, worldWidth, worldHeight);
    this.drawing = this.add.graphics().setDepth(2);
    this.resizeCamera();
    this.scale.on('resize', this.resizeCamera, this);
  }

  private rectangle(g: Phaser.GameObjects.Graphics, rect: Rect, color: number, alpha: number) {
    g.fillStyle(color, alpha).fillRect(wx(rect.minX), wy(rect.maxY), rect.maxX - rect.minX, rect.maxY - rect.minY);
  }

  private mapLabel(text: string, x: number, y: number, color: string, size: number) {
    this.mapLabels.push(this.add.text(x, y, text, {
      fontFamily: 'system-ui, sans-serif', fontSize: size, color, letterSpacing: 3,
    }).setOrigin(0.5).setAlpha(0.58));
  }

  private resizeCamera() {
    this.cameras.main.setZoom(Math.min(0.55, Math.max(0.25, this.scale.width / 2000)));
  }

  update(_time: number, delta: number) {
    const state = this.source.state();
    if (!state?.players || !this.drawing) return;
    const localId = this.source.localId();
    const g = this.drawing.clear();
    const ids = new Set<string>();
    const occupiedLabels: Phaser.Geom.Rectangle[] = [];
    state.players.forEach((p) => {
      ids.add(p.id);
      const targetX = wx(p.x), targetY = wy(p.y);
      const old = this.positions.get(p.id);
      const snap = !old || old.status !== p.status || Math.hypot(old.x - targetX, old.y - targetY) > 450;
      const blend = 1 - Math.exp(-delta / 45);
      const pos = {
        x: snap ? targetX : old.x + (targetX - old.x) * blend,
        y: snap ? targetY : old.y + (targetY - old.y) * blend,
        status: p.status,
      };
      this.positions.set(p.id, pos);
      const mine = p.id === localId;
      const color = colors[p.team];
      const alpha = p.connected ? 1 : 0.4;
      if (mine && p.status === 'free') {
        g.lineStyle(2, 0xffffff, 0.13).strokeCircle(pos.x, pos.y, config.tagRadius);
      }
      if (isSafe(p)) g.lineStyle(4, color, 0.32 * alpha).strokeCircle(pos.x, pos.y, 48);
      g.fillStyle(color, alpha).fillCircle(pos.x, pos.y, 28);
      g.lineStyle(mine ? 6 : 3, mine ? 0xffffff : 0x10212a, alpha).strokeCircle(pos.x, pos.y, 28);
      if (p.status === 'jailed') {
        g.lineStyle(6, 0x101b21).lineBetween(pos.x - 12, pos.y - 12, pos.x + 12, pos.y + 12);
        g.lineBetween(pos.x + 12, pos.y - 12, pos.x - 12, pos.y + 12);
      } else {
        // A small directional mark makes the local player easy to pick out.
        if (mine) g.fillStyle(0xffffff).fillTriangle(pos.x - 12, pos.y - 52, pos.x + 12, pos.y - 52, pos.x, pos.y - 37);
      }
      let label = this.labels.get(p.id);
      if (!label) {
        label = this.add.text(0, 0, '', {
          fontFamily: 'system-ui, sans-serif', fontSize: 27, color: '#edf6f4',
          backgroundColor: '#101b21', padding: { x: 9, y: 3 },
        }).setOrigin(0.5, 0).setDepth(4);
        this.labels.set(p.id, label);
      }
      label.setText(`${p.nickname}${mine ? ' · YOU' : ''}${!p.connected ? ' · away' : ''}`);
      let labelY = pos.y + 43;
      // Nearby safe spawns and jailbreaks can put players side by side. Keep their
      // names legible without changing the authoritative player positions.
      for (let attempt = 0; attempt < 12; attempt++) {
        const bounds = new Phaser.Geom.Rectangle(pos.x - label.width / 2 - 6, labelY, label.width + 12, label.height + 5);
        if (!occupiedLabels.some((other) => Phaser.Geom.Intersects.RectangleToRectangle(bounds, other))) {
          occupiedLabels.push(bounds);
          break;
        }
        labelY += label.height + 8;
      }
      label.setPosition(pos.x, labelY).setAlpha(alpha);
      if (mine) {
        if (!this.cameraReady || snap) {
          this.cameras.main.centerOn(pos.x, pos.y);
          this.cameraReady = true;
        } else {
          const c = this.cameras.main;
          const centerX = c.midPoint.x;
          const centerY = c.midPoint.y;
          c.centerOn(centerX + (pos.x - centerX) * 0.2, centerY + (pos.y - centerY) * 0.2);
        }
      }
    });
    for (const [id, label] of this.labels) {
      if (!ids.has(id)) { label.destroy(); this.labels.delete(id); this.positions.delete(id); }
    }
    state.flags.forEach((flag) => {
      const p = flag.carrierId ? this.positions.get(flag.carrierId) : undefined;
      const x = p ? p.x + 44 : wx(flag.x), y = p ? p.y - 45 : wy(flag.y);
      const color = colors[flag.owner];
      if (flag.status === 'returning') g.lineStyle(4, color, 0.4).strokeCircle(x, y, 75);
      g.lineStyle(7, 0xeaf0e9).lineBetween(x, y + 45, x, y - 44);
      g.fillStyle(color).fillTriangle(x + 3, y - 44, x + 75, y - 20, x + 3, y + 5);
    });
  }
}

export function createArena(element: HTMLElement, source: ArenaSource) {
  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent: element,
    width: element.clientWidth || 900,
    height: element.clientHeight || 600,
    backgroundColor: '#0b171e',
    scene: new ArenaScene(source),
    scale: { mode: Phaser.Scale.NONE },
    input: { keyboard: false },
    render: { antialias: true, roundPixels: false },
    audio: { noAudio: true },
    banner: false,
  });
  const resize = new ResizeObserver(() => {
    if (element.clientWidth && element.clientHeight) game.scale.resize(element.clientWidth, element.clientHeight);
  });
  resize.observe(element);
  return () => { resize.disconnect(); game.destroy(true); };
}

export function drawMinimap(canvas: HTMLCanvasElement, state: GameState, localId: string) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  const scale = canvas.width / worldWidth;
  const x = (v: number) => wx(v) * scale;
  const y = (v: number) => wy(v) * scale;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#142932'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  for (const team of ['north', 'south'] as const) {
    ctx.fillStyle = team === 'north' ? '#1d3b43' : '#3b302b';
    for (const r of config.safe[team]) ctx.fillRect(x(r.minX), y(r.maxY), (r.maxX - r.minX) * scale, (r.maxY - r.minY) * scale);
    const r = config.jail[team];
    ctx.strokeStyle = cssColors[opposite(team)];
    ctx.strokeRect(x(r.minX), y(r.maxY), (r.maxX - r.minX) * scale, (r.maxY - r.minY) * scale);
  }
  ctx.fillStyle = '#bdc6a440'; ctx.fillRect(0, y(-192), canvas.width, 384 * scale);
  state.players.forEach((p: PlayerView) => {
    ctx.beginPath(); ctx.arc(x(p.x), y(p.y), p.id === localId ? 5 : 3, 0, Math.PI * 2);
    ctx.fillStyle = cssColors[p.team]; ctx.fill();
    if (p.id === localId) { ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke(); }
    if (p.status === 'jailed') { ctx.fillStyle = '#101b21'; ctx.fillRect(x(p.x) - 1, y(p.y) - 2, 2, 4); }
  });
  state.flags.forEach((f) => {
    ctx.fillStyle = cssColors[f.owner];
    ctx.fillRect(x(f.x) - 4, y(f.y) - 6, 8, 8);
    ctx.fillStyle = '#f5f5ef'; ctx.fillRect(x(f.x) - 4, y(f.y) - 6, 1, 13);
  });
}
