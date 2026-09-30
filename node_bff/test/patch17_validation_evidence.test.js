import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';

import { createApp } from '../server.js';

async function startApp(app) {
  const server = app.listen(0, '127.0.0.1');
  await new Promise((resolve, reject) => {
    server.once('listening', resolve);
    server.once('error', reject);
  });
  return { server, port: server.address().port };
}

async function closeServer(server) {
  if (!server?.listening) return;
  await new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

async function request(port, method, path, { token, body } = {}) {
  const payload = body === undefined ? undefined : JSON.stringify(body);
  const headers = { connection: 'close' };
  if (payload !== undefined) {
    headers['content-type'] = 'application/json';
    headers['content-length'] = Buffer.byteLength(payload);
  }
  if (token) headers.authorization = token;

  return new Promise((resolve, reject) => {
    const req = http.request(
      { host: '127.0.0.1', port, method, path, headers },
      (res) => {
        let data = '';
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => resolve({ status: res.statusCode, body: JSON.parse(data) }));
      },
    );
    req.on('error', reject);
    if (payload !== undefined) req.write(payload);
    req.end();
  });
}

test('PATCH17 validation evidence routes remain proxy-only', async () => {
  const captured = [];
  const app = createApp({
    fetchImpl: async (url, init) => {
      captured.push({ url, init });
      return new Response(JSON.stringify({ status: 'EVIDENCE_RECORDED' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    },
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(port, 'POST', '/api/experiments/VAL-P17/evidence', {
      token: 'Bearer token-validator',
      body: { sample_size: 10, metrics: { problem_confirmed: 8 }, evidence_refs: ['EV-P17-1'] },
    });
    assert.equal(result.status, 200);
    assert.equal(result.body.status, 'EVIDENCE_RECORDED');
    assert.equal(captured[0].url, 'http://127.0.0.1:8091/api/experiments/VAL-P17/evidence');
    assert.equal(captured[0].init.headers.authorization, 'Bearer token-validator');
  } finally {
    await closeServer(server);
  }
});

test('PATCH17 learning context route is allowlisted and forwards query string', async () => {
  let captured;
  const app = createApp({
    fetchImpl: async (url, init) => {
      captured = { url, init };
      return new Response(JSON.stringify({ status: 'READY' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    },
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(port, 'GET', '/api/learning/context?project_id=P17');
    assert.equal(result.status, 200);
    assert.equal(result.body.status, 'READY');
    assert.equal(captured.url, 'http://127.0.0.1:8091/api/learning/context?project_id=P17');
  } finally {
    await closeServer(server);
  }
});

test('PATCH17 unknown validation route remains fail-closed', async () => {
  let called = false;
  const app = createApp({
    fetchImpl: async () => {
      called = true;
      throw new Error('upstream_should_not_be_called');
    },
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(port, 'POST', '/api/experiments/VAL-P17/other');
    assert.equal(result.status, 404);
    assert.equal(result.body.reason, 'canonical_route_not_found');
    assert.equal(called, false);
  } finally {
    await closeServer(server);
  }
});
