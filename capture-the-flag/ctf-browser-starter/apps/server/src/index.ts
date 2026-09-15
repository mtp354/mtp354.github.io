import { networkInterfaces } from 'node:os';
import { createGameServer } from './server.js';

const port = Number(process.env.PORT ?? 2567);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PORT must be between 1 and 65535.');
const game = await createGameServer({
  port,
  host: process.env.HOST ?? '127.0.0.1',
  basePath: process.env.CTF_BASE_PATH ?? '/',
  reconnectSeconds: Number(process.env.RECONNECT_SECONDS ?? 20),
  ...(process.env.CLIENT_DIST ? {clientDir: process.env.CLIENT_DIST} : {}),
  ...(process.env.ALLOWED_ORIGINS ? {allowedOrigins: process.env.ALLOWED_ORIGINS.split(',').map(value => value.trim())} : {}),
});
console.log(`Capture the Flag: ${game.url}${process.env.CTF_BASE_PATH ?? '/'}`);
if (process.env.HOST === '0.0.0.0') {
  for (const addresses of Object.values(networkInterfaces())) {
    for (const address of addresses ?? []) {
      if (address.family === 'IPv4' && !address.internal) {
        console.log(`Join on this network: http://${address.address}:${port}${process.env.CTF_BASE_PATH ?? '/'}`);
      }
    }
  }
}
console.log('Press Ctrl+C to stop.');
for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.once(signal, () => { void game.close().then(() => process.exit(0)); });
}
