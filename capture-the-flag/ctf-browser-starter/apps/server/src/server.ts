import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { dirname, extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Server } from '@colyseus/core';
import { WebSocketTransport } from '@colyseus/ws-transport';
import { CtfRoom } from './room.js';

const defaultClientDir = resolve(dirname(fileURLToPath(import.meta.url)), '../../client/dist');
const mime: Record<string, string> = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.ico': 'image/x-icon', '.json': 'application/json; charset=utf-8', '.woff2': 'font/woff2',
};

async function serveClient(request: IncomingMessage, response: ServerResponse, clientDir: string, basePath: string): Promise<void> {
  let pathname: string;
  try { pathname = decodeURIComponent(new URL(request.url ?? '/', 'http://localhost').pathname); }
  catch { response.writeHead(400).end('Bad request'); return; }
  response.setHeader('X-Content-Type-Options', 'nosniff');
  if (pathname === '/health') {
    response.writeHead(200, {'Content-Type': 'application/json', 'Cache-Control': 'no-store'}).end(JSON.stringify({ok: true, service: 'ctf'}));
    return;
  }
  if (request.method !== 'GET' && request.method !== 'HEAD') { response.writeHead(405).end(); return; }
  if (!pathname.startsWith(basePath)) { response.writeHead(404).end('Not found'); return; }
  const relativePath = pathname.slice(basePath.length);
  const target = resolve(clientDir, relativePath || 'index.html');
  if (!target.startsWith(`${clientDir}${sep}`)) { response.writeHead(403).end('Forbidden'); return; }
  try {
    const info = await stat(target);
    if (!info.isFile()) { response.writeHead(404).end('Not found'); return; }
    response.writeHead(200, {
      'Content-Type': mime[extname(target)] ?? 'application/octet-stream',
      'Content-Length': info.size,
      'Cache-Control': extname(target) === '.html' ? 'no-cache' : 'public, max-age=3600',
    });
    if (request.method === 'HEAD') response.end();
    else createReadStream(target).on('error', () => response.destroy()).pipe(response);
  } catch {
    response.writeHead(404, {'Content-Type': 'text/plain; charset=utf-8'}).end('Game files are not built. Run npm run build, then npm start.');
  }
}

export interface GameServerOptions {
  port?: number;
  host?: string;
  clientDir?: string;
  basePath?: string;
  reconnectSeconds?: number;
  allowedOrigins?: string[];
}

export async function createGameServer(options: GameServerOptions = {}) {
  const host = options.host ?? '127.0.0.1';
  const clientDir = resolve(options.clientDir ?? defaultClientDir);
  const basePath = `/${(options.basePath ?? '/').replace(/^\/+|\/+$/g, '')}/`.replace(/^\/\//, '/');
  const reconnectSeconds = options.reconnectSeconds ?? 20;
  if (!Number.isFinite(reconnectSeconds) || reconnectSeconds <= 0 || reconnectSeconds > 120) throw new Error('Reconnect grace must be between 0 and 120 seconds.');
  const httpServer = createServer((request, response) => {
    void serveClient(request, response, clientDir, basePath).catch(() => {
      if (!response.headersSent) response.writeHead(500);
      response.end();
    });
  });
  httpServer.requestTimeout = 10_000;
  httpServer.headersTimeout = 10_000;
  const transport = new WebSocketTransport({
    server: httpServer,
    maxPayload: 1024,
    pingInterval: 3000,
    pingMaxRetries: 2,
    ...(options.allowedOrigins?.length ? {
      verifyClient: (info: {origin: string}) => options.allowedOrigins!.includes(info.origin),
    } : {}),
  });
  const server = new Server({transport, gracefullyShutdown: false, greet: false});
  class ConfiguredRoom extends CtfRoom {
    override onCreate(options: unknown): void {
      this.configureReconnect(reconnectSeconds);
      super.onCreate(options);
    }
  }
  server.define('ctf', ConfiguredRoom);
  try {
    await server.listen(options.port ?? 2567, host);
  } catch (error) {
    // A busy port or denied bind must not leave matchmaking timers running.
    await server.gracefullyShutdown(false);
    throw error;
  }
  const address = httpServer.address();
  if (!address || typeof address === 'string') throw new Error('Server did not open a TCP port.');
  let closing: Promise<void> | undefined;
  const close = (): Promise<void> => closing ??= (async () => {
    const closed = httpServer.listening ? new Promise<void>(resolve => httpServer.once('close', resolve)) : Promise.resolve();
    await server.gracefullyShutdown(false);
    await closed;
  })();
  const url = `http://${host === '0.0.0.0' ? 'localhost' : host}:${address.port}`;
  return {server, httpServer, close, url};
}
