import { spawn } from 'node:child_process';
import { resolve } from 'node:path';

const env = { ...process.env, PLAYWRIGHT_BROWSERS_PATH: process.env.PLAYWRIGHT_BROWSERS_PATH || resolve('.playwright-browsers') };
const child = spawn(process.execPath, [resolve('node_modules/@playwright/test/cli.js'), process.argv[2] || 'test', ...process.argv.slice(3)], { stdio: 'inherit', env });
child.on('exit', code => { process.exitCode = code ?? 1; });
