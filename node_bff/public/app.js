const $ = (id) => document.getElementById(id);

const tokenKey = 'aios.patch11.token';
$('token').value = sessionStorage.getItem(tokenKey) || '';

function authHeaders() {
  const raw = $('token').value.trim();
  if (!raw) return {};
  return {
    Authorization: raw.toLowerCase().startsWith('bearer ')
      ? raw
      : `Bearer ${raw}`,
  };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...authHeaders(),
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  let payload;

  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { raw: text };
  }

  if (!response.ok) {
    throw new Error(
      `${response.status} ${payload.reason || payload.status || 'request_failed'}`,
    );
  }

  return payload;
}

function show(label, payload) {
  $('status').textContent = label;
  $('output').textContent = JSON.stringify(payload, null, 2);
}

async function run(label, fn) {
  try {
    const result = await fn();
    show(label, result);
  } catch (error) {
    show(label, { status: 'CLIENT_ERROR', message: error.message });
  }
}

$('saveToken').onclick = () => {
  sessionStorage.setItem(tokenKey, $('token').value.trim());
  show('Token saved for this session.', { status: 'OK' });
};

$('health').onclick = () => run('GET /health', () => api('/health'));
$('ready').onclick = () => run('GET /ready', () => api('/ready'));

$('submitRun').onclick = () => run('POST /api/runs', async () => {
  const body = JSON.parse($('runBody').value);
  const result = await api('/api/runs', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (result.intent_id) $('intentId').value = result.intent_id;
  return result;
});

$('executeIntent').onclick = () => run('POST /api/intents/{id}/execute', () => {
  const id = $('intentId').value.trim();
  if (!id) throw new Error('intent_id_required');

  return api(`/api/intents/${encodeURIComponent(id)}/execute`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({}),
  });
});

$('listApprovals').onclick = () => run('GET /api/approvals', () => api('/api/approvals'));

$('getApproval').onclick = () => run('GET /api/approvals/{id}', () => {
  const id = $('approvalId').value.trim();
  if (!id) throw new Error('approval_id_required');
  return api(`/api/approvals/${encodeURIComponent(id)}`);
});

$('approve').onclick = () => run('POST /api/approvals/{id}/decision', () => {
  const id = $('approvalId').value.trim();
  if (!id) throw new Error('approval_id_required');

  return api(`/api/approvals/${encodeURIComponent(id)}/decision`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      decision: 'APPROVED',
      reason: $('decisionReason').value.trim(),
    }),
  });
});

$('getExecution').onclick = () => run('GET /api/executions/{id}', () => {
  const id = $('executionId').value.trim();
  if (!id) throw new Error('execution_id_required');
  return api(`/api/executions/${encodeURIComponent(id)}`);
});
