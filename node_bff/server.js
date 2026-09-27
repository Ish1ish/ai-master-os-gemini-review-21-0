import express from 'express';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HOST = process.env.AI_OS_BFF_HOST || '127.0.0.1';
const PORT = Number.parseInt(process.env.AI_OS_BFF_PORT || '3001', 10);
const PYTHON_BASE_URL = (process.env.AI_OS_PYTHON_URL || 'http://127.0.0.1:8091').replace(/\/+$/, '');
const JSON_LIMIT = process.env.AI_OS_BFF_JSON_LIMIT || '1mb';
const BFF_DIR = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.join(BFF_DIR, 'public');

const CANONICAL_ROUTE_PATTERNS = [
  { method: 'POST', pattern: /^\/api\/runs$/ },
  { method: 'POST', pattern: /^\/api\/intents\/[^/]+\/execute$/ },
  { method: 'GET', pattern: /^\/api\/approvals$/ },
  { method: 'GET', pattern: /^\/api\/approvals\/[^/]+$/ },
  { method: 'POST', pattern: /^\/api\/approvals\/[^/]+\/decision$/ },
  { method: 'GET', pattern: /^\/api\/executions\/[^/]+$/ },
];

function isCanonicalRoute(method, pathValue) {
  return CANONICAL_ROUTE_PATTERNS.some(
    (entry) => entry.method === method && entry.pattern.test(pathValue),
  );
}

function forwardedHeaders(req) {
  const headers = {
    accept: req.get('accept') || 'application/json',
  };

  const authorization = req.get('authorization');
  if (authorization) {
    headers.authorization = authorization;
  }

  const requestId = req.get('x-request-id');
  if (requestId) {
    headers['x-request-id'] = requestId;
  }

  if (req.is('application/json')) {
    headers['content-type'] = 'application/json';
  }

  return headers;
}

async function proxyCanonicalRequest(req, res, fetchImpl = fetch) {
  const targetUrl = `${PYTHON_BASE_URL}${req.originalUrl}`;
  const init = {
    method: req.method,
    headers: forwardedHeaders(req),
  };

  if (req.method !== 'GET') {
    init.body = JSON.stringify(req.body ?? {});
  }

  try {
    const upstream = await fetchImpl(targetUrl, init);
    const text = await upstream.text();
    const contentType = upstream.headers.get('content-type') || 'application/json';

    res.status(upstream.status);
    res.set('content-type', contentType);
    res.send(text);
  } catch {
    res.status(502).json({
      status: 'BAD_GATEWAY',
      reason: 'python_backend_unreachable',
    });
  }
}

async function checkPythonReadiness(authorization, fetchImpl = fetch) {
  try {
    const headers = { accept: 'application/json' };
    if (authorization) {
      headers.authorization = authorization;
    }

    const upstream = await fetchImpl(`${PYTHON_BASE_URL}/api/approvals`, {
      method: 'GET',
      headers,
    });

    return upstream.status >= 100 && upstream.status < 500;
  } catch {
    return false;
  }
}

export function createApp({ fetchImpl = fetch } = {}) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json({ limit: JSON_LIMIT }));

  app.get('/health', (_req, res) => {
    res.status(200).json({
      status: 'OK',
      service: 'ai-master-os-node-bff',
      authority: 'python-s21',
    });
  });

  app.get('/ready', async (req, res) => {
    const pythonReady = await checkPythonReadiness(
      req.get('authorization'),
      fetchImpl,
    );
    res.status(pythonReady ? 200 : 503).json({
      status: pythonReady ? 'READY' : 'NOT_READY',
      python_backend: pythonReady ? 'OK' : 'UNAVAILABLE',
    });
  });

  app.use(express.static(PUBLIC_DIR, { fallthrough: true }));

  app.use(async (req, res, next) => {
    if (!req.path.startsWith('/api/')) {
      return next();
    }

    if (!isCanonicalRoute(req.method, req.path)) {
      return res.status(404).json({
        status: 'NOT_FOUND',
        reason: 'canonical_route_not_found',
      });
    }

    return proxyCanonicalRequest(req, res, fetchImpl);
  });

  app.use((_req, res) => {
    res.status(404).json({
      status: 'NOT_FOUND',
      reason: 'route_not_found',
    });
  });

  return app;
}

export function startServer({
  host = HOST,
  port = PORT,
  fetchImpl = fetch,
} = {}) {
  const app = createApp({ fetchImpl });
  const server = app.listen(port, host);
  return { app, server };
}

if (process.argv[1] === new URL(import.meta.url).pathname) {
  const { server } = startServer();
  server.on('listening', () => {
    const address = server.address();
    const actualPort = typeof address === 'object' && address ? address.port : PORT;
    process.stdout.write(`AI Master OS Node BFF listening on http://${HOST}:${actualPort}\n`);
  });

  const shutdown = () => {
    server.close(() => process.exit(0));
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}
