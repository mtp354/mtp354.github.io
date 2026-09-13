/** Server-owned, engine-independent rules foundation. Not a network server.
 * Coordinates use Warcraft's x-right/y-up convention. The client must project y.
 * See docs/CORE_RULES.md for source evidence and explicit prototype deviations.
 */
export type Team = 'north' | 'south';
export type Point = { x: number; y: number };
export type Rect = { minX: number; minY: number; maxX: number; maxY: number };
export type Phase = 'lobby' | 'playing' | 'roundOver' | 'finished';
export type Player = Point & {
  id: string; team: Team; status: 'free' | 'jailed';
  kills: number; deaths: number; captures: number;
};
export type Flag = Point & { owner: Team; status: 'home' | 'carried' | 'returning'; carrierId: string | null };
export type Input = { sequence: number; moveX: number; moveY: number; tag: boolean };
export type Config = {
  bounds: Rect; safe: Record<Team, Rect[]>; jail: Record<Team, Rect>;
  rescueSpawn: Record<Team, Point>; spawn: Record<Team, Point>;
  flagHome: Record<Team, Point>; speed: number; pickupRadius: number;
  tagRadius: number; tagCooldownSeconds: number; flagReturnSpeed: number;
};
export type Match = {
  phase: Phase; round: number; targetScore: number; players: Player[];
  flags: Record<Team, Flag>; score: Record<Team, number>;
  lastPoint: { winner: Team; reason: 'capture' | 'allJailed' } | null;
};
const rect = (minX: number, minY: number, maxX: number, maxY: number): Rect => ({minX,minY,maxX,maxY});
/** Measured regions, but post-reset flag positions normalized from round one.
 * Bounds, tag radius, and return speed are provisional; see the specification.
 */
export const DEFAULT_CONFIG: Config = {
  bounds: rect(-1280,-3584,2368,3040),
  safe: {
    north: [rect(-1408,-576,2368,2656),rect(-960,2656,2368,3040)],
    south: [rect(-1376,-3904,2368,-192)],
  },
  // jail[team] is the jail located in that team's territory (holds the enemy).
  jail: {north: rect(512,1472,928,1824),south: rect(480,-2528,928,-2176)},
  rescueSpawn: {north:{x:192,y:576},south:{x:192,y:-1344}},
  spawn: {north:{x:0,y:448},south:{x:-128,y:-1152}},
  flagHome: {north:{x:-32,y:2416},south:{x:-32,y:-3200}},
  speed:370, pickupRadius:200, tagRadius:120, tagCooldownSeconds:1,
  flagReturnSpeed:150,
};
export const opposite = (team: Team): Team => team === 'north' ? 'south' : 'north';
export const distance = (a: Point,b: Point): number => Math.hypot(a.x-b.x,a.y-b.y);
export const center = (r: Rect): Point => ({x:(r.minX+r.maxX)/2,y:(r.minY+r.maxY)/2});
export const contains = (r: Rect,p: Point): boolean =>
  p.x>=r.minX && p.x<=r.maxX && p.y>=r.minY && p.y<=r.maxY;
export const isSafe = (p: Player,c: Config=DEFAULT_CONFIG): boolean => c.safe[p.team].some(r=>contains(r,p));
export const playerById = (m: Match,id: string): Player | undefined => m.players.find(p=>p.id===id);
const flagAtHome = (owner: Team,c: Config): Flag => ({owner,...c.flagHome[owner],status:'home',carrierId:null});

export function createMatch(roster: Array<{id:string;team:Team}>,targetScore=5,c:Config=DEFAULT_CONFIG): Match {
  if (!Number.isSafeInteger(targetScore)||targetScore<1||targetScore>99) throw new Error('Invalid target score');
  if (roster.length>12||new Set(roster.map(p=>p.id)).size!==roster.length) throw new Error('Invalid roster');
  if (roster.some(p=>typeof p.id!=='string'||p.id.length<1||p.id.length>64||(p.team!=='north'&&p.team!=='south'))) throw new Error('Invalid player');
  if (['north','south'].some(team=>roster.filter(p=>p.team===team).length>6)) throw new Error('Team full');
  return {phase:'lobby',round:1,targetScore,score:{north:0,south:0},lastPoint:null,
    flags:{north:flagAtHome('north',c),south:flagAtHome('south',c)},
    players:roster.map(p=>({...p,...c.spawn[p.team],status:'free',kills:0,deaths:0,captures:0}))};
}
export function startMatch(m:Match): boolean {
  if(m.phase!=='lobby'||!m.players.some(p=>p.team==='north')||!m.players.some(p=>p.team==='south')) return false;
  m.phase='playing';return true;
}
/** Strict wire-shape validation. Sequence ordering/rate limiting belong to the server. */
export function parseInput(raw:unknown): Input | null {
  if(typeof raw!=='object'||raw===null||Array.isArray(raw))return null;
  const v=raw as Record<string,unknown>;
  if(Object.keys(v).some(k=>!['sequence','moveX','moveY','tag'].includes(k)))return null;
  if(typeof v.sequence!=='number'||!Number.isSafeInteger(v.sequence)||v.sequence<0)return null;
  if(typeof v.moveX!=='number'||!Number.isFinite(v.moveX)||Math.abs(v.moveX)>1)return null;
  if(typeof v.moveY!=='number'||!Number.isFinite(v.moveY)||Math.abs(v.moveY)>1)return null;
  if(typeof v.tag!=='boolean')return null;
  return {sequence:v.sequence,moveX:v.moveX,moveY:v.moveY,tag:v.tag};
}
/** dt is supplied ONLY by the server fixed-step loop, never from a client message. */
export function movePlayer(m:Match,p:Player,input:Input,dt:number,c:Config=DEFAULT_CONFIG): void {
  if(!Number.isFinite(dt)||dt<0||dt>0.1)throw new Error('Use server substeps of at most 100 ms');
  if(m.phase!=='playing'||p.status!=='free')return;
  const safeInput=parseInput(input);if(!safeInput)return;
  const divisor=Math.max(1,Math.hypot(safeInput.moveX,safeInput.moveY));
  p.x=Math.min(c.bounds.maxX,Math.max(c.bounds.minX,p.x+safeInput.moveX/divisor*c.speed*dt));
  p.y=Math.min(c.bounds.maxY,Math.max(c.bounds.minY,p.y+safeInput.moveY/divisor*c.speed*dt));
  for(const flag of Object.values(m.flags))if(flag.carrierId===p.id){flag.x=p.x;flag.y=p.y;}
}
export function canTag(attacker:Player,victim:Player,c:Config=DEFAULT_CONFIG): boolean {
  return attacker.id!==victim.id&&attacker.team!==victim.team&&attacker.status==='free'&&victim.status==='free'
    &&!isSafe(victim,c)&&distance(attacker,victim)<=c.tagRadius;
}
/** Caller additionally enforces tag cooldowns and canonical same-tick ordering. */
export function tryTag(m:Match,attackerId:string,victimId:string,c:Config=DEFAULT_CONFIG): boolean {
  const a=playerById(m,attackerId),v=playerById(m,victimId);
  if(m.phase!=='playing'||!a||!v||!canTag(a,v,c))return false;
  dropCarriedFlag(m,v.id);v.status='jailed';v.deaths++;a.kills++;
  Object.assign(v,center(c.jail[opposite(v.team)]));
  const winner=allJailedWinner(m);if(winner)finishRound(m,winner,'allJailed');
  return true;
}
/** Safe for both tags and disconnect cleanup. Does not itself award a point. */
export function dropCarriedFlag(m:Match,playerId:string): boolean {
  const p=playerById(m,playerId);if(!p)return false;
  const f=Object.values(m.flags).find(f=>f.carrierId===playerId);if(!f)return false;
  f.x=p.x;f.y=p.y;f.carrierId=null;f.status='returning';return true;
}
export function tryPickup(m:Match,playerId:string,c:Config=DEFAULT_CONFIG): boolean {
  const p=playerById(m,playerId);if(m.phase!=='playing'||!p||p.status!=='free')return false;
  const f=m.flags[opposite(p.team)];
  if(f.status==='carried'||Object.values(m.flags).some(f=>f.carrierId===p.id)||distance(p,f)>c.pickupRadius)return false;
  f.status='carried';f.carrierId=p.id;f.x=p.x;f.y=p.y;return true;
}
export function tryCapture(m:Match,playerId:string,c:Config=DEFAULT_CONFIG): boolean {
  const p=playerById(m,playerId);if(m.phase!=='playing'||!p||p.status!=='free'||!isSafe(p,c))return false;
  if(m.flags[opposite(p.team)].carrierId!==p.id)return false;
  p.captures++;return finishRound(m,p.team,'capture');
}
export function tryRescue(m:Match,rescuerId:string,c:Config=DEFAULT_CONFIG): number {
  const p=playerById(m,rescuerId);
  if(m.phase!=='playing'||!p||p.status!=='free'||!contains(c.jail[opposite(p.team)],p))return 0;
  const jailed=m.players.filter(v=>v.team===p.team&&v.status==='jailed');
  for(const v of jailed){v.status='free';Object.assign(v,c.rescueSpawn[v.team]);}
  return jailed.length;
}
/** Empty teams are not an automatic all-jailed win; disconnect policy is external. */
export function allJailedWinner(m:Match): Team | null {
  if(m.phase!=='playing'||!m.players.some(p=>p.team==='north')||!m.players.some(p=>p.team==='south'))return null;
  for(const team of ['north','south'] as const){
    const members=m.players.filter(p=>p.team===team);
    if(members.every(p=>p.status==='jailed'))return opposite(team);
  }
  return null;
}
export function finishRound(m:Match,winner:Team,reason:'capture'|'allJailed'): boolean {
  if(m.phase!=='playing')return false;
  m.score[winner]++;m.lastPoint={winner,reason};
  m.phase=m.score[winner]>=m.targetScore?'finished':'roundOver';return true;
}
export function nextRound(m:Match,c:Config=DEFAULT_CONFIG): boolean {
  if(m.phase!=='roundOver')return false;
  m.round++;m.lastPoint=null;
  m.flags={north:flagAtHome('north',c),south:flagAtHome('south',c)};
  for(const p of m.players){p.status='free';Object.assign(p,c.spawn[p.team]);}
  m.phase='playing';return true;
}
/** Prototype straight-line return, not Warcraft's pathfinding. Provisional speed. */
export function advanceReturningFlags(m:Match,dt:number,c:Config=DEFAULT_CONFIG): void {
  if(!Number.isFinite(dt)||dt<0||dt>0.1)throw new Error('Use server substeps of at most 100 ms');
  if(m.phase!=='playing')return;
  for(const f of Object.values(m.flags)){
    if(f.status!=='returning')continue;
    const home=c.flagHome[f.owner],d=distance(f,home),step=c.flagReturnSpeed*dt;
    if(d<=step){Object.assign(f,home);f.status='home';f.carrierId=null;}
    else {f.x+=(home.x-f.x)/d*step;f.y+=(home.y-f.y)/d*step;}
  }
}
