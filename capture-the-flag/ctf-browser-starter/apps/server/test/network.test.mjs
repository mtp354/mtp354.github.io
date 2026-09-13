import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer as createTcpServer } from 'node:net';
import { Client } from '@colyseus/sdk';
import { createGameServer } from '../dist/main.js';
import { testRooms } from '../dist/GameRoom.js';

process.env.CTF_TEST_HARNESS = '1';

function freePort() {
  return new Promise((resolve, reject) => {
    const socket = createTcpServer();
    socket.once('error', reject);
    socket.listen(0, '127.0.0.1', () => {
      const port = socket.address().port;
      socket.close(() => resolve(port));
    });
  });
}
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const state = room => JSON.parse(room.state.snapshot);
function waitFor(room, check, timeout = 3000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const interval = setInterval(() => {
      const value = state(room);
      if (check(value)) { clearInterval(interval); resolve(value); }
      else if (Date.now() - start > timeout) { clearInterval(interval); reject(new Error(`Timed out. Last state: ${JSON.stringify(value)}`)); }
    }, 20);
  });
}
const find = (view, id) => view.players.find(p => p.id === id);
const send = (room, sequence, moveX = 0, moveY = 0, tag = false) => room.send('input', { sequence, moveX, moveY, tag });

test('real Colyseus sockets: isolated rooms, gameplay, safeguards, and twelve clients', { timeout: 60000 }, async () => {
  const port = await freePort();
  const server = createGameServer();
  await server.listen(port, '127.0.0.1');
  const client = () => new Client(`http://127.0.0.1:${port}`);
  const rooms = [];
  const create = async name => { const room = await client().create('ctf', { nickname: name }); rooms.push(room); return room; };
  const join = async (id, name) => { const room = await client().joinById(id, { nickname: name }); rooms.push(room); return room; };
  try {
    const health = await fetch(`http://127.0.0.1:${port}/health`);
    assert.deepEqual(await health.json(), { ok: true });

    const north1 = await create('North 1');
    const south1 = await join(north1.roomId, 'South 1');
    const north2 = await join(north1.roomId, 'North 2');
    const south2 = await join(north1.roomId, 'South 2');
    const separate = await create('Elsewhere');
    assert.notEqual(separate.roomId, north1.roomId);
    let v = await waitFor(north1, s => s.players.length === 4);
    assert.equal((await waitFor(south1, s => s.players.length === 4)).players.length, 4);
    assert.equal(state(separate).players.length, 1);
    assert.deepEqual(v.players.map(p => p.team), ['north', 'south', 'north', 'south']);

    south1.send('start', {});
    await sleep(100);
    assert.equal(state(north1).phase, 'lobby', 'non-host cannot start');
    north1.send('start', {});
    v = await waitFor(north1, s => s.phase === 'playing');
    assert.equal((await waitFor(south2, s => s.phase === 'playing')).phase, 'playing');

    const before = find(v, north1.sessionId).x;
    north1.send('input', { sequence: 0, moveX: 1, moveY: 0, tag: false, actorId: south1.sessionId });
    north1.send('input', { sequence: 0, moveX: 100000, moveY: 0, tag: false });
    north1.send('input', { sequence: 0, moveX: NaN, moveY: 0, tag: false });
    north1.send('input', { sequence: 0, moveX: 0, moveY: 0, tag: false, pad: 'x'.repeat(2000) });
    await sleep(130);
    assert.equal(find(state(north1), north1.sessionId).x, before, 'malformed inputs did not move');
    send(north1, 1, 1);
    v = await waitFor(south1, s => find(s,north1.sessionId).x > before + 10);
    assert(find(v,north1.sessionId).x <= before + 110, 'network message frequency did not set speed');
    send(north1, 1, -1);
    await sleep(100);
    assert(find(state(north1),north1.sessionId).x >= find(v,north1.sessionId).x, 'replayed sequence did not reverse motion');
    send(north1, 2);
    for(let i=3;i<55;i++) send(north1,i,1);
    await sleep(150);
    const burstX=find(state(north1),north1.sessionId).x;
    assert(burstX - before < 200, 'rate burst did not speed movement beyond fixed-step bound');
    await sleep(350);
    const expiredX=find(state(north1),north1.sessionId).x;
    await sleep(150);
    assert.equal(find(state(north1),north1.sessionId).x,expiredX,'stale intent expires');

    const model = testRooms.get(north1.roomId);
    assert(model, 'in-process test handle exists');
    model.testOnlyMutate(m => {
      Object.assign(m.players.find(p=>p.id===north1.sessionId), {x:0,y:-1100});
      Object.assign(m.players.find(p=>p.id===south1.sessionId), {x:0,y:-1100});
    });
    send(south1,1,0,0,true);
    v=await waitFor(north2,s=>find(s,north1.sessionId).status==='jailed');
    assert.equal(find(v,north1.sessionId).deaths,1);
    assert.equal(find(v,south1.sessionId).kills,1);
    assert.equal(v.phase,'playing');
    model.testOnlyMutate(m => Object.assign(m.players.find(p=>p.id===north2.sessionId), {x:704,y:-2352}));
    model.step();model.publish();
    v=await waitFor(north1,s=>find(s,north1.sessionId).status==='free');
    assert.deepEqual([find(v,north1.sessionId).x,find(v,north1.sessionId).y],[192,576], 'jailbreak revives at named home spawn');

    model.testOnlyMutate(m => {
      Object.assign(m.players.find(p=>p.id===north1.sessionId),{x:-32,y:-3200});
      Object.assign(m.players.find(p=>p.id===south1.sessionId),{x:-32,y:2416});
    });
    model.step();model.publish();
    v=await waitFor(south2,s=>s.flags.north.status==='carried'&&s.flags.south.status==='carried');
    assert.equal(v.flags.south.carrierId,north1.sessionId);
    model.testOnlyMutate(m => {
      Object.assign(m.players.find(p=>p.id===north1.sessionId),{x:0,y:-1500});
      Object.assign(m.players.find(p=>p.id===south2.sessionId),{x:0,y:-1500});
    });
    send(south2,1,0,0,true);
    v=await waitFor(north2,s=>s.flags.south.status==='returning');
    const returnY=v.flags.south.y;
    await waitFor(north2,s=>s.flags.south.y<returnY-1);
    model.testOnlyMutate(m => Object.assign(m.players.find(p=>p.id===north2.sessionId),{x:m.flags.south.x,y:m.flags.south.y}));
    model.step();model.publish();
    v=await waitFor(north1,s=>s.flags.south.carrierId===north2.sessionId);
    model.testOnlyMutate(m => Object.assign(m.players.find(p=>p.id===north2.sessionId),{x:0,y:448}));
    model.step();model.publish();
    v=await waitFor(south1,s=>s.phase==='roundOver');
    assert.equal(v.score.north,1);
    assert.equal(v.lastPoint.reason,'capture');
    assert.equal(v.flags.north.status,'carried','own flag need not be home to score');
    const frozen=find(v,north2.sessionId).x;
    send(north2,1,1);
    await sleep(120);
    assert.equal(find(state(north2),north2.sessionId).x,frozen,'intermission freezes movement');
    for(let i=0;i<60;i++) model.step();
    model.publish();
    v=await waitFor(north1,s=>s.round===2&&s.phase==='playing');
    assert.equal(v.flags.north.status,'home');assert.equal(v.flags.south.status,'home');
    assert.equal(v.score.north,1);assert.equal(find(v,north1.sessionId).deaths,2);

    model.testOnlyMutate(m => {
      m.players.find(p=>p.id===south2.sessionId).status='jailed';
      Object.assign(m.players.find(p=>p.id===south1.sessionId),{x:0,y:448});
      Object.assign(m.players.find(p=>p.id===north1.sessionId),{x:0,y:448});
    });
    send(north1,55,0,0,true);
    v=await waitFor(south2,s=>s.score.north===2);
    assert.equal(v.lastPoint.reason,'allJailed');
    assert.equal(v.score.south,0);

    // A connected carrier that leaves cannot orphan a carried flag.
    for(let i=0;i<60;i++) model.step();model.publish();
    await waitFor(north1,s=>s.round===3);
    model.testOnlyMutate(m => Object.assign(m.players.find(p=>p.id===north1.sessionId),{x:-32,y:-3200}));
    model.step();model.publish();
    await waitFor(south1,s=>s.flags.south.carrierId===north1.sessionId);
    model.testOnlyMutate(m => Object.assign(m.players.find(p=>p.id===north1.sessionId),{x:0,y:-1500}));
    void north1.leave(false);
    v=await waitFor(south1,s=>s.flags.south.status==='returning'&&s.flags.south.carrierId===null);
    assert.equal(v.score.north,2);
    model.testOnlyMutate(m=>Object.assign(m.players.find(p=>p.id===south1.sessionId),{x:0,y:-1500}));
    send(south1,2,0,0,true);
    v=await waitFor(south2,s=>find(s,north1.sessionId).status==='jailed');
    assert.equal(find(v,north1.sessionId).connected,false,'absent body can still be tagged');
    const reclaimed=await client().reconnect(north1.reconnectionToken);
    rooms.push(reclaimed);
    v=await waitFor(reclaimed,s=>find(s,north1.sessionId)?.connected===true);
    assert.equal(reclaimed.sessionId,north1.sessionId);
    assert.equal(v.players.length,4,'reconnection did not duplicate the slot');
    assert.equal(find(v,north1.sessionId).status,'jailed','reconnection did not clear jail');
    model.testOnlyMutate(m=>Object.assign(m.players.find(p=>p.id===north2.sessionId),{x:704,y:-2352}));
    model.step();model.publish();
    await waitFor(reclaimed,s=>find(s,north1.sessionId).status==='free');
    send(reclaimed,0,1);
    await waitFor(south1,s=>find(s,north1.sessionId).x>192);

    const crowd=[await create('Player 1')];
    for(let i=2;i<=12;i++) crowd.push(await join(crowd[0].roomId,`Player ${i}`));
    v=await waitFor(crowd[0],s=>s.players.length===12,5000);
    assert.equal(v.players.filter(p=>p.team==='north').length,6);
    assert.equal(v.players.filter(p=>p.team==='south').length,6);
    await assert.rejects(()=>client().joinById(crowd[0].roomId,{nickname:'Thirteenth'}));
    crowd[0].send('start',{});
    await Promise.all(crowd.map(r=>waitFor(r,s=>s.phase==='playing',5000)));
    const crowdModel=testRooms.get(crowd[0].roomId);
    const northCarrier=crowd[0].sessionId, southCarrier=crowd[1].sessionId;
    crowdModel.testOnlyMutate(m=>{
      Object.assign(m.players.find(p=>p.id===northCarrier),{x:0,y:448});
      Object.assign(m.players.find(p=>p.id===southCarrier),{x:0,y:-1152});
      Object.assign(m.flags.south,{x:0,y:448,status:'carried',carrierId:northCarrier});
      Object.assign(m.flags.north,{x:0,y:-1152,status:'carried',carrierId:southCarrier});
    });
    crowdModel.step();crowdModel.publish();
    const first=[northCarrier,southCarrier].sort((a,b)=>a.localeCompare(b))[0]===northCarrier?'north':'south';
    v=await waitFor(crowd[0],s=>s.phase==='roundOver');
    assert.equal(v.score[first],1,'same-tick captures resolve by stable player ID order');
    assert.equal(v.score[first==='north'?'south':'north'],0,'only one point is committed');
    for(let points=2;points<=5;points++) {
      for(let i=0;i<60;i++) crowdModel.step();
      crowdModel.testOnlyMutate(m=>{
        const winnerId=first==='north'?northCarrier:southCarrier;
        const flag=m.flags[first==='north'?'south':'north'];
        const player=m.players.find(p=>p.id===winnerId);
        Object.assign(player,{x:0,y:first==='north'?448:-1152});
        Object.assign(flag,{x:player.x,y:player.y,status:'carried',carrierId:winnerId});
      });
      crowdModel.step();crowdModel.publish();
      v=await waitFor(crowd[0],s=>s.score[first]===points);
      assert.equal(v.phase,points===5?'finished':'roundOver','first-to-five match ends at five');
    }

    const host=await create('Host');
    const successor=await join(host.roomId,'Successor');
    const teammate=await join(host.roomId,'Teammate');
    await host.leave();
    v=await waitFor(successor,s=>s.hostId===successor.sessionId);
    assert.equal(v.players.length,2);
    successor.send('start',{});
    await waitFor(teammate,s=>s.phase==='playing');
    await successor.leave();
    v=await waitFor(teammate,s=>s.phase==='finished');
    assert.equal(v.endReason,'disconnect');
    assert.deepEqual(v.score,{north:0,south:0},'empty team does not award a point');
  } finally {
    await Promise.allSettled(rooms.map(r=>Promise.race([r.leave(),sleep(2000)])));
    await server.gracefullyShutdown(false);
  }
});
