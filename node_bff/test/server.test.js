import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';

import { createApp } from '../server.js';

function startUpstream(handler) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(handler);
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      resolve({
        server,
        port: address.port,
        close: () => new Promise((done) => server.close(done)),
      });
    });
  });
}

async function startApp(app) {
  const server = app.listen(0, '127.0.0.1');

  await new Promise((resolve, reject) => {
    server.once('listening', resolve);
    server.once('error', reject);
  });

  const address = server.address();
  return {
    server,
    port: address.port,
  };
}

async function closeServer(server) {
  if (!server) return;
  if (!server.listening) return;
  await new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

async function request(port, method, path, { token, body, headers = {} } = {}) {
  const payload = body === undefined ? undefined : JSON.stringify(body);
  const mergedHeaders = {
    connection: 'close',
    ...headers,
  };
  if (payload !== undefined) {
    mergedHeaders['content-type'] = 'application/json';
    mergedHeaders['content-length'] = Buffer.byteLength(payload);
  }
  if (token) {
    mergedHeaders.authorization = token;
  }

  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host: '127.0.0.1',
        port,
        method,
        path,
        headers: mergedHeaders,
      },
      (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => {
          let parsed;
          try {
            parsed = JSON.parse(data);
          } catch {
            parsed = { raw: data };
          }
          resolve({ status: res.statusCode, headers: res.headers, body: parsed });
        });
      },
    );
    req.on('error', reject);
    if (payload !== undefined) req.write(payload);
    req.end();
  });
}

test('canonical request is forwarded with bearer auth and body', async () => {
  let captured;
  const upstream = await startUpstream((req, res) => {
    let data = '';
    req.on('data', (chunk) => {
      data += chunk;
    });
    req.on('end', () => {
      captured = {
        method: req.method,
        url: req.url,
        authorization: req.headers.authorization,
        spoofedPrincipal: req.headers['x-principal'],
        body: JSON.parse(data),
      };
      res.writeHead(202, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ status: 'PENDING' }));
    });
  });

  const app = createApp({
    fetchImpl: (url, init) => fetch(url, init),
  });
  const { server, port } = await startApp(app);
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    const rewritten = new URL(url);
    rewritten.port = String(upstream.port);
    return originalFetch(rewritten, init);
  };

  try {
    const result = await request(
      port,
      'POST',
      '/api/runs',
      {
        token: 'Bearer token-operator',
        headers: { 'x-principal': 'spoofed-user' },
        body: { run_id: 'RUN-1', intent: 'hello' },
      },
    );
    assert.equal(result.status, 202);
    assert.equal(result.body.status, 'PENDING');
    assert.deepEqual(captured, {
      method: 'POST',
      url: '/api/runs',
      authorization: 'Bearer token-operator',
      spoofedPrincipal: undefined,
      body: { run_id: 'RUN-1', intent: 'hello' },
    });
  } finally {
    globalThis.fetch = originalFetch;
    await closeServer(server);
    await upstream.close();
  }
});

test('unknown api route returns 404 without upstream call', async () => {
  let called = false;
  const app = createApp({
    fetchImpl: async () => {
      called = true;
      throw new Error('upstream_should_not_be_called');
    },
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(
      port,
      'POST',
      '/api/runs/abc/execute',
    );
    assert.equal(result.status, 404);
    assert.equal(result.body.reason, 'canonical_route_not_found');
    assert.equal(called, false);
  } finally {
    await closeServer(server);
  }
});

test('upstream status is preserved', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        status: 'CONFLICT',
        reason: 'idempotency_key_reused_with_different_request',
      }),
      {
        status: 409,
        headers: { 'content-type': 'application/json' },
      },
    );

  const app = createApp();
  const { server, port } = await startApp(app);

  try {
    const result = await request(
      port,
      'POST',
      '/api/intents/INT-1/execute',
      { body: {} },
    );
    assert.equal(result.status, 409);
    assert.equal(result.body.status, 'CONFLICT');
  } finally {
    globalThis.fetch = originalFetch;
    await closeServer(server);
  }
});

test('python backend failure becomes 502', async () => {
  const app = createApp({
    fetchImpl: async () => {
      throw new Error('connection refused');
    },
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(
      port,
      'GET',
      '/api/approvals',
    );
    assert.equal(result.status, 502);
    assert.equal(result.body.status, 'BAD_GATEWAY');
    assert.equal(result.body.reason, 'python_backend_unreachable');
  } finally {
    await closeServer(server);
  }
});

test('readiness treats a protected canonical response as reachable Python S21', async () => {
  let captured;
  const app = createApp({
    fetchImpl: async (url, init) => {
      captured = { url, init };
      return new Response('', { status: 401 });
    },
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(port, 'GET', '/ready', {
      token: 'Bearer token-operator',
    });
    assert.equal(result.status, 200);
    assert.equal(result.body.status, 'READY');
    assert.equal(result.body.python_backend, 'OK');
    assert.equal(captured.url, 'http://127.0.0.1:8091/api/approvals');
    assert.equal(captured.init.headers.authorization, 'Bearer token-operator');
  } finally {
    await closeServer(server);
  }
});

test('readiness reports unavailable when Python S21 returns a server error', async () => {
  const app = createApp({
    fetchImpl: async () => new Response('', { status: 503 }),
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(port, 'GET', '/ready');
    assert.equal(result.status, 503);
    assert.equal(result.body.status, 'NOT_READY');
    assert.equal(result.body.python_backend, 'UNAVAILABLE');
  } finally {
    await closeServer(server);
  }
});


test('X-Request-ID is forwarded to the Python S21 backend', async () => {
  let captured;
  const app = createApp({
    fetchImpl: async (url, init) => {
      captured = { url, init };
      return new Response(
        JSON.stringify({ status: 'OK' }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      );
    },
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(
      port,
      'GET',
      '/api/approvals',
      { headers: { 'x-request-id': 'req-patch08-001' } },
    );
    assert.equal(result.status, 200);
    assert.equal(captured.init.headers['x-request-id'], 'req-patch08-001');
    assert.equal(captured.url, 'http://127.0.0.1:8091/api/approvals');
  } finally {
    await closeServer(server);
  }
});

test('/health returns local liveness without contacting Python S21', async () => {
  let called = false;
  const app = createApp({
    fetchImpl: async () => {
      called = true;
      throw new Error('health_should_not_probe_upstream');
    },
  });
  const { server, port } = await startApp(app);

  try {
    const result = await request(port, 'GET', '/health');
    assert.equal(result.status, 200);
    assert.deepEqual(result.body, {
      status: 'OK',
      service: 'ai-master-os-node-bff',
      authority: 'python-s21',
    });
    assert.equal(called, false);
  } finally {
    await closeServer(server);
  }
});
