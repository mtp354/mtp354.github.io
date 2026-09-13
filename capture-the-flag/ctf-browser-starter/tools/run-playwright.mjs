import { spawn } from 'node:child_process';
import { resolve } from 'node:path';

const env = { ...process.env, PLAYWRIGHT_BROWSERS_PATH: process.env.PLAYWRIGHT_BROWSERS_PATH || resolve('.playwright-browsers') };
const child = spawn(process.execPath, [resolve('node_modules/@playwright/test/cli.js'), 'test', ...process.argv.slice(2)], { stdio: 'inherit', env });
child.on('exit', code => { process.exitCode = code ?? 1; });
