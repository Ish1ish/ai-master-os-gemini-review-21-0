/* O46 Final Manual UI Fix: Golden Run Control + Golden Experience hydration.
 * Explicit user actions only. No auto-execution, no secret rendering, backend remains authoritative.
 */
(function(){
  'use strict';

  const GOLDEN = {
    project_id: 'PROJ-001',
    request: 'أريد بدء مشروع تجاري منخفض التكلفة يعتمد على الذكاء الاصطناعي في مصر، وبرأس مال محدود جدًا. ابحث في الفرص الحالية، وحدد أقوى مشاكل العملاء والفجوات في السوق، وأنشئ أفكارًا عملية وقارن بينها، ثم أوصني بأكثر خيار واقعي أبدأ باختباره أولًا.',
    goal: 'العثور على أكثر فرصة AI منخفضة التكلفة واقعية لاختبارها أولًا في مصر',
    audience: 'أصحاب المشاريع الصغيرة ورواد الأعمال في مصر',
    scope: 'Egypt',
    constraints: [
      'استخدم معلومات حديثة من الويب عندما تكون متاحة.',
      'فضّل الفرص التي تحتاج MVP بسيط وتكلفة بداية منخفضة ويمكن تنفيذها بواسطة مؤسس واحد أو فريق صغير.',
      'لا تقم بأي شراء أو نشر أو إرسال رسائل أو إجراءات خارجية.'
    ],
    language: 'ar'
  };

  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const text = (v, fallback='—') => v === undefined || v === null || v === '' ? fallback : String(v);

  async function api(path, opts={}) {
    if (typeof window.api !== 'function') {
      throw new Error('Authenticated API bridge unavailable.');
    }
    return window.api(path, opts);
  }

  function asRuns(raw) { return Array.isArray(raw) ? raw : (raw?.runs || raw?.items || []); }
  function jobId(run) { return run?.job_id || run?.id || run?.run_id || ''; }
  function latestRun(runs) {
    return runs.slice().sort((a,b) => (Date.parse(b?.updated_at || b?.created_at || '')||0) - (Date.parse(a?.updated_at || a?.created_at || '')||0))[0] || null;
  }
  function resultOf(run) { return run?.result || run?.results || run?.output || run || {}; }
  function decisionOf(r) { return r?.decision_surface || r?.decision || r?.result?.decision_surface || r?.result?.decision || {}; }
  function evidenceOf(r) { return r?.evidence || r?.research || r?.result?.evidence || {}; }
  function govOf(r) { return r?.governance || r?.approval || r?.result?.governance || r?.result?.approval || {}; }
  function outcomeOf(r) { return r?.outcome || r?.execution_outcome || r?.result?.outcome || {}; }
  function learningOf(r) { return r?.learning || r?.learning_context || r?.result?.learning || {}; }
  function nextOf(r, d) { return r?.next_step || r?.next_decision || d?.next_action || r?.result?.next_step || {}; }

  function setText(id, value, fallback='—') {
    const el = document.getElementById(id);
    if (el) el.textContent = text(value, fallback);
  }
  function setHtml(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = value;
  }
  function show(id, visible) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle('hidden', !visible);
  }

  function notify(message, kind='info') {
    const el = document.getElementById('goldenControlMeta');
    if (el) el.textContent = message;
    const msg = document.getElementById('goldenControlStatus');
    if (msg) msg.dataset.o46MessageKind = kind;
  }

  function renderControlRun(run) {
    if (!run) {
      setText('goldenControlHeadline', 'No Golden Run created yet.');
      setText('goldenControlMeta', 'Create a run to begin the end-to-end product journey.');
      setText('goldenControlBadge', 'IDLE');
      setText('goldenControlRunId');
      setText('goldenControlProject');
      setText('goldenControlRunStatus');
      setText('goldenControlGovernance');
      setText('goldenControlNext');
      show('goldenExecuteBtn', false);
      return;
    }
    const r = resultOf(run);
    const d = decisionOf(r);
    const g = govOf(r);
    const n = nextOf(r, d);
    const id = jobId(run);
    sessionStorage.setItem('aios.lastJobId', id);
    setText('goldenControlHeadline', 'Golden Run created.');
    setText('goldenControlMeta', `Run ${id} is bound to backend state. Start governed execution only with the separate action.`);
    setText('goldenControlBadge', text(run.status, 'CREATED').toUpperCase());
    setText('goldenControlRunId', id);
    setText('goldenControlProject', run.project_id || r.project_id || 'PROJ-001');
    setText('goldenControlRunStatus', run.status || r.status || 'CREATED');
    setText('goldenControlGovernance', g.status || g.decision || g.approval || 'PENDING');
    setText('goldenControlNext', n.recommendation || n.next_action || n.action || d.next_action || 'Review the current result');
    show('goldenExecuteBtn', Boolean(id) && !['COMPLETE','CANCELLED','FAILED'].includes(String(run.status||'').toUpperCase()));
    setHtml('goldenControlSteps', buildJourney(run));
  }

  function buildJourney(run) {
    const r = resultOf(run), d = decisionOf(r), g = govOf(r), o = outcomeOf(r), l = learningOf(r), n = nextOf(r, d);
    const stages = [
      ['01','Intent', run.request || GOLDEN.request],
      ['02','Research', evidenceOf(r)?.status || (evidenceOf(r)?.evidence_count || evidenceOf(r)?.source_count ? 'Evidence available' : 'Inspecting evidence')],
      ['03','Decision', d.recommendation || d.status || 'Decision state'],
      ['04','Governance', g.status || g.decision || g.approval || 'Human gate'],
      ['05','Execution', r.execution?.status || run.status || 'Awaiting explicit execution'],
      ['06','Outcome', o.status || o.summary || 'Outcome pending'],
      ['07','Learning', l.signal || l.status || 'Learning pending'],
      ['08','Next Decision', n.recommendation || n.next_action || d.next_action || 'Next step pending']
    ];
    return stages.map(s => `<div class="golden-control-step"><span>${s[0]}</span><div><b>${esc(s[1])}</b><small>${esc(s[2])}</small></div></div>`).join('');
  }

  function renderGoldenExperience(run) {
    if (!run) {
      setHtml('goldenStatus', '<div class="availability-state neutral"><div><h3>No backend run selected</h3><p>Create a Golden Run or select an existing run below. The experience never invents state.</p></div></div>');
      setHtml('goldenJourney', '');
      setHtml('goldenIntent', '<div class="eyebrow">INTENT</div><h3>Waiting for a run</h3><p>Create a governed run to populate this surface.</p>');
      setHtml('goldenDecision', '<div class="eyebrow">DECISION</div><h3>Waiting for decision</h3><p>No backend decision is currently selected.</p>');
      setHtml('goldenGovernance', '<div class="eyebrow">GOVERNANCE</div><h3>Waiting for governance</h3><p>Approval and policy state will appear from the backend.</p>');
      setHtml('goldenOutcome', '<div class="eyebrow">OUTCOME</div><h3>Waiting for outcome</h3><p>No execution outcome is currently selected.</p>');
      setHtml('goldenNext', '<div class="eyebrow">NEXT DECISION</div><h3>Waiting for next route</h3><p>The system will surface the cheapest useful next step when evidence exists.</p>');
      setText('goldenRunMeta', 'No run inspected yet.');
      return;
    }
    const r=resultOf(run), d=decisionOf(r), e=evidenceOf(r), g=govOf(r), o=outcomeOf(r), l=learningOf(r), n=nextOf(r,d), id=jobId(run);
    setHtml('goldenStatus', `<div><div class="eyebrow">LIVE BACKEND RUN</div><h3>${esc(id)}</h3><p>${esc(run.request || GOLDEN.request)}</p></div><span class="status-pill">${esc(run.status || 'UNKNOWN')}</span>`);
    setHtml('goldenJourney', buildJourney(run));
    setHtml('goldenIntent', `<div class="eyebrow">INTENT</div><h3>${esc(run.request || GOLDEN.request)}</h3><p>Audience: ${esc(run.audience || GOLDEN.audience)}</p><p>Goal: ${esc(run.goal || GOLDEN.goal)}</p>`);
    setHtml('goldenDecision', `<div class="eyebrow">DECISION</div><h3>${esc(d.recommendation || d.title || 'No recommendation exposed')}</h3><p>${esc(d.why || d.rationale || 'No rationale exposed by the backend.')}</p><div class="golden-run-meta">Customer: ${esc(d.target_customer || d.customer || run.audience || '—')} · Confidence: ${esc(d.confidence || '—')}</div>`);
    setHtml('goldenGovernance', `<div class="eyebrow">GOVERNANCE</div><h3>${esc(g.status || g.decision || g.approval || 'PENDING')}</h3><p>Risk: ${esc(g.risk || '—')} · External effect: ${esc(g.external_effect ?? g.externalEffect ?? '—')}</p><p>Approval remains backend-authoritative.</p>`);
    setHtml('goldenOutcome', `<div class="eyebrow">OUTCOME & LEARNING</div><h3>${esc(o.status || 'Waiting for outcome')}</h3><p>${esc(o.summary || o.result || 'Observed outcome will appear after governed execution.')}</p><p>Learning: ${esc(l.signal || l.summary || '—')}</p>`);
    setHtml('goldenNext', `<div class="eyebrow">NEXT DECISION</div><h3>${esc(n.recommendation || n.next_action || d.next_action || 'Review the current result')}</h3><p>Derived from backend state; no autonomous action is taken.</p>`);
    setText('goldenRunMeta', `Selected run ${id} · ${run.project_id || '—'} · ${run.status || 'UNKNOWN'}`);
    updateInspector(run);
  }

  function updateInspector(run) {
    if (!run) return;
    const r=resultOf(run), d=decisionOf(r), e=evidenceOf(r), g=govOf(r), o=outcomeOf(r), l=learningOf(r), n=nextOf(r,d);
    const checks = [
      ['Intent', Boolean(run.request)],
      ['Decision', Boolean(d.recommendation || d.status)],
      ['Evidence', Boolean(e.evidence_count || e.source_count || e.status || e.evidence || e.sources)],
      ['Governance', Boolean(g.status || g.decision || g.approval)],
      ['Outcome', Boolean(o.status || o.summary || o.result)],
      ['Learning', Boolean(l.signal || l.summary || l.status)],
      ['Next decision', Boolean(n.recommendation || n.next_action || d.next_action)]
    ];
    setHtml('goldenValidationGrid', checks.map(([label,ok]) => `<div class="card"><span class="label">${esc(label)}</span><strong>${ok ? 'AVAILABLE' : 'WAITING'}</strong><small>${ok ? 'Backend-derived state exposed' : 'No state exposed; nothing invented'}</small></div>`).join(''));
    const banner = document.getElementById('goldenIntegrityBanner');
    if (banner) {
      banner.innerHTML = `<span class="status-dot"></span><div><strong>Backend state inspected</strong><small>${esc(jobId(run))} · read-only product QA</small></div>`;
    }
  }

  async function listRuns() {
    const raw = await api('/runs?limit=25');
    const runs = asRuns(raw);
    return runs.sort((a,b)=>(Date.parse(b?.updated_at||b?.created_at||'')||0)-(Date.parse(a?.updated_at||a?.created_at||'')||0));
  }

  async function loadRun(id) {
    if (!id) return null;
    return api('/runs/' + encodeURIComponent(id));
  }

  async function refreshExperience(preferredId) {
    const runs = await listRuns();
    const select = document.getElementById('goldenRunSelect');
    if (select) {
      const previous = preferredId || select.value || '';
      select.innerHTML = '<option value="">Latest run</option>' + runs.map(x => `<option value="${esc(jobId(x))}">${esc(jobId(x))} · ${esc(x.status||'UNKNOWN')} · ${esc(x.project_id||'—')}</option>`).join('');
      if (previous && runs.some(x => jobId(x) === previous)) select.value = previous;
    }
    const selected = preferredId ? runs.find(x=>jobId(x)===preferredId) : latestRun(runs);
    const full = selected ? await loadRun(jobId(selected)).catch(()=>selected) : null;
    renderGoldenExperience(full);
    return full;
  }

  async function createGolden(btn) {
    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = 'Creating…';
    try {
      const out = await api('/runs', {method:'POST', body:JSON.stringify(GOLDEN)});
      const id = jobId(out);
      if (!id) throw new Error('Backend did not return a run id.');
      sessionStorage.setItem('aios.lastJobId', id);
      const full = await loadRun(id).catch(()=>out);
      renderControlRun(full);
      await refreshExperience(id);
      notify(`Created ${id}. Review the state, then start governed execution explicitly.`, 'success');
    } catch (e) {
      notify('Create failed · ' + (e.message || e), 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  async function executeGolden(btn) {
    const id = sessionStorage.getItem('aios.lastJobId');
    if (!id) { notify('No Golden Run is selected.', 'error'); return; }
    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = 'Starting…';
    try {
      await api('/runs/' + encodeURIComponent(id) + '/execute', {method:'POST', body:JSON.stringify({})});
      const full = await loadRun(id);
      renderControlRun(full);
      await refreshExperience(id);
      notify(`Execution started for ${id}. Governance remains backend-authoritative.`, 'success');
    } catch (e) {
      notify('Execution was not started · ' + (e.message || e), 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  function wire() {
    const create = document.getElementById('goldenCreateBtn');
    const execute = document.getElementById('goldenExecuteBtn');
    const inspect = document.getElementById('goldenInspectBtn');
    const open = document.getElementById('goldenOpenExperience');
    const refresh = document.getElementById('goldenRefresh');
    const inspectRefresh = document.getElementById('goldenInspectRefresh');
    const select = document.getElementById('goldenRunSelect');

    if (create && !create.dataset.o46Bound) { create.dataset.o46Bound='1'; create.addEventListener('click',()=>createGolden(create)); }
    if (execute && !execute.dataset.o46Bound) { execute.dataset.o46Bound='1'; execute.addEventListener('click',()=>executeGolden(execute)); }
    if (inspect && !inspect.dataset.o46Bound) { inspect.dataset.o46Bound='1'; inspect.addEventListener('click',async()=>{ try { const full=await refreshExperience(); if(full) renderControlRun(full); } catch(e) { notify('Inspect failed · '+(e.message||e), 'error'); } }); }
    if (open && !open.dataset.o46Bound) { open.dataset.o46Bound='1'; open.addEventListener('click',()=>window.page?.('golden')); }
    if (refresh && !refresh.dataset.o46Bound) { refresh.dataset.o46Bound='1'; refresh.addEventListener('click',async()=>{ refresh.disabled=true; try { await refreshExperience(sessionStorage.getItem('aios.lastJobId')||''); } finally { refresh.disabled=false; } }); }
    if (inspectRefresh && !inspectRefresh.dataset.o46Bound) { inspectRefresh.dataset.o46Bound='1'; inspectRefresh.addEventListener('click',()=>refreshExperience()); }
    if (select && !select.dataset.o46Bound) { select.dataset.o46Bound='1'; select.addEventListener('change',async()=>{ const id=select.value; const full=id?await loadRun(id):await refreshExperience(); if(id) renderGoldenExperience(full); if(id) renderControlRun(full); }); }
  }

  async function boot() {
    wire();
    try { await refreshExperience(sessionStorage.getItem('aios.lastJobId')||''); } catch (_) { /* safe empty state; do not invent */ }
    const runId=sessionStorage.getItem('aios.lastJobId');
    if (runId) {
      try { const full=await loadRun(runId); renderControlRun(full); } catch (_) {}
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else setTimeout(boot,0);
})();
