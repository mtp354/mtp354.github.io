import { Client, type Room } from 'colyseus.js';
import { DEFAULT_CONFIG, isSafe, opposite } from '@ctf/rules';
import { createArena, drawMinimap } from './arena';
import type { GameState, PlayerView } from './types';
import './style.css';

const app = document.querySelector<HTMLDivElement>('#app')!;
app.innerHTML = `
  <header class="site-header"><a href="${import.meta.env.BASE_URL}" class="brand" aria-label="Capture the Flag home"><span class="brand-mark" aria-hidden="true">⚑</span> CAPTURE THE FLAG <span class="edition">PLAYTEST</span></a><span class="connection" id="connection">Ready to play</span></header>
  <main>
    <section id="welcome" class="welcome">
      <div class="intro"><p class="eyebrow">NORTH VS. SOUTH · UP TO 6V6</p><h1>Cross the line.<br><span>Bring it home.</span></h1><p class="intro-copy">Steal the enemy flag. Make it back to safety.<br>Get caught? Your teammates can break you out.</p>
        <div class="field-art" aria-hidden="true"><span class="art-north">NORTH</span><i class="art-flag north">⚑</i><span class="art-path"></span><i class="art-player"></i><span class="art-band">SAFE CROSSING</span><i class="art-flag south">⚑</i><span class="art-south">SOUTH</span></div>
        <p class="origin-note">A small browser remake of a custom Warcraft III map.<br>Original rules, a new arena, and no installation for players.</p>
      </div>
      <div class="join-card"><p class="eyebrow">GET INTO THE GAME</p><h2>Ready when you are.</h2><label for="nickname">Your name <span class="muted">optional</span></label><input id="nickname" maxlength="20" autocomplete="nickname" placeholder="Choose a name" />
        <button class="primary large" id="practice">Play practice <span aria-hidden="true">→</span></button><p class="button-note">Jump straight into 2v2 with three bots.</p>
        <div class="divider"><span>PLAY WITH FRIENDS</span></div><button class="secondary large" id="create">Create a game</button><p class="button-note">Share a link. Your friends click it to join.</p>
        <form id="join-form"><label for="room-code">Have an invite?</label><div class="join-row"><input id="room-code" placeholder="Room code or invite link" autocomplete="off" spellcheck="false" required /><button class="secondary" id="join" type="submit">Join</button></div></form>
        <div id="front-status" class="status" role="status" aria-live="polite"></div>
        <p class="keyboard-note"><kbd>WASD</kbd> or <kbd>↑ ↓ ← →</kbd> move &nbsp; <kbd>Space</kbd> tag<br>Best played on a computer with a keyboard.</p>
      </div>
    </section>
    <section id="play" class="play" hidden>
      <div class="match-header"><div><p class="eyebrow" id="room-label">YOUR ROOM</p><div class="room-tools"><strong id="room-id"></strong><button class="quiet" id="copy-invite">Copy invite link</button><button class="quiet" id="leave">Leave</button></div></div>
        <div class="scoreboard" aria-label="Match score"><div class="north"><span>NORTH</span><strong id="north-score">0</strong></div><span class="score-separator">:</span><div class="south"><strong id="south-score">0</strong><span>SOUTH</span></div><small id="target">FIRST TO 5</small></div>
        <div class="phase-meta"><strong id="phase">LOBBY</strong><span id="round">Round 1</span></div>
      </div>
      <div class="game-layout"><div class="arena-column"><div class="objective"><span id="local-badge" class="team-badge">CONNECTING</span><span id="objective-text">Getting the arena ready…</span><span id="tag-status">Space · Tag</span></div>
        <div class="arena-wrap" id="arena-wrap" tabindex="0" role="application" aria-label="Capture the Flag arena. WASD or arrows to move, Space to tag, Escape to release controls."><div id="arena"></div><div id="game-overlay" class="game-overlay"><div class="overlay-card"><p id="overlay-kicker" class="eyebrow">YOUR ROOM IS READY</p><h2 id="overlay-title">Bring your team.</h2><p id="overlay-description"></p><button class="primary" id="start">Start match</button><button class="primary" id="resume" hidden>Resume controls</button><button class="primary" id="rematch" hidden>Play again</button><button class="secondary" id="retry" hidden>Reconnect</button></div></div></div>
        <div class="controls-bar"><span><kbd>WASD</kbd> / <kbd>Arrows</kbd> Move &nbsp; <kbd>Space</kbd> Tag nearby enemy</span><span><kbd>Esc</kbd> Release controls</span></div>
        <div id="game-notice" class="game-notice" role="status" aria-live="polite"></div>
      </div><aside class="sidebar"><section class="mini-section"><div class="section-heading"><h3>Arena</h3><span>YOU <i class="you-dot"></i></span></div><canvas id="minimap" width="164" height="298" aria-label="Full arena map showing teams, flags, and jails"></canvas><p class="map-legend"><span class="north">● North</span><span class="south">● South</span><span>⚑ Flag &nbsp; □ Jail</span></p></section>
        <section><h3>Flags</h3><p class="flag-status north" id="north-flag"></p><p class="flag-status south" id="south-flag"></p></section>
        <section><div class="section-heading"><h3>Players <span id="player-count"></span></h3><span title="Tags / captures">TAG / FLAG</span></div><ul id="roster" class="roster"></ul></section>
        <details><summary>How to play</summary><p>You are protected in your own territory. The striped center band protects both teams.</p><p>Pick up the enemy flag by touching it, then cross into your safe side to score.</p><p>Press Space to tag a nearby, unprotected enemy. Enter the enemy jail to rescue all your jailed teammates.</p><p>Jailing the entire opposing team also scores. First to five wins.</p></details>
      </aside></div>
      <div id="invite-fallback" class="invite-fallback" hidden><label for="invite-url">Invite link — copy and send to a friend</label><input id="invite-url" readonly /><button class="quiet" id="hide-invite">Close</button></div>
    </section>
  </main><footer>CAPTURE THE FLAG <span>Small teams. Good escapes.</span></footer>`;

const el = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T;
const text = (id: string, value: string) => { if (el(id).textContent !== value) el(id).textContent = value; };
const show = (id: string, visible: boolean) => { el(id).hidden = !visible; };
const teamName = (team: string) => team === 'north' ? 'North' : 'South';
const safeRead = (storage: Storage, key: string) => { try { return storage.getItem(key); } catch { return null; } };
const safeWrite = (storage: Storage, key: string, value: string | null) => { try { if (value === null) storage.removeItem(key); else storage.setItem(key, value); } catch { /* Gameplay works without storage. */ } };
const endpoint = import.meta.env.VITE_GAME_ENDPOINT || `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${import.meta.env.DEV ? '/game' : ''}`;
const client = new Client(endpoint);
const reconnectKey = `ctf-reconnect:${endpoint}`;
let room: Room<GameState> | undefined;
let state: GameState | undefined;
let destroyArena: (() => void) | undefined;
let busy = false;
let focused = false;
let reconnecting = false;
let intentionallyLeaving = false;
let connectionGeneration = 0;
let sequence = Date.now() * 1000;
let tagQueued = false;
let noticeUntil = 0;
let rosterSignature = '';
let lastPhase = '';
const keys = new Set<string>();
const nickname = el<HTMLInputElement>('nickname');
nickname.value = safeRead(localStorage, 'ctf-nickname') || '';

type SavedRoom = { token: string; roomId: string; savedAt: number };
function savedRoom(): SavedRoom | undefined {
  try {
    const data = JSON.parse(safeRead(sessionStorage, reconnectKey) || 'null');
    if (data && typeof data.token === 'string' && typeof data.roomId === 'string') return data;
  } catch { /* Ignore stale or blocked browser storage. */ }
}
function remember(joined: Room<GameState>) {
  safeWrite(sessionStorage, reconnectKey, JSON.stringify({ token: joined.reconnectionToken, roomId: joined.roomId, savedAt: Date.now() }));
}
function playerName() {
  const chosen = nickname.value.trim().slice(0, 20) || `Runner ${Math.floor(1000 + Math.random() * 9000)}`;
  nickname.value = chosen;
  safeWrite(localStorage, 'ctf-nickname', chosen);
  return chosen;
}
function setBusy(value: boolean, message = '') {
  busy = value;
  for (const id of ['practice', 'create', 'join']) el<HTMLButtonElement>(id).disabled = value;
  text('front-status', message);
  el('front-status').classList.remove('error');
  text('connection', value ? 'Connecting…' : room ? 'Connected' : 'Ready to play');
}
function explainError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  if (/locked|already started|in progress/i.test(message)) return 'That match has already started. Ask the host to create a new room, or play practice.';
  if (/not found|not defined|expired|invalid room|invalid roomId|4212/i.test(message)) return 'That room is no longer available. Check the invite or create a new game.';
  if (/full|maxClients/i.test(message)) return 'That room is full (12 players). Create another game to play.';
  if (/fetch|network|connect|timeout|Failed|error/i.test(message)) return 'Could not reach the game server. Make sure it is running, then try again.';
  return message.slice(0, 180) || 'Could not join the game. Please try again.';
}
function frontError(message: string) {
  setBusy(false, message);
  el('front-status').classList.add('error');
}
function notice(message: string) { text('game-notice', message); noticeUntil = Date.now() + 7000; }
function inviteURL() {
  const url = new URL(location.href);
  url.search = '';
  url.hash = '';
  if (room) url.searchParams.set('room', room.roomId);
  return url.toString();
}
function parseRoomCode(value: string) {
  const trimmed = value.trim();
  if (!trimmed) throw new Error('Enter a room code or paste an invite link.');
  let code = trimmed;
  if (trimmed.includes('://')) {
    const url = new URL(trimmed);
    code = url.searchParams.get('room') || '';
  }
  if (!/^[a-zA-Z0-9_-]{4,64}$/.test(code)) throw new Error('Use the room code or full invite link from the host.');
  return code;
}
async function connect(kind: 'practice' | 'create' | 'join', code?: string) {
  if (busy || room) return;
  setBusy(true, kind === 'practice' ? 'Setting up your practice game…' : 'Connecting to your room…');
  const generation = ++connectionGeneration;
  try {
    const options = { nickname: playerName() };
    const joined = kind === 'join'
      ? await client.joinById<GameState>(parseRoomCode(code || ''), options)
      : await client.create<GameState>('ctf', { ...options, practice: kind === 'practice' });
    if (generation !== connectionGeneration) { await joined.leave(); return; }
    attachRoom(joined);
  } catch (error) { frontError(explainError(error)); }
}
function attachRoom(joined: Room<GameState>) {
  room = joined;
  state = undefined;
  reconnecting = false;
  intentionallyLeaving = false;
  lastPhase = '';
  rosterSignature = '';
  remember(joined);
  show('welcome', false); show('play', true);
  setBusy(false);
  text('room-id', joined.roomId);
  const url = new URL(location.href); url.searchParams.set('room', joined.roomId); history.replaceState(null, '', url);
  joined.onStateChange((snapshot) => {
    if (room !== joined) return;
    state = snapshot;
    if (snapshot.phase === 'playing' && lastPhase === '') acquireFocus();
    lastPhase = snapshot.phase;
    render();
  });
  joined.onMessage('notice', (payload: { message?: string }) => { if (payload?.message) notice(payload.message); });
  joined.onError((_code, message) => { notice(message || 'Connection error.'); });
  joined.onLeave(() => {
    if (room !== joined || intentionallyLeaving) return;
    releaseFocus();
    room = undefined;
    reconnecting = true;
    text('connection', 'Connection lost');
    render();
    void reconnect(joined.reconnectionToken);
  });
  if (!destroyArena) destroyArena = createArena(el('arena'), { state: () => state, localId: () => room?.sessionId || '' });
  render();
}
async function reconnect(token?: string) {
  if (busy) return;
  const saved = savedRoom();
  const actualToken = token || saved?.token;
  if (!actualToken) { frontError('Your reconnect window ended. Create or join a new game.'); return; }
  busy = true;
  reconnecting = true;
  text('connection', 'Reconnecting…');
  text('front-status', 'Rejoining your previous game…');
  const generation = ++connectionGeneration;
  let lastError: unknown;
  for (let attempt = 0; attempt < 5; attempt++) {
    if (generation !== connectionGeneration) return;
    try {
      const joined = await client.reconnect<GameState>(actualToken);
      if (generation !== connectionGeneration) { await joined.leave(); return; }
      attachRoom(joined);
      notice('You are back in the game.');
      return;
    } catch (error) {
      lastError = error;
      if (attempt < 4) await new Promise((resolve) => setTimeout(resolve, 1300));
    }
  }
  busy = false;
  reconnecting = false;
  safeWrite(sessionStorage, reconnectKey, null);
  text('connection', 'Disconnected');
  if (state) { notice('Could not reconnect. Leave to start a new game.'); render(); }
  else { show('play', false); show('welcome', true); frontError(`Could not restore your previous game. ${explainError(lastError)}`); }
}
async function leave() {
  ++connectionGeneration;
  intentionallyLeaving = true;
  releaseFocus();
  const oldRoom = room;
  room = undefined; state = undefined; reconnecting = false;
  safeWrite(sessionStorage, reconnectKey, null);
  const url = new URL(location.href); url.searchParams.delete('room'); history.replaceState(null, '', url);
  destroyArena?.(); destroyArena = undefined;
  show('play', false); show('welcome', true); show('invite-fallback', false);
  setBusy(false); focused = false;
  if (oldRoom) await oldRoom.leave().catch(() => undefined);
}
function acquireFocus() {
  if (!room || state?.phase !== 'playing') return;
  focused = true;
  el('arena-wrap').focus({ preventScroll: true });
  renderOverlay();
}
function releaseFocus() {
  const wasFocused = focused;
  focused = false; keys.clear(); tagQueued = false;
  if (room && wasFocused) sendInput();
  renderOverlay();
}
function sendInput() {
  if (!room || !state) return;
  const active = focused && state.phase === 'playing' && !document.hidden;
  const moveX = active ? Number(keys.has('KeyD') || keys.has('ArrowRight')) - Number(keys.has('KeyA') || keys.has('ArrowLeft')) : 0;
  const moveY = active ? Number(keys.has('KeyW') || keys.has('ArrowUp')) - Number(keys.has('KeyS') || keys.has('ArrowDown')) : 0;
  sequence = Math.max(sequence + 1, Date.now() * 1000);
  room.send('input', { sequence, moveX, moveY, tag: active && tagQueued });
  tagQueued = false;
}
function rosterPlayers() { return state?.players ? [...state.players.values()].sort((a, b) => a.team.localeCompare(b.team) || a.slot - b.slot) : []; }
function renderRoster(players: PlayerView[]) {
  const signature = JSON.stringify(players.map((p) => [p.id, p.nickname, p.team, p.status, p.connected, p.bot, p.kills, p.captures, state?.hostId]));
  if (signature === rosterSignature) return;
  rosterSignature = signature;
  const roster = el('roster'); roster.replaceChildren();
  for (const p of players) {
    const row = document.createElement('li'); row.className = p.team;
    const identity = document.createElement('span');
    const name = document.createElement('strong'); name.textContent = `${p.nickname}${p.id === room?.sessionId ? ' (you)' : ''}`;
    const detail = document.createElement('small'); detail.textContent = [teamName(p.team), p.bot ? 'bot' : p.id === state?.hostId ? 'host' : '', p.status === 'jailed' ? 'jailed' : !p.connected ? 'reconnecting' : ''].filter(Boolean).join(' · ');
    identity.append(name, detail);
    const stats = document.createElement('span'); stats.className = 'player-stats'; stats.textContent = `${p.kills} / ${p.captures}`; stats.title = `${p.kills} tags, ${p.captures} captures, ${p.deaths} times jailed`;
    row.append(identity, stats); roster.append(row);
  }
}
function render() {
  if (!state?.players || !state.flags) { renderOverlay(); return; }
  const players = rosterPlayers();
  const local = room ? state.players.get(room.sessionId) : undefined;
  text('room-label', state.practice ? 'PRACTICE · 2V2 WITH BOTS' : 'INVITE YOUR FRIENDS');
  el<HTMLButtonElement>('copy-invite').disabled = state.practice;
  el('copy-invite').title = state.practice ? 'Practice games are solo. Create a game to invite friends.' : '';
  text('north-score', String(state.northScore)); text('south-score', String(state.southScore));
  text('target', `FIRST TO ${state.targetScore}`);
  text('phase', ({ lobby: 'LOBBY', playing: 'IN PLAY', roundOver: 'ROUND OVER', finished: 'GAME OVER' })[state.phase]);
  text('round', `Round ${state.round}`); text('player-count', `${players.length}/12`);
  renderRoster(players);
  if (local) {
    el('local-badge').className = `team-badge ${local.team}`;
    text('local-badge', `${teamName(local.team).toUpperCase()} · ${local.status === 'jailed' ? 'JAILED' : isSafe(local) ? 'SAFE' : 'EXPOSED'}`);
    const carrying = state.flags.get(opposite(local.team))?.carrierId === local.id;
    const jailedAllies = players.some((p) => p.team === local.team && p.status === 'jailed');
    const enemyFlag = state.flags.get(opposite(local.team));
    const jail = DEFAULT_CONFIG.jail[opposite(local.team)];
    const destination = carrying ? DEFAULT_CONFIG.spawn[local.team] : jailedAllies
      ? { x: (jail.minX + jail.maxX) / 2, y: (jail.minY + jail.maxY) / 2 }
      : enemyFlag || DEFAULT_CONFIG.flagHome[opposite(local.team)];
    const dx = destination.x - local.x, dy = destination.y - local.y;
    const direction = ['→', '↗', '↑', '↖', '←', '↙', '↓', '↘'][(Math.round(Math.atan2(dy, dx) / (Math.PI / 4)) + 8) % 8];
    text('objective-text', local.status === 'jailed' ? 'A free teammate can rescue you from this jail.' : carrying ? `You have the flag! ${direction} Return to your safe territory.` : jailedAllies ? `Teammates jailed! ${direction} Reach their jail to rescue everyone.` : `${direction} Steal the ${teamName(opposite(local.team))} flag. Bring it to your safe side.`);
    const cooldown = Math.max(0, local.tagReadyAt - state.serverTime);
    text('tag-status', local.status === 'jailed' ? 'Awaiting rescue' : cooldown > 0 ? `Tag ready in ${cooldown.toFixed(1)}s` : 'Space · Tag ready');
  }
  for (const team of ['north', 'south'] as const) {
    const flag = state.flags.get(team);
    if (!flag) continue;
    const carrier = flag.carrierId ? state.players.get(flag.carrierId) : undefined;
    text(`${team}-flag`, `⚑ ${teamName(team)} · ${flag.status === 'home' ? 'at home' : flag.status === 'returning' ? 'returning home' : `with ${carrier?.nickname || 'a runner'}`}`);
  }
  drawMinimap(el<HTMLCanvasElement>('minimap'), state, room?.sessionId || '');
  renderOverlay();
}
function renderOverlay() {
  if (el('play').hidden) return;
  const phase = state?.phase;
  for (const id of ['start', 'resume', 'rematch', 'retry']) show(id, false);
  let kicker = '', title = '', description = '';
  if (!room) {
    kicker = 'CONNECTION'; title = reconnecting ? 'Rejoining your game…' : 'Connection lost';
    description = reconnecting ? 'Your spot is held briefly. We are trying to bring you back.' : 'Leave this room to create or join another game.';
  } else if (!state) {
    kicker = 'CONNECTED'; title = 'Opening the arena…'; description = 'Getting the latest game state.';
  } else if (phase === 'lobby') {
    const players = rosterPlayers();
    const canStart = players.some((p) => p.team === 'north' && p.connected) && players.some((p) => p.team === 'south' && p.connected);
    const host = state.hostId === room.sessionId;
    kicker = `ROOM ${room.roomId}`; title = canStart ? 'Teams are ready.' : 'Bring your team.';
    description = host ? canStart ? 'Start whenever you are ready. New players can join until the match starts.' : 'Copy the invite link and send it to a friend. You need one player on each team to start.' : 'You are in! The host will start the match once both teams are ready.';
    show('start', host); el<HTMLButtonElement>('start').disabled = !canStart;
  } else if (phase === 'roundOver') {
    kicker = `ROUND ${state.round} COMPLETE`; title = `${teamName(state.lastPointWinner)} scores!`;
    description = `${state.lastPointReason === 'allJailed' ? 'The whole opposing team was jailed.' : 'The flag made it home.'} Next round in ${Math.max(1, Math.ceil(state.phaseEndsAt - state.serverTime))}…`;
  } else if (phase === 'finished') {
    kicker = 'MATCH COMPLETE';
    title = state.endReason ? 'Match ended' : `${teamName(state.lastPointWinner)} wins!`;
    description = state.endReason ? 'A team no longer has players. Create a new room to play again.' : `Final score: North ${state.northScore} · South ${state.southScore}.`;
    show('rematch', state.hostId === room.sessionId && !state.endReason);
  } else if (!focused) {
    kicker = 'CONTROLS PAUSED'; title = 'Jump back in.';
    description = 'The match is still running. Click below or click the arena to resume.';
    show('resume', true);
  } else { show('game-overlay', false); return; }
  text('overlay-kicker', kicker); text('overlay-title', title); text('overlay-description', description);
  show('game-overlay', true);
}

el('practice').addEventListener('click', () => void connect('practice'));
el('create').addEventListener('click', () => void connect('create'));
el('join-form').addEventListener('submit', (event) => { event.preventDefault(); void connect('join', el<HTMLInputElement>('room-code').value); });
el('leave').addEventListener('click', () => void leave());
el('start').addEventListener('click', () => { room?.send('start', {}); focused = true; el('arena-wrap').focus(); });
el('rematch').addEventListener('click', () => { room?.send('rematch', {}); focused = true; el('arena-wrap').focus(); });
el('resume').addEventListener('click', acquireFocus);
el('retry').addEventListener('click', () => void reconnect());
el('arena-wrap').addEventListener('pointerdown', (event) => { if (!(event.target instanceof HTMLButtonElement)) acquireFocus(); });
el('copy-invite').addEventListener('click', async () => {
  const url = inviteURL();
  try { await navigator.clipboard.writeText(url); notice('Invite link copied. Send it to a friend to join.'); }
  catch { show('invite-fallback', true); el<HTMLInputElement>('invite-url').value = url; el<HTMLInputElement>('invite-url').select(); }
});
el('hide-invite').addEventListener('click', () => show('invite-fallback', false));
window.addEventListener('blur', releaseFocus);
document.addEventListener('visibilitychange', () => { if (document.hidden) releaseFocus(); });
document.addEventListener('focusin', (event) => { if (focused && event.target instanceof HTMLElement && !el('arena-wrap').contains(event.target)) releaseFocus(); });
window.addEventListener('keydown', (event) => {
  if (event.code === 'Escape') { releaseFocus(); el('arena-wrap').blur(); return; }
  if (!focused || state?.phase !== 'playing') return;
  if (['KeyW', 'KeyA', 'KeyS', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(event.code)) {
    event.preventDefault(); keys.add(event.code);
    if (event.code === 'Space' && !event.repeat) tagQueued = true;
  }
});
window.addEventListener('keyup', (event) => { keys.delete(event.code); });
setInterval(() => { sendInput(); if (state) render(); if (noticeUntil && Date.now() > noticeUntil) { text('game-notice', ''); noticeUntil = 0; } }, 50);

const requestedRoom = new URL(location.href).searchParams.get('room');
const previous = savedRoom();
if (previous && (!requestedRoom || requestedRoom === previous.roomId)) void reconnect();
else if (requestedRoom) { el<HTMLInputElement>('room-code').value = requestedRoom; void connect('join', requestedRoom); }
