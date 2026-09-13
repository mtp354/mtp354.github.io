import Phaser from 'phaser';
import { Client, type Room } from '@colyseus/sdk';
import { DEFAULT_CONFIG, type Team } from '@ctf/rules';
import './style.css';

type ViewPlayer = { id: string; name: string; team: Team; x: number; y: number; status: 'free'|'jailed'; safe: boolean; connected: boolean; kills: number; deaths: number; captures: number };
type ViewFlag = { owner: Team; x: number; y: number; status: 'home'|'carried'|'returning'; carrierId: string|null };
type View = { phase: 'lobby'|'playing'|'roundOver'|'finished'; round: number; targetScore: number; score: Record<Team,number>; lastPoint: {winner:Team;reason:string}|null; endReason: string; hostId: string; players: ViewPlayer[]; flags: Record<Team,ViewFlag> };
const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const status = $<HTMLParagraphElement>('status');
const nickname = $<HTMLInputElement>('nickname');
const roomCode = $<HTMLInputElement>('room-code');
const startButton = $<HTMLButtonElement>('start');
const minimap = $<HTMLCanvasElement>('minimap');
const ctx = minimap.getContext('2d')!;
const bounds = DEFAULT_CONFIG.bounds;
const worldW = bounds.maxX - bounds.minX;
const worldH = bounds.maxY - bounds.minY;
const project = (x: number, y: number) => ({ x: x - bounds.minX, y: bounds.maxY - y });
const color = (team: Team) => team === 'north' ? 0x53a7ff : 0xff9a56;
const cssColor = (team: Team) => team === 'north' ? '#53a7ff' : '#ff9a56';
const client = new Client(import.meta.env.VITE_CTF_SERVER_URL || 'http://127.0.0.1:2567');
let room: Room | null = null;
let view: View | null = null;
let sequence = 0;
let controls = false;
let tagPulse = false;
const held = new Set<string>();

class Arena extends Phaser.Scene {
  private shapes!: Phaser.GameObjects.Graphics;
  private labels = new Map<string, Phaser.GameObjects.Text>();
  private positions = new Map<string, {x:number;y:number}>();
  constructor() { super('arena'); }
  create(): void {
    this.cameras.main.setBounds(0, 0, worldW, worldH).setZoom(0.62);
    const ground = this.add.graphics();
    ground.fillStyle(0x244638).fillRect(0, 0, worldW, worldH);
    ground.lineStyle(2,0xffffff,0.075);
    for(let x=0;x<=worldW;x+=256)ground.lineBetween(x,0,x,worldH);
    for(let y=0;y<=worldH;y+=256)ground.lineBetween(0,y,worldW,y);
    const safe = (team:Team) => {
      for (const r of DEFAULT_CONFIG.safe[team]) {
        const at = project(r.minX, r.maxY);
        ground.fillStyle(color(team), 0.11).fillRect(at.x, at.y, r.maxX-r.minX, r.maxY-r.minY);
        ground.lineStyle(5, color(team), 0.35).strokeRect(at.x, at.y, r.maxX-r.minX, r.maxY-r.minY);
      }
    };
    safe('south'); safe('north');
    // Both safe rectangles include the measured -576..-192 central overlap.
    const overlapTop = project(0,-192).y;
    ground.fillStyle(0xd8d77a,0.12).fillRect(0,overlapTop,worldW,384);
    for (const team of ['north','south'] as const) {
      const jail = DEFAULT_CONFIG.jail[team], at = project(jail.minX,jail.maxY);
      ground.fillStyle(0xb269db,0.28).fillRect(at.x,at.y,jail.maxX-jail.minX,jail.maxY-jail.minY);
      ground.lineStyle(5,0xc895e5,0.8).strokeRect(at.x,at.y,jail.maxX-jail.minX,jail.maxY-jail.minY);
      this.add.text(at.x,at.y-36,`${team === 'north' ? 'SOUTH' : 'NORTH'} JAIL`,{fontSize:'32px',color:'#e3baff'});
    }
    this.add.text(80,project(0,2700).y,'NORTH SAFE',{fontSize:'45px',color:'#9acbff'});
    this.add.text(80,project(0,-2600).y,'SOUTH SAFE',{fontSize:'45px',color:'#ffc09c'});
    this.add.text(80,overlapTop+70,'CENTRAL SAFE OVERLAP',{fontSize:'30px',color:'#e6e6a8'});
    this.shapes = this.add.graphics();
    this.game.canvas.tabIndex = 0;
    this.game.canvas.addEventListener('pointerdown', () => { controls = true; this.game.canvas.focus(); status.textContent = 'Arena focused — WASD/arrows move, Space tags.'; });
  }
  update(_time: number, delta: number): void {
    this.shapes.clear();
    if (!view) return;
    const activeIds = new Set<string>();
    for (const p of view.players) {
      activeIds.add(p.id);
      const target = project(p.x,p.y);
      const previous = this.positions.get(p.id) ?? target;
      const factor = Math.min(1,delta/90);
      const at = {x:previous.x+(target.x-previous.x)*factor,y:previous.y+(target.y-previous.y)*factor};
      this.positions.set(p.id,at);
      this.shapes.fillStyle(color(p.team), p.connected ? 1 : 0.4).fillCircle(at.x,at.y,33);
      this.shapes.lineStyle(p.id === room?.sessionId ? 7 : 3,p.safe ? 0xf3f5d2 : 0x18252e).strokeCircle(at.x,at.y,36);
      if (p.status === 'jailed') this.shapes.lineStyle(7,0x181a24).lineBetween(at.x-22,at.y-22,at.x+22,at.y+22);
      let label = this.labels.get(p.id);
      if (!label) { label = this.add.text(at.x,at.y-80,'',{fontSize:'26px',color:'#ffffff',backgroundColor:'#18252ec9'}).setOrigin(0.5); this.labels.set(p.id,label); }
      label.setText(p.name || 'Runner').setPosition(at.x,at.y-80);
    }
    for (const [id,label] of this.labels) if (!activeIds.has(id)) { label.destroy(); this.labels.delete(id); this.positions.delete(id); }
    for (const team of ['north','south'] as const) {
      const f = view.flags[team], at = project(f.x,f.y);
      this.shapes.fillStyle(0xffdf62).fillTriangle(at.x,at.y-55,at.x-27,at.y+22,at.x+27,at.y+22);
      this.shapes.lineStyle(4,color(team)).strokeTriangle(at.x,at.y-55,at.x-27,at.y+22,at.x+27,at.y+22);
      if (f.status === 'returning') this.shapes.lineStyle(3,0xffdf62,0.7).strokeCircle(at.x,at.y,70);
    }
    const me = view.players.find(p=>p.id === room?.sessionId);
    if (me) {
      const at = this.positions.get(me.id) ?? project(me.x,me.y);
      this.cameras.main.centerOn(at.x,at.y);
    }
  }
}

new Phaser.Game({type:Phaser.AUTO,width:1000,height:650,parent:'game',backgroundColor:'#183326',scene:[Arena],render:{pixelArt:true}});

function updateHud(): void {
  if (!view) return;
  const v=view;
  $<HTMLHeadingElement>('score').textContent=`North ${v.score.north} · South ${v.score.south} / ${v.targetScore}`;
  $<HTMLParagraphElement>('phase').textContent = v.phase === 'roundOver' && v.lastPoint
    ? `Round ${v.round}: ${v.lastPoint.winner} scored (${v.lastPoint.reason}). Resetting…`
    : v.phase === 'finished' ? (v.endReason === 'disconnect' ? 'Match ended: a team disconnected.' : `Match finished — ${v.lastPoint?.winner ?? 'unknown'} wins.`)
    : `${v.phase === 'lobby' ? 'Lobby' : 'Round '+v.round}`;
  const me=v.players.find(p=>p.id===room?.sessionId);
  $<HTMLParagraphElement>('me').textContent=me ? `You: ${me.name} · ${me.team} · ${me.status}${me.safe ? ' · home safe' : ''}` : 'Waiting for your player slot…';
  $<HTMLParagraphElement>('flags').textContent=(['north','south'] as const).map(team=>{
    const flag=v.flags[team], carrier=v.players.find(p=>p.id===flag.carrierId);
    return `${team} flag: ${flag.status}${carrier ? ` by ${carrier.name}` : ''}`;
  }).join(' · ');
  const list=$<HTMLUListElement>('players'); list.replaceChildren();
  for(const p of v.players){const li=document.createElement('li');li.textContent=`${p.name} (${p.team}) ${p.status}${p.connected?'':' · offline'} · K${p.kills}/D${p.deaths}/C${p.captures}`;li.style.color=cssColor(p.team);list.append(li);}
  const north=v.players.filter(p=>p.team==='north').length, south=v.players.filter(p=>p.team==='south').length;
  $<HTMLParagraphElement>('roster').textContent=`North ${north}/6 · South ${south}/6. ${v.phase === 'lobby' ? 'Host starts when both teams have a player.' : 'Roster locked.'}`;
  startButton.hidden=!(v.phase==='lobby' && v.hostId===room?.sessionId);
  startButton.disabled=north===0||south===0;
  $<HTMLDivElement>('room-details').hidden=false;
  drawMinimap();
}

function drawMinimap(): void {
  if(!view)return;
  const W=minimap.width,H=minimap.height;
  const mx=(x:number)=>(x-bounds.minX)/worldW*W, my=(y:number)=>(bounds.maxY-y)/worldH*H;
  ctx.clearRect(0,0,W,H);ctx.fillStyle='#173528';ctx.fillRect(0,0,W,H);
  for(const team of ['south','north'] as const){ctx.fillStyle=team==='north'?'#254d66':'#68432d';for(const r of DEFAULT_CONFIG.safe[team])ctx.fillRect(mx(r.minX),my(r.maxY),mx(r.maxX)-mx(r.minX),my(r.minY)-my(r.maxY));}
  for(const team of ['north','south'] as const){const r=DEFAULT_CONFIG.jail[team];ctx.fillStyle='#9c68b5';ctx.fillRect(mx(r.minX),my(r.maxY),mx(r.maxX)-mx(r.minX),my(r.minY)-my(r.maxY));const f=view.flags[team];ctx.fillStyle='#ffdd59';ctx.fillRect(mx(f.x)-3,my(f.y)-3,6,6);}
  for(const p of view.players){ctx.beginPath();ctx.arc(mx(p.x),my(p.y),p.id===room?.sessionId?5:3,0,Math.PI*2);ctx.fillStyle=cssColor(p.team);ctx.fill();}
}

async function connect(create: boolean): Promise<void> {
  if(room) return;
  status.textContent='Connecting…';
  const name=nickname.value.trim();
  if(name.length<1||name.length>18){status.textContent='Nickname must be 1–18 characters.';return;}
  try {
    const code=roomCode.value.trim();
    const next=create ? await client.create('ctf',{nickname:name}) : await client.joinById(code,{nickname:name});
    attach(next);
  } catch(error){status.textContent=`Could not join: ${error instanceof Error ? error.message : String(error)}`;}
}

function attach(next: Room): void {
  room=next;sequence=0;held.clear();tagPulse=false;
  roomCode.value=next.roomId;
  const invite=new URL(window.location.href);invite.searchParams.set('room',next.roomId);
  window.history.replaceState(null,'',invite);
  sessionStorage.setItem('ctf-token',next.reconnectionToken);
  sessionStorage.setItem('ctf-room',next.roomId);
  status.textContent=`Connected to room ${next.roomId}. Click the arena to control.`;
  $<HTMLSpanElement>('room-label').textContent=`Room ${next.roomId}`;
  const accept=(state: any)=>{try{view=JSON.parse(state.snapshot) as View;updateHud();}catch{status.textContent='Invalid server state.';}};
  accept(next.state);next.onStateChange(accept);
  next.onDrop(()=>{controls=false;held.clear();tagPulse=false;status.textContent='Connection lost; reconnecting…';});
  next.onReconnect(()=>{sessionStorage.setItem('ctf-token',next.reconnectionToken);status.textContent='Reconnected.';});
  next.onLeave(()=>{room=null;controls=false;held.clear();tagPulse=false;sessionStorage.removeItem('ctf-token');status.textContent='Disconnected. Create or join another room.';});
}

$<HTMLButtonElement>('create').onclick=()=>void connect(true);
$<HTMLButtonElement>('join').onclick=()=>void connect(false);
startButton.onclick=()=>room?.send('start',{});
$<HTMLButtonElement>('copy').onclick=()=>{const url=new URL(window.location.href);url.searchParams.set('room',room?.roomId ?? '');void navigator.clipboard.writeText(url.href).then(()=>{status.textContent='Invite link copied.';});};
roomCode.value=new URLSearchParams(window.location.search).get('room') ?? '';

const movementKeys=new Set(['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowLeft','ArrowDown','ArrowRight']);
window.addEventListener('keydown',event=>{
  if(event.code==='Escape'){controls=false;held.clear();tagPulse=false;status.textContent='Controls released. Click the arena to resume.';return;}
  if(!controls || event.target instanceof HTMLInputElement) return;
  if(movementKeys.has(event.code)){held.add(event.code);event.preventDefault();}
  if(event.code==='Space'){if(!event.repeat)tagPulse=true;event.preventDefault();}
});
window.addEventListener('keyup',event=>held.delete(event.code));
function stopInput(){controls=false;held.clear();tagPulse=false;}
window.addEventListener('blur',stopInput);
document.addEventListener('visibilitychange',()=>{if(document.hidden)stopInput();});
setInterval(()=>{
  if(!room || view?.phase!=='playing')return;
  const moveX=controls ? Number(held.has('KeyD')||held.has('ArrowRight'))-Number(held.has('KeyA')||held.has('ArrowLeft')) : 0;
  const moveY=controls ? Number(held.has('KeyW')||held.has('ArrowUp'))-Number(held.has('KeyS')||held.has('ArrowDown')) : 0;
  room.send('input',{sequence:sequence++,moveX,moveY,tag:controls&&tagPulse});tagPulse=false;
},50);

// A reload reclaims only the same reserved seat. An expired token leaves the user in the lobby.
const token=sessionStorage.getItem('ctf-token');
if(token && sessionStorage.getItem('ctf-room')===roomCode.value){
  void client.reconnect(token).then(attach).catch(()=>{sessionStorage.removeItem('ctf-token');status.textContent='Previous room expired. Create or join a room.';});
}
