import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdir } from 'node:fs/promises';
import { chromium } from 'playwright';
import { Client } from 'colyseus.js';
import { matchMaker } from '@colyseus/core';
import { createGameServer } from '../apps/server/dist/server.js';

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(predicate, message, timeout = 6000) {
  const end = Date.now() + timeout;
  while (!predicate()) {
    assert.ok(Date.now() < end, message);
    await pause(25);
  }
}
async function textIs(page, selector, text) {
  await page.waitForFunction(({selector,text}) => document.querySelector(selector)?.textContent?.includes(text), {selector,text});
}
async function resume(page) {
  const button = page.locator('#resume');
  if (await button.isVisible()) await button.click();
  else await page.locator('#arena-wrap').click({position:{x:50,y:50}});
}

test('two browser contexts play, jail, rescue, capture, reset and reconnect; solo practice starts', {timeout:90000}, async t => {
  const game = await createGameServer({port:0,host:'127.0.0.1',reconnectSeconds:10});
  const sdkRooms = [];
  let launchedBrowser;
  t.after(async () => {
    await Promise.allSettled(sdkRooms.map(room => room.leave()));
    await launchedBrowser?.close();
    await game.close();
  });
  const browser = await chromium.launch({headless:true, ...(process.env.CHROME_PATH ? {executablePath:process.env.CHROME_PATH} : {}), args:['--no-sandbox']});
  launchedBrowser = browser;
  const first = await browser.newContext({viewport:{width:1440,height:1100}});
  const second = await browser.newContext({viewport:{width:1440,height:1100}});
  const host = await first.newPage();
  const guest = await second.newPage();
  const errors = [];
  for (const page of [host,guest]) page.on('pageerror', error => errors.push(error.message));
  await host.goto(game.url);
  await host.locator('#nickname').fill('North tester');
  await host.locator('#create').click();
  await textIs(host,'#overlay-title','Bring your team');
  const code = await host.locator('#room-id').textContent();
  const room = matchMaker.getLocalRoomById(code);
  assert.ok(room);
  await guest.goto(`${game.url}/?room=${encodeURIComponent(code)}`);
  await textIs(guest,'#overlay-title','Teams are ready');
  assert.equal(await guest.locator('#room-id').textContent(),code,'invite auto-joins the same room');
  // Two SDK teammates keep this a 2v2 round so the first tag can be rescued.
  const sdk = new Client(game.url);
  const northAlly = await sdk.joinById(code,{nickname:'North ally'});
  sdkRooms.push(northAlly);
  const southAlly = await sdk.joinById(code,{nickname:'South ally'});
  sdkRooms.push(southAlly);
  await host.locator('#start').click();
  await textIs(host,'#phase','IN PLAY');
  await textIs(guest,'#phase','IN PLAY');
  await host.locator('#arena canvas').waitFor({state:'visible'});
  const simulation = room.simulation;
  const north = simulation.match.players.find(p=>p.id!==northAlly.sessionId && p.team==='north');
  const south = simulation.match.players.find(p=>p.id!==southAlly.sessionId && p.team==='south');
  assert.ok(north && south);
  const xBefore = north.x;
  await resume(host);
  await host.keyboard.down('d');
  await until(()=>north.x>xBefore+80,'keyboard movement reaches authoritative server');
  await host.keyboard.up('d');
  await host.keyboard.press('Escape');
  await pause(120);
  const stopped = north.x;
  await pause(350);
  assert.ok(Math.abs(north.x-stopped)<1,'Escape releases controls and stops movement');
  // Test fixture positioning only; this is not a production message or endpoint.
  Object.assign(north,{x:0,y:300});
  Object.assign(south,{x:60,y:300});
  await resume(host);
  await host.keyboard.press('Space');
  await until(()=>south.status==='jailed','Space tags the vulnerable opposing player');
  await textIs(guest,'#local-badge','JAILED');
  await textIs(guest,'#objective-text','rescue');
  Object.assign(simulation.match.players.find(p=>p.id===southAlly.sessionId),{x:720,y:1600});
  await until(()=>south.status==='free','entering enemy jail rescues teammate');
  assert.equal(south.y,-1344,'jailbreak revives at home');
  await textIs(guest,'#local-badge','SAFE');
  Object.assign(north,{x:-32,y:-3200});
  await until(()=>simulation.match.flags.south.carrierId===north.id,'enemy flag picked up');
  await textIs(host,'#objective-text','You have the flag');
  Object.assign(north,{x:0,y:300});
  await until(()=>simulation.match.score.north===1,'flag scores on reaching home side');
  await textIs(host,'#north-score','1');
  await textIs(guest,'#north-score','1');
  await textIs(host,'#phase','ROUND OVER');
  await until(()=>simulation.match.round===2 && simulation.match.phase==='playing','round resets',6000);
  await textIs(guest,'#round','Round 2');
  const previousId = south.id;
  await guest.reload();
  await textIs(guest,'#phase','IN PLAY');
  assert.equal(simulation.match.players.length,4,'reload reclaims seat');
  assert.ok(simulation.players.get(previousId)?.connected,'same player reconnects');
  await resume(guest);
  const reconnectedX = south.x;
  await guest.keyboard.down('d');
  await until(()=>south.x>reconnectedX+40,'movement works after refresh');
  await guest.keyboard.up('d');
  await mkdir('test-results',{recursive:true});
  await host.screenshot({path:'test-results/multiplayer.png',fullPage:true});
  await host.locator('#leave').click();
  await host.locator('#practice').click();
  await textIs(host,'#phase','IN PLAY');
  await textIs(host,'#room-label','PRACTICE');
  const practice = matchMaker.getLocalRoomById(await host.locator('#room-id').textContent());
  assert.equal(practice.simulation.match.players.length,4);
  assert.equal([...practice.simulation.players.values()].filter(p=>p.bot).length,3);
  await host.screenshot({path:'test-results/practice.png',fullPage:true});
  assert.deepEqual(errors,[],'no browser JavaScript errors');
});
