import { test, expect } from '@playwright/test';
import { Client, type Room } from '@colyseus/sdk';
import { createServer as createTcpServer } from 'node:net';
import { resolve } from 'node:path';
import { createGameServer } from '../apps/server/dist/main.js';
import { testRooms } from '../apps/server/dist/GameRoom.js';

const sleep = (ms: number) => new Promise<void>(done => setTimeout(done, ms));
function freePort(): Promise<number> {
  return new Promise((resolvePort, reject) => {
    const socket = createTcpServer();socket.once('error',reject);
    socket.listen(0,'127.0.0.1',()=>{const port=(socket.address() as {port:number}).port;socket.close(()=>resolvePort(port));});
  });
}

test('two browser contexts render and act through the authoritative jail/flag/score/reset loop', async ({ browser }) => {
  process.env.CTF_TEST_HARNESS='1';
  const port=await freePort();
  process.env.VITE_CTF_SERVER_URL=`http://127.0.0.1:${port}`;
  const server=createGameServer();
  await server.listen(port,'127.0.0.1');
  const { createServer }=await import('../apps/client/node_modules/vite/dist/node/index.js');
  const vite=await createServer({configFile:resolve('apps/client/vite.config.ts')});
  await vite.listen();
  const url=vite.resolvedUrls?.local[0] ?? 'http://127.0.0.1:5173/';
  const a=await browser.newContext({viewport:{width:1360,height:900}});
  const b=await browser.newContext({viewport:{width:1360,height:900}});
  const north=await a.newPage(), south=await b.newPage();
  const errors:string[]=[];
  north.on('pageerror',error=>errors.push(`north: ${error.message}`));
  south.on('pageerror',error=>errors.push(`south: ${error.message}`));
  const sdk=new Client(`http://127.0.0.1:${port}`);
  const extras:Room[]=[];
  try {
    await north.goto(url);
    await expect(north.locator('#game canvas')).toBeVisible();
    await north.locator('#nickname').fill('NorthBrowser');
    await north.locator('#create').click();
    await expect.poll(()=>north.locator('#room-code').inputValue()).not.toBe('');
    const code=await north.locator('#room-code').inputValue();
    expect(code.length).toBeGreaterThan(0);
    await south.goto(`${url}?room=${code}`);
    await south.locator('#nickname').fill('SouthBrowser');
    await south.locator('#join').click();
    await expect(south.locator('#room-label')).toContainText(code);
    extras.push(await sdk.joinById(code,{nickname:'NorthExtra'}));
    extras.push(await sdk.joinById(code,{nickname:'SouthExtra'}));
    const model=testRooms.get(code)!;
    expect(model).toBeTruthy();
    const northId=JSON.parse(model.state.snapshot).players.find((p:{name:string})=>p.name==='NorthBrowser').id as string;
    const southId=JSON.parse(model.state.snapshot).players.find((p:{name:string})=>p.name==='SouthBrowser').id as string;
    const northExtra=JSON.parse(model.state.snapshot).players.find((p:{name:string})=>p.name==='NorthExtra').id as string;
    await expect(north.locator('#roster')).toContainText('North 2/6 · South 2/6');
    await north.locator('#start').click();
    await expect(north.locator('#phase')).toContainText('Round 1');
    await expect(south.locator('#phase')).toContainText('Round 1');

    const x=model.canonical.players.find(p=>p.id===northId)!.x;
    await north.locator('#game canvas').click();
    await north.keyboard.down('d');await sleep(270);await north.keyboard.up('d');
    await expect.poll(()=>model.canonical.players.find(p=>p.id===northId)!.x).toBeGreaterThan(x+15);
    await expect(north.locator('#minimap')).toBeVisible();

    // Browser South tags a vulnerable North teammate; Browser North rescues them.
    model.testOnlyMutate(m=>{
      Object.assign(m.players.find(p=>p.id===northExtra),{x:0,y:-1100});
      Object.assign(m.players.find(p=>p.id===southId),{x:0,y:-1100});
    });
    await south.locator('#game canvas').click();
    await south.keyboard.press('Space');
    await expect.poll(()=>model.canonical.players.find(p=>p.id===northExtra)!.status).toBe('jailed');
    await expect(north.locator('#players')).toContainText('NorthExtra (north) jailed');
    model.testOnlyMutate(m=>Object.assign(m.players.find(p=>p.id===northId),{x:704,y:-2352}));
    model.step();model.publish();
    await expect.poll(()=>model.canonical.players.find(p=>p.id===northExtra)!.status).toBe('free');
    expect(model.canonical.players.find(p=>p.id===northExtra)!.y).toBe(576);

    // Both flags can be carried; Browser South tags the North carrier.
    model.testOnlyMutate(m=>{
      Object.assign(m.players.find(p=>p.id===northId),{x:-32,y:-3200});
      Object.assign(m.players.find(p=>p.id===southId),{x:-32,y:2416});
    });
    model.step();model.publish();
    await expect(north.locator('#flags')).toContainText('north flag: carried');
    await expect(south.locator('#flags')).toContainText('south flag: carried');
    // North Extra drops the carried North flag in the enemy half, then South Extra
    // frees the browser player. This keeps South from scoring while they tag North.
    model.testOnlyMutate(m=>{
      Object.assign(m.players.find(p=>p.id===northExtra),{x:0,y:1000});
      Object.assign(m.players.find(p=>p.id===southId),{x:0,y:1000});
    });
    extras[0].send('input',{sequence:0,moveX:0,moveY:0,tag:true});
    await expect.poll(()=>model.canonical.players.find(p=>p.id===southId)!.status).toBe('jailed');
    expect(model.canonical.flags.north.status).toBe('returning');
    model.testOnlyMutate(m=>Object.assign(m.players.find(p=>p.id===extras[1].sessionId),{x:704,y:1648}));
    model.step();model.publish();
    await expect.poll(()=>model.canonical.players.find(p=>p.id===southId)!.status).toBe('free');
    await sleep(1050); // browser South's one-second tag cooldown
    model.testOnlyMutate(m=>{
      Object.assign(m.players.find(p=>p.id===northId),{x:0,y:-1500});
      Object.assign(m.players.find(p=>p.id===southId),{x:0,y:-1500});
    });
    await south.keyboard.press('Space');
    await expect.poll(()=>model.canonical.flags.south.status).toBe('returning');
    await expect(north.locator('#flags')).toContainText('south flag: returning');
    model.testOnlyMutate(m=>Object.assign(m.players.find(p=>p.id===northExtra),{x:704,y:-2352}));
    model.step();model.publish();
    model.testOnlyMutate(m=>Object.assign(m.players.find(p=>p.id===northId),{x:m.flags.south.x,y:m.flags.south.y}));
    model.step();model.publish();
    await expect.poll(()=>model.canonical.flags.south.carrierId).toBe(northId);
    model.testOnlyMutate(m=>Object.assign(m.players.find(p=>p.id===northId),{x:0,y:448}));
    model.step();model.publish();
    await expect(north.locator('#score')).toContainText('North 1 · South 0');
    await expect(south.locator('#phase')).toContainText('Resetting');
    expect(model.canonical.flags.north.status).toBe('returning');
    await expect(north.locator('#phase')).toContainText('Round 2',{timeout:5000});
    expect(model.canonical.flags.north.status).toBe('home');
    await north.screenshot({path:'test-results/ctf-playable.png',fullPage:true});
    expect(errors).toEqual([]);
  } finally {
    await Promise.allSettled(extras.map(r=>r.leave()));
    await a.close();await b.close();
    await vite.close();await server.gracefullyShutdown(false);
  }
});
