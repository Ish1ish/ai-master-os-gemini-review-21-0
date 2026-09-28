import test from 'node:test';
import assert from 'node:assert/strict';
import { startServer } from '../server.js';

test('canonical console is served by the BFF', async (t) => {
  const { server } = startServer({ host: '127.0.0.1', port: 0 });
  t.after(() => server.close());

  await new Promise((resolve) => server.once('listening', resolve));
  const address = server.address();
  const port = typeof address === 'object' && address ? address.port : 0;

  const response = await fetch(`http://127.0.0.1:${port}/`);
  const body = await response.text();

  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type') || '', /text\/html/);
  assert.match(body, /AI Master OS/);
  assert.match(body, /CANONICAL S21/);
});

test('canonical API allowlist still rejects legacy run listing', async (t) => {
  const { server } = startServer({ host: '127.0.0.1', port: 0 });
  t.after(() => server.close());

  await new Promise((resolve) => server.once('listening', resolve));
  const address = server.address();
  const port = typeof address === 'object' && address ? address.port : 0;

  const response = await fetch(`http://127.0.0.1:${port}/api/runs?limit=10`);
  const payload = await response.json();

  assert.equal(response.status, 404);
  assert.equal(payload.reason, 'canonical_route_not_found');
});
