import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

test('direct node launch remains alive on Windows path semantics', async (t) => {
  const serverPath = fileURLToPath(
    new URL('../server.js', import.meta.url),
  );

  const child = spawn(
    process.execPath,
    [serverPath],
    {
      env: {
        ...process.env,
        AI_OS_BFF_HOST: '127.0.0.1',
        AI_OS_BFF_PORT: '0',
        AI_OS_PYTHON_URL: 'http://127.0.0.1:9',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    },
  );

  t.after(() => {
    if (!child.killed && child.exitCode === null) {
      child.kill();
    }
  });

  const output = [];
  const errors = [];

  child.stdout.on('data', (chunk) => output.push(chunk.toString()));
  child.stderr.on('data', (chunk) => errors.push(chunk.toString()));

  const started = await new Promise((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error(`BFF did not start. stderr=${errors.join('')}`)),
      3000,
    );

    child.stdout.on('data', () => {
      const text = output.join('');
      if (text.includes('AI Master OS Node BFF listening on http://127.0.0.1:')) {
        clearTimeout(timeout);
        resolve(true);
      }
    });

    child.once('exit', (code, signal) => {
      clearTimeout(timeout);
      reject(
        new Error(
          `BFF exited before announcing listen address: code=${code} signal=${signal} stderr=${errors.join('')}`,
        ),
      );
    });
  });

  assert.equal(started, true);
});
