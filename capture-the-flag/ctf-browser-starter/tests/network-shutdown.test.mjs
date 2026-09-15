import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

test('shutdown closes active sockets and pending reconnections without retaining timers', { timeout: 8000 }, async () => {
  // A child process detects leaked handles even when close() itself succeeds.
  const { stdout, stderr } = await promisify(execFile)(process.execPath, [
    fileURLToPath(new URL('./fixtures/shutdown-client.mjs', import.meta.url)),
  ], { timeout: 5000, maxBuffer: 32768 });
  assert.match(stdout, /shutdown complete/);
  assert.equal(stderr, '');
});
