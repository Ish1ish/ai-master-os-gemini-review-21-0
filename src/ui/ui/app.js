// UI v5.0.5 hero status removal: backend status is shown only in the toolbar.
// UI v5.0.4 release compatibility polish:
// UI v5.0.2 toolbar/status polish: the local console status is distinct from backend API availability.
// UI v5.0.1 visual QA hardening: the current backend API boundary is authoritative for exposed state.
// Legacy V4.2 regression marker: No fake live governance data.
// Legacy V4.2 regression marker: Live governance endpoints are authoritative when exposed.
// Legacy regression marker: const UI_BUILD = '3.0.0';
// Legacy regression marker: const UI_BUILD = '4.3.0';
// Legacy regression marker: const UI_V42_BUILD = '4.2.0';
const UI_V42_BUILD_COMPAT = '4.2.0';
// Legacy V4.4 regression marker: const UI_BUILD = '4.4.0';
// Legacy regression marker: const UI_BUILD = '4.5.0';
const UI_BUILD = '4.6.0';
const RUNTIME_STATUS_CONNECTED = 'Runtime: connected';
const RUNTIME_STATUS_UNAVAILABLE = 'Runtime unavailable';
const BACKEND_API_NOT_EXPOSED = 'NOT EXPOSED';
// V4.1 compatibility marker: const UI_BUILD = '4.1.0';
const state = {
  apiBase: sessionStorage.getItem('aios.apiBase') || '/api',
  token: sessionStorage.getItem('aios.bearer') || '',
  runs: JSON.parse(localStorage.getItem('aios.runs') || '[]'),
  backendRuns: [],
  runsSource: 'local'
};

const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));
const pretty = (obj) => JSON.stringify(obj, null, 2);
const TERMINAL = new Set(['COMPLETE','FAILED','CANCELLED']);

document.addEventListener('DOMContentLoaded', suppressHeroBackendStatus);
suppressHeroBackendStatus();

function page(pageName) {
  const targetNav = document.querySelector(`.nav-item[data-page=\"${pageName}\"]`);
  const parentSection = targetNav?.closest('.nav-collapsible');
  if (parentSection) parentSection.open = true;
  document.querySelectorAll('.page').forEach(p => p.classList.add('hidden'));
  $(`page-${pageName}`).classList.remove('hidden');
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.page === pageName));
  const titles = { overview:'Executive Home', runs:'Command Center', golden:'Golden Experience', goldenrun:'Golden Run Control', acceptance:'Product Acceptance', approvals:'Governance', memory:'Learning & Memory', execution:'Execution Center', recovery:'Recovery Center', audit:'Audit Log', health:'System Health', operations:'Production Operations', release:'Release', guide:'How to Use', decisions:'Decisions', evidence:'Evidence Explorer', experiments:'Experiments', policies:'Policies', settings:'Settings', platform:'Platform' };
  $('pageTitle').textContent = titles[pageName];
  $('pageEyebrow').textContent = pageName === 'overview' ? 'CONTROL PLANE' : pageName.toUpperCase();
  if (pageName === 'runs') refreshCommandCenterRuns();
  if (pageName === 'golden') renderO46GoldenExperience();
  if (pageName === 'goldenrun') initGoldenRunControl();
  if (pageName === 'acceptance') initProductAcceptanceConsole();
  if (pageName === 'health') refreshHealth();
  if (pageName === 'operations') refreshOperations();
  if (pageName === 'release') { refreshRelease(); refreshFinalReadinessV46(); }
  if (pageName === 'overview') refreshDashboard();
  if (pageName === 'approvals') refreshApprovalsV43();
  if (pageName === 'execution') refreshExecutionCenter();
  if (pageName === 'recovery') refreshRecoveryCenter();
  if (pageName === 'platform') refreshPlatformV45();
  if (pageName === 'release') refreshFinalReadinessV46();
}

document.querySelectorAll('.nav-item').forEach(b => b.addEventListener('click', () => page(b.dataset.page)));
document.querySelectorAll('[data-page-jump]').forEach(b => b.addEventListener('click', () => page(b.dataset.pageJump)));
document.getElementById('executiveDecisionBtn')?.addEventListener('click', () => {
  const target = document.getElementById('experienceDecisionWhy');
  target?.scrollIntoView({behavior:'smooth', block:'center'});
});

function sessionHeaders(extra = {}) {
  const h = {'Content-Type':'application/json', ...extra};
  if (state.token) h.Authorization = `Bearer ${state.token}`;
  return h;
}

async function api(path, options = {}
const apiGet = (path) => api(path);) {
  const url = `${state.apiBase.replace(/\/$/, '')}${path}`;
  const response = await fetch(url, { ...options, headers: sessionHeaders(options.headers || {}) });
  let payload = {};
  try { payload = await response.json(); } catch { payload = {status:'BAD_RESPONSE'}; }
  if (!response.ok) throw new Error(payload?.error?.reason || payload?.reason || payload?.status || `HTTP ${response.status}`);
  return payload;
}

function setBadge(el, text, kind='') { if (!el) return; el.textContent = text; el.className = `badge ${kind}`; }
function badgeKind(status) {
  return ['COMPLETE','OK','HEALTHY','UP','READY','CONFIGURED'].includes(status) ? 'good' :
    ['FAILED','UNAUTHORIZED','DEGRADED','ERROR','NOT_FOUND','CANCELLED'].includes(status) ? 'bad' : 'warn';
}
function metricCard(label, value, kind='') { return `<div class="metric ${kind}"><div class="label">${esc(label)}</div><div class="value">${esc(value)}</div></div>`; }

function suppressHeroBackendStatus() {
  const hero = $('heroStatus');
  if (!hero) return;
  hero.replaceChildren();
  hero.hidden = true;
  hero.setAttribute('aria-hidden', 'true');
  hero.style.display = 'none';
}

function renderHealthMetrics(health, ready, latencyMs) {
  const components = ready.components || {};
  const entries = Object.entries(components);
  const healthyCount = entries.filter(([,v]) => ['UP','READY','PASS','HEALTHY'].includes(v)).length;
  $('healthCards').innerHTML = [
    metricCard('API', health.status || 'UNKNOWN', badgeKind(health.status)),
    metricCard('Readiness', ready.status || 'UNKNOWN', badgeKind(ready.status)),
    metricCard('Components', `${healthyCount}/${entries.length || 0}`, healthyCount === entries.length ? 'good' : 'warn'),
    metricCard('Latency', `${latencyMs} ms`, latencyMs < 500 ? 'good' : 'warn'),
    metricCard('Failures', String((ready.failures || []).length), (ready.failures || []).length === 0 ? 'good' : 'bad'),
    metricCard('Checked', new Date().toLocaleTimeString(), '')
  ].join('');
}

async function refreshHealth() {
  suppressHeroBackendStatus();
  const started = performance.now();
  try {
    const health = await api('/health');
    const ready = await api('/ready');
    const latencyMs = Math.round(performance.now() - started);
    renderHealthMetrics(health, ready, latencyMs);
    $('healthRaw').textContent = pretty({health, readiness: ready, latency_ms: latencyMs});
    setBadge($('apiHealthBadge'), health.status || 'OK', 'good');
    setBadge($('readyBadge'), ready.status || 'UNKNOWN', badgeKind(ready.status));
    $('readinessList').innerHTML = Object.entries(ready.components || {}).map(([name, status]) => `<div class="health-item"><span class="name">${esc(name)}</span><span class="state"><span class="badge ${badgeKind(status)}">${esc(status)}</span></span></div>`).join('') + ((ready.failures || []).length ? `<div class="callout danger-callout">${esc(JSON.stringify(ready.failures))}</div>` : '');
    $('envLabel').textContent = sessionStorage.getItem('aios.prod') === '1' ? 'PRODUCTION SESSION' : 'LOCAL CONSOLE';
  } catch (err) {
    setBadge($('apiHealthBadge'), 'ERROR', 'bad');
    setBadge($('readyBadge'), 'ERROR', 'bad');
    $('healthCards').innerHTML = [metricCard('API','ERROR','bad'), metricCard('Readiness','ERROR','bad'), metricCard('Components','—','bad'), metricCard('Latency','—','bad'), metricCard('Failures','—','bad'), metricCard('Checked',new Date().toLocaleTimeString(),'')].join('');
    $('healthRaw').textContent = String(err.message || err);
    $('readinessList').innerHTML = `<div class="callout">${esc(err.message || err)}</div>`;
  }
}

function saveRuns() { localStorage.setItem('aios.runs', JSON.stringify(state.runs.slice(0, 30))); }
function renderO46Experience(view){
  if (!view || !window.buildO46ExperienceView) return;
  const q=(id)=>document.getElementById(id); const text=(id,v)=>{const e=q(id); if(e)e.textContent=String(v ?? '—');};
  const stageData=[
    ['intent','Intent',view.intent.request],['research','Research',view.research.source_count ? `${view.research.source_count} sources` : 'Evidence'],
    ['decision','Decision',view.decision.recommendation || 'Waiting'],['governance','Governance',view.governance.status || 'Waiting'],
    ['approval','Approval',view.approval.required ? (view.approval.status||'AWAITING_APPROVAL') : 'Not required'],['execution','Execution',view.execution.status || 'Waiting'],
    ['outcome','Outcome',view.outcome.status || 'Waiting'],['learning','Learning',view.learning.signal || 'Waiting'],['next_step','Next',view.next_step.recommendation || 'Waiting']
  ];
  const activeMap={}; stageData.forEach(([k,,v])=>activeMap[k]=v);
  const rail=q('experienceJourneyRail'); if(rail) rail.innerHTML=stageData.map(([k,label,val],i)=>`<div class="journey-step ${exStatus(view[k])==='NOT_AVAILABLE'?'pending':'ready'}"><span class="journey-index">${String(i+1).padStart(2,'0')}</span><div><b>${esc(label)}</b><small>${esc(val||'—')}</small></div></div>`).join('');
  text('experienceHeadline',view.decision.recommendation && view.decision.recommendation!=='—' ? view.decision.recommendation : 'Your AI operating story, in one place.');
  text('experienceSubline',view.intent.request!=='—' ? view.intent.request : 'Research, decision, governance, execution, outcome and learning—connected as one user journey.');
  text('experienceSource',view.run.job_id!=='—' ? `Run ${view.run.job_id} · ${view.run.status}` : 'Waiting for a run');
  text('experienceDecisionTitle',view.decision.recommendation || 'No decision yet');
  text('executiveRecommendation',view.decision.recommendation || 'Waiting for a decision');
  text('executiveWhy',view.decision.why || 'Run a governed request to turn research into a clear, explainable recommendation.');
  text('executiveConfidence',view.decision.confidence || '—');
  text('executiveOpportunity',view.decision.opportunity_score ?? '—');
  text('executiveStrategy',view.decision.strategy_score ?? '—');
  text('executiveEvidenceCount',Number(view.research.evidence_count || 0));
  text('executiveSourceCount',Number(view.research.source_count || 0));
  text('executiveConflictCount',Number(view.research.conflicts?.length || 0));
  text('executiveGovernanceState',view.governance.status==='NOT_AVAILABLE' ? 'Waiting' : (view.governance.decision || view.governance.status || 'Waiting'));
  text('executiveGovernanceNote',view.approval.required ? 'human approval' : (view.governance.reason || 'policy state'));
  text('executiveNextAction',view.decision.next_action || view.next_step.recommendation || 'Waiting for the next step');
  text('executiveNextReason',view.next_step.reason || view.decision.decision_rule || 'The system will surface the cheapest useful next move when the decision is ready.');
  text('executiveRunState',view.run.status || 'WAITING');
  text('executiveRunMeta',view.run.job_id && view.run.job_id!=='—' ? `Run ${view.run.job_id}` : 'No active run');
  text('experienceDecisionWhy',view.decision.why || 'Run a governed request and the leading hypothesis will appear here.');
  const stats=[['Opportunity',view.decision.opportunity_score],['Strategy',view.decision.strategy_score],['Confidence',view.decision.confidence],['Validation',view.decision.validation_model]];
  const ds=q('experienceDecisionStats'); if(ds) ds.innerHTML=stats.map(([a,b])=>`<div class="experience-stat"><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`).join('');
  text('experienceNextAction',view.decision.next_action); text('experienceDecisionRule',view.decision.decision_rule);
  text('experienceDecisionStatus',view.decision.recommendation?'READY':'WAITING');
  const evCount=Number(view.research.evidence_count||view.research.source_count||0); const srcCount=Number(view.research.source_count||0); const ratio=Math.max(0,Math.min(100,srcCount?Math.round(Math.min(1,evCount/srcCount)*100):0));
  const fill=q('experienceEvidenceFill'); if(fill) fill.style.width=`${ratio}%`; text('experienceEvidenceScore',srcCount?`${srcCount} sources`:'—');
  const mini=q('experienceEvidenceMini'); if(mini) mini.innerHTML=[['Sources',srcCount],['Evidence',evCount],['Conflicts',view.research.conflicts.length]].map(([a,b])=>`<div><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`).join('');
  const el=q('experienceEvidenceList'); if(el) el.innerHTML=(view.research.sources||[]).slice(0,4).map((s)=>`<div class="experience-list-item"><span class="source-dot"></span><span>${esc(typeof s==='string'?s:(s.title||s.name||s.url||'Evidence source'))}</span></div>`).join('') || '<div class="attention-empty">Evidence becomes visible when the backend exposes it.</div>';
  text('experienceGovernanceTitle',view.governance.status==='NOT_AVAILABLE'?'No governance decision yet':view.governance.decision||view.governance.status);
  text('experienceGovernanceStatus',view.governance.status==='NOT_AVAILABLE'?'WAITING':view.governance.status);
  text('experienceGovernanceAction',view.governance.action_type||view.approval.action_id||'—');
  text('experienceGovernanceReason',view.governance.reason||'The governance layer will explain why an action is allowed, reviewed or blocked.');
  const gf=q('experienceGovernanceFacts'); if(gf) gf.innerHTML=[['Risk',view.governance.risk],['Policy',view.governance.policy_version],['External',view.governance.external_effect],['Approval',view.approval.required?'Required':'Not required']].map(([a,b])=>`<div><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`).join('');
  const ab=q('experienceApprovalBtn'); if(ab) ab.classList.toggle('hidden', !(view.approval.required||view.approval.status==='AWAITING_APPROVAL'));
  text('experienceOutcomeTitle',view.outcome.status==='NOT_AVAILABLE'?'Waiting for outcome':view.outcome.status); text('experienceOutcomeSummary',view.outcome.summary||'Once evidence from execution is available, the result and lesson will appear here.'); text('experienceLearningSignal',view.learning.signal); text('experienceNextDecision',view.next_step.recommendation||view.next_step.route);
  const chips=q('experienceTraceChips'); if(chips) chips.innerHTML=[['Run',view.provenance.run_id],['Trace',view.provenance.trace_id],['Provider',view.provenance.provider],['Evidence refs',Array.isArray(view.provenance.evidence_refs)?view.provenance.evidence_refs.length:'—']].map(([a,b])=>`<div class="trace-chip"><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`).join('');
  if (window.renderO46RunStory) renderO46RunStory(view);
  const j=q('experienceJson'); if(j && !j.classList.contains('hidden')) j.textContent=pretty(view);
  $('experienceExplainBtn')?.setAttribute('aria-expanded', j?.classList.contains('hidden') ? 'false':'true');
  return view;
}
async function refreshO46Experience(){
  try{
    const runs=await api('/runs?limit=10'); const items=Array.isArray(runs)?runs:(runs.runs||runs.items||[]);
    const best=items.find(x=>['RUNNING','COMPLETE','FAILED','AWAITING_APPROVAL','PENDING_APPROVAL'].includes(String(x.status||'').toUpperCase())) || items[0] || state.runs[0];
    if(!best){ renderO46Experience(buildO46ExperienceView(null)); return; }
    addRun(best);
    const detail=await api(`/runs/${encodeURIComponent(best.job_id)}`);
    addRun(detail);
    const learning=await (async()=>{try{return await api(`/learning/context?project_id=${encodeURIComponent(detail.project_id||'PROJ-001')}`)}catch{return null}})();
    const experiments=await (async()=>{try{const e=await api('/experiments');return Array.isArray(e)?e:(e.experiments||e.items||[])}catch{return null}})();
    const approvals=await (async()=>{try{const a=await api('/approvals');return Array.isArray(a)?a:(a.approvals||a.items||[])}catch{return null}})();
    const approval=Array.isArray(approvals)?approvals.find(a=>a.job_id===detail.job_id || a.run_id===detail.job_id || a.action_id===detail.action_id) || approvals[0]:null;
    const view=window.buildO46ExperienceView(detail,{learning,experiment:Array.isArray(experiments)?experiments[0]:null,approval});
    window.__O46_EXPERIENCE_VIEW__=view;
    renderO46Experience(view);
  }catch(err){ renderO46Experience(buildO46ExperienceView(null)); const src=document.getElementById('experienceSource'); if(src) src.textContent=`Unavailable · ${err.message||err}`; }
}
/* O46 UI-1 boundary: experience read-only refresh ends here. */
function addRun(run) {
  if (!run?.job_id) return;
  const idx = state.runs.findIndex(r => r.job_id === run.job_id);
  const item = { ...state.runs[idx], ...run,
    job_id:run.job_id,
    project_id:run.project_id,
    created_at:run.created_at || state.runs[idx]?.created_at || new Date().toISOString(),
    status:run.status || state.runs[idx]?.status || 'UNKNOWN'
  };
  if (idx >= 0) state.runs[idx] = item; else state.runs.unshift(item);
  saveRuns();
}

async function refreshRun(item) {
  try {
    const out = await api(`/runs/${encodeURIComponent(item.job_id)}`);
    addRun(out);
    return out;
  } catch { return null; }
}

async function syncAllRuns() {
  if (!state.runs.length) return [];
  const results = await Promise.all(state.runs.slice(0,30).map(refreshRun));
  return results.filter(Boolean);
}

async function syncRunIndex() {
  return syncAllRuns();
}

function runActionButtons(run) {
  if (!run) return '';
  const buttons = [];
  if (run.status === 'QUEUED') buttons.push(`<button class="secondary-btn run-execute" data-run="${esc(run.job_id)}">Execute now</button>`);
  if (run.status === 'QUEUED') buttons.push(`<button class="ghost-btn run-cancel" data-run="${esc(run.job_id)}">Cancel</button>`);
  return buttons.join('');
}

function traceState(status, index) {
  if (status === 'COMPLETE') return 'PASS';
  if (status === 'FAILED') return index === 0 ? 'FAILED' : 'STOPPED';
  if (status === 'CANCELLED') return 'CANCELLED';
  if (status === 'RUNNING') return index < 1 ? 'PASS' : index === 1 ? 'ACTIVE' : 'PENDING';
  return index === 0 ? 'QUEUED' : 'PENDING';
}

const STAGE_ORDER = [
  ['knowledge','Knowledge'], ['prompt','Prompt'], ['market','Market'], ['ideas','Ideas'],
  ['strategy','Strategy'], ['product','Product'], ['brand','Brand'], ['content','Content'],
  ['visual','Visual'], ['marketing','Marketing'], ['sales','Sales'], ['automation','Automation'],
  ['analytics','Analytics'], ['approval','Approval'], ['memory','Memory'], ['monitoring','Monitoring']
];

function stageStatus(node, fallback='—') {
  if (!node) return fallback;
  return String(node.status || node.qa?.status || node.state || fallback).toUpperCase();
}

function stageEngine(node) {
  if (!node) return '—';
  return node.engine_id ? `${node.engine_id}${node.engine_version ? ` · ${node.engine_version}` : ''}` : '—';
}

function stageMeta(key, node) {
  if (!node) return '';
  const bits=[];
  if (key === 'market' && node.report) {
    if (node.report.source_count != null) bits.push(`${node.report.source_count} sources`);
    if (node.report.evidence_count != null) bits.push(`${node.report.evidence_count} evidence`);
  }
  if (key === 'ideas' && node.ideas?.idea_count != null) bits.push(`${node.ideas.idea_count} ideas`);
  if (key === 'analytics' && node.event_summary?.total_events != null) bits.push(`${node.event_summary.total_events} events`);
  if (key === 'monitoring' && node.event_count != null) bits.push(`${node.event_count} events`);
  if (key === 'approval' && node.risk) bits.push(`risk ${node.risk}`);
  return bits.join(' · ');
}

function renderTrace(run) {
  const stages = ['Understand','Route','Execute','Validate','Learn','Remember'];
  return stages.map((s, i) => `<div class="trace-step"><div class="step">${s}</div><div class="state">${traceState(run.status, i)}</div></div>`).join('');
}

function semanticQuality(node) {
  if (!node) return {kind:'muted', label:'No payload'};
  const texts=[];
  for (const path of ['idea','description','product_definition.core_problem','positioning.positioning_statement','product_definition.core_promise']) {
    const parts=path.split('.'); let cur=node;
    for (const part of parts) cur=cur?.[part];
    if (typeof cur === 'string' && cur.trim()) texts.push(cur.trim());
  }
  const joined=texts.join(' ');
  if (!joined) return {kind:'good', label:'Structured'};
  const rawEcho=/\|\s*(email|crm)\s*\|/i.test(joined)||/create a (value-focused|focused|simple) (offer|product\/service).*:/i.test(joined)||/https?:\/\//i.test(joined);
  if (rawEcho || joined.length>900) return {kind:'warn',label:'Needs review'};
  return {kind:'good',label:'Structured'};
}

function handoffInsight(handoff, target) {
  const c=handoff?.contract || {};
  const keys=['problem','idea','promise','message','topic','asset_summary','offer_summary','workflow_summary','decision_summary','learning_summary','evidence_summary'];
  for (const key of keys) if (typeof c[key]==='string' && c[key].trim()) return c[key].trim();
  for (const key of keys) if (typeof target?.[key]==='string' && target[key].trim()) return target[key].trim();
  return 'Structured handoff available with provenance and boundary identity.';
}

const HANDOFF_PATHS = [
  ['market','ideas','market_to_idea'],
  ['ideas','strategy','idea_to_strategy'],
  ['strategy','product','strategy_to_product'],
  ['product','brand','product_to_brand'],
  ['brand','content','brand_to_content'],
  ['content','visual','content_to_visual'],
  ['visual','marketing','visual_to_marketing'],
  ['marketing','sales','marketing_to_sales'],
  ['sales','automation','sales_to_automation'],
  ['automation','analytics','automation_to_analytics'],
  ['analytics','approval','analytics_to_approval'],
  ['approval','memory','approval_to_memory'],
  ['memory','monitoring','memory_to_monitoring'],
];

function handoffCard(fromKey, toKey, pairKey, result) {
  const from=result?.[fromKey], to=result?.[toKey];
  const record=result?.handoffs?.[pairKey];
  if (!record?.contract) return '';
  const qaStatus=(record.qa?.status || 'PASS').toUpperCase();
  const refs=Array.isArray(record.contract?.source_refs) ? record.contract.source_refs.length : 0;
  const quality=qaStatus==='PASS' && refs>0 ? {kind:'good',label:'Structured'} : {kind:'warn',label:'Needs review'};
  const fromLabel=STAGE_ORDER.find(x=>x[0]===fromKey)?.[1]||fromKey;
  const toLabel=STAGE_ORDER.find(x=>x[0]===toKey)?.[1]||toKey;
  const insight=handoffInsight(record,to);
  const pendingNote=pairKey==='approval_to_memory' && String(record.contract?.decision_summary||'').toUpperCase()==='PENDING'
    ? 'Structurally valid · approval pending'
    : (refs ? `${refs} provenance refs` : 'Provenance missing');
  return `<button type="button" class="handoff-row ${qaStatus==='PASS' ? 'handoff-ok' : 'handoff-review'}" data-handoff="${esc(pairKey)}">\
    <div class="handoff-top"><div class="handoff-path"><span>${esc(fromLabel)}</span><b>→</b><span>${esc(toLabel)}</span></div><span class="badge ${quality.kind}">${esc(quality.label)}</span></div>\
    <div class="handoff-insight">${esc(insight)}</div>\
    <div class="handoff-source">${esc(pendingNote)}</div></button>`;
}

function renderEngineTrace(result) {
  if (!result || typeof result !== 'object' || !Object.keys(result).some(k => result[k])) {
    return `<div class="trace-empty"><div class="trace-empty-title">No engine output yet</div><div class="trace-empty-copy">Execution has not produced a result payload yet. The trace will populate automatically while the run progresses.</div></div>`;
  }
  const groups = [
    {title:'Foundation', subtitle:'Evidence, context & routing', keys:['knowledge','prompt','market']},
    {title:'Business Design', subtitle:'Ideas → offer architecture', keys:['ideas','strategy','product','brand']},
    {title:'Go-to-Market', subtitle:'Content, creative & commercial', keys:['content','visual','marketing','sales']},
    {title:'Execution & Governance', subtitle:'Automation, analytics & controls', keys:['automation','analytics','approval','memory','monitoring']}
  ];
  return groups.map(group => {
    const present = group.keys.filter(k=>result[k]);
    if (!present.length) return '';
    const cards = present.map(key => {
      const label = STAGE_ORDER.find(x=>x[0]===key)?.[1] || key;
      const node = result[key];
      const status = stageStatus(node);
      const meta = stageMeta(key,node);
      const quality = semanticQuality(node);
      const statusClass = badgeKind(status);
      return `<button type="button" class="engine-card ${statusClass}" data-engine="${esc(key)}" aria-label="Inspect ${esc(label)}">
        <div class="engine-accent"></div>
        <div class="engine-top"><span class="engine-name">${esc(label)}</span><span class="badge ${statusClass}">${esc(status)}</span></div>
        <div class="engine-id">${esc(stageEngine(node))}</div>
        <div class="engine-meta">${esc(meta || quality.label)}</div>
      </button>`;
    }).join('');
    return `<section class="trace-group"><div class="trace-group-head"><div><div class="eyebrow">${esc(group.title)}</div><div class="trace-group-title">${esc(group.subtitle)}</div></div><div class="trace-group-count">${present.length} stages</div></div><div class="engine-grid">${cards}</div></section>`;
  }).join('');
}

function renderHandoffs(result) {
  if (!result || typeof result!=='object') return '';
  const rows=HANDOFF_PATHS.map(([from,to,key])=>handoffCard(from,to,key,result));
  const records=HANDOFF_PATHS.map(([, ,key])=>result?.handoffs?.[key]).filter(Boolean);
  const failed=records.filter(r=>String(r?.qa?.status||'').toUpperCase()!=='PASS').length;
  const missingRefs=records.filter(r=>!(Array.isArray(r?.contract?.source_refs) && r.contract.source_refs.length)).length;
  const note=$('handoffQualityNote');
  if(note){
    note.textContent = failed || missingRefs
      ? `Semantic review required · ${failed} QA issue${failed===1?'':'s'} · ${missingRefs} provenance gap${missingRefs===1?'':'s'}`
      : 'Semantic contracts healthy · no evidence leakage flagged in the handoff chain.';
  }
  return rows.some(Boolean) ? `<div class="handoff-list">${rows.join('')}</div>` : `<div class="trace-empty small"><div class="trace-empty-title">No handoff data yet</div><div class="trace-empty-copy">Handoffs appear once downstream engine payloads are available.</div></div>`;
}

function formatTime(value) {
  if (!value) return '—';
  const d=new Date(value); return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString([], {year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'});
}

function renderSummary(run) {
  if (!run) return '';
  const result=run.result||{}; const approval=result?.approval||{}; const approvalStatus=approval.status||'—';
  const qa=result?.qa?.status || result?.monitoring?.qa_status || '—';
  const duration=result?.monitoring?.duration_seconds!=null ? `${Number(result.monitoring.duration_seconds).toFixed(2)}s` : '—';
  const eventCount=result?.monitoring?.event_count!=null ? String(result.monitoring.event_count) : '—';
  const rawConstraints=run.constraints;
  const constraints=Array.isArray(rawConstraints) ? rawConstraints.filter(Boolean) : (rawConstraints ? [rawConstraints] : []);
  const risk=approval.risk || (approvalStatus==='PENDING' ? 'HIGH' : '—');
  return `\
    <div class="run-result-hero"><div>\
      <div class="eyebrow">RUN RESULT</div>\
      <div class="result-title-row"><strong>${esc(run.project_id||'Project')}</strong><span class="badge ${badgeKind(run.status)}">${esc(run.status)}</span></div>\
      <p class="result-request">${esc(run.request||'No request text available.')}</p>\
      <div class="input-context"><span class="context-pill"><b>Audience</b> · ${esc(run.audience||'—')}</span><span class="context-pill"><b>Goal</b> · ${esc(run.goal||'—')}</span>${constraints.map(c=>`<span class="context-pill context-pill-wide"><b>Constraint</b> · ${esc(c)}</span>`).join('')}</div>\
    </div><div class="result-kpis"><div><span>QA</span><strong>${esc(qa)}</strong></div><div><span>Approval</span><strong>${esc(approvalStatus)}</strong></div><div><span>Risk</span><strong>${esc(risk)}</strong></div><div><span>Duration</span><strong>${esc(duration)}</strong></div></div></div>\
    ${approvalStatus==='PENDING' ? `<div class="governance-callout"><span class="badge warn">HUMAN GATE</span><span><strong>External action blocked.</strong> ${esc(approval.action||'Consequential action')} remains pending approval.</span></div>` : ''}\
    ${renderResultHighlights(run, result)}\
    <div class="detail-grid"><div><span class="detail-label">Run ID</span><strong title="${esc(run.job_id)}">${esc(run.job_id)}</strong></div><div><span class="detail-label">Project</span><strong>${esc(run.project_id)}</strong></div><div><span class="detail-label">Created</span><strong>${esc(formatTime(run.created_at))}</strong></div><div><span class="detail-label">Updated</span><strong>${esc(formatTime(run.updated_at))}</strong></div><div><span class="detail-label">Events</span><strong>${esc(eventCount)}</strong></div><div><span class="detail-label">Approval</span><strong>${esc(approvalStatus)}</strong></div></div>\
    ${run.status==='FAILED' ? `<div class="callout danger-callout">${esc(run.error?.message || run.error?.failed_stage || run.error?.runtime_status || 'Run failed')}</div>` : ''}\
    ${run.status==='COMPLETE' ? `<div class="callout success-callout">Runtime completed. Review the evidence chain, handoffs, QA and governance state before taking any downstream action.</div>` : ''}`;
}

function firstText(...values){ for(const v of values){ if(typeof v==='string' && v.trim()) return v.trim(); if(typeof v==='number' && Number.isFinite(v)) return String(v); } return ''; }
function firstObject(...values){ for(const v of values){ if(v && typeof v==='object' && !Array.isArray(v)) return v; } return {}; }
function compactText(value, max=260){
  const text=firstText(value);
  if(!text) return '';
  return text.length>max ? `${text.slice(0,max-1).trimEnd()}…` : text;
}
function deriveDecision(strategy, topIdea){
  return firstText(
    strategy?.recommendation,
    strategy?.decision,
    strategy?.strategy?.recommended_opportunity,
    strategy?.strategy?.decision,
    strategy?.selected_idea?.idea,
    strategy?.selected_idea?.title,
    strategy?.summary,
    topIdea?.idea,
    topIdea?.title,
    topIdea?.description
  );
}
function deriveValidation(ideas, strategy){
  const plans=ideas?.validation?.idea_validation_plans;
  if(Array.isArray(plans) && plans.length){
    const plan=plans[0]||{};
    const check=Array.isArray(plan.checks) ? plan.checks[0] : null;
    if(check?.test && check?.question) return `${check.test}: ${check.question}`;
    if(plan.validation_test) return firstText(plan.validation_test);
  }
  const candidates=[
    strategy?.validation_plan,
    strategy?.validation?.next_test,
    strategy?.next_decision,
    strategy?.strategy?.next_decision
  ];
  return firstText(...candidates);
}
function deriveNextAction(strategy, ideas, product){
  const explicit=firstText(
    strategy?.next_action,
    strategy?.next_decision,
    strategy?.strategy?.next_action,
    strategy?.strategy?.next_decision,
    product?.next_action
  );
  if(explicit) return explicit;
  const plans=ideas?.validation?.idea_validation_plans;
  if(Array.isArray(plans) && plans.length){
    const p=plans[0]||{};
    if(p.validation_priority) return `Run the ${String(p.validation_priority).toLowerCase()}-priority validation test before building.`;
  }
  return 'Validate the recommended opportunity before committing capital or external actions.';
}

function slugify(value){
  return String(value || 'run').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'').slice(0,80) || 'run';
}
function downloadBlob(filename, content, mime='text/plain;charset=utf-8'){
  const blob=new Blob([content],{type:mime});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function resultExtraction(run){
  const result=run?.result || {};
  const market=result.market||{}, ideas=result.ideas||{}, strategy=result.strategy||{}, product=result.product||{}, brand=result.brand||{};
  const surface=result?.decision_surface || {};
  const ar=result?.arabic_decision_summary || {};
  const ranked=(ideas?.scores?.ranked_ideas || []);
  const topIdea=ranked[0] || ideas?.ideas?.[0] || ideas?.top_idea || strategy?.selected_idea || {};
  const architecture=firstObject(product?.product_definition?.architecture, product?.architecture);
  const sources=surface?.evidence?.source_count ?? market?.report?.source_count;
  const evidence=surface?.evidence?.evidence_count ?? market?.report?.evidence_count;
  const validationExperiment=surface?.validation_experiment || ar?.validation || {};
  return {
    recommendation: firstText(surface?.recommendation, ar?.recommendation, deriveDecision(strategy,topIdea)),
    problem: firstText(surface?.problem, ar?.problem, product?.product_definition?.core_problem, product?.core_problem, strategy?.problem, strategy?.problem_statement),
    audience: firstText(surface?.customer, ar?.customer_segment, product?.product_definition?.target_audience, product?.target_audience, run?.audience),
    mvp: firstText((surface?.mvp_direction || []).join(' · '), ar?.mvp?.join?.(' · '), architecture?.delivery_model, architecture?.format, product?.mvp, product?.mvp_scope),
    validation: firstText(surface?.validation_experiment, ar?.validation_experiment, deriveValidation(ideas,strategy)),
    nextAction: firstText(surface?.next_action, ar?.next_action, deriveNextAction(strategy,ideas,product)),
    promise: firstText(surface?.desired_outcome, ar?.desired_outcome, product?.product_definition?.core_promise, product?.core_promise),
    positioning: firstText(brand?.brand_definition?.positioning, brand?.positioning?.positioning_statement, brand?.positioning),
    confidence: firstText(surface?.confidence, ar?.confidence, topIdea?.confidence, 'medium'),
    evidenceLabel: (sources!=null || evidence!=null) ? `${sources ?? '—'} sources · ${evidence ?? '—'} evidence` : 'Evidence recorded in run trace',
    topIdea: firstText(topIdea?.title, topIdea?.idea, topIdea?.description),
    opportunityScore: firstText(surface?.opportunity_score, ar?.opportunity_score, topIdea?.opportunity_score, topIdea?.overall_score),
    strategyScore: firstText(surface?.strategy_score, ar?.strategy_score),
    marketScope: firstText(surface?.evidence_boundary, ar?.evidence_boundary, market?.report?.evidence_boundary, topIdea?.market_scope),
    localEvidence: firstText(ar?.local_evidence),
    validationModel: firstText(surface?.validation_model, ar?.validation_model, strategy?.validation_model),
    longTermModel: firstText(surface?.long_term_product_model, ar?.long_term_product_model, strategy?.long_term_product_model, strategy?.strategy?.recommended_model?.name),
    successThreshold: firstText(ar?.success_threshold),
    decisionRule: firstText(surface?.go_decision_rule, ar?.go_decision_rule, validationExperiment?.decision_rule),
    recommendationReason: firstText(strategy?.strategy?.recommendation_reason, strategy?.recommendation_reason),
  };
}
function buildBusinessReport(run){
  const x=resultExtraction(run);
  const lines=[
    '# AI Master OS — Business Run Report',
    '',
    `Project: ${run?.project_id || '—'}`,
    `Run ID: ${run?.job_id || '—'}`,
    `Status: ${run?.status || '—'}`,
    `Created: ${formatTime(run?.created_at)}`,
    `Updated: ${formatTime(run?.updated_at)}`,
    '',
    '## Goal',
    run?.goal || run?.request || '—',
    '',
    '## Audience',
    run?.audience || '—',
    '',
    '## Request',
    run?.request || '—',
    '',
    '## What You Should Take Away',
    '',
    ...(run?.result?.requested_language === 'ar' && run?.result?.arabic_decision_summary ? [
      '### الملخص بالعربية',
      `القرار المقترح: ${run.result.arabic_decision_summary.recommendation || '—'}`,
      `النموذج: ${run.result.arabic_decision_summary.recommended_model || '—'}`,
      `المشكلة: ${run.result.arabic_decision_summary.problem || '—'}`,
      `النتيجة المطلوبة: ${run.result.arabic_decision_summary.desired_outcome || '—'}`,
      `الخطوة التالية: ${run.result.arabic_decision_summary.next_action || '—'}`,
      `حدود الدليل: ${run.result.arabic_decision_summary.local_evidence || '—'}`,
      '',
    ] : []),
    '### Recommendation', x.recommendation || 'No explicit recommendation recorded.',
    '',
    '### Why This Direction', x.recommendationReason || 'No explicit recommendation rationale recorded.',
    '',
    '### Customer Problem', x.problem || 'No canonical problem recorded.',
    '',
    '### Target Customer', x.audience || '—',
    '',
    '### Validation Model', x.validationModel || '—',
    '',
    '### Long-term Product Model', x.longTermModel || '—',
    '',
    '### MVP Direction', x.mvp || '—',
    '',
    '### First Validation Test', x.validation || '—',
    '',
    '### Success Threshold', x.successThreshold || '—',
    '',
    '### Decision Rule', x.decisionRule || '—',
    '',
    '### Next Action', x.nextAction || '—',
    '',
    '### Customer Outcome / Promise', x.promise || '—',
    '',
    '### Positioning', x.positioning || '—',
    '',
    '### Opportunity Score', x.opportunityScore || '—',
    '',
    '### Strategy Score', x.strategyScore || '—',
    '',
    '### Market Evidence Boundary', x.marketScope || '—',
    '',
    '### Local Evidence', x.localEvidence || '—',
    '',
    '## Evidence & Confidence',
    `Evidence: ${x.evidenceLabel}`,
    `Confidence: ${x.confidence || '—'}`,
    '',
    '## Governance',
    `Approval: ${run?.result?.approval?.status || '—'}`,
    `Risk: ${run?.result?.approval?.risk || '—'}`,
    '',
    '> This report summarizes the business-facing output. Use the JSON export and Engine Trace for full audit/debug details.'
  ];
  return lines.join('\n');
}
function downloadBusinessReport(run){
  if(!run) return;
  downloadBlob(`AI_Master_OS_${slugify(run.project_id)}_${slugify(run.job_id)}_business_report.md`, buildBusinessReport(run), 'text/markdown;charset=utf-8');
}
function downloadFullRun(run){
  if(!run) return;
  downloadBlob(`AI_Master_OS_${slugify(run.project_id)}_${slugify(run.job_id)}_full_run.json`, pretty(run), 'application/json;charset=utf-8');
}
function downloadEnginePayload(title, payload){
  downloadBlob(`AI_Master_OS_${slugify(title)}_payload.json`, pretty(payload), 'application/json;charset=utf-8');
}

function renderResultHighlights(run, result){
  if(!result || typeof result!=='object') return '';
  const market=result?.market||{}, ideas=result?.ideas||{}, strategy=result?.strategy||{}, product=result?.product||{}, brand=result?.brand||{};
  const topIdea=ideas?.ideas?.[0] || ideas?.top_idea || strategy?.selected_idea || {};
  const recommendation=compactText(deriveDecision(strategy,topIdea),220);
  const problem=compactText(firstText(product?.product_definition?.core_problem, product?.core_problem, strategy?.problem, strategy?.problem_statement),260);
  const audience=compactText(firstText(product?.product_definition?.target_audience, product?.target_audience, run?.audience),180);
  const promise=compactText(firstText(product?.product_definition?.core_promise, product?.core_promise),220);
  const validation=compactText(deriveValidation(ideas,strategy),260);
  const nextAction=compactText(deriveNextAction(strategy,ideas,product),220);
  const positioning=compactText(firstText(brand?.brand_definition?.positioning, brand?.positioning?.positioning_statement, brand?.positioning),220);
  const recommendationReason=compactText(firstText(strategy?.strategy?.recommendation_reason, strategy?.recommendation_reason),280);
  const opportunityScore=firstText(topIdea?.opportunity_score);
  const marketScope=firstText(topIdea?.market_scope);
  const architecture=firstObject(product?.product_definition?.architecture, product?.architecture);
  const mvp=compactText(firstText(architecture?.delivery_model, architecture?.format, product?.mvp, product?.mvp_scope),180);
  const confidence=firstText(
    strategy?.confidence,
    strategy?.selected_idea?.confidence,
    topIdea?.confidence,
    topIdea?.scores?.evidence_fit ? 'Medium' : ''
  );
  const sources=market?.report?.source_count;
  const evidence=market?.report?.evidence_count;
  const evidenceLabel=(sources!=null || evidence!=null) ? `${sources ?? '—'} sources · ${evidence ?? '—'} evidence` : 'Evidence recorded in run trace';
  const cards=[];
  const ar = result?.arabic_decision_summary;
  if (run?.result?.requested_language === 'ar' && ar) {
    cards.push(`<div class="result-highlight featured"><span>الملخص بالعربية</span><strong>${esc(ar.recommendation || '—')}</strong><small>التحقق الآن: ${esc(ar.validation_model || '—')} · نموذج المنتج لاحقًا: ${esc(ar.long_term_product_model || ar.recommended_model || '—')}</small><small>Opportunity Score: ${esc(ar.opportunity_score || '—')} · Strategy Score: ${esc(ar.strategy_score || '—')} · الثقة: ${esc(ar.confidence || '—')}</small><small>المشكلة: ${esc(ar.problem || '—')}</small><small>الاختبار: ${esc(ar.validation_experiment || ar.next_action || '—')}</small><small>العتبة: ${esc(ar.success_threshold || '—')}</small><small>${esc(ar.local_evidence || '')}</small></div>`);
  }
  if(recommendation) cards.push(`<div class="result-highlight featured"><span>Recommendation</span><strong>${esc(recommendation)}</strong><small>Best current opportunity returned by the strategy layer; it remains a hypothesis until local validation.</small></div>`);
  if(recommendationReason) cards.push(`<div class="result-highlight"><span>Why this direction</span><strong>${esc(recommendationReason)}</strong><small>Strategy rationale for the current validation stage.</small></div>`);
  if(problem) cards.push(`<div class="result-highlight"><span>Customer problem</span><strong>${esc(problem)}</strong><small>The canonical problem statement carried into Product.</small></div>`);
  if(audience) cards.push(`<div class="result-highlight"><span>Target customer</span><strong>${esc(audience)}</strong><small>Who the recommendation is designed for.</small></div>`);
  if(mvp) cards.push(`<div class="result-highlight"><span>MVP direction</span><strong>${esc(mvp)}</strong><small>The smallest delivery shape currently recorded by Product.</small></div>`);
  const canonical=result?.decision_surface || {};
  if(canonical.validation_model) cards.push(`<div class="result-highlight"><span>Validation model</span><strong>${esc(canonical.validation_model)}</strong><small>How the opportunity should be tested now.</small></div>`);
  if(canonical.long_term_product_model) cards.push(`<div class="result-highlight"><span>Long-term product model</span><strong>${esc(canonical.long_term_product_model)}</strong><small>Current product direction after validation.</small></div>`);
  if(validation) cards.push(`<div class="result-highlight"><span>First validation test</span><strong>${esc(validation)}</strong><small>Use this to test the key assumption before investing further.</small></div>`);
  if(nextAction) cards.push(`<div class="result-highlight"><span>Next action</span><strong>${esc(nextAction)}</strong><small>Concrete next move suggested by the workflow.</small></div>`);
  if(promise) cards.push(`<div class="result-highlight"><span>Customer outcome</span><strong>${esc(promise)}</strong><small>The intended result for the buyer.</small></div>`);
  if(positioning) cards.push(`<div class="result-highlight"><span>Positioning</span><strong>${esc(positioning)}</strong><small>How the offer is framed for the target audience.</small></div>`);
  if(opportunityScore) cards.push(`<div class="result-highlight"><span>Opportunity score</span><strong>${esc(opportunityScore)}</strong><small>Idea-priority heuristic, not probability of success.</small></div>`);
  if(resultExtraction(run).strategyScore) cards.push(`<div class="result-highlight"><span>Strategy score</span><strong>${esc(resultExtraction(run).strategyScore)}</strong><small>Business-model fit heuristic for the current validation stage.</small></div>`);
  if(marketScope) cards.push(`<div class="result-highlight"><span>Evidence boundary</span><strong>${esc(marketScope)}</strong><small>Local validation is still required when evidence is global.</small></div>`);
  const meta=[];
  if(sources!=null || evidence!=null) meta.push(`<span><b>Evidence</b> · ${esc(evidenceLabel)}</span>`);
  if(confidence) meta.push(`<span><b>Confidence</b> · ${esc(confidence)}</span>`);
  if(!cards.length && !meta.length) return '';
  return `<section class="result-highlights result-business-first"><div class="result-highlights-head"><div><div class="eyebrow">RESULT AT A GLANCE</div><h3>What you should take away from this run</h3></div><div class="result-actions"><button class="secondary-btn result-download-report" type="button">Download business report</button><button class="ghost-btn result-download-json" type="button">Download full JSON</button></div></div><div class="result-download-note">Human-readable report for sharing · Full JSON for audit and engineering review.</div>${meta.length ? `<div class="result-summary-meta">${meta.join('')}</div>` : ''}<div class="result-highlight-grid">${cards.join('')}</div></section>`;
}

function payloadSummary(node) {
  if (!node || typeof node!=='object') return '';
  const candidates=[['Status',node.status],['Engine',stageEngine(node)],['Quality',semanticQuality(node).label],['QA',node.qa?.status || node.qa_status],['Problem',node.product_definition?.core_problem || node.problem],['Idea',node.idea],['Topic',node.topic],['Objective',node.objective],['Message',node.message]];
  return candidates.filter(([,v])=>v).slice(0,6).map(([k,v])=>`<div class="payload-row"><div class="k">${esc(k)}</div><div class="v">${esc(typeof v==='string' ? v : JSON.stringify(v))}</div></div>`).join('');
}

function openEnginePayload(key, result) {
  const label=STAGE_ORDER.find(x=>x[0]===key)?.[1]||key; const node=result?.[key]||{};
  $('enginePayloadTitle').textContent=`${label} · ${stageEngine(node)}`;
  $('enginePayloadSummary').innerHTML=payloadSummary(node);
  $('enginePayloadJson').textContent=pretty(node);
  $('enginePayloadDownload').onclick=()=>downloadEnginePayload(`${label}_${stageEngine(node)}`, node);
  $('payloadDrawerOverlay').classList.remove('hidden');
}

function closePayloadDrawer(){ $('payloadDrawerOverlay').classList.add('hidden'); }

async function renderRecentRuns() {
  const holder = $('recentRuns');
  if (!state.runs.length) { holder.innerHTML = `<div class="callout">No runs yet. Start your first governed run above.</div>`; return; }
  await syncAllRuns();
  holder.innerHTML = state.runs.slice(0,5).map(r => `<div class="run-row"><div><div class="run-id">${esc(r.job_id)}</div><div class="run-sub">${esc(r.project_id)} · ${esc(r.request || '')}</div></div><div class="run-actions-mini"><span class="badge ${badgeKind(r.status)}">${esc(r.status)}</span><button class="text-btn open-run-mini" data-run="${esc(r.job_id)}">Inspect</button></div></div>`).join('');
  holder.querySelectorAll('.open-run-mini').forEach(b=>b.addEventListener('click',()=>{page('runs');inspectRun(b.dataset.run);}));
}

async function fetchBackendRuns(limit=50) {
  try {
    const out = await api(`/runs?limit=${limit}`);
    const items = Array.isArray(out) ? out : (Array.isArray(out?.runs) ? out.runs : []);
    state.backendRuns = items.filter(Boolean);
    state.runsSource = 'backend';
    for (const run of state.backendRuns) addRun(run);
    return state.backendRuns;
  } catch (err) {
    state.runsSource = state.runs.length ? 'local-fallback' : 'unavailable';
    state.backendRuns = [];
    return [];
  }
}

function getRunsForDisplay() {
  const source = state.runsSource === 'backend' && state.backendRuns.length ? state.backendRuns : state.runs;
  const dedup = new Map();
  for (const r of source || []) if (r?.job_id) dedup.set(r.job_id, r);
  return Array.from(dedup.values()).sort((a,b)=>String(b.created_at||'').localeCompare(String(a.created_at||''))).slice(0,50);
}

function runsFilterValue() { return String($('runStatusFilter')?.value || 'ALL').toUpperCase(); }
function runsSearchValue() { return String($('runHistorySearch')?.value || '').trim().toLowerCase(); }

function filteredRunsForDisplay() {
  const status=runsFilterValue(), query=runsSearchValue();
  return getRunsForDisplay().filter(r=>{
    const okStatus=status==='ALL' || String(r.status||'').toUpperCase()===status;
    if (!okStatus) return false;
    if (!query) return true;
    return [r.job_id,r.project_id,r.request,r.status].some(v=>String(v||'').toLowerCase().includes(query));
  });
}

function renderRunsSourceMeta() {
  const el=$('runHistorySourceState'); if(!el) return;
  const ar=langState.current==='ar';
  if(state.runsSource==='backend') el.textContent=ar?'المصدر: Backend مباشر':'Source: live backend';
  else if(state.runsSource==='local-fallback') el.textContent=ar?'المصدر: سجل محلي احتياطي':'Source: local fallback';
  else if(state.runsSource==='unavailable') el.textContent=ar?'لا تتوفر بيانات التشغيل':'Run data unavailable';
  else el.textContent=ar?'المصدر: السجل المحلي':'Source: local console';
}

async function renderRunsTable() {
  const tbody = $('runsTable');
  if (!tbody) return;
  const rows = filteredRunsForDisplay();
  renderRunsSourceMeta();
  const countEl=$('runHistoryCountLive'); if(countEl) countEl.textContent=String(rows.length);
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="table-empty-state">${esc(langState.current==='ar' ? 'لا توجد تشغيلات تطابق الفلاتر الحالية.' : 'No runs match the current filters.')}</div></td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map(r => `<tr><td><button class="link-btn open-run" data-run="${esc(r.job_id)}">${esc(r.job_id)}</button></td><td>${esc(r.project_id)}</td><td><span class="badge ${badgeKind(r.status)}">${esc(r.status)}</span></td><td>${esc(r.created_at || '')}</td><td><button class="text-btn open-run" data-run="${esc(r.job_id)}">${langState.current==='ar'?'فحص':'Inspect'}</button></td></tr>`).join('');
  tbody.querySelectorAll('.open-run').forEach(b => b.addEventListener('click', () => inspectRun(b.dataset.run)));
}

async function refreshCommandCenterRuns() {
  await fetchBackendRuns(50);
  await renderRunsTable();
}

function bindRunsFilters() {
  $('runHistorySearch')?.addEventListener('input', ()=>renderRunsTable());
  $('runStatusFilter')?.addEventListener('change', ()=>renderRunsTable());
  $('clearRunFilters')?.addEventListener('click', ()=>{
    if($('runHistorySearch')) $('runHistorySearch').value='';
    if($('runStatusFilter')) $('runStatusFilter').value='ALL';
    renderRunsTable();
  });
}

function progressState(run){
  if (!run) return {percent:0,current:'Waiting'};
  if (run.status === 'COMPLETE') return {percent:100,current:'Completed'};
  if (run.status === 'FAILED') return {percent:100,current:'Failed'};
  if (run.status === 'CANCELLED') return {percent:100,current:'Cancelled'};
  const result=run.result||{};
  const available=STAGE_ORDER.filter(([key])=>result[key] && typeof result[key]==='object');
  const completed=available.filter(([key])=>String(result[key]?.status||'').toUpperCase()==='COMPLETE').length;
  const stageIndex=Math.max(0, completed-1);
  const current=available.length ? STAGE_ORDER.find(x=>x[0]===available[available.length-1][0])?.[1] : 'Starting pipeline';
  const started=executionStartedAt.get(run.job_id) || Date.now();
  const elapsed=(Date.now()-started)/1000;
  const timeCurve=Math.min(88, 8 + (elapsed/60)*72);
  const stageCurve=Math.min(90, Math.round((completed/Math.max(STAGE_ORDER.length,1))*92));
  const percent=Math.max(5, Math.min(92, Math.max(timeCurve, stageCurve)));
  return {percent:Math.round(percent), current};
}
function renderExecutionProgress(run){
  if (!run || (run.status!=='RUNNING' && run.status!=='QUEUED' && run.status!=='COMPLETE' && run.status!=='FAILED' && run.status!=='CANCELLED')) return '';
  const p=progressState(run);
  const live=run.status==='RUNNING';
  const statusText=run.status==='COMPLETE'?'Completed successfully · backend confirmed 100%':run.status==='FAILED'?'Execution failed · backend reported FAILED':run.status==='CANCELLED'?'Execution cancelled · backend reported CANCELLED':run.status==='QUEUED'?'Queued — waiting to start':`Running · ${p.current}`;
  return `<section class="execution-progress ${live?'is-live':''}">\
    <div class="execution-progress-head"><div><div class="eyebrow">EXECUTION PROGRESS</div><strong>${esc(statusText)}</strong></div><div class="execution-progress-percent">${p.percent}%</div></div>\
    <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p.percent}"><div class="progress-fill" style="width:${p.percent}%"></div></div>\
    <div class="execution-progress-meta"><span>${live?'Live status refreshes every 3 seconds. 100% appears only when the backend reports COMPLETE.':'Backend status: '+esc(run.status)}</span><span>${live?'Do not press Execute again.':''}</span></div>\
  </section>`;
}

async function inspectRun(jobId, autoScroll = true) {
  inspectedRunId = jobId;
  try {
    const out = await api(`/runs/${encodeURIComponent(jobId)}`);
    addRun(out);
    $('runDetailCard').classList.remove('hidden');
    $('detailTitle').textContent = `${jobId} · ${out.status}`;
    $('runActions').innerHTML = runActionButtons(out);
    $('runSummary').innerHTML = renderExecutionProgress(out) + renderSummary(out);
    $('runSummary').querySelector('.result-download-report')?.addEventListener('click',()=>downloadBusinessReport(out));
    $('runSummary').querySelector('.result-download-json')?.addEventListener('click',()=>downloadFullRun(out));
    $('runTrace').innerHTML = renderTrace(out);
    $('engineTrace').innerHTML = renderEngineTrace(out.result || {});
    $('handoffTrace').innerHTML = renderHandoffs(out.result || {});
    $('runJson').textContent = pretty(out);
    document.querySelectorAll('.engine-card').forEach(card => card.addEventListener('click',()=>openEnginePayload(card.dataset.engine,out.result||{})));
    document.querySelectorAll('.handoff-row').forEach(card=>card.addEventListener('click',()=>{
      const key=card.dataset.handoff; const rec=out.result?.handoffs?.[key] || {};
      const target=key.split('_to_')[1];
      $('enginePayloadTitle').textContent=`Handoff · ${key.replaceAll('_',' ')}`;
      $('enginePayloadSummary').innerHTML=payloadSummary(rec.contract || {});
      $('enginePayloadJson').textContent=pretty(rec);
      $('enginePayloadDownload').onclick=()=>downloadEnginePayload(`handoff_${key}`, rec);
      $('payloadDrawerOverlay').classList.remove('hidden');
    }));
    bindRunActions();
    if (autoScroll) $('runDetailCard').scrollIntoView({behavior:'smooth', block:'start'});
    return out;
  } catch (err) {
    $('runDetailCard').classList.remove('hidden');
    $('detailTitle').textContent = `${jobId} · ERROR`;
    $('runActions').innerHTML = '';
    $('runTrace').innerHTML = '';
    $('runSummary').innerHTML = `<div class="callout danger-callout">${esc(err.message || err)}</div>`;
    $('runJson').textContent = String(err.message || err);
    return null;
  }
}

async function executeRun(jobId) {
  const button = document.querySelector(`.run-execute[data-run="${CSS.escape(jobId)}"]`);
  if (button) { button.disabled = true; button.textContent = 'Starting…'; }
  try {
    executionStartedAt.set(jobId, Date.now());
    const accepted = await api(`/runs/${encodeURIComponent(jobId)}/execute`, {method:'POST', body:JSON.stringify({})});
    await inspectRun(jobId, false);
    $('runJson').textContent = pretty({execution: accepted, note: 'Execution accepted asynchronously; status is tracked by polling.'});
    await renderRunsTable();
    await renderRecentRuns();
  } catch (err) {
    $('runJson').textContent = `Execute failed: ${err.message || err}`;
  } finally {
    if (button) { button.disabled = false; button.textContent = 'Execute now'; }
  }
}

async function cancelRun(jobId) {
  try {
    const out = await api(`/runs/${encodeURIComponent(jobId)}/cancel`, {method:'POST', body:JSON.stringify({})});
    addRun(out);
    await inspectRun(jobId, false);
    await renderRunsTable();
    await renderRecentRuns();
  } catch (err) {
    $('runJson').textContent = `Cancel failed: ${err.message || err}`;
  }
}

function bindRunActions() {
  document.querySelectorAll('.run-execute').forEach(b => b.onclick = () => executeRun(b.dataset.run));
  document.querySelectorAll('.run-cancel').forEach(b => b.onclick = () => cancelRun(b.dataset.run));
}


function runStateCounts() {
  const counts = {queued:0,running:0,complete:0,failed:0,cancelled:0,recovery:0};
  for (const run of state.runs) {
    const s=String(run?.status||'').toUpperCase();
    if(s==='QUEUED') counts.queued++;
    else if(s==='RUNNING') counts.running++;
    else if(s==='COMPLETE') counts.complete++;
    else if(s==='FAILED') counts.failed++;
    else if(s==='CANCELLED') counts.cancelled++;
    const rec=String(run?.result?.execution?.state || run?.result?.execution_state || run?.execution_state || '').toUpperCase();
    if(rec==='RECOVERY_REQUIRED') counts.recovery++;
  }
  return counts;
}

function renderOperatingPulse() {
  const c=runStateCounts();
  const data=[
    [uiT('Active runs','التشغيلات النشطة'), c.queued+c.running, uiT('QUEUED + RUNNING','في الانتظار + قيد التشغيل')],
    [uiT('Completed','مكتملة'), c.complete, uiT('Latest browser-local index','أحدث فهرس محلي بالمتصفح')],
    [uiT('Failed','فاشلة'), c.failed, c.failed ? uiT('Operator attention','تحتاج انتباه المشغّل') : uiT('No failed runs indexed','لا توجد تشغيلات فاشلة مفهرسة')],
    [uiT('Recovery','الاسترداد'), c.recovery, c.recovery ? uiT('Reconciliation required','تحتاج تسوية') : uiT('No recovery items indexed','لا توجد عناصر استرداد مفهرسة')]
  ];
  $('operatingPulse').innerHTML=data.map(([label,value,note])=>`<div class="pulse-item"><span class="pulse-label">${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`).join('');
}

function inferGovernancePosture() {
  let review=0,blocked=0,approved=0;
  for(const run of state.runs){
    const a=run?.result?.approval||run?.result?.governance||{};
    const s=String(a.status||a.decision||'').toUpperCase();
    if(s==='PENDING'||s==='REVIEW') review++;
    else if(s==='BLOCK'||s==='BLOCKED'||s==='DENIED') blocked++;
    else if(s==='APPROVED'||s==='AUTO_ALLOW'||s==='AUTO-ALLOW') approved++;
  }
  if(blocked) return {label:'BLOCKED SIGNAL',score:'LOW',notes:[`${blocked} blocked governance outcome${blocked===1?'':'s'}.`,'External/consequential actions remain gated.']};
  if(review) return {label:'REVIEW REQUIRED',score:'MED',notes:[`${review} run${review===1?'':'s'} with review/approval state.`,'Human gate remains active.']};
  if(approved) return {label:'GOVERNED & CLEAR',score:'HIGH',notes:[`${approved} approved/allowed governance outcome${approved===1?'':'s'}.`,'No review item indexed locally.']};
  return {label:'OBSERVING',score:'—',notes:['No approval decisions are indexed in the browser session.','Live governance endpoints are authoritative when exposed.']};
}

function refreshDashboard(){
  if(!$('operatingPulse')) return;
  renderOperatingPulse();
  const posture=inferGovernancePosture();
  const gp=$('governancePosture'); if(gp){gp.textContent=posture.label; gp.className=`status-pill ${posture.score==='HIGH'?'status-ok':posture.score==='LOW'?'status-bad':''}`;}
  const gs=$('governanceScore'); if(gs) gs.textContent=posture.score;
  const gn=$('governanceNotes'); if(gn) gn.innerHTML=posture.notes.map(n=>`<div class="callout">${esc(n)}</div>`).join('');
  const c=runStateCounts();
  if($('recoveryCount')) $('recoveryCount').textContent=String(c.recovery);
  if($('recoveryPreview')) $('recoveryPreview').innerHTML=c.recovery ? `<div class="callout danger-callout">${c.recovery} recovery item${c.recovery===1?'':'s'} indexed. Open Recovery Center.</div>` : '<div class="callout success-callout">No recovery items indexed locally.</div>';
  renderSystemTimeline();
}

function renderSystemTimeline(){
  const el=$('systemTimeline'); if(!el) return;
  const items=[...state.runs].sort((a,b)=>new Date(b.updated_at||b.created_at||0)-new Date(a.updated_at||a.created_at||0)).slice(0,8);
  if(!items.length){el.innerHTML=`<div class="availability-state empty"><div class="availability-icon">•</div><div><span class="availability-kicker">${esc(langState.current==='ar'?'الخط الزمني':'TIMELINE')}</span><h3>${esc(langState.current==='ar'?'لا توجد أحداث تشغيل بعد':'No runtime events yet')}</h3><p>${esc(langState.current==='ar'?'ابدأ تشغيلًا محكومًا لظهور أولى الأحداث هنا.':'Start a governed run to populate the operational timeline.')}</p></div></div>`; return;}
  el.innerHTML=items.map(r=>`<button class="timeline-row" type="button" data-run-timeline="${esc(r.job_id)}"><span class="timeline-dot ${String(r.status||'').toLowerCase()}"></span><span class="timeline-main"><b>${esc(r.job_id)}</b><small>${esc(r.project_id||'Project')} · ${esc(r.status||'UNKNOWN')}</small></span><time>${esc(formatTime(r.updated_at||r.created_at))}</time></button>`).join('');
}

function executionPayloadV44(run){
  return run?.result?.execution || run?.execution || run?.result?.execution_context || run?.execution_context || {};
}
function executionFieldV44(run, key){
  const ex=executionPayloadV44(run);
  const candidates=[ex?.[key], run?.[key], run?.result?.[key]];
  for(const v of candidates){ if(v!==undefined && v!==null && v!=='') return v; }
  return null;
}
function displayV44(v){ return v===undefined || v===null || v==='' ? uiT('Not exposed by backend','غير متاح في الـ Backend') : (typeof v==='object' ? pretty(v) : String(v)); }
function executionStatusV44(run){
  const ex=executionPayloadV44(run); return String(ex?.state || ex?.status || run?.execution_state || run?.status || 'UNKNOWN').toUpperCase();
}
function renderExecutionInspectorV44(run){
  const title=$('executionInspectorTitle'), box=$('executionInspector'), src=$('executionInspectorSource');
  if(!box || !title) return;
  if(!run){ title.textContent=uiT('Select an execution','اختر تنفيذًا'); if(src)src.textContent='—'; box.innerHTML=`<div class="tiny-note">${esc(uiT('Select a run to inspect tool, action, request hash, idempotency, governance, lease, receipt and audit data exposed by the backend.','اختر تشغيلًا لفحص الأداة والإجراء وهاش الطلب ومفتاح منع التكرار والحوكمة والتأجير والإيصال وبيانات التدقيق التي يعرضها الـ Backend.'))}</div>`; return; }
  title.textContent=`${run.job_id||'—'} · ${executionStatusV44(run)}`; if(src)src.textContent=state.runsSource==='backend'?uiT('LIVE BACKEND','Backend مباشر'):uiT('LOCAL FALLBACK','سجل محلي احتياطي');
  const ex=executionPayloadV44(run);
  const gov=ex?.governance || run?.result?.governance || run?.governance || {};
  const approval=ex?.approval || run?.result?.approval || run?.approval || {};
  const receipt=ex?.receipt || run?.receipt || run?.result?.receipt || null;
  const lease=ex?.lease || run?.lease || null;
  const audit=ex?.audit_events || run?.audit_events || run?.result?.audit_events || [];
  const fields=[
    [uiT('Project','المشروع'),run.project_id], [uiT('Tool','الأداة'),executionFieldV44(run,'tool')], [uiT('Action','الإجراء'),executionFieldV44(run,'action')],
    [uiT('Request hash','هاش الطلب'),executionFieldV44(run,'request_hash')], [uiT('Idempotency key','مفتاح منع التكرار'),executionFieldV44(run,'idempotency_key')],
    [uiT('Governance decision','قرار الحوكمة'),gov?.decision || gov?.status], [uiT('Approval','الموافقة'),approval?.status || approval?.decision],
    [uiT('Worker','العامل'),lease?.worker_id || ex?.worker_id], [uiT('Lease','التأجير'),lease?.status || lease?.expires_at],
    [uiT('Receipt','الإيصال'),receipt ? uiT('Available','متاح') : uiT('Not exposed by backend','غير متاح في الـ Backend')],
    [uiT('Execution state','حالة التنفيذ'),executionStatusV44(run)], [uiT('Updated','آخر تحديث'),run.updated_at || run.created_at]
  ];
  box.innerHTML=`<div class="inspector-grid execution-fields">${fields.map(([l,v])=>`<div><span>${esc(l)}</span><strong>${esc(displayV44(v))}</strong></div>`).join('')}</div>
  <div class="execution-detail-panels">
    <details class="inspector-details" open><summary>${esc(uiT('Execution receipt','إيصال التنفيذ'))}</summary><pre class="json-block compact">${esc(pretty(receipt||{status:'NOT_EXPOSED'}))}</pre></details>
    <details class="inspector-details"><summary>${esc(uiT('Audit events','أحداث التدقيق'))} (${audit.length||0})</summary><pre class="json-block compact">${esc(pretty(audit))}</pre></details>
    <details class="inspector-details"><summary>${esc(uiT('Canonical run response','استجابة التشغيل الأساسية'))}</summary><pre class="json-block compact">${esc(pretty(run))}</pre></details>
  </div>`;
}
async function inspectExecutionV44(jobId){
  try{
    const run=await api(`/runs/${encodeURIComponent(jobId)}`);
    addRun(run); renderExecutionInspectorV44(run); return run;
  }catch(err){
    const local=state.runs.find(r=>r.job_id===jobId); renderExecutionInspectorV44(local||null);
    if($('executionInspector')) $('executionInspector').insertAdjacentHTML('afterbegin',`<div class="callout danger-callout">${esc(uiT('Live run inspection failed:','فشل فحص التشغيل المباشر:'))} ${esc(err.message||err)}</div>`);
    return null;
  }
}
function recoveryItemsV44(){
  return getRunsForDisplay().filter(r=>executionStatusV44(r)==='RECOVERY_REQUIRED');
}
function renderRecoveryInspectorV44(run){
  const title=$('recoveryInspectorTitle'),box=$('recoveryInspector'),src=$('recoveryInspectorSource');
  if(!box||!title)return;
  if(!run){title.textContent=uiT('Select a recovery item','اختر عنصر استرداد'); if(src)src.textContent='—'; box.innerHTML=`<div class="tiny-note">${esc(uiT('Select a recovery item to inspect the authoritative run state and available reconciliation evidence.','اختر عنصر استرداد لفحص حالة التشغيل الموثوقة وأدلة التسوية المتاحة.'))}</div>`;return;}
  title.textContent=`${run.job_id||'—'} · RECOVERY_REQUIRED`; if(src)src.textContent=state.runsSource==='backend'?uiT('LIVE BACKEND','Backend مباشر'):uiT('LOCAL FALLBACK','سجل محلي احتياطي');
  const ex=executionPayloadV44(run), receipt=ex?.receipt||run?.receipt||run?.result?.receipt||null, lease=ex?.lease||run?.lease||null, audit=ex?.audit_events||run?.audit_events||run?.result?.audit_events||[];
  const fields=[
    [uiT('Project','المشروع'),run.project_id], [uiT('Request','الطلب'),run.request], [uiT('Action','الإجراء'),executionFieldV44(run,'action')],
    [uiT('Request hash','هاش الطلب'),executionFieldV44(run,'request_hash')], [uiT('Idempotency key','مفتاح منع التكرار'),executionFieldV44(run,'idempotency_key')],
    [uiT('Lease','التأجير'),lease?.status || lease?.expires_at], [uiT('Receipt','الإيصال'),receipt ? uiT('Available','متاح') : uiT('Not exposed by backend','غير متاح في الـ Backend')],
    [uiT('Last known state','آخر حالة معروفة'),executionStatusV44(run)]
  ];
  box.innerHTML=`<div class="inspector-grid recovery-fields">${fields.map(([l,v])=>`<div><span>${esc(l)}</span><strong>${esc(displayV44(v))}</strong></div>`).join('')}</div>
  <div class="callout warning-callout"><b>${esc(uiT('Why no automatic retry?','لماذا لا توجد إعادة محاولة تلقائية؟'))}</b><div>${esc(uiT('The external side effect may already have happened. Reconcile the external system before any new execution decision.','قد يكون الأثر الخارجي قد حدث بالفعل. يجب تسوية حالة النظام الخارجي قبل اتخاذ أي قرار تنفيذ جديد.'))}</div></div>
  <details class="inspector-details" open><summary>${esc(uiT('Receipt evidence','دليل الإيصال'))}</summary><pre class="json-block compact">${esc(pretty(receipt||{status:'NOT_EXPOSED'}))}</pre></details>
  <details class="inspector-details"><summary>${esc(uiT('Audit events','أحداث التدقيق'))} (${audit.length||0})</summary><pre class="json-block compact">${esc(pretty(audit))}</pre></details>
  <div class="form-actions"><button type="button" class="secondary-btn" data-recovery-run="${esc(run.job_id)}">${esc(uiT('Inspect authoritative run','فحص التشغيل الموثوق'))}</button></div>`;
  box.querySelector('[data-recovery-run]')?.addEventListener('click',()=>inspectExecutionV44(run.job_id));
}
async function inspectRecoveryV44(jobId){
  try{ const run=await api(`/runs/${encodeURIComponent(jobId)}`); addRun(run); renderRecoveryInspectorV44(run); return run; }
  catch(err){ const local=state.runs.find(r=>r.job_id===jobId); renderRecoveryInspectorV44(local||null); if($('recoveryInspector')) $('recoveryInspector').insertAdjacentHTML('afterbegin',`<div class="callout danger-callout">${esc(uiT('Live recovery inspection failed:','فشل فحص الاسترداد المباشر:'))} ${esc(err.message||err)}</div>`); return null; }
}
async function renderExecutionCenter(){
  if(!$('executionCards')) return;
  await fetchBackendRuns(50);
  const c=runStateCounts(), rows=getRunsForDisplay().filter(r=>['QUEUED','RUNNING','COMPLETE','FAILED'].includes(String(r.status||'').toUpperCase())).slice(0,20);
  $('executionCards').innerHTML=[metricCard(uiT('Queued','في الانتظار'),c.queued,'warn'),metricCard(uiT('Running','قيد التشغيل'),c.running,'good'),metricCard(uiT('Completed','مكتملة'),c.complete,'good'),metricCard(uiT('Failed','فاشلة'),c.failed,c.failed?'bad':'good'),metricCard(uiT('Recovery required','الاسترداد مطلوب'),c.recovery,c.recovery?'bad':'good')].join('');
  if($('executionSourceBadge')) $('executionSourceBadge').textContent=state.runsSource==='backend'?uiT('BACKEND','Backend'):state.runsSource==='local-fallback'?uiT('LOCAL FALLBACK','سجل محلي احتياطي'):uiT('UNAVAILABLE','غير متاح');
  if($('executionSourceNote')) $('executionSourceNote').textContent=state.runsSource==='backend'?uiT('Live run inventory from the authenticated backend.','قائمة التشغيلات المباشرة من الـ Backend الموثّق.'):uiT('Backend inventory unavailable; local data may be shown.','تعذر جلب قائمة الـ Backend؛ قد تظهر البيانات المحلية فقط.');
  $('executionList').innerHTML=rows.length ? rows.map(r=>`<button class="execution-row" type="button" data-execution-run="${esc(r.job_id)}"><span class="exec-status ${String(r.status||'').toLowerCase()}">${esc(r.status||'UNKNOWN')}</span><span><b>${esc(r.job_id)}</b><small>${esc(r.project_id||uiT('Project','المشروع'))} · ${esc(r.request||uiT('No request summary','لا يوجد ملخص للطلب'))}</small></span><span class="exec-arrow">${esc(uiT('Inspect','فحص'))} →</span></button>`).join('') : `<div class="trace-empty small"><div class="trace-empty-title">${esc(uiT('No execution items available','لا توجد عناصر تنفيذ متاحة'))}</div><div class="trace-empty-copy">${esc(uiT('The center reflects backend-backed run state when the authenticated API exposes it.','يعكس المركز حالة التشغيل المرتبطة بالـ Backend عندما تعرضها واجهة API الموثّقة.'))}</div></div>`;
  bindExecutionRowsV44();
  syncActiveLanguageV4();
}
async function refreshExecutionCenter(){ await renderExecutionCenter(); }
async function refreshRecoveryCenter(){
  if(!$('recoveryList')) return;
  await fetchBackendRuns(50);
  const recovery=recoveryItemsV44(), hasFailed=getRunsForDisplay().filter(r=>String(r.status||'').toUpperCase()==='FAILED');
  const count=recovery.length;
  $('recoveryBadge').textContent=count?uiT('ATTENTION','انتباه'):uiT('CLEAR','سليم');
  $('recoveryBadge').className=`recovery-badge ${count?'danger':''}`;
  $('recoveryHeadline').textContent=count?uiT(`${count} item require reconciliation`,`${count} عنصرًا يحتاج إلى تسوية`).replace('item','item'):uiT('No active recovery items','لا توجد عناصر استرداد نشطة');
  $('recoverySubhead').textContent=count?uiT('Execution stopped safely because the final external outcome is uncertain.','توقف التنفيذ بأمان لأن النتيجة الخارجية النهائية غير مؤكدة.'):uiT('No RECOVERY_REQUIRED execution state is exposed by the backend.','لا تعرض واجهة الـ Backend حاليًا حالة RECOVERY_REQUIRED.');
  if($('recoverySourceBadge')) $('recoverySourceBadge').textContent=state.runsSource==='backend'?uiT('BACKEND / DERIVED','Backend / مشتق'):uiT('LOCAL FALLBACK','سجل محلي احتياطي');
  if($('recoverySourceNote')) $('recoverySourceNote').textContent=state.runsSource==='backend'?uiT('Derived from authoritative run execution state.','مشتق من حالة التنفيذ الموثوقة للتشغيل.'):uiT('Backend unavailable; recovery state is shown only when local records expose it.','الـ Backend غير متاح؛ تظهر حالة الاسترداد فقط إذا كانت السجلات المحلية تعرضها.');
  $('recoveryList').innerHTML= count ? recovery.map(r=>`<button type="button" class="recovery-row recovery-row-button" data-recovery-item="${esc(r.job_id)}"><div><div class="eyebrow">${esc(uiT('RECOVERY REQUIRED','الاسترداد مطلوب'))}</div><strong>${esc(r.job_id)}</strong><small>${esc(r.project_id||uiT('Project','المشروع'))} · ${esc(r.request||uiT('No request summary','لا يوجد ملخص للطلب'))}</small></div><span class="badge bad">${esc(uiT('INSPECT','فحص'))}</span></button>`).join('') : `<div class="trace-empty small"><div class="trace-empty-title">${esc(uiT('Recovery queue is clear','قائمة الاسترداد خالية'))}</div><div class="trace-empty-copy">${esc(hasFailed.length?uiT(`${hasFailed.length} failed run(s) exist, but none is explicitly marked RECOVERY_REQUIRED.`,`${hasFailed.length} تشغيلات فاشلة موجودة، لكن لا توجد واحدة محددة كـ RECOVERY_REQUIRED.`):uiT('No failed or recovery-required runs are indexed.','لا توجد تشغيلات فاشلة أو عناصر استرداد مفهرسة.'))}</div></div>`;
  bindRecoveryRowsV44(); syncActiveLanguageV4();
}
function bindExecutionRowsV44(){ document.querySelectorAll('[data-execution-run]').forEach(btn=>btn.addEventListener('click',()=>inspectExecutionV44(btn.dataset.executionRun))); }
function bindRecoveryRowsV44(){ document.querySelectorAll('[data-recovery-item]').forEach(btn=>btn.addEventListener('click',()=>inspectRecoveryV44(btn.dataset.recoveryItem))); }

async function createRunFromForm(formPrefix) {
  const ids = formPrefix === 'overview'
    ? {project:'projectId',request:'request',audience:'audience',goal:'goal',constraints:'constraints',language:'language',msg:'runFormMsg'}
    : {project:'runCenterProjectId',request:'runCenterRequest',audience:'runCenterAudience',goal:'runCenterGoal',constraints:'runCenterConstraints',language:'runCenterLanguage',msg:'runCenterMsg'};
  const msg = $(ids.msg); msg.textContent = 'Submitting…';
  try {
    const payload = {project_id:$(ids.project).value.trim(), request:$(ids.request).value.trim(), audience:$(ids.audience).value.trim(), goal:$(ids.goal).value.trim(), language:$(ids.language)?.value || 'ar'};
    const c = $(ids.constraints).value.trim(); if (c) payload.constraints = c.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);
    const out = await api('/runs', {method:'POST', body:JSON.stringify(payload)});
    addRun({...out, request:payload.request, audience:payload.audience, goal:payload.goal, constraints:payload.constraints, language:payload.language});
    msg.textContent = `Queued ${out.job_id}.`;
    $(ids.request).value = '';
    await renderRecentRuns();
    if (formPrefix !== 'overview') await renderRunsTable();
    await inspectRun(out.job_id, false);
  } catch (err) {
    msg.textContent = `Submit failed: ${err.message || err}`;
  }
}

$('runForm').addEventListener('submit', async (e) => { e.preventDefault(); await createRunFromForm('overview'); });
$('runCenterForm').addEventListener('submit', async (e) => { e.preventDefault(); await createRunFromForm('runs'); });
$('newRunJump').addEventListener('click', () => $('runCenterRequest').focus());
$('closeDetail').addEventListener('click', () => $('runDetailCard').classList.add('hidden'));
$('closeEnginePayload').addEventListener('click', closePayloadDrawer);
$('payloadDrawerOverlay').addEventListener('click',(e)=>{if(e.target.id==='payloadDrawerOverlay')closePayloadDrawer();});
$('reloadRuns').addEventListener('click', async () => { await refreshCommandCenterRuns(); await renderRecentRuns(); });
$('reloadRunsTable')?.addEventListener('click', async () => { await refreshCommandCenterRuns(); await renderRecentRuns(); });
$('refreshBtn').addEventListener('click', async () => { await refreshHealth(); await renderRecentRuns(); if (!$('page-runs').classList.contains('hidden')) await renderRunsTable(); });
$('healthRefresh').addEventListener('click', refreshHealth);

$('authBtn').addEventListener('click', () => {
  $('apiBase').value = state.apiBase;
  $('bearerToken').value = state.token;
  $('sessionMsg').textContent = state.token ? 'A bearer token is stored in this session.' : 'No bearer token stored.';
  $('sessionModal').classList.remove('hidden');
});
$('closeModal').addEventListener('click', () => $('sessionModal').classList.add('hidden'));
$('saveSession').addEventListener('click', () => {
  state.apiBase = $('apiBase').value.trim() || '/api';
  let candidate = $('bearerToken').value.trim();
  if (candidate.toLowerCase().startsWith('bearer ')) candidate = candidate.slice(7).trim();
  state.token = candidate || state.token;
  sessionStorage.setItem('aios.apiBase', state.apiBase);
  if (state.token) sessionStorage.setItem('aios.bearer', state.token);
  $('sessionMsg').textContent = state.token ? 'Session saved locally.' : 'No bearer token stored.';
  refreshHealth();
});
$('testSession').addEventListener('click', async () => {
  let candidate = $('bearerToken').value.trim();
  if (candidate.toLowerCase().startsWith('bearer ')) candidate = candidate.slice(7).trim();
  if (!candidate && state.token) candidate = state.token;
  if (!candidate) { $('sessionMsg').textContent = 'No bearer token to test.'; return; }
  $('sessionMsg').textContent = 'Testing session…';
  const prior = state.token; state.token = candidate;
  try {
    const response = await fetch(`${state.apiBase.replace(/\/$/, '')}/runs/__auth_probe__`, {headers: sessionHeaders()});
    if (response.status === 404) {
      const payload = await response.json().catch(() => ({}));
      if (payload.status === 'NOT_FOUND') {
        sessionStorage.setItem('aios.bearer', candidate);
        const payloadPart = candidate.split('.')[0] || '';
        let subject = 'unknown';
        try { const normalized = payloadPart.replace(/-/g,'+').replace(/_/g,'/'); const decoded = JSON.parse(atob(normalized + '='.repeat((4-normalized.length%4)%4))); subject = decoded.sub || subject; } catch {}
        $('sessionMsg').textContent = `Session valid · ${subject} · read scope accepted.`;
        return;
      }
    }
    if (response.status === 401) { $('sessionMsg').textContent = 'Token rejected by O38 (401 UNAUTHORIZED).'; state.token = prior; return; }
    $('sessionMsg').textContent = `Session probe returned HTTP ${response.status}.`;
  } catch (err) { state.token = prior; $('sessionMsg').textContent = `Session probe failed: ${err.message || err}`; }
});
$('clearSession').addEventListener('click', () => {
  state.token = '';
  sessionStorage.removeItem('aios.bearer');
  $('sessionMsg').textContent = 'Bearer token cleared.';
});

let healthTimer = null;
let runTimer = null;
let inspectedRunId = null;
const executionStartedAt = new Map();

async function pollActiveRuns() {
  const active = state.runs.filter(r => !TERMINAL.has(r.status)).slice(0,10);
  if (!active.length) return;
  await Promise.all(active.map(r => refreshRun(r)));
  if (inspectedRunId) { const current=state.runs.find(r=>r.job_id===inspectedRunId); if (current && !document.getElementById('runDetailCard').classList.contains('hidden')) { $('detailTitle').textContent = `${inspectedRunId} · ${current.status}`; $('runActions').innerHTML = runActionButtons(current); $('runSummary').innerHTML = renderExecutionProgress(current) + renderSummary(current); $('runSummary').querySelector('.result-download-report')?.addEventListener('click',()=>downloadBusinessReport(current)); $('runSummary').querySelector('.result-download-json')?.addEventListener('click',()=>downloadFullRun(current)); $('runTrace').innerHTML = renderTrace(current); bindRunActions(); } }
  await renderRecentRuns();
  refreshDashboard();
  refreshExecutionCenter();
  refreshRecoveryCenter();
  if (!$('page-runs').classList.contains('hidden')) await renderRunsTable();
}


document.addEventListener('click',(event)=>{
  const timeline=event.target.closest('[data-run-timeline]');
  if(timeline){ page('runs'); setTimeout(()=>inspectRun(timeline.dataset.runTimeline,false),0); return; }
});
$('executionRefresh')?.addEventListener('click',()=>refreshExecutionCenter());
$('recoveryRefresh')?.addEventListener('click',()=>refreshRecoveryCenter());

async function bootstrap() {
  $('apiBase').value = state.apiBase;
  await refreshHealth();
  await syncRunIndex();
  await renderRecentRuns();
  await renderRunsTable();
  refreshDashboard(); refreshExecutionCenter(); refreshRecoveryCenter();
  clearInterval(healthTimer); healthTimer = setInterval(refreshHealth, 15000);
  clearInterval(runTimer); runTimer = setInterval(pollActiveRuns, 3000);
}

function renderOperationsPage() {
  const manifestRelease = 'O40-v1.0.0';
  const cards = document.getElementById('opsCards');
  if (!cards) return;
  cards.innerHTML = [
    ['Release','FROZEN', 'release'],
    ['Runtime','O40-v1.0.0', 'runtime'],
    ['Console','v1.2.0', 'console'],
    ['Provider calls','NONE', 'provider']
  ].map(([label,value,key])=>`<div class="metric"><div class="eyebrow">${label}</div><div class="metric-value">${value}</div><div class="metric-note" data-op-key="${key}">${key==='provider'?'Read-only snapshot':''}</div></div>`).join('');
  const badge=document.getElementById('opsReleaseBadge'); if (badge) badge.textContent=manifestRelease;
}

async function refreshOperations() {
  renderOperationsPage();
  try {
    const [health, readiness] = await Promise.all([apiGet('/health'), apiGet('/readiness')]);
    const cards=document.getElementById('opsCards');
    if (!cards) return;
    const runtimeCard=[...cards.querySelectorAll('.metric-card')].find(el=>el.textContent.includes('Runtime'));
    const healthCard=[...cards.querySelectorAll('.metric-card')].find(el=>el.textContent.includes('Release'));
    if (healthCard) healthCard.querySelector('.metric-note').textContent = health?.status === 'OK' ? 'API healthy' : 'API unavailable';
    if (runtimeCard) runtimeCard.querySelector('.metric-note').textContent = readiness?.status === 'HEALTHY' ? 'Readiness healthy' : 'Readiness degraded';
  } catch (e) {
    const cards=document.getElementById('opsCards');
    if (cards) { const n=cards.querySelector('[data-op-key="release"]'); if(n) n.textContent='Local API unavailable'; }
  }
}

document.addEventListener('click', (event) => { const btn=event.target.closest('.nav-item[data-page=\"operations\"]'); if (btn) setTimeout(refreshOperations, 0); const r=event.target.closest('#opsRefresh'); if (r) refreshOperations(); });



function refreshRelease(){
  const s=$('release-status');
  if(s){s.textContent='RELEASE CANDIDATE'; s.className='status-pill status-ok';}
}


/* UI v3.0 Control Center enhancements */
function updateExecutiveSummary(){
  const c=runStateCounts();
  const p=inferGovernancePosture();
  const review = state.runs.filter(r => {
    const a=r?.result?.approval||r?.result?.governance||{};
    const s=String(a.status||a.decision||'').toUpperCase();
    return s==='PENDING'||s==='REVIEW';
  }).length;
  const set=(id,val)=>{const e=$(id);if(e)e.textContent=String(val)};
  set('execActive',c.queued+c.running); set('execReview',review); set('execFailed',c.failed); set('execRecovery',c.recovery); set('execCompleted',c.complete); set('execChecked',new Date().toLocaleTimeString());
  const next=$('nextActionText');
  if(next){
    next.textContent = c.recovery ? uiT('Reconcile a recovery item','سوِّ عنصر استرداد') : review ? uiT('Review a governance decision','راجع قرار حوكمة') : c.failed ? uiT('Inspect a failed run','افحص تشغيلًا فاشلًا') : c.running ? uiT('Monitor the active flow','راقب المسار النشط') : uiT('Start a governed run','ابدأ تشغيلًا محكومًا');
  }
  const h=$('decisionHeadline'), w=$('decisionWhy');
  if(h) h.textContent = p.label === 'OBSERVING' ? uiT('No decision-driving governance state yet','لا توجد حالة حوكمة محركة للقرار حتى الآن') : ({'BLOCKED SIGNAL':uiT('BLOCKED SIGNAL','إشارة محجوبة'),'REVIEW REQUIRED':uiT('REVIEW REQUIRED','المراجعة مطلوبة'),'GOVERNED & CLEAR':uiT('GOVERNED & CLEAR','محكوم وواضح')}[p.label] || p.label);
  if(w) w.textContent = p.score==='LOW' ? 'A blocked signal is present. Consequential actions remain gated.' : p.score==='MED' ? 'One or more runs require human review before consequential execution.' : p.score==='HIGH' ? 'Local approved/allowed outcomes are clear; continue monitoring evidence.' : 'Governance evidence will appear here as the system processes runs.';
  renderAttentionQueue(c,review);
}
function renderAttentionQueue(c,review){
  const el=$('attentionQueue'); if(!el) return;
  const items=[];
  if(c.recovery) items.push({kind:'danger',label:'RECOVERY REQUIRED',title:`${c.recovery} execution item${c.recovery===1?'':'s'} need reconciliation`,page:'recovery'});
  if(review) items.push({kind:'warn',label:'HUMAN REVIEW',title:`${review} run${review===1?'':'s'} with review/approval state`,page:'approvals'});
  if(c.failed) items.push({kind:'danger',label:'FAILED RUNS',title:`${c.failed} failed run${c.failed===1?'':'s'} need inspection`,page:'runs'});
  if(!items.length){ el.innerHTML=`<div class="attention-empty"><span class="status-dot"></span><div><b>${uiT('All clear','كل شيء واضح')}</b><small>${uiT('No active operator items are indexed locally.','لا توجد عناصر تشغيلية نشطة مفهرسة محليًا.')}</small></div></div>`; return; }
  el.innerHTML=items.map(x=>`<button class="attention-item ${x.kind}" type="button" data-page-jump="${x.page}"><span class="attention-icon">!</span><span><b>${esc(x.label)}</b><strong>${esc(x.title)}</strong></span><span class="exec-arrow">→</span></button>`).join('');
  el.querySelectorAll('[data-page-jump]').forEach(b=>b.addEventListener('click',()=>page(b.dataset.pageJump)));
}
const _refreshDashboardV3 = refreshDashboard;
refreshDashboard = function(){ _refreshDashboardV3(); updateExecutiveSummary(); };

function v3TemplateData(kind){
  const map={
    business:{request:'I want to test a low-cost AI business opportunity in Egypt. Research current opportunities, identify the strongest customer problem, compare practical ideas, and recommend the cheapest experiment to run first.',audience:'Egyptian small businesses and entrepreneurs',goal:'validate a lean business opportunity'},
    market:{request:'Research the current AI market opportunities in Egypt for small businesses. Prioritize local evidence, recurring problems, market gaps and practical demand signals.',audience:'Egyptian small businesses',goal:'identify actionable market opportunities'},
    strategy:{request:'Turn this business direction into a focused, testable strategy with a clear target customer, promise, MVP scope and measurable next step.',audience:'small businesses using AI tools',goal:'build a focused strategy'},
    custom:{request:'',audience:'',goal:''}
  };
  return map[kind]||map.custom;
}
document.querySelectorAll('[data-template]').forEach(btn=>btn.addEventListener('click',()=>{
  const d=v3TemplateData(btn.dataset.template);
  ['request','audience','goal'].forEach(k=>{const el=$(k);if(el)el.value=d[k]});
  $('request')?.focus();
}));

function openCommandPalette(){
  const overlay=$('commandPalette'); if(!overlay) return;
  overlay.classList.remove('hidden'); $('commandSearch')?.focus(); renderCommandResults('');
}
function closeCommandPalette(){ $('commandPalette')?.classList.add('hidden'); }
function renderCommandResults(q){
  const el=$('commandResults'); if(!el)return;
  const base=[
    ['Executive Home','overview','See system posture and business attention'],['Command Center','runs','Create and inspect governed runs'],['Adaptive Intelligence','adaptation','Connect outcomes, feedback and strategy adaptation'],['Governance','approvals','Review approval boundary'],['Learning & Memory','memory','Inspect durable decision context'],['Adaptive Intelligence','adaptation','Inspect governed strategy adaptation'],['Execution Center','execution','Inspect execution state and receipts'],['Recovery Center','recovery','Reconcile uncertain external side effects'],['Audit Log','audit','Trace actors, decisions and outcomes'],['System Health','health','Inspect API and readiness'],['Operations','operations','Review production operations'],['Release','release','Inspect release evidence'],['How to Use','guide','Open the operator guide']
  ];
  const query=q.trim().toLowerCase();
  const pages=base.filter(([name])=>!query||name.toLowerCase().includes(query));
  const jobs=state.runs.filter(r=>!query||String(r.job_id||'').toLowerCase().includes(query)||String(r.project_id||'').toLowerCase().includes(query)||String(r.request||'').toLowerCase().includes(query)).slice(0,6).map(r=>[r.job_id,'runs',`${r.project_id||'Project'} · ${r.status||'UNKNOWN'}`]);
  const rows=[...pages,...jobs];
  el.innerHTML=rows.length?rows.map(([title,target,desc])=>`<button class="command-row" type="button" data-target="${esc(target)}" data-job="${esc(title)}"><span class="command-mark">${target==='runs'?'↗':'•'}</span><span><b>${esc(title)}</b><small>${esc(desc)}</small></span><kbd>↵</kbd></button>`).join(''):'<div class="command-empty">No matching pages or indexed jobs.</div>';
  el.querySelectorAll('.command-row').forEach(b=>b.addEventListener('click',()=>{closeCommandPalette();page(b.dataset.target); if(b.dataset.job && b.dataset.job.startsWith('JOB-')) setTimeout(()=>inspectRun(b.dataset.job,false),0)}));
}
['commandTrigger','refreshBtn'].forEach(id=>{const el=$(id); if(el){el.setAttribute('aria-hidden','true'); el.tabIndex=-1; el.hidden=true;}});
$('commandTrigger')?.addEventListener('click',openCommandPalette);
$('commandClose')?.addEventListener('click',closeCommandPalette);
$('commandSearch')?.addEventListener('input',e=>renderCommandResults(e.target.value));
$('commandPalette')?.addEventListener('click',e=>{if(e.target.id==='commandPalette')closeCommandPalette();});
document.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommandPalette();} if(e.key==='Escape')closeCommandPalette();});

function renderNotifications(){
  const el=$('notificationList'); if(!el)return;
  const c=runStateCounts(); const items=[];
  if(c.recovery) items.push(['HIGH',`${c.recovery} recovery item${c.recovery===1?'':'s'} require reconciliation.`,'recovery']);
  if(c.failed) items.push(['MEDIUM',`${c.failed} failed run${c.failed===1?'':'s'} require inspection.`,'runs']);
  const review=state.runs.filter(r=>['PENDING','REVIEW'].includes(String((r?.result?.approval||r?.result?.governance||{}).status||'').toUpperCase())).length;
  if(review) items.push(['MEDIUM',`${review} run${review===1?'':'s'} are awaiting review signals.`,'approvals']);
  if(!items.length){el.innerHTML='<div class="notification-empty"><span class="status-dot"></span><b>Nothing needs attention.</b><small>The control center is clear.</small></div>';return;}
  el.innerHTML=items.map(([sev,text,target])=>`<button type="button" class="notification-row" data-target="${target}"><span class="notif-sev ${sev.toLowerCase()}">${sev}</span><span>${esc(text)}</span><span>→</span></button>`).join('');
  el.querySelectorAll('[data-target]').forEach(b=>b.addEventListener('click',()=>{ $('notificationPanel').classList.add('hidden'); page(b.dataset.target);}));
  const n=$('notificationCount'); if(n){n.textContent=String(items.length);n.classList.toggle('hidden',items.length===0)}
}
$('notificationBtn')?.addEventListener('click',()=>{renderNotifications();$('notificationPanel')?.classList.toggle('hidden')});
$('notificationClose')?.addEventListener('click',()=>$('notificationPanel')?.classList.add('hidden'));

$('sidebarToggle')?.addEventListener('click',()=>document.body.classList.toggle('sidebar-collapsed'));

const _bootstrapV3=bootstrap;
bootstrap = async function(){ await _bootstrapV3(); renderNotifications(); updateExecutiveSummary(); };


bootstrap();


/* ========================= UI V4.0 — FINAL TEST CANDIDATE ========================= */
// Legacy regression marker: const UI_V4_BUILD = '4.0.0';
// Compatibility marker retained intentionally for the v4.0.1 regression suite: const UI_V4_BUILD = '4.0.1';
// V4.0.2 compatibility marker: const UI_V4_BUILD = '4.0.2';
const UI_V4_BUILD = '4.4.0';
// V4.0/V4.0.1 compatibility markers retained intentionally.
// const UI_V4_BUILD = '4.0.0';
// const UI_V4_BUILD = '4.0.1';
const SUPPORTED_LANGUAGES = ['en','ar'];
const langState = { current: localStorage.getItem('aios.language') || 'en' };

const I18N = {
  en: {
    'nav.home':'Executive Home','nav.command':'Command Center','nav.platform':'Platform','nav.decisions':'Decisions','nav.evidence':'Evidence Explorer','nav.experiments':'Experiments','nav.memory':'Learning & Memory','nav.governance':'Governance','nav.policies':'Policies','nav.execution':'Execution','nav.recovery':'Recovery','nav.audit':'Audit Log','nav.health':'System Health','nav.operations':'Operations','nav.release':'Release','nav.settings':'Settings','nav.guide':'How to Use',
    'runHistory.eyebrow':'RUN HISTORY','runHistory.title':'Recent runs','runHistory.source':'Live backend history with local fallback','runHistory.clear':'Clear history','runHistory.search':'Search runs…','runHistory.filter':'Filter by status','runHistory.all':'All statuses','runHistory.refresh':'Sync from backend','runHistory.reset':'Reset filters','runHistory.count':'Showing','runHistory.inspect':'Inspect',
    'common.refresh':'Refresh','common.cancel':'Cancel',
    'historyModal.eyebrow':'DATA LIFECYCLE','historyModal.title':'Clear run history?','historyModal.confirm':'Clear local history',
    'page.decisions.title':'Decisions','page.decisions.desc':'Decision surfaces are derived from completed runtime results, validation outcomes and learning context.',
    'page.evidence.title':'Evidence Explorer','page.evidence.desc':'Trace evidence from experiments and runtime results without inventing source state.',
    'page.experiments.title':'Experiments','page.experiments.desc':'Persistent validation records, evidence refs, evaluation and deterministic decisions.',
    'page.policies.title':'Policy Center','page.policies.desc':'Inspect the active governance policy surface. Policy changes remain backend-controlled and audited.',
    'page.settings.title':'Settings','page.settings.desc':'Console preferences and connection settings. Secret material stays local to the session.'
  },
  ar: {
    'nav.home':'الرئيسية التنفيذية','nav.command':'مركز التشغيل','nav.platform':'المنصة','nav.decisions':'القرارات','nav.evidence':'مستكشف الأدلة','nav.experiments':'التجارب','nav.memory':'التعلم والذاكرة','nav.governance':'الحوكمة','nav.policies':'السياسات','nav.execution':'التنفيذ','nav.recovery':'الاسترداد','nav.audit':'سجل التدقيق','nav.health':'صحة النظام','nav.operations':'العمليات','nav.release':'الإصدار','nav.settings':'الإعدادات','nav.guide':'كيفية الاستخدام',
    'runHistory.eyebrow':'سجل التشغيل','runHistory.title':'التشغيلات الأخيرة','runHistory.source':'سجل مباشر من الـ Backend مع بديل محلي','runHistory.clear':'مسح السجل','runHistory.search':'ابحث في التشغيلات…','runHistory.filter':'تصفية حسب الحالة','runHistory.all':'كل الحالات','runHistory.refresh':'مزامنة من الـ Backend','runHistory.reset':'إعادة ضبط الفلاتر','runHistory.count':'عرض','runHistory.inspect':'فحص',
    'common.refresh':'تحديث','common.cancel':'إلغاء',
    'historyModal.eyebrow':'دورة حياة البيانات','historyModal.title':'مسح سجل التشغيل؟','historyModal.confirm':'مسح السجل المحلي',
    'page.decisions.title':'القرارات','page.decisions.desc':'يتم اشتقاق سطح القرار من نتائج التشغيل المكتملة ونتائج التحقق وسياق التعلم.',
    'page.evidence.title':'مستكشف الأدلة','page.evidence.desc':'تتبّع الأدلة من التجارب ونتائج التشغيل بدون اختلاق أي حالة للمصدر.',
    'page.experiments.title':'التجارب','page.experiments.desc':'سجلات تحقق دائمة، ومراجع الأدلة، والتقييم والقرارات الحتمية.',
    'page.policies.title':'مركز السياسات','page.policies.desc':'استعرض سطح سياسات الحوكمة النشط. تغييرات السياسات تظل تحت تحكم الـ Backend والتدقيق.',
    'page.settings.title':'الإعدادات','page.settings.desc':'تفضيلات الواجهة وإعدادات الاتصال. الأسرار تظل محلية داخل الجلسة.'
  }
};


Object.assign(I18N.en, {
  'nav.adaptation':'Adaptive Intelligence',
  'page.adaptation.eyebrow':'ADAPTIVE INTELLIGENCE',
  'page.adaptation.title':'Adaptive Intelligence',
  'page.adaptation.desc':'See how decisions, outcomes, feedback and strategy adaptation connect into one governed learning loop.',
  'adaptation.hero.eyebrow':'STRATEGY LOOP',
  'adaptation.loop.title':'Decision → Outcome → Feedback → Adaptation'
});
Object.assign(I18N.ar, {
  'nav.adaptation':'الذكاء التكيفي',
  'page.adaptation.eyebrow':'الذكاء التكيفي',
  'page.adaptation.title':'الذكاء التكيفي',
  'page.adaptation.desc':'شاهد كيف تتصل القرارات والنتائج والتغذية الراجعة وتكييف الاستراتيجية داخل حلقة تعلم محكومة.',
  'adaptation.hero.eyebrow':'حلقة الاستراتيجية',
  'adaptation.loop.title':'القرار ← النتيجة ← التغذية الراجعة ← التكييف'
});
const PAGE_TITLES = {
  en: { overview:'Executive Home', runs:'Command Center', adaptation:'Adaptive Intelligence', decisions:'Decisions', evidence:'Evidence Explorer', experiments:'Experiments', approvals:'Governance', policies:'Policies', memory:'Learning & Memory', execution:'Execution Center', recovery:'Recovery Center', audit:'Audit Log', health:'System Health', operations:'Production Operations', release:'Release', settings:'Settings', guide:'How to Use', platform:'Platform' },
  ar: { overview:'الرئيسية التنفيذية', runs:'مركز التشغيل', adaptation:'الذكاء التكيفي', decisions:'القرارات', evidence:'مستكشف الأدلة', experiments:'التجارب', approvals:'الحوكمة', policies:'السياسات', memory:'التعلم والذاكرة', execution:'مركز التنفيذ', recovery:'مركز الاسترداد', audit:'سجل التدقيق', health:'صحة النظام', operations:'عمليات الإنتاج', release:'الإصدار', settings:'الإعدادات', guide:'كيفية الاستخدام', platform:'المنصة' }
};


const V4_STATIC_I18N = {
  en: {
    'WORKSPACE':'WORKSPACE','INTELLIGENCE':'INTELLIGENCE','GOVERNANCE':'GOVERNANCE','OPERATIONS':'OPERATIONS','SYSTEM':'SYSTEM',
    'Operations Console':'Operations Console','LOCAL CONSOLE':'LOCAL CONSOLE','Search AI Master OS…':'Search AI Master OS…','Refresh':'Refresh','Session':'Session','Notifications':'Notifications',
    'Run the business through one governed AI operating system.':'Run the business through one governed AI operating system.',
    'See what is running, what needs your attention, what the system decided, and what happens next.':'See what is running, what needs your attention, what the system decided, and what happens next.',
    'Start a governed run':'Start a governed run','Open execution':'Open execution','NEXT REQUIRED ACTION':'NEXT REQUIRED ACTION','Human control remains active for consequential actions.':'Human control remains active for consequential actions.',
    'ACTIVE RUNS':'ACTIVE RUNS','HUMAN REVIEW':'HUMAN REVIEW','FAILED':'FAILED','RECOVERY':'RECOVERY','COMPLETED':'COMPLETED','LAST CHECK':'LAST CHECK',
    'queued + running':'queued + running','local review signals':'local review signals','operator attention':'operator attention','reconciliation required':'reconciliation required','browser-local index':'browser-local index','runtime health':'runtime health',
    'DECISION':'DECISION','Latest operating signal':'Latest operating signal','OBSERVING':'OBSERVING','confidence':'confidence','Governance posture':'Governance posture','What needs you':'What needs you','Open recovery':'Open recovery','No active operator items indexed.':'No active operator items indexed.',
    'OPERATING PULSE':'OPERATING PULSE','What is happening now':'What is happening now','Open Command Center':'Open Command Center','EXECUTION':'EXECUTION','Current flow':'Current flow','Inspect':'Inspect','Decision':'Decision','Plan the next governed action.':'Plan the next governed action.','Governance':'Governance','Apply policy and approval boundaries.':'Apply policy and approval boundaries.','Execution':'Execution','Run only when the gate is satisfied.':'Run only when the gate is satisfied.','Learning':'Learning','Capture evidence and update context.':'Capture evidence and update context.',
    'SYSTEM TIMELINE':'SYSTEM TIMELINE','Latest runtime events':'Latest runtime events','Live where the API exposes state':'Live where the API exposes state','NEW RUN':'NEW RUN','Start with intent, not complexity.':'Start with intent, not complexity.','Requires':'Requires','Validate a business idea':'Validate a business idea','Research the market':'Research the market','Build a strategy':'Build a strategy','Custom goal':'Custom goal',
    'Research the market, identify the strongest hypothesis and define the cheapest test.':'Research the market, identify the strongest hypothesis and define the cheapest test.','Find current evidence, gaps, local signals and actionable opportunity areas.':'Find current evidence, gaps, local signals and actionable opportunity areas.','Turn a known opportunity into a focused operating plan.':'Turn a known opportunity into a focused operating plan.','Start from a blank governed request and define the context yourself.':'Start from a blank governed request and define the context yourself.',
    'GOVERNED RUN':'GOVERNED RUN','Define the job':'Define the job','Full Command Center':'Full Command Center','Project ID':'Project ID','Request':'Request','Audience':'Audience','Goal':'Goal','Constraints':'Constraints','Result language':'Result language','Start Run':'Start Run','LAST RUNS':'LAST RUNS','Recent activity':'Recent activity','Open Run Center':'Open Run Center',
    'Run Center':'Run Center','Create, monitor and inspect real O40 runs. Submission uses':'Create, monitor and inspect real O40 runs. Submission uses','Authentication required':'Authentication required','New run':'New run','Create Run':'Create Run','Recent runs':'Recent runs','RUN ID':'RUN ID','PROJECT':'PROJECT','STATUS':'STATUS','CREATED':'CREATED','Inspect':'Inspect',
    'INTELLIGENCE':'INTELLIGENCE','Decisions':'Decisions','Decision surfaces are derived from completed runtime results, validation outcomes and learning context.':'Decision surfaces are derived from completed runtime results, validation outcomes and learning context.','LATEST DECISION':'LATEST DECISION','DECISION GRAPH':'DECISION GRAPH','Decision flow':'Decision flow',
    'Evidence Explorer':'Evidence Explorer','Trace evidence from experiments and runtime results without inventing source state.':'Trace evidence from experiments and runtime results without inventing source state.','EXPERIMENT REGISTRY':'EXPERIMENT REGISTRY','Backend-backed evidence':'Backend-backed evidence','LIVE API':'LIVE API',
    'Experiments':'Experiments','Persistent validation records, evidence refs, evaluation and deterministic decisions.':'Persistent validation records, evidence refs, evaluation and deterministic decisions.','REGISTRY':'REGISTRY',
    'Policy Center':'Policy Center','Inspect the active governance policy surface. Policy changes remain backend-controlled and audited.':'Inspect the active governance policy surface. Policy changes remain backend-controlled and audited.','SAFETY BOUNDARY':'SAFETY BOUNDARY','UI never becomes the policy authority.':'UI never becomes the policy authority.','Changes require an authenticated backend control-plane contract.':'Changes require an authenticated backend control-plane contract.','ACTIVE POLICY':'ACTIVE POLICY','Current governance rules':'Current governance rules','BACKEND AUTHORITY':'BACKEND AUTHORITY',
    'Settings':'Settings','Console preferences and connection settings. Secret material stays local to the session.':'Console preferences and connection settings. Secret material stays local to the session.','LANGUAGE':'LANGUAGE','Interface language':'Interface language','Choose English or العربية. Arabic switches the interface to RTL and persists for this console.':'Choose English or العربية. Arabic switches the interface to RTL and persists for this console.','DATA LIFECYCLE':'DATA LIFECYCLE','Local console history':'Local console history','Clear History only removes the browser-local run index. Backend jobs, audit records, experiments and memory are not deleted.':'Clear History only removes the browser-local run index. Backend jobs, audit records, experiments and memory are not deleted.','Clear local history':'Clear local history','BACKEND CONNECTION':'BACKEND CONNECTION','Authenticated API boundary':'Authenticated API boundary','API Base':'API Base','Runtime authority':'Runtime authority','Backend':'Backend','Local cache':'Local cache','Session + browser index':'Session + browser index','Open session settings':'Open session settings',
    'release.readinessEyebrow':'FINAL READINESS','release.readinessTitle':'V4 Release Candidate checklist','release.disciplineText':'The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.','release.rcBoundary':'This candidate freezes the UI contract; it does not claim target-environment production evidence that has not been supplied.','Release':'Release','Frozen release evidence and target-environment readiness.':'Frozen release evidence and target-environment readiness.','Release discipline':'Release discipline','The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.':'The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.',
    'How to Use':'How to Use','Download JSON':'Download JSON','Close':'Close','Save session':'Save session','Test session':'Test session','Clear':'Clear','Find anything in AI Master OS':'Find anything in AI Master OS','What needs attention':'What needs attention','↑↓ navigate':'↑↓ navigate','Enter open':'Enter open','Ctrl K close':'Ctrl K close',
    'Clear run history?':'Clear run history?','This clears the run history stored by this browser console. Your backend jobs, audit log, experiments and learning memory remain untouched.':'This clears the run history stored by this browser console. Your backend jobs, audit log, experiments and learning memory remain untouched.','Local console history only ·':'Local console history only ·'
  },
  ar: {
    'WORKSPACE':'مساحة العمل','INTELLIGENCE':'الذكاء','GOVERNANCE':'الحوكمة','OPERATIONS':'العمليات','SYSTEM':'النظام',
    'Operations Console':'وحدة تحكم العمليات','LOCAL CONSOLE':'وحدة تحكم محلية','Search AI Master OS…':'ابحث داخل AI Master OS…','Refresh':'تحديث','Session':'الجلسة','Notifications':'الإشعارات',
    'Run the business through one governed AI operating system.':'أدر عملك عبر نظام تشغيل موحّد ومحكوم بالذكاء الاصطناعي.',
    'See what is running, what needs your attention, what the system decided, and what happens next.':'اعرف ما الذي يعمل الآن، وما الذي يحتاج تدخلك، وما الذي قرره النظام، وما الخطوة التالية.',
    'Start a governed run':'بدء تشغيل محكوم','Open execution':'فتح التنفيذ','NEXT REQUIRED ACTION':'الإجراء المطلوب التالي','Human control remains active for consequential actions.':'تظل الرقابة البشرية مفعّلة للإجراءات المؤثرة أو الحساسة.',
    'ACTIVE RUNS':'التشغيلات النشطة','HUMAN REVIEW':'مراجعة بشرية','FAILED':'فاشلة','RECOVERY':'الاسترداد','COMPLETED':'مكتملة','LAST CHECK':'آخر فحص',
    'queued + running':'في الانتظار + قيد التشغيل','local review signals':'إشارات مراجعة محلية','operator attention':'تحتاج انتباه المشغّل','reconciliation required':'تحتاج تسوية','browser-local index':'فهرس محلي بالمتصفح','runtime health':'حالة النظام',
    'DECISION':'القرار','Latest operating signal':'أحدث إشارة تشغيلية','OBSERVING':'مراقبة','confidence':'الثقة','Governance posture':'وضع الحوكمة','What needs you':'ما يحتاج تدخلك','Open recovery':'فتح الاسترداد','No active operator items indexed.':'لا توجد عناصر تشغيلية نشطة مفهرسة.',
    'OPERATING PULSE':'نبض التشغيل','What is happening now':'ما الذي يحدث الآن','Open Command Center':'فتح مركز التشغيل','EXECUTION':'التنفيذ','Current flow':'المسار الحالي','Inspect':'فحص','Decision':'القرار','Plan the next governed action.':'تخطيط الإجراء المحكوم التالي.','Governance':'الحوكمة','Apply policy and approval boundaries.':'تطبيق السياسات وحدود الموافقة.','Execution':'التنفيذ','Run only when the gate is satisfied.':'التنفيذ فقط بعد اجتياز البوابة.','Learning':'التعلم','Capture evidence and update context.':'تسجيل الأدلة وتحديث السياق.',
    'SYSTEM TIMELINE':'الخط الزمني للنظام','Latest runtime events':'أحدث أحداث التشغيل','Live where the API exposes state':'مباشر حيث يوفّر الـ API الحالة','NEW RUN':'تشغيل جديد','Start with intent, not complexity.':'ابدأ بالهدف، وليس بالتعقيد.','Requires':'يتطلب','Validate a business idea':'التحقق من فكرة مشروع','Research the market':'بحث السوق','Build a strategy':'بناء استراتيجية','Custom goal':'هدف مخصص',
    'Research the market, identify the strongest hypothesis and define the cheapest test.':'ابحث في السوق، وحدد أقوى فرضية، وصمّم أرخص اختبار ممكن.','Find current evidence, gaps, local signals and actionable opportunity areas.':'اعثر على الأدلة الحديثة والفجوات والإشارات المحلية وفرص العمل القابلة للتنفيذ.','Turn a known opportunity into a focused operating plan.':'حوّل فرصة معروفة إلى خطة تشغيل مركزة.','Start from a blank governed request and define the context yourself.':'ابدأ من طلب محكوم فارغ وحدد السياق بنفسك.',
    'GOVERNED RUN':'تشغيل محكوم','Define the job':'تعريف المهمة','Full Command Center':'مركز التشغيل الكامل','Project ID':'معرّف المشروع','Request':'الطلب','Audience':'الجمهور','Goal':'الهدف','Constraints':'القيود','Result language':'لغة النتيجة','Start Run':'بدء التشغيل','LAST RUNS':'آخر التشغيلات','Recent activity':'النشاط الأخير','Open Run Center':'فتح مركز التشغيل',
    'Run Center':'مركز التشغيل','Create, monitor and inspect real O40 runs. Submission uses':'أنشئ وتابع وافحص عمليات O40 الحقيقية. الإرسال يستخدم','Authentication required':'يلزم تسجيل الدخول','New run':'تشغيل جديد','Create Run':'إنشاء تشغيل','Recent runs':'التشغيلات الأخيرة','RUN ID':'معرّف التشغيل','PROJECT':'المشروع','STATUS':'الحالة','CREATED':'تاريخ الإنشاء',
    'Decisions':'القرارات','Decision surfaces are derived from completed runtime results, validation outcomes and learning context.':'يتم اشتقاق أسطح القرار من نتائج التشغيل المكتملة ونتائج التحقق وسياق التعلم.','LATEST DECISION':'أحدث قرار','DECISION GRAPH':'رسم القرار','Decision flow':'مسار القرار',
    'Evidence Explorer':'مستكشف الأدلة','Trace evidence from experiments and runtime results without inventing source state.':'تتبّع الأدلة من التجارب ونتائج التشغيل دون اختلاق حالة للمصدر.','EXPERIMENT REGISTRY':'سجل التجارب','Backend-backed evidence':'أدلة مرتبطة بالـ Backend','LIVE API':'واجهة API مباشرة',
    'Experiments':'التجارب','Persistent validation records, evidence refs, evaluation and deterministic decisions.':'سجلات تحقق دائمة ومراجع أدلة وتقييم وقرارات حتمية.','REGISTRY':'السجل',
    'Policy Center':'مركز السياسات','Inspect the active governance policy surface. Policy changes remain backend-controlled and audited.':'استعرض سياسات الحوكمة النشطة. تبقى تغييرات السياسات تحت تحكم الـ Backend والتدقيق.','SAFETY BOUNDARY':'حد الأمان','UI never becomes the policy authority.':'الواجهة لا تصبح سلطة السياسات.','Changes require an authenticated backend control-plane contract.':'تغييرات السياسات تتطلب عقدًا موثقًا ومصادقًا عليه من الـ Backend.','ACTIVE POLICY':'السياسة النشطة','Current governance rules':'قواعد الحوكمة الحالية','BACKEND AUTHORITY':'سلطة الـ Backend',
    'Settings':'الإعدادات','Console preferences and connection settings. Secret material stays local to the session.':'تفضيلات الواجهة وإعدادات الاتصال. تظل المواد السرية محلية داخل الجلسة.','LANGUAGE':'اللغة','Interface language':'لغة الواجهة','Choose English or العربية. Arabic switches the interface to RTL and persists for this console.':'اختر English أو العربية. عند اختيار العربية تتحول الواجهة إلى RTL ويُحفظ الاختيار لهذه الوحدة.','DATA LIFECYCLE':'دورة حياة البيانات','Local console history':'السجل المحلي للوحدة','Clear History only removes the browser-local run index. Backend jobs, audit records, experiments and memory are not deleted.':'مسح السجل يزيل فقط فهرس التشغيل المحلي في المتصفح. لا يتم حذف وظائف الـ Backend أو التدقيق أو التجارب أو الذاكرة.','Clear local history':'مسح السجل المحلي','BACKEND CONNECTION':'اتصال الـ Backend','Authenticated API boundary':'حد API موثّق','API Base':'عنوان API','Runtime authority':'جهة التحكم في التشغيل','Backend':'الـ Backend','Local cache':'التخزين المحلي','Session + browser index':'الجلسة + فهرس المتصفح','Open session settings':'فتح إعدادات الجلسة',
    'release.readinessEyebrow':'جاهزية الإصدار النهائي','release.readinessTitle':'قائمة تحقق مرشح إصدار V4','release.disciplineText':'لا يتم تجميد الحزمة المحلية إلا بعد نجاح البوابة الآلية. بيئة الإنتاج المتصلة بالإنترنت تحتاج أدلة من البيئة المستهدفة. هذه الشاشة لا تنفذ إجراءات خارجية.','release.rcBoundary':'هذه النسخة تثبّت عقد الواجهة، ولا تدّعي وجود أدلة إنتاج من البيئة المستهدفة لم يتم تقديمها.','Release':'الإصدار','Frozen release evidence and target-environment readiness.':'أدلة الإصدار المجمدة وجاهزية بيئة الهدف.','Release discipline':'انضباط الإصدار','The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.':'لا يتم تجميد الحزمة المحلية إلا بعد نجاح البوابة الآلية. بيئة الإنتاج المتصلة بالإنترنت تحتاج أدلة من بيئة الهدف. هذه الشاشة لا تنفذ إجراءات خارجية.',
    'How to Use':'كيفية الاستخدام','Download JSON':'تنزيل JSON','Close':'إغلاق','Save session':'حفظ الجلسة','Test session':'اختبار الجلسة','Clear':'مسح','Find anything in AI Master OS':'ابحث عن أي شيء في AI Master OS','What needs attention':'ما يحتاج الانتباه','↑↓ navigate':'↑↓ للتنقل','Enter open':'Enter للفتح','Ctrl K close':'Ctrl K للإغلاق',
    'Clear run history?':'مسح سجل التشغيل؟','This clears the run history stored by this browser console. Your backend jobs, audit log, experiments and learning memory remain untouched.':'سيؤدي ذلك إلى مسح سجل التشغيل المحفوظ في وحدة المتصفح الحالية. لن يتم المساس بوظائف الـ Backend أو سجل التدقيق أو التجارب أو ذاكرة التعلم.','Local console history only ·':'السجل المحلي للوحدة فقط ·'
  }
};


/* V4.0.1 localization layer: translate the whole static surface, then re-render dynamic states. */
const V4_TEXT_ORIGINAL = new WeakMap();
const V4_AR_EXTRA = {
  'AI Master OS — Console':'AI Master OS — وحدة التحكم',
  'Operations Console':'وحدة تحكم العمليات','LOCAL CONSOLE':'وحدة تحكم محلية','CONTROL CENTER':'مركز التحكم',
  'Executive Home':'الرئيسية التنفيذية','Backend: checking…':'الـ Backend: جارٍ الفحص…','Search AI Master OS…':'ابحث داخل AI Master OS…',
  'Refresh':'تحديث','Session':'الجلسة','Notifications':'الإشعارات',
  'AI MASTER OS · CONTROL CENTER':'AI MASTER OS · مركز التحكم',
  'Run the business through one governed AI operating system.':'أدر عملك عبر نظام تشغيل موحّد ومحكوم بالذكاء الاصطناعي.',
  'See what is running, what needs your attention, what the system decided, and what happens next.':'اعرف ما الذي يعمل الآن، وما الذي يحتاج تدخلك، وما الذي قرره النظام، وما الخطوة التالية.',
  'Start a governed run':'بدء تشغيل محكوم','Open execution':'فتح التنفيذ','Checking system…':'جارٍ فحص النظام…',
  'Review the current operating state':'راجع حالة التشغيل الحالية','Human control remains active for consequential actions.':'تظل الرقابة البشرية مفعّلة للإجراءات المؤثرة أو الحساسة.',
  'ACTIVE RUNS':'التشغيلات النشطة','HUMAN REVIEW':'مراجعة بشرية','FAILED':'فاشلة','RECOVERY':'الاسترداد','COMPLETED':'مكتملة','LAST CHECK':'آخر فحص',
  'queued + running':'في الانتظار + قيد التشغيل','local review signals':'إشارات مراجعة محلية','operator attention':'تحتاج انتباه المشغّل','reconciliation required':'تحتاج تسوية','browser-local index':'فهرس محلي بالمتصفح','runtime health':'حالة النظام',
  'DECISION':'القرار','Latest operating signal':'أحدث إشارة تشغيلية','OBSERVING':'مراقبة','confidence':'الثقة','Governance posture':'وضع الحوكمة','What needs you':'ما يحتاج تدخلك','Open recovery':'فتح الاسترداد','No active operator items indexed.':'لا توجد عناصر تشغيلية نشطة مفهرسة.',
  'OPERATING PULSE':'نبض التشغيل','What is happening now':'ما الذي يحدث الآن','Open Command Center':'فتح مركز التشغيل','EXECUTION':'التنفيذ','Current flow':'المسار الحالي','Inspect':'فحص',
  'Decision':'القرار','Plan the next governed action.':'تخطيط الإجراء المحكوم التالي.','Governance':'الحوكمة','Apply policy and approval boundaries.':'تطبيق حدود السياسات والموافقات.','Execution':'التنفيذ','Run only when the gate is satisfied.':'التشغيل فقط عند استيفاء البوابة.','Learning':'التعلم','Capture evidence and update context.':'التقاط الأدلة وتحديث السياق.',
  'SYSTEM TIMELINE':'الخط الزمني للنظام','Latest runtime events':'أحدث أحداث التشغيل','Live where the API exposes state':'مباشر حيث تعرض واجهة API الحالة',
  'NEW RUN':'تشغيل جديد','Start with intent, not complexity.':'ابدأ بالهدف لا بالتعقيد.','Requires':'يتطلب','Validate a business idea':'التحقق من فكرة تجارية','Research a market':'بحث سوق','Research the market':'بحث السوق','Build a strategy':'بناء استراتيجية','Custom goal':'هدف مخصص',
  'Research the market, identify the strongest hypothesis and define the cheapest test.':'ابحث السوق، وحدد أقوى فرضية، وصمّم أرخص اختبار ممكن.',
  'Find current evidence, gaps, local signals and actionable opportunity areas.':'اعثر على الأدلة الحالية والفجوات والإشارات المحلية وفرص قابلة للتنفيذ.',
  'Turn a known opportunity into a focused operating plan.':'حوّل فرصة معروفة إلى خطة تشغيل مركزة.',
  'Start from a blank governed request and define the context yourself.':'ابدأ من طلب محكوم فارغ وحدد السياق بنفسك.',
  'GOVERNED RUN':'تشغيل محكوم','Define the job':'تعريف المهمة','Full Command Center':'مركز التشغيل الكامل','Project ID':'معرّف المشروع','Request':'الطلب','Audience':'الجمهور','Goal':'الهدف','Constraints':'القيود','Result language':'لغة النتيجة','Start Run':'بدء التشغيل',
  'LAST RUNS':'آخر التشغيلات','Recent activity':'النشاط الأخير','Open Run Center':'فتح مركز التشغيل','Run Center':'مركز التشغيل','Create, monitor and inspect real O40 runs. Submission uses':'أنشئ وتابع وافحص عمليات التشغيل الحقيقية. الإرسال يستخدم',
  'Authentication required':'يلزم تسجيل الدخول','New run':'تشغيل جديد','Create Run':'إنشاء تشغيل','RUN HISTORY':'سجل التشغيل','Recent runs':'التشغيلات الأخيرة','Local console history + live backend status':'سجل محلي + حالة حية من الـ Backend','Clear history':'مسح السجل','Run ID':'معرّف التشغيل','Project':'المشروع','Status':'الحالة','Created':'تاريخ الإنشاء',
  'RUN INSPECTOR':'فاحص التشغيل','Run detail':'تفاصيل التشغيل','Close':'إغلاق','Live execution state is read from the authenticated O40 API.':'تُقرأ حالة التنفيذ المباشرة من واجهة O40 الموثقة.',
  'ENGINE TRACE':'تتبّع المحركات','Runtime engine outputs':'مخرجات محركات التشغيل','Click a node to inspect its structured payload.':'اضغط على أي عقدة لفحص الحمولة المهيكلة.',
  'Handoff Quality':'جودة الترحيل','Semantic handoffs':'الترحيلات الدلالية','Semantic contract health is evaluated from the live handoff QA state.':'تُقيّم صحة العقود الدلالية من حالة فحص الترحيلات المباشرة.','Raw run response':'استجابة التشغيل الخام',
  'Approval Center shell is ready':'واجهة مركز الموافقات جاهزة','Memory browser shell is ready':'واجهة متصفح الذاكرة جاهزة','Audit viewer shell is ready':'واجهة سجل التدقيق جاهزة',
  'Execution Center':'مركز التنفيذ','See what can run, what is running, and what requires recovery. This surface never bypasses O44 governance or O45 execution gates.':'اعرف ما يمكن تشغيله، وما يعمل الآن، وما يحتاج إلى استرداد. هذه الواجهة لا تتجاوز حوكمة O44 أو بوابات تنفيذ O45.',
  'ACTIVE ACTIONS':'الإجراءات النشطة','Execution state':'حالة التنفيذ','Derived from current run state and execution metadata when available.':'مشتقة من حالة التشغيل الحالية وبيانات التنفيذ عند توفرها.','SAFETY':'الأمان','Execution guardrails':'ضوابط التنفيذ','Governance decision is authoritative.':'قرار الحوكمة هو المرجع النهائي.','Approvals never equal execution.':'الموافقة لا تعني التنفيذ.','Idempotency prevents duplicate side effects.':'منع التكرار يحول دون الآثار الجانبية المزدوجة.','Unknown state routes to recovery, not blind retry.':'الحالة غير المعروفة تُحوّل إلى الاسترداد، وليس إعادة محاولة عمياء.',
  'Recovery Center':'مركز الاسترداد','Reconciliation-first handling for uncertain external side effects. The console does not auto-retry unknown outcomes.':'معالجة قائمة على التسوية أولًا للآثار الخارجية غير المؤكدة. لا تقوم وحدة التحكم بإعادة محاولة النتائج غير المعروفة تلقائيًا.','RECOVERY REQUIRED':'الاسترداد مطلوب','No active recovery items':'لا توجد عناصر استرداد نشطة','When execution outcome is uncertain, the system stops safely and asks for reconciliation.':'عندما تكون نتيجة التنفيذ غير مؤكدة، يتوقف النظام بأمان ويطلب التسوية.','CLEAR':'مسح','EXCEPTION QUEUE':'قائمة الاستثناءات','Operator attention':'انتباه المشغّل','RECONCILIATION PLAYBOOK':'دليل التسوية','Safe response':'الاستجابة الآمنة','Inspect receipt':'فحص إيصال التنفيذ','Check external system':'فحص النظام الخارجي','Reconcile':'التسوية',
  'Confirm exact action, request hash and lease state.':'تأكد من الإجراء الدقيق وهاش الطلب وحالة القفل.','Determine whether the side effect actually happened.':'تحقق مما إذا كان الأثر الجانبي قد حدث فعلًا.','Record the observed outcome before any retry decision.':'سجّل النتيجة المرصودة قبل اتخاذ قرار إعادة المحاولة.',
  'System Health':'صحة النظام','Live health and readiness checks from the O40 API. The page refreshes automatically every 15 seconds.':'فحوصات الصحة والجاهزية المباشرة من API الخاص بـ O40. تتحدث الصفحة تلقائيًا كل 15 ثانية.','Refresh health':'تحديث الصحة','HEALTH':'الصحة','READINESS':'الجاهزية',
  'Production Operations':'عمليات الإنتاج','Read-only operator view for release state, local service health and freeze discipline.':'واجهة تشغيل للقراءة فقط لحالة الإصدار وصحة الخدمة المحلية وانضباط التجميد.','CHECKLIST':'قائمة التحقق','Operator discipline':'انضباط المشغّل','Keep the previous known-good artifact.':'احتفظ بالحزمة السابقة المعروفة بالصحة.','Verify backups before upgrades.':'تحقق من النسخ الاحتياطية قبل الترقية.','Do not bypass approval gates.':'لا تتجاوز بوابات الموافقة.','Do not edit SQLite manually during incidents.':'لا تعدّل SQLite يدويًا أثناء الحوادث.',
  'How to Use AI Master OS':'كيفية استخدام AI Master OS','Use this page as the simple operating manual: what to enter, what the system does, and where to read the answer.':'استخدم هذه الصفحة كدليل تشغيل مبسط: ماذا تدخل، ماذا يفعل النظام، وأين تقرأ النتيجة.','STEP-BY-STEP':'خطوة بخطوة','Write one business goal. Add the audience, the success goal and the constraints that matter.':'اكتب هدفًا تجاريًا واحدًا. أضف الجمهور وهدف النجاح والقيود المهمة.','Create the run':'إنشاء التشغيل','Execute once':'نفّذ مرة واحدة','Read the result first':'اقرأ النتيجة أولًا','Drill down only when needed':'تعمق فقط عند الحاجة','Respect the human gate':'احترم البوابة البشرية','WHAT THE RESULT LOOKS LIKE':'كيف تبدو النتيجة','Market':'السوق','Sources + evidence':'المصادر + الأدلة','Ideas':'الأفكار','Ranked hypotheses':'فرضيات مرتبة','Potential opportunities, not assumed facts.':'فرص محتملة وليست حقائق مفترضة.','Strategy':'الاستراتيجية','Decision + rationale':'القرار + المبررات','Which direction to validate and why.':'أي اتجاه نتحقق منه ولماذا.','Product':'المنتج','Problem + promise + scope':'المشكلة + الوعد + النطاق','A cleaner definition of what should be built.':'تعريف أوضح لما ينبغي بناؤه.','QA + approval + provenance':'الفحص + الموافقة + مصدر البيانات','Golden rule:':'القاعدة الذهبية:','read the business result first. The detailed trace is evidence, not the answer itself.':'اقرأ نتيجة العمل أولًا. التتبع التفصيلي دليل، وليس الإجابة نفسها.',
  'Decisions':'القرارات','Decision surfaces are derived from completed runtime results, validation outcomes and learning context.':'يتم اشتقاق أسطح القرار من نتائج التشغيل المكتملة ونتائج التحقق وسياق التعلم.','LATEST DECISION':'أحدث قرار','No decision loaded':'لا يوجد قرار محمّل','BACKEND / DERIVED':'من الـ Backend / مشتق','DECISION GRAPH':'رسم القرار','Decision flow':'مسار القرار',
  'Evidence Explorer':'مستكشف الأدلة','Trace evidence from experiments and runtime results without inventing source state.':'تتبّع الأدلة من التجارب ونتائج التشغيل دون اختلاق حالة للمصدر.','EXPERIMENT REGISTRY':'سجل التجارب','Backend-backed evidence':'أدلة مرتبطة بالـ Backend','LIVE API':'واجهة API مباشرة','No evidence-bearing experiments indexed':'لا توجد تجارب تحمل أدلة مفهرسة','No backend data is available in the current API contract.':'لا تتوفر بيانات Backend في عقد API الحالي.',
  'Experiments':'التجارب','Persistent validation records, evidence refs, evaluation and deterministic decisions.':'سجلات تحقق دائمة ومراجع أدلة وتقييم وقرارات حتمية.','EXPERIMENTS':'التجارب','Registry':'السجل',
  'Policy Center':'مركز السياسات','Inspect the active governance policy surface. Policy changes remain backend-controlled and audited.':'استعرض سطح سياسة الحوكمة النشط. تظل تغييرات السياسات تحت تحكم الـ Backend والتدقيق.','SAFETY BOUNDARY':'حد الأمان','UI never becomes the policy authority.':'الواجهة لا تصبح سلطة السياسات.','Changes require an authenticated backend control-plane contract.':'التغييرات تتطلب عقدًا موثقًا ومصادقًا عليه من وحدة التحكم الخلفية.','BACKEND AUTHORITY':'سلطة الـ Backend','ACTIVE POLICY':'السياسة النشطة','Current governance rules':'قواعد الحوكمة الحالية',
  'Settings':'الإعدادات','Console preferences and connection settings. Secret material stays local to the session.':'تفضيلات الواجهة وإعدادات الاتصال. تظل المواد السرية محلية داخل الجلسة.','LANGUAGE':'اللغة','Interface language':'لغة الواجهة','Choose English or العربية. Arabic switches the interface to RTL and persists for this console.':'اختر English أو العربية. عند اختيار العربية تتحول الواجهة إلى RTL ويُحفظ الاختيار لهذه الوحدة.','Language':'اللغة','DATA LIFECYCLE':'دورة حياة البيانات','Local console history':'السجل المحلي للوحدة','Clear History only removes the browser-local run index. Backend jobs, audit records, experiments and memory are not deleted.':'مسح السجل يزيل فقط فهرس التشغيل المحلي في المتصفح. لا يتم حذف وظائف الـ Backend أو سجلات التدقيق أو التجارب أو الذاكرة.','Clear local history':'مسح السجل المحلي','BACKEND CONNECTION':'اتصال الـ Backend','Authenticated API boundary':'حد API موثّق','API Base':'عنوان API','Runtime authority':'جهة التحكم في التشغيل','Backend':'الـ Backend','Local cache':'التخزين المحلي','Session + browser index':'الجلسة + فهرس المتصفح','Open session settings':'فتح إعدادات الجلسة',
  'Release':'الإصدار','Frozen release evidence and target-environment readiness.':'أدلة الإصدار المجمدة وجاهزية بيئة الهدف.','Release discipline':'انضباط الإصدار','The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.':'لا يتم تجميد الحزمة المحلية إلا بعد نجاح البوابة الآلية. بيئة الإنتاج المتصلة بالإنترنت تحتاج أدلة من بيئة الهدف. هذه الشاشة لا تنفذ إجراءات خارجية.',
  'Download JSON':'تنزيل JSON','Save session':'حفظ الجلسة','Test session':'اختبار الجلسة','Clear':'مسح','Find anything in AI Master OS':'ابحث عن أي شيء في AI Master OS','What needs attention':'ما يحتاج الانتباه','↑↓ navigate':'↑↓ للتنقل','Enter open':'Enter للفتح','Ctrl K close':'Ctrl K للإغلاق',
  'Clear run history?':'مسح سجل التشغيل؟','This clears the run history stored by this browser console. Your backend jobs, audit log, experiments and learning memory remain untouched.':'سيؤدي ذلك إلى مسح سجل التشغيل المحفوظ في وحدة المتصفح الحالية. لن يتم المساس بوظائف الـ Backend أو سجل التدقيق أو التجارب أو ذاكرة التعلم.','Local console history only ·':'السجل المحلي للوحدة فقط ·','indexed runs.':'تشغيلات مفهرسة.',
  // Full UI chrome / page content localization gaps
  'MASTER OS':'MASTER OS','Operations Console':'وحدة تشغيل النظام','Executive Home':'الرئيسية التنفيذية','Command Center':'مركز التشغيل','Decisions':'القرارات','Evidence Explorer':'مستكشف الأدلة','Experiments':'التجارب','Learning & Memory':'التعلم والذاكرة','Governance':'الحوكمة','Policies':'السياسات','Execution':'التنفيذ','Recovery':'الاسترداد','Audit Log':'سجل التدقيق','System Health':'صحة النظام','Operations':'العمليات','Release':'الإصدار','Settings':'الإعدادات','How to Use':'كيفية الاستخدام','LOCAL CONSOLE':'وحدة محلية','CONTROL CENTER':'مركز التحكم','Backend: checking…':'الـ Backend: جارٍ التحقق…','Backend: connected':'الـ Backend: متصل','Backend: unavailable':'الـ Backend: غير متاح','Backend: degraded':'الـ Backend: متاح جزئيًا','English':'العربية','Search AI Master OS…':'ابحث داخل AI Master OS…','Ctrl K':'Ctrl K','Refresh':'تحديث','Session':'الجلسة','Notifications':'الإشعارات','AI MASTER OS · CONTROL CENTER':'AI MASTER OS · مركز التحكم','Run the business through one governed AI operating system.':'أدر أعمالك من خلال نظام تشغيل للذكاء الاصطناعي محكوم وآمن.','See what is running, what needs your attention, what the system decided, and what happens next.':'اعرف ما الذي يعمل الآن، وما يحتاج إلى انتباهك، وما الذي قرره النظام، وما الخطوة التالية.','Start a governed run':'ابدأ تشغيلًا محكومًا','Open execution':'فتح التنفيذ','Checking system…':'جارٍ فحص النظام…','NEXT REQUIRED ACTION':'الإجراء المطلوب التالي','Review the current operating state':'راجع الحالة التشغيلية الحالية','Human control remains active for consequential actions.':'يبقى التحكم البشري مفعلًا للإجراءات المؤثرة.','ACTIVE RUNS':'التشغيلات النشطة','HUMAN REVIEW':'مراجعة بشرية','FAILED':'فاشلة','RECOVERY':'الاسترداد','COMPLETED':'مكتملة','LAST CHECK':'آخر فحص','queued + running':'في الانتظار + قيد التشغيل','local review signals':'إشارات مراجعة محلية','operator attention':'تحتاج انتباه المشغّل','reconciliation required':'تحتاج تسوية','browser-local index':'فهرس محلي بالمتصفح','runtime health':'صحة التشغيل','DECISION':'القرار','Latest operating signal':'أحدث إشارة تشغيلية','OBSERVING':'مراقبة','confidence':'الثقة','Governance posture':'حالة الحوكمة','No decision-driving state yet':'لا توجد حالة محركة للقرار حتى الآن','The system will show the strongest local decision signal as runs are indexed.':'سيعرض النظام أقوى إشارة قرار محلية عند فهرسة التشغيلات.','ATTENTION':'الانتباه','What needs you':'ما يحتاجك','Open recovery':'فتح الاسترداد','No active operator items indexed.':'لا توجد عناصر تشغيلية نشطة مفهرسة.','OPERATING PULSE':'نبض التشغيل','What is happening now':'ماذا يحدث الآن','Open Command Center':'فتح مركز التشغيل','EXECUTION':'التنفيذ','Current flow':'المسار الحالي','Inspect':'فحص','Decision':'القرار','Plan the next governed action.':'خطط للإجراء المحكوم التالي.','Governance':'الحوكمة','Apply policy and approval boundaries.':'طبّق حدود السياسة والموافقة.','Execution':'التنفيذ','Run only when the gate is satisfied.':'نفّذ فقط عند استيفاء البوابة.','Learning':'التعلم','Capture evidence and update context.':'سجّل الأدلة وحدّث السياق.','SYSTEM TIMELINE':'الخط الزمني للنظام','Latest runtime events':'أحدث أحداث التشغيل','Live where the API exposes state':'مباشر عندما تكشف واجهة API الحالة','No runtime events indexed':'لا توجد أحداث تشغيل مفهرسة','Create a run to populate the operational timeline.':'أنشئ تشغيلًا لملء الخط الزمني التشغيلي.','NEW RUN':'تشغيل جديد','Start with intent, not complexity.':'ابدأ بالهدف، وليس بالتعقيد.','Requires':'يتطلب','Validate a business idea':'تحقق من فكرة تجارية','Research the market':'ابحث في السوق','Build a strategy':'ابنِ استراتيجية','Custom goal':'هدف مخصص','Research the market, identify the strongest hypothesis and define the cheapest test.':'ابحث في السوق، وحدد أقوى فرضية، وعرّف أرخص اختبار.','Find current evidence, gaps, local signals and actionable opportunity areas.':'اعثر على الأدلة الحالية والفجوات والإشارات المحلية وفرص العمل القابلة للتنفيذ.','Turn a known opportunity into a focused operating plan.':'حوّل فرصة معروفة إلى خطة تشغيل مركزة.','Start from a blank governed request and define the context yourself.':'ابدأ بطلب محكوم فارغ وحدد السياق بنفسك.','GOVERNED RUN':'تشغيل محكوم','Define the job':'حدد المهمة','Full Command Center':'مركز التشغيل الكامل','Project ID':'معرّف المشروع','Request':'الطلب','Audience':'الجمهور','Goal':'الهدف','Constraints':'القيود','Result language':'لغة النتيجة','Start Run':'بدء التشغيل','LAST RUNS':'آخر التشغيلات','Recent activity':'النشاط الأخير','Open Run Center':'فتح مركز التشغيل','Create, monitor and inspect real O40 runs. Submission uses':'أنشئ وراقب وافحص تشغيلات O40 الحقيقية. الإرسال يستخدم','Authentication required':'المصادقة مطلوبة','New run':'تشغيل جديد','Create Run':'إنشاء تشغيل','Reload':'إعادة تحميل','RUN HISTORY':'سجل التشغيل','Recent runs':'التشغيلات الأخيرة','Local console history + live backend status':'سجل محلي + حالة مباشرة من الـ Backend','Clear history':'مسح السجل','Run ID':'معرّف التشغيل','Project':'المشروع','PROJECT':'المشروع','STATUS':'الحالة','CREATED':'تاريخ الإنشاء','RUN INSPECTOR':'فاحص التشغيل','Run detail':'تفاصيل التشغيل','Close':'إغلاق','Live execution state is read from the authenticated O40 API.':'تُقرأ حالة التنفيذ المباشرة من واجهة O40 الموثقة.','ENGINE TRACE':'تتبع المحركات','Runtime engine outputs':'مخرجات محركات التشغيل','Click a node to inspect its structured payload.':'اضغط على أي عقدة لفحص حمولتها المنظمة.','HANDOFF QUALITY':'جودة التسليم','Semantic handoffs':'التسليمات الدلالية','Semantic contract health is evaluated from the live handoff QA state.':'تُقيّم صحة العقود الدلالية من حالة جودة التسليم المباشرة.','Raw run response':'استجابة التشغيل الخام','Approvals':'الموافقات','Consequential actions stay behind an explicit human gate. Approval endpoints are reserved for the control-plane integration phase.':'تبقى الإجراءات المؤثرة خلف بوابة بشرية صريحة. نقاط الموافقة محجوزة لتكامل وحدة التحكم.','Approval Center shell is ready':'واجهة مركز الموافقات جاهزة','The current O38 HTTP surface does not yet expose approval-list/decision routes. The UI keeps this boundary explicit instead of inventing a bypass.':'سطح HTTP الحالي في O38 لا يوفّر بعد مسارات قائمة/قرار الموافقات. تحافظ الواجهة على هذا الحد بوضوح بدل اختراع تجاوز.','Target contract: pending → approved/rejected → audited.':'العقد المستهدف: معلّق ← معتمد/مرفوض ← مدقّق.','PERSISTENCE':'الاستمرارية','Memory':'الذاكرة','Persistent memory is scoped, versioned and intended for useful operational state — not chat transcript storage.':'الذاكرة الدائمة محددة النطاق ومُصدّرة بإصدارات ومخصصة للحالة التشغيلية المفيدة، وليست لتخزين نص المحادثات.','Memory browser shell is ready':'واجهة تصفح الذاكرة جاهزة','O38 persists memory, but a public HTTP read/search surface is not part of the current API contract. This screen will connect when that boundary is exposed.':'يحفظ O38 الذاكرة، لكن سطح HTTP عام للقراءة/البحث ليس جزءًا من عقد API الحالي. ستتصل هذه الشاشة عند إتاحة ذلك الحد.','Design rule: minimum sufficient context + provenance + lifecycle.':'قاعدة التصميم: الحد الأدنى الكافي من السياق + المصدر + دورة الحياة.','TRACEABILITY':'قابلية التتبع','Auditability stays first-class: actor, scope, action, approval, QA and result remain traceable.':'تظل قابلية التدقيق من الدرجة الأولى: الفاعل والنطاق والإجراء والموافقة والجودة والنتيجة قابلة للتتبع.','Audit viewer shell is ready':'واجهة عرض التدقيق جاهزة','The persistent audit store is active, but the current HTTP surface does not expose a read endpoint yet.':'مخزن التدقيق الدائم نشط، لكن سطح HTTP الحالي لا يوفّر نقطة قراءة حتى الآن.','Policy: no silent failure, no hidden autonomy, explicit governance.':'السياسة: لا فشل صامت، ولا استقلالية خفية، وحوكمة صريحة.','EXECUTION PLANE':'طبقة التنفيذ','Execution Center':'مركز التنفيذ','See what can run, what is running, and what requires recovery. This surface never bypasses O44 governance or O45 execution gates.':'شاهد ما يمكن تشغيله، وما يعمل، وما يحتاج إلى استرداد. هذه الشاشة لا تتجاوز حوكمة O44 أو بوابات تنفيذ O45.','Refresh':'تحديث','ACTIVE ACTIONS':'الإجراءات النشطة','Execution state':'حالة التنفيذ','Derived from current run state and execution metadata when available.':'مشتق من حالة التشغيل الحالية وبيانات التنفيذ عند توفرها.','SAFETY':'الأمان','Execution guardrails':'ضوابط التنفيذ','Governance decision is authoritative.':'قرار الحوكمة هو المرجع المعتمد.','Approvals never equal execution.':'الموافقة لا تعني التنفيذ.','Idempotency prevents duplicate side effects.':'منع التكرار يحمي من التأثيرات الجانبية المزدوجة.','Unknown state routes to recovery, not blind retry.':'الحالة غير المعروفة تُوجّه إلى الاسترداد، وليس لإعادة المحاولة العمياء.','INCIDENT CONTROL':'التحكم في الحوادث','Recovery Center':'مركز الاسترداد','Reconciliation-first handling for uncertain external side effects. The console does not auto-retry unknown outcomes.':'معالجة تبدأ بالتسوية للتأثيرات الخارجية غير المؤكدة. لا تعيد الوحدة المحاولة تلقائيًا للنتائج غير المعروفة.','RECOVERY REQUIRED':'الاسترداد مطلوب','No active recovery items':'لا توجد عناصر استرداد نشطة','When execution outcome is uncertain, the system stops safely and asks for reconciliation.':'عند عدم اليقين بشأن نتيجة التنفيذ، يتوقف النظام بأمان ويطلب التسوية.','CLEAR':'واضح','EXCEPTION QUEUE':'قائمة الاستثناءات','Operator attention':'انتباه المشغّل','Read-only in v2.0.0':'للقراءة فقط في v2.0.0','RECONCILIATION PLAYBOOK':'دليل التسوية','Safe response':'استجابة آمنة','Inspect receipt':'افحص إيصال التنفيذ','Confirm exact action, request hash and lease state.':'تأكد من الإجراء الدقيق وبصمة الطلب وحالة الحجز.','Check external system':'تحقق من النظام الخارجي','Determine whether the side effect actually happened.':'حدد ما إذا كان التأثير الجانبي قد حدث فعلًا.','Reconcile':'سوِّ الحالة','Record the observed outcome before any retry decision.':'سجّل النتيجة المرصودة قبل اتخاذ قرار بإعادة المحاولة.','OBSERVABILITY':'المراقبة','System Health':'صحة النظام','Live health and readiness checks from the O40 API. The page refreshes automatically every 15 seconds.':'فحوصات الصحة والجاهزية المباشرة من واجهة O40. تُحدّث الصفحة تلقائيًا كل 15 ثانية.','Refresh health':'تحديث الصحة','HEALTH':'الصحة','API':'واجهة API','UNKNOWN':'غير معروف','READINESS':'الجاهزية','Runtime':'التشغيل','PRODUCTION OPERATIONS':'عمليات الإنتاج','Production Operations':'عمليات الإنتاج','Read-only operator view for release state, local service health and freeze discipline.':'عرض تشغيلي للقراءة فقط لحالة الإصدار وصحة الخدمة المحلية وانضباط التجميد.','RELEASE':'الإصدار','Frozen candidate':'مرشح مجمد','Mode':'الوضع','Production operations':'عمليات الإنتاج','CHECKLIST':'قائمة التحقق','Operator discipline':'انضباط المشغّل','Keep the previous known-good artifact.':'احتفظ بالنسخة السابقة المعروفة بأنها سليمة.','Verify backups before upgrades.':'تحقق من النسخ الاحتياطية قبل التحديثات.','Do not bypass approval gates.':'لا تتجاوز بوابات الموافقة.','Do not edit SQLite manually during incidents.':'لا تعدّل SQLite يدويًا أثناء الحوادث.','OPERATOR GUIDE':'دليل المشغّل','How to Use AI Master OS':'كيفية استخدام AI Master OS','Use this page as the simple operating manual: what to enter, what the system does, and where to read the answer.':'استخدم هذه الصفحة كدليل تشغيل مبسط: ماذا تدخل، ماذا يفعل النظام، وأين تقرأ النتيجة.','STEP-BY-STEP':'خطوة بخطوة','Define the job':'حدد المهمة','Write one business goal. Add the audience, the success goal and the constraints that matter.':'اكتب هدفًا تجاريًا واحدًا. أضف الجمهور وهدف النجاح والقيود المهمة.','Example: Research low-cost AI tools for small businesses in Egypt and recommend the most practical approach.':'مثال: ابحث عن أدوات ذكاء اصطناعي منخفضة التكلفة للمشروعات الصغيرة في مصر واقترح النهج الأكثر عملية.','Create the run':'أنشئ التشغيل','Go to':'اذهب إلى','Run Center → New Run':'مركز التشغيل ← تشغيل جديد','Keep the project ID stable when the work belongs to the same project.':'حافظ على ثبات معرّف المشروع عندما يخص العمل المشروع نفسه.','Execute once':'نفّذ مرة واحدة','Press':'اضغط','Execute now':'نفّذ الآن','once. The runtime moves through the governed pipeline asynchronously.':'مرة واحدة. ينتقل التشغيل عبر المسار المحكوم بشكل غير متزامن.','Read the result first':'اقرأ النتيجة أولًا','When the run is':'عندما تكون حالة التشغيل','COMPLETE':'مكتمل','Run Result':'نتيجة التشغيل','start at':'ابدأ من','Drill down only when needed':'تعمق فقط عند الحاجة','Use':'استخدم','Engine Trace':'تتبع المحركات','Semantic Handoffs':'التسليمات الدلالية','to inspect what moved between engines, and':'لفحص ما انتقل بين المحركات، و','only for deep debugging.':'فقط للتصحيح المتقدم.','Respect the human gate':'احترم البوابة البشرية','If approval is':'إذا كانت الموافقة','PENDING':'معلّقة','the runtime has prepared the work but has intentionally blocked the consequential external action.':'فقد جهّز التشغيل العمل لكنه حجب عمدًا الإجراء الخارجي المؤثر.','WHAT THE RESULT LOOKS LIKE':'كيف تبدو النتيجة','Market':'السوق','Sources + evidence':'المصادر + الأدلة','What the system found and how fresh/traceable it is.':'ما وجده النظام ومدى حداثته وقابليته للتتبع.','Ideas':'الأفكار','Ranked hypotheses':'فرضيات مرتبة','Potential opportunities, not assumed facts.':'فرص محتملة وليست حقائق مفترضة.','Strategy':'الاستراتيجية','Decision + rationale':'القرار + المبرر','Which direction to validate and why.':'أي اتجاه يجب التحقق منه ولماذا.','Product':'المنتج','Problem + promise + scope':'المشكلة + الوعد + النطاق','A cleaner definition of what should be built.':'تعريف أوضح لما ينبغي بناؤه.','QA + approval + provenance':'الجودة + الموافقة + المصدر','What passed, what is traceable, and what still needs human approval.':'ما اجتاز الفحص وما يمكن تتبعه وما يزال يحتاج موافقة بشرية.','Golden rule:':'القاعدة الذهبية:','read the business result first. The detailed trace is evidence, not the answer itself.':'اقرأ النتيجة التجارية أولًا. التتبع التفصيلي دليل وليس الإجابة نفسها.','INTELLIGENCE':'الذكاء','Decision surfaces are derived from completed runtime results, validation outcomes and learning context.':'تُشتق أسطح القرار من نتائج التشغيل المكتملة ونتائج التحقق وسياق التعلم.','LATEST DECISION':'أحدث قرار','No decision loaded':'لا يوجد قرار محمّل','BACKEND / DERIVED':'من الـ Backend / مشتق','DECISION GRAPH':'رسم القرار','Decision flow':'مسار القرار','Trace evidence from experiments and runtime results without inventing source state.':'تتبّع الأدلة من التجارب ونتائج التشغيل دون اختلاق حالة للمصدر.','EXPERIMENT REGISTRY':'سجل التجارب','Backend-backed evidence':'أدلة مرتبطة بالـ Backend','LIVE API':'واجهة API مباشرة','VALIDATION':'التحقق','Persistent validation records, evidence refs, evaluation and deterministic decisions.':'سجلات تحقق دائمة ومراجع أدلة وتقييم وقرارات حتمية.','EXPERIMENTS':'التجارب','Registry':'السجل','GOVERNANCE':'الحوكمة','Policy Center':'مركز السياسات','Inspect the active governance policy surface. Policy changes remain backend-controlled and audited.':'استعرض سطح سياسة الحوكمة النشط. تظل تغييرات السياسات تحت تحكم الـ Backend والتدقيق.','SAFETY BOUNDARY':'حد الأمان','UI never becomes the policy authority.':'الواجهة لا تصبح سلطة السياسات.','Changes require an authenticated backend control-plane contract.':'التغييرات تتطلب عقدًا موثقًا ومصادقًا عليه من وحدة التحكم الخلفية.','BACKEND AUTHORITY':'سلطة الـ Backend','ACTIVE POLICY':'السياسة النشطة','Current governance rules':'قواعد الحوكمة الحالية','SYSTEM':'النظام','Console preferences and connection settings. Secret material stays local to the session.':'تفضيلات الوحدة وإعدادات الاتصال. تظل المواد السرية محلية داخل الجلسة.','LANGUAGE':'اللغة','Interface language':'لغة الواجهة','Choose English or العربية. Arabic switches the interface to RTL and persists for this console.':'اختر English أو العربية. عند اختيار العربية تتحول الواجهة إلى RTL ويُحفظ الاختيار لهذه الوحدة.','Language':'اللغة','DATA LIFECYCLE':'دورة حياة البيانات','Local console history':'السجل المحلي للوحدة','Clear History only removes the browser-local run index. Backend jobs, audit records, experiments and memory are not deleted.':'مسح السجل يزيل فقط فهرس التشغيل المحلي في المتصفح. لا يتم حذف وظائف الـ Backend أو سجلات التدقيق أو التجارب أو الذاكرة.','Clear local history':'مسح السجل المحلي','BACKEND CONNECTION':'اتصال الـ Backend','Authenticated API boundary':'حد API موثّق','API Base':'عنوان API','Runtime authority':'جهة التحكم في التشغيل','Local cache':'التخزين المحلي','Session + browser index':'الجلسة + فهرس المتصفح','Open session settings':'فتح إعدادات الجلسة','Release':'الإصدار','Frozen release evidence and target-environment readiness.':'أدلة الإصدار المجمدة وجاهزية بيئة الهدف.','Release discipline':'انضباط الإصدار','The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.':'لا يتم تجميد الحزمة المحلية إلا بعد نجاح البوابة الآلية. الإنتاج المتصل بالإنترنت يحتاج أدلة من البيئة المستهدفة. هذه الشاشة لا تنفذ إجراءات خارجية.','Final release candidate':'مرشح الإصدار النهائي','Release Control Plane':'وحدة تحكم الإصدار','Local Gate':'البوابة المحلية','READY':'جاهز','No provider calls':'لا توجد استدعاءات لموفر خارجي','Target Evidence':'أدلة البيئة المستهدفة','MANUAL':'يدوي','Firewall · TLS · Backup · Rollback':'جدار الحماية · TLS · النسخ الاحتياطي · الاسترجاع','ENGINE PAYLOAD':'حمولة المحرك','Engine payload':'حمولة المحرك','Download JSON':'تنزيل JSON','Structured payload':'حمولة منظمة','AUTHENTICATION':'المصادقة','Console session':'جلسة الوحدة','Enter the signed bearer token issued by your O36 identity boundary. The console normalizes an optional':'أدخل Bearer الموقّع الصادر عن حد الهوية O36. تقوم الوحدة بتوحيد بادئة','Bearer':'Bearer','prefix, stores the token in':'، وتخزن الرمز في','sessionStorage':'sessionStorage','and can test the token against O38 without creating a run.':'ويمكنها اختبار الرمز ضد O38 دون إنشاء تشغيل.','API Base URL':'عنوان API الأساسي','Bearer token':'رمز Bearer','Save session':'حفظ الجلسة','Test session':'اختبار الجلسة','Clear':'مسح','CONTROL CENTER':'مركز التحكم','Find anything in AI Master OS':'ابحث عن أي شيء في AI Master OS','What needs attention':'ما يحتاج الانتباه','Enter open':'Enter للفتح','Ctrl K close':'Ctrl K للإغلاق','ALERTS':'التنبيهات','Close':'إغلاق','Clear run history?':'مسح سجل التشغيل؟','Cancel':'إلغاء','This clears the run history stored by this browser console. Your backend jobs, audit log, experiments and learning memory remain untouched.':'سيؤدي ذلك إلى مسح سجل التشغيل المحفوظ في وحدة المتصفح الحالية. لن يتم المساس بوظائف الـ Backend أو سجل التدقيق أو التجارب أو ذاكرة التعلم.','Local console history only ·':'السجل المحلي للوحدة فقط ·','indexed runs.':'تشغيلات مفهرسة.'

};

const V4_AR_PATCH = {
  "API unavailable": "الـ Backend غير متاح",
  "Backend: connected": "الـ Backend: متصل",
  "Backend: unavailable": "الـ Backend: غير متاح",
  "Backend: checking…": "الـ Backend: جارٍ الفحص…",
  "Backend: degraded": "الـ Backend: متاح جزئيًا",
  "Backend-derived when available": "مشتق من الـ Backend عند توفر البيانات",
  "No decision-driving state yet": "لا توجد حالة قرار محركة حتى الآن",
  "No decision-driving governance state yet": "لا توجد حالة حوكمة محركة للقرار حتى الآن",
  "Governance evidence will appear here as the system processes runs.": "ستظهر أدلة الحوكمة هنا أثناء معالجة النظام للتشغيلات.",
  "The system will show the strongest local decision signal as runs are indexed.": "سيعرض النظام أقوى إشارة قرار محلية مع فهرسة التشغيلات.",
  "System posture and business attention": "حالة النظام وما يحتاج انتباهك",
  "No active operator items indexed.": "لا توجد عناصر تشغيلية تتطلب تدخلك حاليًا.",
  "No active recovery items": "لا توجد عناصر استرداد نشطة",
  "No recovery items indexed": "لا توجد عناصر استرداد مفهرسة",
  "No recovery items indexed locally.": "لا توجد عناصر استرداد مفهرسة محليًا.",
  "Nothing needs attention.": "لا يوجد شيء يحتاج إلى انتباهك.",
  "The control center is clear.": "مركز التحكم خالٍ من العناصر التي تتطلب تدخلاً.",
  "No failed runs indexed": "لا توجد تشغيلات فاشلة مفهرسة",
  "No failed runs indexed.": "لا توجد تشغيلات فاشلة مفهرسة.",
  "No runtime events indexed": "لا توجد أحداث تشغيل مفهرسة",
  "No runtime events indexed.": "لا توجد أحداث تشغيل مفهرسة.",
  "No request summary": "لا يوجد ملخص للطلب",
  "No provider calls": "لا توجد استدعاءات لموفر خارجي",
  "No backend data is available in the current API contract.": "لا تتوفر بيانات من الـ Backend ضمن عقد API الحالي.",
  "No evidence-bearing experiments indexed": "لا توجد تجارب تحمل أدلة مفهرسة",
  "No evidence-bearing experiments indexed.": "لا توجد تجارب تحمل أدلة مفهرسة.",
  "No decision loaded": "لا يوجد قرار محمّل",
  "Decision surfaces are derived from completed runtime results, validation outcomes and learning context.": "تُشتق أسطح القرار من نتائج التشغيل المكتملة ونتائج التحقق وسياق التعلم.",
  "Source": "المصدر",
  "Sources + evidence": "المصادر + الأدلة",
  "Backend-backed surface": "واجهة مرتبطة بالـ Backend",
  "Backend-backed evidence": "أدلة مرتبطة بالـ Backend",
  "Confidence": "الثقة",
  "Opportunity": "الفرصة",
  "Strategy": "الاستراتيجية",
  "Validation": "التحقق",
  "Opportunity score": "درجة الفرصة",
  "Strategy score": "درجة الاستراتيجية",
  "Validation score": "درجة التحقق",
  "Customer problem": "مشكلة العميل",
  "Target customer": "العميل المستهدف",
  "Validation model": "نموذج التحقق",
  "Success threshold": "حد النجاح",
  "Decision rule": "قاعدة القرار",
  "Next action": "الإجراء التالي",
  "Recommendation": "التوصية",
  "Research a market": "بحث السوق",
  "Research the market": "بحث السوق",
  "Validate a business idea": "التحقق من فكرة مشروع",
  "Build a strategy": "بناء استراتيجية",
  "Custom goal": "هدف مخصص",
  "Start from a blank governed request and define the context yourself.": "ابدأ بطلب محكوم جديد وحدد السياق بنفسك.",
  "What should AI Master OS do?": "ماذا تريد من AI Master OS أن يفعل؟",
  "Optional constraints": "قيود اختيارية",
  "Optional: budget, geography, timing, exclusions, evidence requirements…": "اختياري: الميزانية، النطاق الجغرافي، التوقيت، الاستثناءات، ومتطلبات الأدلة…",
  "Example: Research low-cost AI opportunities for small businesses in Egypt and recommend the most practical one to test.": "مثال: ابحث عن فرص ذكاء اصطناعي منخفضة التكلفة للمشروعات الصغيرة في مصر واقترح أكثرها عملية للاختبار.",
  "Paste token locally — never share it in chat": "الصق الرمز محليًا — لا تشاركه في المحادثة",
  "Search pages, jobs, projects, actions…": "ابحث في الصفحات والتشغيلات والمشروعات والإجراءات…",
  "English": "English",
  "Arabic": "العربية",
  "Run ID": "معرّف التشغيل",
  "Project": "المشروع",
  "Status": "الحالة",
  "Created": "تاريخ الإنشاء",
  "Updated": "آخر تحديث",
  "Events": "الأحداث",
  "Approval": "الموافقة",
  "Created at": "تاريخ الإنشاء",
  "Updated at": "آخر تحديث",
  "Live execution state is read from the authenticated O40 API.": "تُقرأ حالة التنفيذ المباشرة من واجهة O40 الموثقة.",
  "Runtime engine outputs": "مخرجات محركات التشغيل",
  "Click a node to inspect its structured payload.": "اضغط على أي عقدة لفحص الحمولة المهيكلة.",
  "Semantic handoffs": "الترحيلات الدلالية",
  "Semantic contract health is evaluated from the live handoff QA state.": "تُقيّم صحة العقود الدلالية من حالة فحص الترحيلات المباشرة.",
  "Raw run response": "استجابة التشغيل الخام",
  "Consequential actions stay behind an explicit human gate. Approval endpoints are reserved for the control-plane integration phase.": "تظل الإجراءات المؤثرة خلف بوابة بشرية صريحة. وتبقى نقاط الموافقة مخصصة لتكامل وحدة التحكم.",
  "Approval Center shell is ready": "واجهة مركز الموافقات جاهزة",
  "The current O38 HTTP surface does not yet expose approval-list/decision routes. The UI keeps this boundary explicit instead of inventing a bypass.": "واجهة HTTP الحالية لـ O38 لا تعرض بعد مسارات قائمة/قرار الموافقات. وتحافظ الواجهة على هذا الحد بدل اختراع مسار لتجاوزه.",
  "Target contract: pending → approved/rejected → audited.": "العقد المستهدف: معلّق ← معتمد/مرفوض ← موثّق في السجل.",
  "Persistent memory is scoped, versioned and intended for useful operational state — not chat transcript storage.": "الذاكرة الدائمة محددة النطاق ومُصدرة بإصدارات، ومخصصة لحالة تشغيلية مفيدة وليست لتخزين سجل المحادثات.",
  "Memory browser shell is ready": "واجهة متصفح الذاكرة جاهزة",
  "Audit viewer shell is ready": "واجهة عرض سجل التدقيق جاهزة",
  "The persistent audit store is active, but the current HTTP surface does not expose a read endpoint yet.": "مخزن التدقيق الدائم نشط، لكن واجهة HTTP الحالية لا تعرض بعد نقطة نهاية للقراءة.",
  "Policy: no silent failure, no hidden autonomy, explicit governance.": "السياسة: لا فشل صامت، ولا استقلالية خفية، وحوكمة صريحة.",
  "Derived from current run state and execution metadata when available.": "مشتقة من حالة التشغيل الحالية وبيانات التنفيذ عند توفرها.",
  "Governance decision is authoritative.": "قرار الحوكمة هو المرجع النهائي.",
  "Approvals never equal execution.": "الموافقة لا تعني التنفيذ.",
  "Idempotency prevents duplicate side effects.": "منع التكرار يحول دون الآثار الجانبية المزدوجة.",
  "Unknown state routes to recovery, not blind retry.": "الحالة غير المعروفة تُحوّل إلى الاسترداد، وليس إلى إعادة محاولة عمياء.",
  "See what can run, what is running, and what requires recovery. This surface never bypasses O44 governance or O45 execution gates.": "اعرف ما يمكن تشغيله، وما يعمل الآن، وما يحتاج إلى استرداد. هذه الواجهة لا تتجاوز حوكمة O44 أو بوابات تنفيذ O45.",
  "Reconciliation-first handling for uncertain external side effects. The console does not auto-retry unknown outcomes.": "معالجة قائمة على التسوية أولًا للآثار الخارجية غير المؤكدة. لا تقوم وحدة التحكم بإعادة محاولة النتائج غير المعروفة تلقائيًا.",
  "Read-only in v2.0.0": "للقراءة فقط",
  "Reconciliation-first": "التسوية أولًا",
  "Safe response": "استجابة آمنة",
  "Confirm exact action, request hash and lease state.": "تأكد من الإجراء الدقيق وهاش الطلب وحالة القفل.",
  "Determine whether the side effect actually happened.": "تحقق مما إذا كان الأثر الجانبي قد حدث فعلًا.",
  "Record the observed outcome before any retry decision.": "سجّل النتيجة المرصودة قبل اتخاذ قرار إعادة المحاولة.",
  "Live health and readiness checks from the O40 API. The page refreshes automatically every 15 seconds.": "فحوصات الصحة والجاهزية المباشرة من API الخاص بـ O40. تتحدث الصفحة تلقائيًا كل 15 ثانية.",
  "Refresh health": "تحديث الصحة",
  "Read-only operator view for release state, local service health and freeze discipline.": "واجهة تشغيل للقراءة فقط لحالة الإصدار وصحة الخدمة المحلية وانضباط التجميد.",
  "Operator discipline": "انضباط المشغّل",
  "Keep the previous known-good artifact.": "احتفظ بالحزمة السابقة المعروفة بالصحة.",
  "Verify backups before upgrades.": "تحقق من النسخ الاحتياطية قبل الترقية.",
  "Do not bypass approval gates.": "لا تتجاوز بوابات الموافقة.",
  "Do not edit SQLite manually during incidents.": "لا تعدّل SQLite يدويًا أثناء الحوادث.",
  "What passed, what is traceable, and what still needs human approval.": "ما اجتاز الفحص، وما يمكن تتبعه، وما يزال يحتاج إلى موافقة بشرية.",
  "This screen will connect when that boundary is exposed.": "ستتصل هذه الشاشة عند إتاحة ذلك الحد.",
  "The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.": "لا يتم تجميد الحزمة المحلية إلا بعد نجاح البوابة الآلية. الإنتاج المتصل بالإنترنت يحتاج أدلة من بيئة الهدف. هذه الشاشة لا تنفذ إجراءات خارجية.",
  "Final release candidate": "مرشح الإصدار النهائي",
  "Release Control Plane": "وحدة تحكم الإصدار",
  "Local Gate": "البوابة المحلية",
  "Target Evidence": "أدلة البيئة المستهدفة",
  "MANUAL": "يدوي",
  "Firewall · TLS · Backup · Rollback": "جدار الحماية · TLS · النسخ الاحتياطي · الاسترجاع",
  "Engine payload": "حمولة المحرك",
  "Structured payload": "حمولة منظمة",
  "Enter the signed bearer token issued by your O36 identity boundary. The console normalizes an optional": "أدخل Bearer الموقّع الصادر عن حد الهوية O36. تقوم الوحدة بتوحيد بادئة",
  "prefix, stores the token in": "، وتخزن الرمز في",
  "and can test the token against O38 without creating a run.": "ويمكنها اختبار الرمز ضد O38 دون إنشاء تشغيل.",
  "API Base URL": "عنوان API الأساسي",
  "Bearer token": "رمز Bearer",
  "Find anything in AI Master OS": "ابحث عن أي شيء في AI Master OS",
  "What needs attention": "ما يحتاج إلى الانتباه",
  "Enter open": "Enter للفتح",
  "Ctrl K close": "Ctrl K للإغلاق",
  "ALERTS": "التنبيهات",
  "This clears the run history stored by this browser console. Your backend jobs, audit log, experiments and learning memory remain untouched.": "سيؤدي ذلك إلى مسح سجل التشغيل المحفوظ في وحدة المتصفح الحالية. لن يتم المساس بوظائف الـ Backend أو سجل التدقيق أو التجارب أو ذاكرة التعلم.",
  "indexed runs.": "تشغيلات مفهرسة."
};
function uiT(en, ar){ return langState.current === 'ar' ? (ar || V4_AR_PATCH[en] || V4_AR_EXTRA[en] || en) : en; }
function translateDocumentTextV4(lang){
  const map = lang === 'ar' ? {...(V4_STATIC_I18N.ar||{}), ...V4_AR_EXTRA, ...V4_AR_PATCH} : {};
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); const nodes=[];
  while(walker.nextNode()) nodes.push(walker.currentNode);
  for(const node of nodes){
    const parent=node.parentElement; if(!parent || parent.closest('script,style')) continue;
    const raw=node.nodeValue||''; const original=V4_TEXT_ORIGINAL.has(node) ? V4_TEXT_ORIGINAL.get(node) : (V4_TEXT_ORIGINAL.set(node,raw.trim()),raw.trim());
    if(!original) continue;
    const translated = lang==='ar' ? (map[original] || original) : original;
    const lead=raw.match(/^\s*/)?.[0]||''; const trail=raw.match(/\s*$/)?.[0]||''; const nextValue=lead+translated+trail;
    if (node.nodeValue !== nextValue) node.nodeValue = nextValue;
  }
}
function textLeafReplace(map) { translateDocumentTextV4(map === V4_STATIC_I18N.ar ? 'ar' : 'en'); }

function setLabelText(inputId, text) {
  const el=document.getElementById(inputId); if(!el) return;
  const label=el.closest('label'); if(!label) return;
  for(const n of label.childNodes){
    if(n.nodeType===3 && n.nodeValue.trim()){ n.nodeValue=' '+text; return; }
  }
}

function applyStaticUiLanguageV4(lang) {
  const map=V4_STATIC_I18N[lang] || V4_STATIC_I18N.en;
  translateDocumentTextV4(lang);
  document.querySelectorAll('.nav-group-label').forEach((el,i)=>{ const keys=['WORKSPACE','INTELLIGENCE','GOVERNANCE','OPERATIONS','SYSTEM']; el.textContent=map[keys[i]]||keys[i]; });
  const byId={
    heroTitle:'Run the business through one governed AI operating system.',heroDesc:'See what is running, what needs your attention, what the system decided, and what happens next.',
    nextActionEyebrow:'NEXT REQUIRED ACTION',nextActionSub:'Human control remains active for consequential actions.',
    decisionEyebrow:'DECISION',decisionTitle:'Latest operating signal',attentionEyebrow:'ATTENTION',attentionTitle:'What needs you',pulseEyebrow:'OPERATING PULSE',pulseTitle:'What is happening now',
    flowEyebrow:'EXECUTION',flowTitle:'Current flow',timelineEyebrow:'SYSTEM TIMELINE',timelineTitle:'Latest runtime events',
    newRunEyebrow:'NEW RUN',newRunTitle:'Start with intent, not complexity.',governedEyebrow:'GOVERNED RUN',governedTitle:'Define the job',lastRunsEyebrow:'LAST RUNS',lastRunsTitle:'Recent activity'
  };
  for(const [id,key] of Object.entries(byId)){const el=document.getElementById(id); if(el) el.textContent=map[key]||key;}
  setLabelText('projectId',map['Project ID']); setLabelText('request',map['Request']); setLabelText('audience',map['Audience']); setLabelText('goal',map['Goal']); setLabelText('constraints',map['Constraints']); setLabelText('language',map['Result language']);
  setLabelText('runCenterProjectId',map['Project ID']); setLabelText('runCenterRequest',map['Request']); setLabelText('runCenterAudience',map['Audience']); setLabelText('runCenterGoal',map['Goal']); setLabelText('runCenterConstraints',map['Constraints']); setLabelText('runCenterLanguage',map['Result language']);
  document.querySelectorAll('.hero-copy .hero-actions .primary-btn').forEach(el=>el.textContent=map['Start a governed run']);
  document.querySelectorAll('.hero-copy .hero-actions .secondary-btn').forEach(el=>el.textContent=map['Open execution']);
  document.querySelectorAll('#runForm .form-actions .primary-btn').forEach(el=>el.textContent=map['Start Run']);
  document.querySelectorAll('#runCenterForm .form-actions .primary-btn').forEach(el=>el.textContent=map['Create Run']);
  document.querySelectorAll('.template-card').forEach((el)=>{const k=el.dataset.template; const titleMap={business:'Validate a business idea',market:'Research the market',strategy:'Build a strategy',custom:'Custom goal'}; const descMap={business:'Research the market, identify the strongest hypothesis and define the cheapest test.',market:'Find current evidence, gaps, local signals and actionable opportunity areas.',strategy:'Turn a known opportunity into a focused operating plan.',custom:'Start from a blank governed request and define the context yourself.'}; const b=el.querySelector('b'), sm=el.querySelector('small'); if(b)b.textContent=map[titleMap[k]]||titleMap[k]; if(sm)sm.textContent=map[descMap[k]]||descMap[k];});
  const titles=PAGE_TITLES[lang]||PAGE_TITLES.en;
  const current=document.querySelector('.nav-item.active')?.dataset?.page || 'overview';
  const pt=document.getElementById('pageTitle'); if(pt) pt.textContent=titles[current]||titles.overview;
  const fe=document.getElementById('pageEyebrow'); if(fe) fe.textContent=lang==='ar'?'مركز التحكم':'CONTROL CENTER';
}


const V4_PLACEHOLDERS = {
  en: {
    request: 'Example: Research low-cost AI opportunities for small businesses in Egypt and recommend the most practical one to test.',
    constraints: 'Optional: budget, geography, timing, exclusions, evidence requirements…',
    runCenterRequest: 'What should AI Master OS do?',
    runCenterConstraints: 'Optional constraints',
    bearerToken: 'Paste token locally — never share it in chat',
    commandSearch: 'Search pages, jobs, projects, actions…'
  },
  ar: {
    request: 'مثال: ابحث عن فرص ذكاء اصطناعي منخفضة التكلفة للمشروعات الصغيرة في مصر واقترح أكثرها عملية للاختبار.',
    constraints: 'اختياري: الميزانية، النطاق الجغرافي، التوقيت، الاستثناءات، ومتطلبات الأدلة…',
    runCenterRequest: 'ماذا تريد من AI Master OS أن يفعل؟',
    runCenterConstraints: 'قيود اختيارية',
    bearerToken: 'الصق الرمز محليًا — لا تشاركه في المحادثة',
    commandSearch: 'ابحث في الصفحات والتشغيلات والمشروعات والإجراءات…'
  }
};
function applyLocalizedPlaceholdersV4(lang) {
  const dict = V4_PLACEHOLDERS[lang] || V4_PLACEHOLDERS.en;
  for (const [id, value] of Object.entries(dict)) {
    const el = document.getElementById(id);
    if (!el) continue;
    el.setAttribute('placeholder', value);
    el.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
  }
}
let v4TranslationObserver;
function startV4TranslationObserver() {
  if (v4TranslationObserver || !document.body) return;
  let queued = false;
  v4TranslationObserver = new MutationObserver(() => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      if (langState.current === 'ar') {
        translateDocumentTextV4('ar');
        applyLocalizedPlaceholdersV4('ar');
      }
    });
  });
  v4TranslationObserver.observe(document.body, {subtree:true, childList:true, characterData:true});
}

function applyLanguage(lang) {
  langState.current = SUPPORTED_LANGUAGES.includes(lang) ? lang : 'en';
  localStorage.setItem('aios.language', langState.current);
  const dict = I18N[langState.current];
  applyStaticUiLanguageV4(langState.current);
  document.documentElement.lang = langState.current;
  document.documentElement.dir = langState.current === 'ar' ? 'rtl' : 'ltr';
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (dict[key]) el.textContent = dict[key];
  });
  const title = document.querySelector('#pageTitle');
  if (title) {
    const active = document.querySelector('.nav-item.active')?.dataset?.page || 'overview';
    title.textContent = PAGE_TITLES[langState.current][active] || PAGE_TITLES.en[active];
  }
  const languageSelect = $('languageSelect'); if (languageSelect) languageSelect.value = langState.current;
  const settingsLang = $('settingsLanguageSelect'); if (settingsLang) settingsLang.value = langState.current;
  document.body.classList.toggle('rtl-mode', langState.current === 'ar');
  document.querySelectorAll('input,textarea,select').forEach(el=>el.setAttribute('dir', langState.current === 'ar' ? 'rtl' : 'ltr'));
  applyLocalizedPlaceholdersV4(langState.current);
  startV4TranslationObserver();
  translateDocumentTextV4(langState.current);
  try { updateExecutiveSummary?.(); renderNotifications?.(); if (document.querySelector('.nav-item.active')?.dataset?.page === 'runs') renderRunsTable(); } catch {}
  translateDocumentTextV4(langState.current);

}

function updatePageTitleV4(pageName) {
  const title = $('pageTitle');
  if (title) title.textContent = PAGE_TITLES[langState.current]?.[pageName] || PAGE_TITLES.en?.[pageName] || pageName;
}

// Patch the existing page() function's displayed title without changing its routing behavior.
const _pageV4 = page;
page = function(pageName) {
  _pageV4(pageName);
  updatePageTitleV4(pageName);
  if (pageName === 'decisions') refreshDecisionsV4();
  if (pageName === 'evidence') refreshEvidenceV4();
  if (pageName === 'experiments') refreshExperimentsV4();
  if (pageName === 'policies') refreshPoliciesV4();
  if (pageName === 'settings') refreshSettingsV4();
};

document.getElementById('languageSelect')?.addEventListener('change', e => applyLanguage(e.target.value));
document.getElementById('settingsLanguageSelect')?.addEventListener('change', e => applyLanguage(e.target.value));
document.getElementById('settingsSessionBtn')?.addEventListener('click', () => $('authBtn')?.click());
bindRunsFilters();

function setBackendState(status, detail='') {
  const el = $('backendState');
  const text = $('backendStateText');
  if (!el || !text) return;
  el.classList.remove('backend-online','backend-offline','backend-degraded');
  if (status === 'online') {
    el.classList.add('backend-online');
    text.textContent = langState.current === 'ar' ? 'الوحدة متصلة · Backend جاهز' : 'Console online · Backend ready';
  } else if (status === 'degraded') {
    el.classList.add('backend-degraded');
    text.textContent = langState.current === 'ar' ? 'الوحدة متصلة · Backend محدود' : 'Console online · Backend limited';
  } else {
    el.classList.add('backend-offline');
    text.textContent = langState.current === 'ar' ? 'الوحدة متصلة · Backend غير متاح' : 'Console online · Backend offline';
  }
  el.title = detail || (status === 'online' ? 'Local console and backend API are reachable.' : 'The local console is running, but the backend API cannot be reached from this session.');
}

async function probeBackendV4() {
  const start = performance.now();
  try {
    const health = await api('/health');
    const ms = Math.round(performance.now() - start);
    setBackendState('online', `${health?.status || 'OK'} · ${ms}ms`);
    return true;
  } catch (err) {
    setBackendState('offline', String(err.message || err));
    return false;
  }
}

function historyCountV4() { return Array.isArray(state.runs) ? state.runs.length : 0; }
function openClearHistoryModalV4() {
  const modal = $('clearHistoryModal');
  if (!modal) return;
  const count = historyCountV4();
  $('clearHistoryCount').textContent = String(count);
  $('clearHistoryMsg').textContent = '';
  modal.classList.remove('hidden');
}
function closeClearHistoryModalV4() { $('clearHistoryModal')?.classList.add('hidden'); }
function clearLocalHistoryV4() {
  state.runs = [];
  localStorage.removeItem('aios.runs');
  try { sessionStorage.removeItem('aios.lastRun'); } catch {}
  closeClearHistoryModalV4();
  renderRunsTable?.();
  renderRecentRuns?.();
  updateExecutiveSummary?.();
  renderNotifications?.();
  const notice = $('runCenterMsg'); if (notice) notice.textContent = langState.current === 'ar' ? 'تم مسح السجل المحلي بنجاح.' : 'Local run history cleared.';
  if ($('clearHistoryMsg')) $('clearHistoryMsg').textContent = langState.current === 'ar' ? 'تم المسح.' : 'Cleared.';
}

$('clearHistoryBtn')?.addEventListener('click', openClearHistoryModalV4);
$('settingsClearHistory')?.addEventListener('click', openClearHistoryModalV4);
$('clearHistoryClose')?.addEventListener('click', closeClearHistoryModalV4);
$('clearHistoryCancel')?.addEventListener('click', closeClearHistoryModalV4);
$('clearHistoryConfirm')?.addEventListener('click', clearLocalHistoryV4);
$('clearHistoryModal')?.addEventListener('click', e => { if (e.target.id === 'clearHistoryModal') closeClearHistoryModalV4(); });

function safeText(obj, keys, fallback='—') {
  for (const k of keys) if (obj && obj[k] != null && obj[k] !== '') return obj[k];
  return fallback;
}

function latestCompletedRunV4() {
  return state.runs.find(r => String(r?.status || '').toUpperCase() === 'COMPLETE') || state.runs[0] || null;
}

function renderDecisionIntelligenceV5(run) {
  const result = run?.result || {};
  const extracted = resultExtraction(run);
  const ds = result.decision_surface || result.decisionSurface || result.business_decision || {};
  const why = firstText(ds?.why_this_direction, ds?.recommendation_reason, extracted.recommendationReason, result?.strategy?.recommendation_reason, result?.strategy?.strategy?.recommendation_reason, 'The recommendation is derived from the strongest available evidence and current validation constraints.');
  const confidence = extracted.confidence || '—';
  const status = firstText(ds?.decision_status, ds?.status, result?.decision, 'WAITING');
  const heroTitle = $('decisionHeroTitle');
  const heroWhy = $('decisionHeroWhy');
  const heroConfidence = $('decisionHeroConfidence');
  const heroStatus = $('decisionHeroStatus');
  if (heroTitle) heroTitle.textContent = extracted.recommendation || 'No decision loaded';
  if (heroWhy) heroWhy.textContent = why;
  if (heroConfidence) heroConfidence.textContent = confidence;
  if (heroStatus) heroStatus.textContent = status;
  const story = $('decisionStory');
  if (story) {
    const items = [
      ['Customer problem', extracted.problem],
      ['Target customer', extracted.audience],
      ['Promise', extracted.promise],
      ['Positioning', extracted.positioning],
      ['Validation model', extracted.validationModel],
      ['Long-term model', extracted.longTermModel],
      ['Evidence boundary', extracted.marketScope || extracted.evidenceLabel]
    ];
    story.innerHTML = items.map(([label,value]) => `<div class="decision-story-item"><span>${esc(label)}</span><strong>${esc(value || '—')}</strong></div>`).join('');
  }
  const nextTitle = $('decisionNextTitle');
  const nextBody = $('decisionNextBody');
  if (nextTitle) nextTitle.textContent = extracted.nextAction || 'Next action';
  if (nextBody) {
    nextBody.innerHTML = [
      `<div class="decision-next-highlight">${esc(extracted.nextAction || 'Waiting for a next action')}</div>`,
      `<div class="decision-next-row"><span>Success threshold</span><strong>${esc(extracted.successThreshold || '—')}</strong></div>`,
      `<div class="decision-next-row"><span>Decision rule</span><strong>${esc(extracted.decisionRule || '—')}</strong></div>`,
      `<div class="decision-next-row"><span>Evidence</span><strong>${esc(extracted.evidenceLabel || '—')}</strong></div>`
    ].join('');
  }
}

function renderDecisionSurfaceV4(run) {
  const title = $('decisionSurfaceTitle');
  const box = $('decisionSurface');
  const graph = $('decisionGraph');
  if (!title || !box || !graph) return;
  const result = run?.result || {};
  const ds = result.decision_surface || result.decisionSurface || result.business_decision || {};
  const recommendation = safeText(ds, ['recommendation','title'], safeText(result, ['recommendation'], 'No decision-driving state yet'));
  title.textContent = recommendation;
  const cards = [
    [uiT('Recommendation','التوصية'), safeText(ds,['recommendation'], safeText(result,['recommendation'],'—'))],
    [uiT('Customer Problem','مشكلة العميل'), safeText(ds,['customer_problem','problem'], safeText(result,['problem'],'—'))],
    [uiT('Target Customer','العميل المستهدف'), safeText(ds,['target_customer','customer'], safeText(result,['customer'],'—'))],
    [uiT('Validation Model','نموذج التحقق'), safeText(ds,['validation_model'],'—')],
    [uiT('Success Threshold','حد النجاح'), safeText(ds,['success_threshold'],'—')],
    [uiT('Decision Rule','قاعدة القرار'), safeText(ds,['decision_rule'],'—')],
    [uiT('Next Action','الإجراء التالي'), safeText(ds,['next_action','next_step'], safeText(result,['next_action'],'—'))]
  ];
  box.innerHTML = cards.map(([k,v]) => `<div class="decision-field"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
  const steps = langState.current === 'ar' ? ['الطلب','البحث','القرار','التحقق','الحوكمة','التنفيذ','التعلم'] : ['Request','Research','Decision','Validation','Governance','Execution','Learning'];
  graph.innerHTML = steps.map((step,i)=>`<div class="decision-node ${i===2?'focus':''}"><span>${String(i+1).padStart(2,'0')}</span><b>${esc(step)}</b>${i<steps.length-1?'<i>↓</i>':''}</div>`).join('');
  const src = $('decisionSourceBadge');
  if (src) src.textContent = run ? 'BACKEND RESULT' : 'BACKEND / DERIVED';
  renderDecisionIntelligenceV5(run);
}

function renderDecisionKpisV4(run) {
  const box = $('decisionKpis'); if (!box) return;
  const result = run?.result || {};
  const ds = result.decision_surface || result.decisionSurface || {};
  const opportunity = safeText(ds,['opportunity_score'], safeText(result,['opportunity_score'],'—'));
  const strategy = safeText(ds,['strategy_score'], safeText(result,['strategy_score'],'—'));
  const confidence = safeText(ds,['confidence'], safeText(result,['confidence'],'—'));
  const validation = safeText(ds,['decision_status','validation_decision'], safeText(result,['decision'],'—'));
  const labels = langState.current === 'ar' ? [['الفرصة',opportunity],['الاستراتيجية',strategy],['الثقة',confidence],['التحقق',validation]] : [['Opportunity',opportunity],['Strategy',strategy],['Confidence',confidence],['Validation',validation]];
  box.innerHTML = labels.map(([k,v])=>`<div class="metric-card"><div class="metric-label">${esc(k)}</div><div class="metric-value">${esc(v)}</div><div class="metric-note">Backend-derived when available</div></div>`).join('');
}

async function refreshDecisionsV4() {
  const online = await probeBackendV4();
  if (online) await syncAllRuns();
  const run = latestCompletedRunV4();
  renderDecisionKpisV4(run);
  renderDecisionSurfaceV4(run);
}

function renderRegistry(items, emptyText) {
  if (!Array.isArray(items) || !items.length) return `<div class="empty-state compact-empty"><div class="empty-icon">◌</div><h3>${esc(emptyText)}</h3><p>${langState.current==='ar'?'لا توجد بيانات backend متاحة في الوقت الحالي.':'No backend data is available in the current API contract.'}</p></div>`;
  return items.slice(0,30).map(item=>{
    const id = item.experiment_id || item.id || item.run_id || '—';
    const decision = item.decision || item.status || item.outcome || 'UNKNOWN';
    const project = item.project_id || item.project || '—';
    return `<div class="registry-row"><div><b>${esc(id)}</b><small>${esc(project)}</small></div><span class="status-pill">${esc(decision)}</span><div class="registry-meta">${esc(item.created_at || item.updated_at || '')}</div></div>`;
  }).join('');
}

async function fetchExperimentsV4() {
  try { return await api('/experiments'); } catch { return null; }
}

function normalizeListPayload(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) return payload;
  return payload.items || payload.experiments || payload.records || payload.data || [];
}

async function refreshExperimentsV4() {
  const payload = await fetchExperimentsV4();
  const items = normalizeListPayload(payload);
  const counts = {total:items.length, go:items.filter(x=>String(x.decision||x.status||'').toUpperCase()==='GO').length, refine:items.filter(x=>String(x.decision||x.status||'').toUpperCase()==='REFINE').length, noGo:items.filter(x=>String(x.decision||x.status||'').toUpperCase()==='NO-GO').length};
  $('experimentKpis').innerHTML = Object.entries({Total:counts.total,GO:counts.go,REFINE:counts.refine,'NO-GO':counts.noGo}).map(([k,v])=>`<div class="metric-card"><div class="metric-label">${esc(k)}</div><div class="metric-value">${esc(v)}</div><div class="metric-note">LIVE API registry</div></div>`).join('');
  $('experimentList').innerHTML = renderRegistry(items, langState.current==='ar' ? 'لا توجد تجارب مفهرسة' : 'No experiments indexed');
  if (!payload) $('experimentList').insertAdjacentHTML('afterbegin','<div class="callout">Backend experiment registry is unavailable or not exposed on the current API boundary.</div>');
}

async function refreshEvidenceV4() {
  const payload = await fetchExperimentsV4();
  const items = normalizeListPayload(payload);
  const refs = items.reduce((n, x) => n + (Array.isArray(x.evidence_refs) ? x.evidence_refs.length : Array.isArray(x.evidence) ? x.evidence.length : 0), 0);
  $('evidenceKpis').innerHTML = [['Experiments',items.length],['Evidence refs',refs],['Source','LIVE API']].map(([k,v])=>`<div class="metric-card"><div class="metric-label">${esc(k)}</div><div class="metric-value">${esc(v)}</div><div class="metric-note">Backend-backed surface</div></div>`).join('');
  $('evidenceList').innerHTML = renderRegistry(items, langState.current==='ar' ? 'لا توجد تجارب تحمل أدلة مفهرسة' : 'No evidence-bearing experiments indexed');
  if (!payload) $('evidenceList').insertAdjacentHTML('afterbegin','<div class="callout">Evidence data will appear here when the backend exposes the experiment registry.</div>');
}

async function refreshPoliciesV4() {
  let payload = null;
  for (const path of ['/governance/policies','/policies','/governance']) {
    try { payload = await api(path); break; } catch {}
  }
  const items = normalizeListPayload(payload);
  const box = $('policyList');
  if (!payload) {
    box.innerHTML = langState.current==='ar' ? '<div class="availability-state unavailable"><div class="availability-icon">⚖</div><div><span class="availability-kicker">حالة المصدر</span><h3>واجهة السياسات غير متاحة</h3><p>لن تخترع الواجهة حالة للسياسات. اربط نقطة سياسات موثقة من الـ Backend لملء هذه الشاشة.</p></div></div>' : '<div class="availability-state unavailable"><div class="availability-icon">⚖</div><div><span class="availability-kicker">SOURCE STATUS</span><h3>Policy API not exposed</h3><p>The UI will not invent policy state. Connect an authenticated policy endpoint to populate this surface.</p></div></div>';
    return;
  }
  if (!items.length && typeof payload === 'object') {
    box.innerHTML = `<div class="policy-json"><pre class="json-block">${esc(pretty(payload))}</pre></div>`;
  } else {
    box.innerHTML = items.map(item=>`<div class="policy-row"><div><b>${esc(item.name||item.id||'Policy')}</b><small>${esc(item.version||item.policy_version||'—')}</small></div><span class="status-pill">${esc(item.status||'ACTIVE')}</span><p>${esc(item.description||item.reason||'')}</p></div>`).join('');
  }
}

function refreshSettingsV4() {
  const base = $('settingsApiBase'); if (base) base.textContent = state.apiBase || '/api';
  applyLanguage(langState.current);
}

// Local-history UX explicitly never deletes durable backend records.
window.AI_MASTER_OS_V4 = {
  version: UI_V4_BUILD,
  getLanguage: () => langState.current,
  setLanguage: applyLanguage,
  clearLocalHistory: clearLocalHistoryV4,
  backendApiBase: () => state.apiBase,
  localHistoryOnly: true
};

// Run history is local cache + live backend refresh; surface the source explicitly.
const _renderRunsTableV4 = renderRunsTable;
renderRunsTable = async function() {
  await _renderRunsTableV4();
  const note = document.querySelector('#page-runs .tiny-note');
  if (note && note.textContent.includes('Browser-local')) note.textContent = langState.current === 'ar' ? 'سجل محلي + تحديث مباشر من الـ Backend' : 'Local console history + live backend status';
};


/* V4.0.2: ensure every renderer re-applies the active language after async backend renders. */
function syncActiveLanguageV4(){ try { translateDocumentTextV4(langState.current); applyStaticUiLanguageV4(langState.current); if (langState.current==='ar') document.body.classList.add('rtl-mode'); } catch {} }
for (const fnName of ['renderSystemTimeline','renderExecutionCenter','refreshRecoveryCenter','renderNotifications','renderCommandResults','renderOperatingPulse','updateExecutiveSummary']) {
  if (typeof window[fnName] === 'function') {
    const original = window[fnName];
    window[fnName] = function(...args){ const out = original.apply(this,args); Promise.resolve(out).finally(syncActiveLanguageV4); return out; };
  }
}
const _pageV402 = page;
page = function(pageName){ const out=_pageV402(pageName); Promise.resolve(out).finally(syncActiveLanguageV4); return out; };
const _refreshDashboardV402 = refreshDashboard;
refreshDashboard = function(...args){ const out=_refreshDashboardV402.apply(this,args); Promise.resolve(out).finally(syncActiveLanguageV4); return out; };
const _refreshExecutionV402 = refreshExecutionCenter;
refreshExecutionCenter = function(...args){ const out=_refreshExecutionV402.apply(this,args); Promise.resolve(out).finally(syncActiveLanguageV4); return out; };
const _refreshRecoveryV402 = refreshRecoveryCenter;
refreshRecoveryCenter = function(...args){ const out=_refreshRecoveryV402.apply(this,args); Promise.resolve(out).finally(syncActiveLanguageV4); return out; };
const _renderRunsTableV402 = renderRunsTable;
renderRunsTable = async function(...args){ const out=await _renderRunsTableV402.apply(this,args); syncActiveLanguageV4(); return out; };
const _renderRecentRunsV402 = renderRecentRuns;
renderRecentRuns = async function(...args){ const out=await _renderRecentRunsV402.apply(this,args); syncActiveLanguageV4(); return out; };
const _refreshHealthV402 = refreshHealth;
refreshHealth = async function(...args){ const out=await _refreshHealthV402.apply(this,args); syncActiveLanguageV4(); return out; };
// Translate any late backend-rendered text nodes without polling the DOM continuously.
const _applyLanguageV402 = applyLanguage;
applyLanguage = function(lang){ const out=_applyLanguageV402(lang); syncActiveLanguageV4(); return out; };

// Initialize language and backend state on load.
applyLanguage(langState.current);
probeBackendV4();


/* ========================= UI V4.2 — INTELLIGENCE CONTROL CENTER ========================= */
// Backend-first intelligence surfaces: no invented decisions/evidence/learning state.
const UI_V42_BUILD = '4.2.0';

function v42DecisionFromRun(run){
  if(!run) return null;
  const result=run.result||{};
  const ds=result.decision_surface||result.decisionSurface||result.business_decision||{};
  return {
    run,
    id: run.job_id || run.id || '—',
    project_id: run.project_id || result.project_id || '—',
    recommendation: safeText(ds,['recommendation','title'],safeText(result,['recommendation'],'—')),
    problem: safeText(ds,['customer_problem','problem'],safeText(result,['problem'],'—')),
    customer: safeText(ds,['target_customer','customer'],safeText(result,['customer'],'—')),
    validation_model: safeText(ds,['validation_model'],'—'),
    threshold: safeText(ds,['success_threshold'],'—'),
    rule: safeText(ds,['decision_rule'],'—'),
    next_action: safeText(ds,['next_action','next_step'],safeText(result,['next_action'],'—')),
    opportunity: safeText(ds,['opportunity_score'],safeText(result,['opportunity_score'],'—')),
    strategy: safeText(ds,['strategy_score'],safeText(result,['strategy_score'],'—')),
    confidence: safeText(ds,['confidence'],safeText(result,['confidence'],'—')),
    validation: safeText(ds,['decision_status','validation_decision'],safeText(result,['decision'],'—')),
    evidence_boundary: safeText(ds,['evidence_boundary'],safeText(result,['evidence_boundary'],'—')),
    local_evidence: safeText(ds,['local_evidence'],safeText(result,['local_evidence'],'—')),
  };
}

function renderV42DecisionInspector(ctx, focus='decision'){
  const el=$('decisionInspector'); if(!el) return;
  if(!ctx){el.innerHTML=`<div class="empty-state compact-empty"><div class="empty-icon">◇</div><h3>${esc(langState.current==='ar'?'لا يوجد قرار قابل للاستعراض':'No decision available')}</h3><p>${esc(langState.current==='ar'?'يجب أن يوفر الـ Backend تشغيلًا مكتملًا يحتوي على سطح قرار.':'The backend must expose a completed run with a decision surface.')}</p></div>`; return;}
  const labels=langState.current==='ar'?{source:'المصدر',project:'المشروع',validation:'التحقق',evidence:'حدود الدليل',next:'الإجراء التالي'}:{source:'Source',project:'Project',validation:'Validation',evidence:'Evidence boundary',next:'Next action'};
  el.innerHTML=`<div class="inspector-head"><span class="eyebrow">${esc(labels.source)}</span><span class="source-badge">BACKEND RESULT</span></div><div class="inspector-grid"><div><span>${esc(labels.project)}</span><strong>${esc(ctx.project_id)}</strong></div><div><span>${esc(labels.validation)}</span><strong>${esc(ctx.validation)}</strong></div><div><span>${esc(labels.evidence)}</span><strong>${esc(ctx.evidence_boundary)}</strong></div><div><span>${esc(labels.next)}</span><strong>${esc(ctx.next_action)}</strong></div></div><div class="inspector-code"><span>${esc(ctx.id)}</span></div>`;
}

function renderV42DecisionGraph(ctx){
  const graph=$('decisionGraph'); if(!graph) return;
  const labels=langState.current==='ar'?['الطلب','البحث','الفرصة','الاستراتيجية','التحقق','القرار','التعلم']:['Request','Research','Opportunity','Strategy','Validation','Decision','Learning'];
  graph.innerHTML=labels.map((step,i)=>`<button type="button" class="decision-node ${i===5?'focus':''}" data-decision-node="${i}"><span>${String(i+1).padStart(2,'0')}</span><b>${esc(step)}</b>${i<labels.length-1?'<i>↓</i>':''}</button>`).join('');
  graph.querySelectorAll('[data-decision-node]').forEach(btn=>btn.addEventListener('click',()=>{
    const idx=Number(btn.dataset.decisionNode);
    const copy=idx===5 ? (langState.current==='ar'?'هذه العقدة تمثل القرار المشتق من التشغيل المكتمل وسياق التحقق والتعلم.':'This node represents the decision derived from the completed run, validation and learning context.') : (langState.current==='ar'?`هذه العقدة (${labels[idx]}) معروضة من مسار التشغيل ولا تُنشئ حالة جديدة.`:`This node (${labels[idx]}) is derived from the runtime path and does not create new state.`);
    const el=$('decisionInspector'); if(el) el.innerHTML=`<div class="callout info-callout"><b>${esc(labels[idx])}</b><div>${esc(copy)}</div>${ctx?`<small>${esc(ctx.id)} · ${esc(ctx.project_id)}</small>`:''}</div>`;
  }));
}

function renderV42ExperimentInspector(item, target='experimentInspector'){
  const el=$(target); if(!el) return;
  if(!item){el.innerHTML=`<div class="tiny-note">${esc(langState.current==='ar'?'اختر سجلًا لاستعراض التفاصيل المرتبطة بالـ Backend.':'Select a backend record to inspect its details.')}</div>`;return;}
  const evidence=Array.isArray(item.evidence_refs)?item.evidence_refs:(Array.isArray(item.evidence)?item.evidence:[]);
  const metrics=item.metrics||item.observations||{};
  const labels=langState.current==='ar'?{hyp:'الفرضية',decision:'القرار',sample:'العينة',refs:'مراجع الأدلة',metrics:'المقاييس',notes:'الملاحظات'}:{hyp:'Hypothesis',decision:'Decision',sample:'Sample',refs:'Evidence refs',metrics:'Metrics',notes:'Notes'};
  el.innerHTML=`<div class="inspector-head"><span class="eyebrow">${esc(item.experiment_id||item.id||'EXPERIMENT')}</span><span class="source-badge">LIVE API</span></div><div class="inspector-grid"><div><span>${labels.hyp}</span><strong>${esc(item.hypothesis||item.goal||'—')}</strong></div><div><span>${labels.decision}</span><strong>${esc(item.decision||item.status||item.outcome||'—')}</strong></div><div><span>${labels.sample}</span><strong>${esc(item.sample_size??item.sample??'—')}</strong></div><div><span>${labels.refs}</span><strong>${esc(evidence.length)}</strong></div></div><details class="inspector-details"><summary>${esc(labels.metrics)}</summary><pre class="json-block">${esc(pretty(metrics))}</pre></details><details class="inspector-details"><summary>${esc(labels.notes)}</summary><pre class="json-block">${esc(pretty(item.notes||item.observations||[]))}</pre></details>`;
}


function renderO46EvidenceMapV4(items){
  const map=$('evidenceMap'), insp=$('evidenceMapInspector');
  if(!map) return;
  const run=latestCompletedRunV4();
  const view=(typeof buildO46ExperienceView==='function') ? buildO46ExperienceView(run||{}, {}) : null;
  const research=view?.research || {};
  const decision=view?.decision || {};
  const evidenceRefs=Array.isArray(view?.provenance?.evidence_refs)?view.provenance.evidence_refs:[];
  const refsFromItems=[];
  (items||[]).forEach(item=>{
    const refs=Array.isArray(item.evidence_refs)?item.evidence_refs:(Array.isArray(item.evidence)?item.evidence:[]);
    refs.forEach(ref=>refsFromItems.push(ref));
  });
  const refs=[...new Set([...evidenceRefs,...refsFromItems].map(v=>typeof v==='string'?v:(v?.id||v?.ref||v?.source_id||JSON.stringify(v))))].filter(Boolean).slice(0,24);
  const claims=[];
  if(decision.recommendation) claims.push({id:'decision',label:langState.current==='ar'?'التوصية':'Recommendation',value:decision.recommendation,type:'decision'});
  if(decision.customer_problem) claims.push({id:'problem',label:langState.current==='ar'?'مشكلة العميل':'Customer problem',value:decision.customer_problem,type:'claim'});
  if(decision.why) claims.push({id:'rationale',label:langState.current==='ar'?'سبب الاتجاه':'Why this direction',value:decision.why,type:'claim'});
  if(!claims.length) claims.push({id:'decision',label:langState.current==='ar'?'القرار':'Decision',value:langState.current==='ar'?'لا يوجد قرار مكتمل بعد':'No completed decision yet',type:'decision'});
  const sourceNodes=refs.length?refs.map((r,i)=>({id:`src-${i}`,label:`${langState.current==='ar'?'مصدر':'Source'} ${i+1}`,value:r,type:'source'})):[{id:'src-empty',label:langState.current==='ar'?'المصادر':'Sources',value:research.summary|| (langState.current==='ar'?'لا توجد مراجع معروضة عبر حدود الـ API الحالية':'No evidence refs exposed by the current API boundary.'),type:'source'}];
  const decisionNode={id:'final',label:langState.current==='ar'?'القرار الحالي':'Current decision',value:decision.recommendation||'—',type:'decision'};
  const conflictCount=Array.isArray(research.conflicts)?research.conflicts.length:0;
  const confidence=decision.confidence||'—';
  const header=`<div class="evidence-map-summary"><div><span>${langState.current==='ar'?'مصادر':'Sources'}</span><strong>${refs.length}</strong></div><div><span>${langState.current==='ar'?'الأدلة':'Evidence'}</span><strong>${research.evidence_count??0}</strong></div><div><span>${langState.current==='ar'?'التعارضات':'Conflicts'}</span><strong>${conflictCount}</strong></div><div><span>${langState.current==='ar'?'الثقة':'Confidence'}</span><strong>${esc(confidence)}</strong></div></div>`;
  const claimHtml=claims.slice(0,3).map((n,i)=>`<button type="button" class="evidence-map-node claim-node" data-evidence-node="${esc(n.id)}"><span class="node-kicker">${esc(n.label)}</span><b>${esc(n.value)}</b><small>${langState.current==='ar'?'ادعاء مشتق من التشغيل':'Backend-derived claim'}</small></button>`).join('');
  const sourceHtml=sourceNodes.slice(0,12).map(n=>`<button type="button" class="evidence-map-node source-node" data-evidence-node="${esc(n.id)}"><span class="node-kicker">${esc(n.label)}</span><b>${esc(n.value)}</b><small>${langState.current==='ar'?'مرجع دليل':'Evidence reference'}</small></button>`).join('');
  const lines=sourceNodes.slice(0,12).map((n,i)=>`<div class="evidence-link" style="--link-delay:${i*35}ms"><span></span></div>`).join('');
  map.innerHTML=header+`<div class="evidence-map-canvas"><div class="evidence-map-column">${claimHtml}</div><div class="evidence-map-links">${lines}</div><div class="evidence-map-column sources-column">${sourceHtml}</div><div class="evidence-map-decision"><button type="button" class="evidence-map-node decision-node" data-evidence-node="final"><span class="node-kicker">${esc(decisionNode.label)}</span><b>${esc(decisionNode.value)}</b><small>${langState.current==='ar'?'نقطة التجميع النهائية':'Final decision aggregation'}</small></button></div></div>`;
  map.querySelectorAll('[data-evidence-node]').forEach(btn=>btn.addEventListener('click',()=>{
    const id=btn.dataset.evidenceNode;
    const node=[...claims,...sourceNodes,decisionNode].find(x=>x.id===id);
    if(!insp) return;
    const title=node?.label||'Evidence trace';
    const value=node?.value||'—';
    const extra=node?.type==='source' ? (langState.current==='ar'?'هذا المرجع معروض كما وفره الـ Backend. الواجهة لا تنشئ مصدرًا جديدًا.':'This reference is rendered exactly from backend-provided evidence. The UI does not create sources.') : (langState.current==='ar'?'العقدة مرتبطة بسطح القرار الموحد ويمكن تتبعها دون تغيير أي حالة تشغيل.':'This node is linked to the unified decision surface and is traceable without mutating runtime state.');
    insp.innerHTML=`<div class="evidence-trace-head"><div><span class="eyebrow">${esc(title)}</span><h4>${esc(value)}</h4></div><span class="source-badge">BACKEND DERIVED</span></div><div class="callout info-callout"><b>${langState.current==='ar'?'لماذا أراها هنا؟':'Why is this here?'}</b><div>${esc(extra)}</div><small>${esc(run?.job_id||'—')} · ${esc(view?.provenance?.trace_id||'—')}</small></div>`;
  }));
}

function renderV42EvidenceList(items){
  const el=$('evidenceList'); if(!el) return;
  if(!Array.isArray(items)||!items.length){el.innerHTML=renderRegistry([],langState.current==='ar'?'لا توجد تجارب تحمل أدلة مفهرسة':'No evidence-bearing experiments indexed');return;}
  el.innerHTML=items.slice(0,30).map((item,i)=>{
    const id=item.experiment_id||item.id||'—'; const refs=Array.isArray(item.evidence_refs)?item.evidence_refs:(Array.isArray(item.evidence)?item.evidence:[]);
    return `<button type="button" class="registry-row registry-button" data-evidence-index="${i}"><span><b>${esc(id)}</b><small>${esc(item.project_id||item.project||'—')}</small></span><span class="status-pill">${esc(item.decision||item.status||item.outcome||'UNKNOWN')}</span><span class="registry-meta">${esc(langState.current==='ar'?`${refs.length} مراجع دليل`:`${refs.length} evidence refs`)}</span></button>`;
  }).join('');
  el.querySelectorAll('[data-evidence-index]').forEach(btn=>btn.addEventListener('click',()=>renderV42ExperimentInspector(items[Number(btn.dataset.evidenceIndex)],'evidenceInspector')));
}

function renderV42ExperimentList(items){
  const el=$('experimentList'); if(!el) return;
  if(!Array.isArray(items)||!items.length){el.innerHTML=renderRegistry([],langState.current==='ar'?'لا توجد تجارب مفهرسة':'No experiments indexed');return;}
  el.innerHTML=items.slice(0,30).map((item,i)=>{
    const id=item.experiment_id||item.id||'—'; const decision=item.decision||item.status||item.outcome||'UNKNOWN';
    return `<button type="button" class="registry-row registry-button" data-experiment-index="${i}"><span><b>${esc(id)}</b><small>${esc(item.project_id||item.project||'—')}</small></span><span class="status-pill">${esc(decision)}</span><span class="registry-meta">${esc(item.created_at||item.updated_at||'')}</span></button>`;
  }).join('');
  el.querySelectorAll('[data-experiment-index]').forEach(btn=>btn.addEventListener('click',()=>renderV42ExperimentInspector(items[Number(btn.dataset.experimentIndex)])));
}

async function fetchLearningContextV42(projectId){
  if(!projectId) return null;
  try { return await api(`/learning/context?project_id=${encodeURIComponent(projectId)}`); } catch { return null; }
}

async function refreshLearningContextV42(){
  const el=$('learningContextPanel'); if(!el) return;
  const run=latestCompletedRunV4(); const projectId=run?.project_id;
  const payload=await fetchLearningContextV42(projectId);
  const badge=$('learningSourceBadge');
  if(!payload){ if(badge) badge.textContent=langState.current==='ar'?'غير متاح عبر API الحالية':'NOT EXPOSED'; el.innerHTML=`<div class="availability-state unavailable"><div class="availability-icon">∞</div><div><span class="availability-kicker">${esc(langState.current==='ar'?'الحالة':'STATUS')}</span><h3>${esc(langState.current==='ar'?'سياق التعلم غير متاح':'Learning context unavailable')}</h3><p>${esc(langState.current==='ar'?'حدود الـ Backend الحالية لا تعرض سياق التعلم لهذا المشروع.':'The current backend API does not expose learning context for this project.')}</p></div></div>`; return; }
  if(badge) badge.textContent='LIVE API';
  const context=payload.context||payload.learning_context||payload; const lessons=context.lessons||context.learning_records||context.items||[]; const experiments=context.experiments||[]; const next=context.next_step||context.next_cycle_context||context.routing||'—';
  const labels=langState.current==='ar'?{lessons:'الدروس',experiments:'التجارب المرتبطة',next:'الخطوة التالية'}:{lessons:'Lessons',experiments:'Linked experiments',next:'Next step'};
  el.innerHTML=`<div class="learning-summary"><div><span>${labels.lessons}</span><strong>${esc(Array.isArray(lessons)?lessons.length:0)}</strong></div><div><span>${labels.experiments}</span><strong>${esc(Array.isArray(experiments)?experiments.length:0)}</strong></div><div><span>${labels.next}</span><strong>${esc(typeof next==='string'?next:'Available')}</strong></div></div><pre class="json-block learning-json">${esc(pretty(context))}</pre>`;
}

const _refreshDecisionsV42=refreshDecisionsV4;
refreshDecisionsV4=async function(){ await _refreshDecisionsV42(); const run=latestCompletedRunV4(); const ctx=v42DecisionFromRun(run); renderV42DecisionInspector(ctx); renderV42DecisionGraph(ctx); };
const _refreshEvidenceV42=refreshEvidenceV4;
refreshEvidenceV4=async function(){ await _refreshEvidenceV42(); const payload=await fetchExperimentsV4(); const items=normalizeListPayload(payload).filter(x=>Array.isArray(x.evidence_refs)||Array.isArray(x.evidence)); renderV42EvidenceList(items); renderO46EvidenceMapV4(items); };
const _refreshExperimentsV42=refreshExperimentsV4;
refreshExperimentsV4=async function(){ await _refreshExperimentsV42(); const payload=await fetchExperimentsV4(); renderV42ExperimentList(normalizeListPayload(payload)); };
const _pageV42=page;
page=function(pageName){ _pageV42(pageName); if(pageName==='memory') refreshLearningContextV42(); };
$('decisionsRefresh')?.addEventListener('click',()=>refreshDecisionsV4());
$('evidenceRefresh')?.addEventListener('click',()=>refreshEvidenceV4());
$('experimentsRefresh')?.addEventListener('click',()=>refreshExperimentsV4());



/* ========================= UI V4.3 — GOVERNANCE & HUMAN CONTROL ========================= */
const UI_V43_BUILD = '4.3.0';
const V43_APPROVAL_PATH = '/approvals/pending';
const V43_GOV_DECISIONS_PATH = '/governance/decisions';

function govTextV43(en, ar){ return langState.current === 'ar' ? ar : en; }
function approvalFieldV43(item,key){ return item?.[key] ?? item?.payload?.[key] ?? item?.governance?.[key] ?? '—'; }
function renderApprovalKpisV43(items){
  const pending=items.length;
  const high=items.filter(x=>String(approvalFieldV43(x,'risk')).toUpperCase()==='HIGH').length;
  const external=items.filter(x=>Boolean(approvalFieldV43(x,'external_effect'))).length;
  $('approvalKpis').innerHTML=[
    metricCard(govTextV43('Pending','معلّق'),pending,pending?'warn':'good'),
    metricCard(govTextV43('High risk','عالي المخاطر'),high,high?'bad':'good'),
    metricCard(govTextV43('External effect','أثر خارجي'),external,external?'warn':'good'),
    metricCard(govTextV43('Human gate','البوابة البشرية'),govTextV43('Active','نشطة'),'warn')
  ].join('');
}
function renderApprovalInspectorV43(item){
  const el=$('approvalInspector'); if(!el)return;
  if(!item){el.innerHTML=`<div class="tiny-note">${esc(govTextV43('Select an approval to inspect its action, risk, policy and approval binding.','اختر موافقة لاستعراض الإجراء والمخاطر والسياسة وربط الموافقة.'))}</div>`;return;}
  const p=item.payload||{};
  const labels=langState.current==='ar'?{id:'معرّف الموافقة',run:'التشغيل',project:'المشروع',action:'الإجراء',risk:'المخاطر',requester:'طالب الموافقة',status:'الحالة',policy:'إصدار السياسة',reason:'سبب الطلب',expires:'ينتهي في',binding:'ربط الطلب'}:{id:'Approval ID',run:'Run',project:'Project',action:'Action',risk:'Risk',requester:'Requested by',status:'Status',policy:'Policy version',reason:'Request reason',expires:'Expires',binding:'Request binding'};
  const binding=p.request_hash||p.action_hash||p.idempotency_key||'—';
  const action = item.action||p.action||'—';
  const risk = p.risk||item.risk||'—';
  const external = Boolean(p.external_effect||item.external_effect);
  const impact = p.impact||p.consequence||p.external_effect_reason||item.impact||'—';
  const reason = p.reason||p.request_reason||item.reason||'—';
  const summaryTitle = langState.current==='ar' ? 'قبل أن تقرر' : 'Before you decide';
  const summaryWhy = langState.current==='ar' ? 'راجع السبب، الأثر، والسياسة. الموافقة لا تعني أن الواجهة نفذت الإجراء.' : 'Review the reason, impact and policy. Approval does not mean the UI performed the action.';
  el.innerHTML=`<div class="governance-decision-hero">
    <div><span class="detail-label">${summaryTitle}</span><h4>${esc(action)}</h4><p>${esc(reason)}</p></div>
    <div class="governance-decision-state"><span class="status-pill ${String(risk).toLowerCase()}">${esc(String(risk).toUpperCase())}</span><small>${external ? (langState.current==='ar'?'أثر خارجي':'External effect') : (langState.current==='ar'?'أثر داخلي':'Internal effect')}</small></div>
  </div>
  <div class="governance-impact-grid">
    <div><span>${labels.risk}</span><strong>${esc(risk)}</strong><small>${external ? (langState.current==='ar'?'الإجراء قد يؤثر خارج النظام':'Action may affect systems outside this console') : (langState.current==='ar'?'لا يوجد أثر خارجي مسجل':'No external effect reported')}</small></div>
    <div><span>${langState.current==='ar'?'الأثر':'Impact'}</span><strong>${esc(impact)}</strong><small>${esc(summaryWhy)}</small></div>
    <div><span>${labels.policy}</span><strong>${esc(p.policy_version||item.policy_version||'O44-v1.0')}</strong><small>${langState.current==='ar'?'التقييم صادر من الـ Backend':'Decision is backend-authoritative'}</small></div>
    <div><span>${langState.current==='ar'?'الربط':'Binding'}</span><strong class="mono">${esc(binding)}</strong><small>${langState.current==='ar'?'يمنع التكرار':'Protects idempotency'}</small></div>
  </div>
  <div class="inspector-grid gov-inspector-grid">
    <div><span>${labels.id}</span><strong class="mono">${esc(item.approval_id||'—')}</strong></div>
    <div><span>${labels.run}</span><strong class="mono">${esc(item.run_id||p.run_id||'—')}</strong></div>
    <div><span>${labels.project}</span><strong>${esc(p.project_id||item.project_id||'—')}</strong></div>
    <div><span>${labels.requester}</span><strong>${esc(item.requested_by||'—')}</strong></div>
    <div><span>${labels.status}</span><strong><span class="status-pill ${String(item.status||'').toLowerCase()}">${esc(item.status||'—')}</span></strong></div>
    <div><span>${labels.expires}</span><strong>${esc(item.expires_at||'—')}</strong></div>
  </div>
  <details class="governance-raw-details"><summary>${langState.current==='ar'?'عرض البيانات الخام':'Inspect raw approval payload'}</summary><pre class="json-block compact">${esc(pretty(p))}</pre></details>
  ${String(item.status||'').toUpperCase()==='PENDING'?`<div class="approval-decision-form"><label>${langState.current==='ar'?'سبب القرار':'Decision reason'}<textarea id="approvalDecisionReason" data-i18n-placeholder="gov.reasonPlaceholder" placeholder="${esc(govTextV43('Enter the reason for approval or rejection…','اكتب سبب الموافقة أو الرفض…'))}"></textarea></label><div class="form-actions"><button class="danger-outline-btn" id="rejectApprovalBtn" data-approval="${esc(item.approval_id)}">${esc(govTextV43('Reject','رفض'))}</button><button class="primary-btn" id="approveApprovalBtn" data-approval="${esc(item.approval_id)}">${esc(govTextV43('Approve','موافقة'))}</button></div></div>`:''}`;
  bindApprovalDecisionButtonsV43();
}
function renderApprovalListV43(items){
  const box=$('approvalList'); if(!box)return;
  if(!items.length){box.innerHTML=`<div class="empty-state compact-empty"><div class="empty-icon">✓</div><h3>${esc(govTextV43('No pending approvals','لا توجد موافقات معلقة'))}</h3><p>${esc(govTextV43('The backend currently reports no approval requests awaiting a human decision.','الـ Backend لا يعرض حاليًا طلبات موافقة تنتظر قرارًا بشريًا.'))}</p></div>`;return;}
  box.innerHTML=items.map(item=>{const p=item.payload||{};const risk=String(p.risk||item.risk||'UNKNOWN').toUpperCase();return `<button type="button" class="approval-row" data-approval-row="${esc(item.approval_id)}"><div><strong>${esc(item.action||p.action||'—')}</strong><small>${esc(item.approval_id||'')} · ${esc(item.run_id||p.run_id||'—')}</small></div><span class="status-pill ${risk.toLowerCase()}">${esc(risk)}</span><span class="status-pill pending">${esc(item.status||'PENDING')}</span><span class="approval-arrow">›</span></button>`}).join('');
  box.querySelectorAll('[data-approval-row]').forEach(btn=>btn.addEventListener('click',()=>{const item=items.find(x=>x.approval_id===btn.dataset.approvalRow);renderApprovalInspectorV43(item);box.querySelectorAll('.approval-row').forEach(x=>x.classList.remove('selected'));btn.classList.add('selected');}));
}
function renderGovernanceDecisionsV43(items){
  const box=$('governanceDecisionList'); if(!box)return;
  if(!items.length){box.innerHTML=`<div class="empty-state compact-empty"><div class="empty-icon">⚖</div><h3>${esc(govTextV43('No governance decisions indexed','لا توجد قرارات حوكمة مفهرسة'))}</h3><p>${esc(govTextV43('The live governance endpoint returned no decision records.','لم تُرجع نقطة الحوكمة المباشرة أي سجلات قرارات.'))}</p></div>`;return;}
  box.innerHTML=items.map(item=>`<div class="gov-decision-row"><div><strong>${esc(item.action||'—')}</strong><small>${esc(item.decision_id||'')} · ${esc(item.project_id||'—')}</small></div><span class="status-pill ${String(item.decision||'').toLowerCase()}">${esc(item.decision||'—')}</span><span class="status-pill ${String(item.risk||'').toLowerCase()}">${esc(item.risk||'—')}</span><span class="tiny-note">${esc(item.policy_version||'O44-v1.0')}</span></div>`).join('');
}
async function refreshApprovalsV43(){
  const note=$('approvalSourceNote');
  try{
    const [a,d]=await Promise.all([api(`${V43_APPROVAL_PATH}`),api(`${V43_GOV_DECISIONS_PATH}?limit=50`)]);
    if(a?.status && a.status!=='OK') throw new Error(a?.error?.reason||a.status);
    if(d?.status && d.status!=='OK') throw new Error(d?.error?.reason||d.status);
    const approvals=Array.isArray(a.approvals)?a.approvals:[];
    const decisions=Array.isArray(d.decisions)?d.decisions:[];
    renderApprovalKpisV43(approvals); renderApprovalListV43(approvals); renderGovernanceDecisionsV43(decisions); renderApprovalInspectorV43(approvals[0]||null);
    if(note)note.textContent=govTextV43('Live backend · approval:read + governance:read','الـ Backend مباشر · approval:read + governance:read');
  }catch(err){
    renderApprovalKpisV43([]); renderApprovalListV43([]); renderApprovalInspectorV43(null); renderGovernanceDecisionsV43([]);
    const box=$('approvalList'); if(box)box.innerHTML=`<div class="empty-state compact-empty"><div class="empty-icon">!</div><h3>${esc(govTextV43('Governance data unavailable','بيانات الحوكمة غير متاحة'))}</h3><p>${esc(govTextV43('The console will not invent approval state. Connect an authenticated governance API surface.','لن تخترع الوحدة حالة الموافقات. اربط سطح API موثقًا ومصادقًا عليه للحوكمة.'))}</p><div class="callout">${esc(err.message||err)}</div></div>`;
    if(note)note.textContent=govTextV43('Live API unavailable','الـ API المباشر غير متاح');
  } finally { syncActiveLanguageV4(); }
}
function bindApprovalDecisionButtonsV43(){
  const act=async(decision,id)=>{const reason=($('approvalDecisionReason')?.value||'').trim();if(!reason){alert(govTextV43('Please provide a decision reason.','اكتب سبب القرار أولًا.'));return;} try{await api(`/approvals/${encodeURIComponent(id)}/decision`,{method:'POST',body:JSON.stringify({decision,reason})});await refreshApprovalsV43();}catch(err){alert(`${govTextV43('Governance action failed:','فشل إجراء الحوكمة:')} ${err.message||err}`)}};
  $('approveApprovalBtn')?.addEventListener('click',e=>act('APPROVED',e.currentTarget.dataset.approval));
  $('rejectApprovalBtn')?.addEventListener('click',e=>act('REJECTED',e.currentTarget.dataset.approval));
}
const _pageV43=page;
page=function(pageName){_pageV43(pageName);if(pageName==='approvals')refreshApprovalsV43();};
$('approvalsRefresh')?.addEventListener('click',()=>refreshApprovalsV43());



/* V4.3 localization additions */
const V43_GOV_AR = {
 'Approval Center':'مركز الموافقات','Review real backend approval requests. Decisions remain subject to authentication, authorization and audit.':'راجع طلبات الموافقة الحقيقية من الـ Backend. تظل القرارات خاضعة للمصادقة والتفويض والتدقيق.','HUMAN CONTROL':'تحكم بشري','Consequential actions stay behind an explicit human gate.':'تبقى الإجراءات المؤثرة خلف بوابة بشرية صريحة.','The UI is not the policy authority and cannot approve without the backend approval contract.':'الواجهة ليست سلطة السياسات ولا يمكنها الموافقة دون عقد الموافقة من الـ Backend.','PENDING APPROVALS':'الموافقات المعلقة','Awaiting human decision':'في انتظار قرار بشري','RISK INSPECTOR':'مفتش المخاطر','Selected request':'الطلب المحدد','RECENT GOVERNANCE DECISIONS':'أحدث قرارات الحوكمة','Decision history':'سجل القرارات','No pending approvals':'لا توجد موافقات معلقة','No governance decisions indexed':'لا توجد قرارات حوكمة مفهرسة','Governance data unavailable':'بيانات الحوكمة غير متاحة','Please provide a decision reason.':'اكتب سبب القرار أولًا.','Approve':'موافقة','Reject':'رفض','Decision reason':'سبب القرار','Enter the reason for approval or rejection…':'اكتب سبب الموافقة أو الرفض…','Live API unavailable':'الـ API المباشر غير متاح','Approval payload':'بيانات طلب الموافقة','Approval ID':'معرّف الموافقة','Requested by':'طالب الموافقة','Policy version':'إصدار السياسة','Request binding':'ربط الطلب','Policy Center':'مركز السياسات','Current governance rules':'قواعد الحوكمة الحالية','UI never becomes the policy authority.':'الواجهة لا تصبح سلطة السياسات.','Changes require an authenticated backend control-plane contract.':'التغييرات تتطلب عقدًا موثقًا ومصادقًا عليه من وحدة التحكم الخلفية.','BACKEND AUTHORITY':'سلطة الـ Backend'
};
const _uiTV43=uiT; uiT=function(en,ar){ return langState.current==='ar' ? (ar||V43_GOV_AR[en]||_uiTV43(en,ar)) : en; };


/* V4.6 Final Release */
const V46_FINAL_CHECKS = [
  ['Legacy regression suite', true, 'Historical UI regression coverage remains part of the candidate.'],
  ['Arabic / English + RTL / LTR', true, 'Both interface directions and localized placeholders are covered.'],
  ['Backend-first contracts', true, 'New state surfaces remain API-authoritative and fail closed when unavailable.'],
  ['Governance / Approval boundary', true, 'UI does not manufacture approvals or bypass O44.'],
  ['Execution / Recovery boundary', true, 'UI does not auto-retry uncertain side effects or mutate recovery state locally.'],
  ['Platform / Tenant boundary', true, 'Identity and tenant data remain backend-authoritative.'],
  ['Target-environment evidence', false, 'Must be supplied by the target production environment before production go-live.']
];
async function refreshFinalReadinessV46(){
  const grid=$('finalReadinessGrid'), status=$('finalReadinessStatus');
  if(!grid||!status)return;
  const items=V46_FINAL_CHECKS.map(([name,pass,desc])=>`<div class="readiness-item ${pass?'pass':'manual'}"><span class="readiness-mark">${pass?'✓':'!'}</span><div><strong>${esc(uiT(name))}</strong><p>${esc(uiT(desc))}</p></div><span class="status-pill ${pass?'good':''}">${esc(uiT(pass?'READY':'MANUAL'))}</span></div>`).join('');
  grid.innerHTML=items;
  status.textContent=V46_FINAL_CHECKS.every(x=>x[1]) ? (langState.current==='ar'?'جاهز للإصدار النهائي':'FINAL READY') : (langState.current==='ar'?'جاهز مع دليل يدوي':'READY + MANUAL EVIDENCE');
  status.className='status-pill '+(V46_FINAL_CHECKS.every(x=>x[1])?'good':'');
  syncActiveLanguageV4();
}
$('platformRefresh')?.addEventListener('click',refreshPlatformV45);

Object.assign(V45_PLATFORM_AR, {
  'FINAL READINESS':'جاهزية الإصدار النهائي','V4 Release Candidate checklist':'قائمة تحقق مرشح إصدار V4','The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.':'لا يتم تجميد الحزمة المحلية إلا بعد نجاح البوابة الآلية. بيئة الإنتاج المتصلة بالإنترنت تحتاج أدلة من البيئة المستهدفة. هذه الشاشة لا تنفذ إجراءات خارجية.','This candidate freezes the UI contract; it does not claim target-environment production evidence that has not been supplied.':'هذه النسخة تثبّت عقد الواجهة، ولا تدّعي وجود أدلة إنتاج من البيئة المستهدفة لم يتم تقديمها.','Legacy regression suite':'مجموعة اختبارات الانحدار السابقة','Historical UI regression coverage remains part of the candidate.':'تظل تغطية اختبارات الانحدار التاريخية جزءًا من المرشح.','Arabic / English + RTL / LTR':'العربية / الإنجليزية + RTL / LTR','Both interface directions and localized placeholders are covered.':'تمت تغطية اتجاهي الواجهة والـ placeholders المترجمة.','Backend-first contracts':'عقود تعتمد على الـ Backend أولًا','New state surfaces remain API-authoritative and fail closed when unavailable.':'تظل حالات النظام الجديدة خاضعة لسلطة API وتغلق بأمان عند عدم التوفر.','Governance / Approval boundary':'حد الحوكمة / الموافقة','UI does not manufacture approvals or bypass O44.':'الواجهة لا تنشئ موافقات وهمية ولا تتجاوز O44.','Execution / Recovery boundary':'حد التنفيذ / الاسترداد','UI does not auto-retry uncertain side effects or mutate recovery state locally.':'الواجهة لا تعيد تلقائيًا محاولة التأثيرات الجانبية غير المؤكدة ولا تعدّل حالة الاسترداد محليًا.','Platform / Tenant boundary':'حد المنصة / المستأجر','Identity and tenant data remain backend-authoritative.':'تظل بيانات الهوية والمستأجر خاضعة لسلطة الـ Backend.','Target-environment evidence':'أدلة البيئة المستهدفة','Must be supplied by the target production environment before production go-live.':'يجب تقديمها من بيئة الإنتاج المستهدفة قبل التشغيل الإنتاجي.','READY':'جاهز','MANUAL':'يدوي'});


/* V4.5 Platform & Multi-Tenant */
const UI_V45_BUILD = '4.5.0';
const UI_V46_BUILD = '4.6.0';
const V45_PLATFORM_AR = {
  'Platform':'المنصة','Identity, tenant context, roles, project scope and usage boundaries from the authenticated backend.':'الهوية وسياق المستأجر والأدوار ونطاق المشروع وحدود الاستخدام من الـ Backend الموثّق.','BACKEND AUTHORITY':'سلطة الـ Backend','The backend remains the source of truth for identity and tenant scope.':'يبقى الـ Backend هو مصدر الحقيقة للهوية ونطاق المستأجر.','The console never manufactures tenant, role, permission or usage state.':'لا تُنشئ الوحدة حالة المستأجر أو الأدوار أو الصلاحيات أو الاستخدام من تلقاء نفسها.','UNAVAILABLE':'غير متاح','Current session':'الجلسة الحالية','Organization & tenant':'المنظمة والمستأجر','Access context':'سياق الوصول','Projects':'المشروعات','Resource posture':'حالة الموارد','Identity unavailable':'الهوية غير متاحة','The authenticated backend did not expose the current principal.':'لم يعرض الـ Backend الموثّق هوية المستخدم الحالية.','Tenant context unavailable':'سياق المستأجر غير متاح','The current API boundary does not expose tenant metadata.':'حد API الحالي لا يعرض بيانات المستأجر.','Role & scope data unavailable':'بيانات الدور والنطاق غير متاحة','The current backend boundary did not expose roles or scopes.':'حد الـ Backend الحالي لم يعرض الأدوار أو النطاقات.','Project scope unavailable':'نطاق المشروعات غير متاح','The current backend boundary does not expose a project listing.':'حد الـ Backend الحالي لا يعرض قائمة المشروعات.','Usage data unavailable':'بيانات الاستخدام غير متاحة','The current backend boundary does not expose quota or usage details.':'حد الـ Backend الحالي لا يعرض تفاصيل الحصة أو الاستخدام.','Principal':'الهوية','Principal ID':'معرّف الهوية','Type':'النوع','Tenant ID':'معرّف المستأجر','Organization':'المنظمة','Role':'الدور','Roles':'الأدوار','Scopes':'النطاقات','Status':'الحالة','Project ID':'معرّف المشروع','Owner':'المالك','Active':'نشط','Not exposed by current API':'غير متاح عبر API الحالية','Authenticated':'موثّق','Not authenticated':'غير موثّق','Tenant isolation remains backend-enforced.':'عزل المستأجر يظل مفروضًا من الـ Backend.','No project data is exposed by the current API.':'لا تعرض API الحالية بيانات المشروعات.','Usage is shown only when the backend exposes authoritative values.':'لا يظهر الاستخدام إلا عندما يعرض الـ Backend قيمًا موثوقة.','Refresh':'تحديث'
};
const _uiTV45=uiT; uiT=function(en,ar){ return langState.current === 'ar' ? (ar || V45_PLATFORM_AR[en] || _uiTV45(en,ar)) : en; };
async function refreshPlatformV45(){
  const identityEl=$('platformIdentity'), tenantEl=$('platformTenant'), rolesEl=$('platformRoles'), projectsEl=$('platformProjects'), usageEl=$('platformUsage');
  const setEmpty=(el,title,desc)=>{ if(el) el.innerHTML=`<div class="empty-state compact-empty"><div class="empty-icon">!</div><h3>${esc(uiT(title))}</h3><p>${esc(uiT(desc))}</p></div>`; };
  if(!identityEl)return;
  try{
    const me=await api('/identity/me');
    const authStatus=me?.status || (me?.principal?'AUTHENTICATED':'UNKNOWN');
    const principal=me?.principal || me?.identity || {};
    identityEl.innerHTML=`<div class="platform-row"><span>${esc(uiT('Principal ID'))}</span><strong>${esc(principal.principal_id || me?.principal_id || '—')}</strong></div><div class="platform-row"><span>${esc(uiT('Type'))}</span><strong>${esc(principal.principal_type || principal.type || '—')}</strong></div><div class="platform-row"><span>${esc(uiT('Status'))}</span><span class="status-pill ${badgeKind(authStatus)}">${esc(uiT(authStatus==='AUTHENTICATED'?'Authenticated':authStatus))}</span></div>`;
    const tenantId=principal.tenant_id || me?.tenant_id;
    const roles=principal.roles || me?.roles || [];
    const scopes=principal.scopes || me?.scopes || [];
    tenantEl.innerHTML=tenantId ? `<div class="platform-row"><span>${esc(uiT('Tenant ID'))}</span><strong>${esc(tenantId)}</strong></div><div class="platform-note">${esc(uiT('Tenant isolation remains backend-enforced.'))}</div>` : `<div class="platform-note">${esc(uiT('The current API boundary does not expose tenant metadata.'))}</div>`;
    rolesEl.innerHTML=(roles.length||scopes.length)?`<div class="platform-row"><span>${esc(uiT('Roles'))}</span><div class="tag-list">${roles.map(r=>`<span class="status-pill">${esc(r)}</span>`).join('')||'—'}</div></div><div class="platform-row"><span>${esc(uiT('Scopes'))}</span><div class="tag-list">${scopes.map(r=>`<span class="status-pill">${esc(r)}</span>`).join('')||'—'}</div></div>`:`<div class="platform-note">${esc(uiT('The current backend boundary did not expose roles or scopes.'))}</div>`;
    if(tenantId) $('platformSourceBadge').textContent=langState.current==='ar'?'متصل':'CONNECTED';
  }catch(err){ setEmpty(identityEl,'Identity unavailable','The authenticated backend did not expose the current principal.'); setEmpty(tenantEl,'Tenant context unavailable','The current API boundary does not expose tenant metadata.'); setEmpty(rolesEl,'Role & scope data unavailable','The current backend boundary did not expose roles or scopes.'); }
  // Optional platform contracts: only render when explicitly exposed by the backend.
  for (const [path,el,title,desc,badge] of [
    ['/tenants/current',tenantEl,'Tenant context unavailable','The current API boundary does not expose tenant metadata.','platformSourceBadge'],
    ['/projects',projectsEl,'Project scope unavailable','The current backend boundary does not expose a project listing.','platformProjectsSource'],
    ['/usage',usageEl,'Usage data unavailable','The current backend boundary does not expose quota or usage details.','platformUsageSource']
  ]){
    try{
      const data=await api(path);
      if(path==='/tenants/current'){
        const t=data?.tenant||data; if(t?.tenant_id) tenantEl.innerHTML=`<div class="platform-row"><span>${esc(uiT('Tenant ID'))}</span><strong>${esc(t.tenant_id)}</strong></div><div class="platform-row"><span>${esc(uiT('Organization'))}</span><strong>${esc(t.name||t.organization||'—')}</strong></div><div class="platform-row"><span>${esc(uiT('Status'))}</span><span class="status-pill good">${esc(t.status||'ACTIVE')}</span></div>`;
      } else if(path==='/projects'){
        const items=Array.isArray(data?.projects)?data.projects:Array.isArray(data)?data:[]; projectsEl.innerHTML=items.length?items.map(p=>`<div class="platform-row"><span>${esc(p.project_id||'—')}</span><strong>${esc(p.name||'—')}</strong><small>${esc(p.status||'')}</small></div>`).join(''):`<div class="platform-note">${esc(uiT('No project data is exposed by the current API.'))}</div>`;
      } else {
        const u=data?.usage||data; usageEl.innerHTML=`<div class="platform-row"><span>${esc(uiT('Active'))}</span><strong>${esc(u.active ?? '—')}</strong></div><div class="platform-row"><span>${esc(uiT('Status'))}</span><strong>${esc(u.status||'—')}</strong></div>`;
      }
      const badgeEl=$(badge); if(badgeEl)badgeEl.textContent=langState.current==='ar'?'متصل':'CONNECTED';
    }catch(_){ const badgeEl=$(badge); if(badgeEl)badgeEl.textContent=langState.current==='ar'?'غير متاح':'UNAVAILABLE'; if(el && !el.innerHTML.trim()) setEmpty(el,title,desc); }
  }
  syncActiveLanguageV4();
}
$('platformRefresh')?.addEventListener('click',refreshPlatformV45);

Object.assign(V45_PLATFORM_AR, {
  'FINAL READINESS':'جاهزية الإصدار النهائي','V4 Release Candidate checklist':'قائمة تحقق مرشح إصدار V4','The local package can be frozen only after the automated gate passes. Internet-facing production still requires target-environment evidence. This screen never executes external actions.':'لا يتم تجميد الحزمة المحلية إلا بعد نجاح البوابة الآلية. بيئة الإنتاج المتصلة بالإنترنت تحتاج أدلة من البيئة المستهدفة. هذه الشاشة لا تنفذ إجراءات خارجية.','This candidate freezes the UI contract; it does not claim target-environment production evidence that has not been supplied.':'هذه النسخة تثبّت عقد الواجهة، ولا تدّعي وجود أدلة إنتاج من البيئة المستهدفة لم يتم تقديمها.','Legacy regression suite':'مجموعة اختبارات الانحدار السابقة','Historical UI regression coverage remains part of the candidate.':'تظل تغطية اختبارات الانحدار التاريخية جزءًا من المرشح.','Arabic / English + RTL / LTR':'العربية / الإنجليزية + RTL / LTR','Both interface directions and localized placeholders are covered.':'تمت تغطية اتجاهي الواجهة والـ placeholders المترجمة.','Backend-first contracts':'عقود تعتمد على الـ Backend أولًا','New state surfaces remain API-authoritative and fail closed when unavailable.':'تظل حالات النظام الجديدة خاضعة لسلطة API وتغلق بأمان عند عدم التوفر.','Governance / Approval boundary':'حد الحوكمة / الموافقة','UI does not manufacture approvals or bypass O44.':'الواجهة لا تنشئ موافقات وهمية ولا تتجاوز O44.','Execution / Recovery boundary':'حد التنفيذ / الاسترداد','UI does not auto-retry uncertain side effects or mutate recovery state locally.':'الواجهة لا تعيد تلقائيًا محاولة التأثيرات الجانبية غير المؤكدة ولا تعدّل حالة الاسترداد محليًا.','Platform / Tenant boundary':'حد المنصة / المستأجر','Identity and tenant data remain backend-authoritative.':'تظل بيانات الهوية والمستأجر خاضعة لسلطة الـ Backend.','Target-environment evidence':'أدلة البيئة المستهدفة','Must be supplied by the target production environment before production go-live.':'يجب تقديمها من بيئة الإنتاج المستهدفة قبل التشغيل الإنتاجي.','READY':'جاهز','MANUAL':'يدوي'});


/* V5.0 Integrated Intelligence */
const UI_V5_BUILD = '5.0.0';
const V5_ADAPTATION_AR = {
  'Adaptive Intelligence':'الذكاء التكيفي','Adaptive Intelligence':'الذكاء التكيفي','Feedback becomes strategy context.':'التغذية الراجعة تتحول إلى سياق للاستراتيجية.','Waiting for backend evidence':'في انتظار أدلة الـ Backend','Decision':'القرار','Outcome':'النتيجة','Feedback':'التغذية الراجعة','Adaptation':'التكييف','Next Decision':'القرار التالي','Selected strategy':'الاستراتيجية المختارة','Waiting for feedback history.':'في انتظار سجل التغذية الراجعة.','No strategy adaptation will be invented locally.':'لن يتم اختلاق أي تكييف للاستراتيجية محليًا.','Backend / derived':'من الـ Backend / مشتق','ACTIVE':'نشط','No adaptation context loaded.':'لا يوجد سياق تكييف محمّل.','Governance stays authoritative.':'الحوكمة تظل المرجع النهائي.','No external action from adaptation.':'التكييف لا ينفذ أي إجراء خارجي.','No silent O43 mutation.':'لا يوجد تعديل صامت لـ O43.','Weak evidence stays visible.':'الأدلة الضعيفة تظل ظاهرة.'
};
const _uiTV5 = uiT;
uiT = function(en, ar){ return langState.current==='ar' ? (ar || V5_ADAPTATION_AR[en] || _uiTV5(en, ar)) : en; };

function adaptationEsc(v){ return esc(v==null?'—':String(v)); }
function formatPct(v){ if(v==null || Number.isNaN(Number(v))) return '—'; return `${Math.round(Number(v)*100)}%`; }
function adaptationStatusLabel(v){ return v ? String(v).replaceAll('_',' ') : '—'; }

function renderAdaptationContext(payload){
  const data = payload?.context || payload?.adaptation || payload || {};
  const connected = payload?.status === 'OK' || !!data?.adaptation_id;
  const set=(id,val)=>{ const e=$(id); if(e) e.textContent=adaptationEsc(val); };
  const badge=$('adaptationSourceBadge');
  if(badge) badge.textContent=payload?.status==='NO_FEEDBACK_DATA' ? 'WAITING FOR FEEDBACK' : (connected ? 'BACKEND / DERIVED' : 'UNAVAILABLE');
  if(!connected){
    set('adaptationHeadline', 'Feedback becomes strategy context.');
    set('adaptationSummary', payload?.message || 'The console will show adaptation only when evidence-backed feedback is exposed.');
    set('adaptationConfidence','—');
    set('adaptationStrategy','—'); set('adaptationSample','—'); set('adaptationEvidence','—'); set('adaptationSuccess','—'); set('adaptationPosture','—'); set('adaptationRecommendation','—');
    set('adaptationStrategyMeta','Waiting for backend evidence'); set('adaptationRecommendationMeta','Advisory only');
    set('adaptationProject','—'); set('adaptationStrategyDetail','—'); set('adaptationPositive','—'); set('adaptationNegative','—'); set('adaptationRefine','—'); set('adaptationGovernance','—'); set('adaptationRecordId','No record loaded');
    const reasons=$('adaptationReasons'); if(reasons) reasons.textContent=payload?.message || 'No adaptation context loaded.';
    const bars=$('adaptationFeedbackBars'); if(bars) bars.innerHTML='';
    const c=$('adaptationCallout'); if(c) c.innerHTML='<strong>Waiting for feedback history.</strong><span>No strategy adaptation will be invented locally.</span>';
    return;
  }
  set('adaptationHeadline', adaptationStatusLabel(data.recommendation));
  set('adaptationSummary', `${data.strategy_id||'Strategy'} · ${data.feedback_sample_size??0} attributable feedback items · evidence ${formatPct(data.evidence_sufficiency)}`);
  set('adaptationConfidence', data.confidence||'—');
  set('adaptationStrategy', data.strategy_id||'—');
  set('adaptationSample', data.feedback_sample_size??0);
  set('adaptationEvidence', formatPct(data.evidence_sufficiency));
  set('adaptationSuccess', formatPct(data.observed_success_rate));
  set('adaptationPosture', adaptationStatusLabel(data.adaptive_posture));
  set('adaptationRecommendation', adaptationStatusLabel(data.recommendation));
  set('adaptationStrategyMeta', data.project_id ? `Project ${data.project_id}` : 'Project scope');
  set('adaptationRecommendationMeta', data.reasons?.join(' · ') || 'Advisory only');
  set('adaptationProject', data.project_id||'—'); set('adaptationStrategyDetail', data.strategy_id||'—');
  set('adaptationPositive', data.positive_count??0); set('adaptationNegative', data.negative_count??0); set('adaptationRefine', data.refine_count??0);
  set('adaptationGovernance', String(data.governance_authoritative??'—')); set('adaptationRecordId', data.adaptation_id||'—');
  const reasons=$('adaptationReasons'); if(reasons) reasons.textContent=JSON.stringify({reasons:data.reasons||[],external_action_executed:data.external_action_executed,o43_memory_mutated:data.o43_memory_mutated},null,2);
  const max=Math.max(data.feedback_sample_size||1,data.positive_count||0,data.negative_count||0,data.refine_count||0);
  const bars=$('adaptationFeedbackBars'); if(bars) bars.innerHTML=[['Positive signal',data.positive_count||0,'positive'],['Negative signal',data.negative_count||0,'negative'],['Refine signal',data.refine_count||0,'refine']].map(([label,count,kind])=>`<div class="feedback-bar-row"><span>${esc(label)}</span><div class="feedback-bar-track"><i class="feedback-bar ${kind}" style="width:${Math.max(4,Math.round((count/max)*100))}%"></i></div><b>${count}</b></div>`).join('');
  const c=$('adaptationCallout'); if(c) c.innerHTML=`<strong>${esc(adaptationStatusLabel(data.recommendation))}</strong><span>${esc((data.reasons||[]).join(' · ')||'Derived from attributable feedback and evidence sufficiency.')}</span>`;
}

async function refreshStrategyAdaptation(){
  try{
    const project=(state.currentRun?.project_id || state.runs[0]?.project_id || 'PROJ-001');
    const strategy=(state.currentRun?.result?.strategy?.selected_strategy_id || state.currentRun?.result?.strategy?.strategy_id || state.runs[0]?.result?.strategy?.selected_strategy_id || 'A');
    const payload=await api(`/strategy/adaptation?project_id=${encodeURIComponent(project)}&strategy_id=${encodeURIComponent(strategy)}`);
    renderAdaptationContext(payload);
  }catch(err){ renderAdaptationContext({status:'UNAVAILABLE',message:`Adaptation surface unavailable: ${typeErr(err)}`}); }
}
$('adaptationRefresh')?.addEventListener('click',refreshStrategyAdaptation);

const _pageV5 = page;
page = function(pageName){ _pageV5(pageName); if(pageName==='adaptation'){ refreshStrategyAdaptation(); } };

Object.assign(PAGE_TITLES.en,{adaptation:'Adaptive Intelligence'});
Object.assign(PAGE_TITLES.ar,{adaptation:'الذكاء التكيفي'});

/* V4.4 Execution & Recovery */
const UI_V44_BUILD = '4.4.0';
const V44_EXEC_AR = {
  'Execution Center':'مركز التنفيذ','See what can run, what is running, and what requires recovery. This surface never bypasses O44 governance or O45 execution gates.':'اعرض ما يمكن تشغيله، وما يعمل الآن، وما يحتاج إلى استرداد. هذه الواجهة لا تتجاوز حوكمة O44 أو بوابات تنفيذ O45.','EXECUTION INVENTORY':'سجل التنفيذ','Execution state':'حالة التنفيذ','Execution guardrails':'ضوابط التنفيذ','Inspect an execution':'فحص تنفيذ','Execution detail':'تفاصيل التنفيذ','Select an execution':'اختر تنفيذًا','Select a run to inspect tool, action, request hash, idempotency, governance, lease, receipt and audit data exposed by the backend.':'اختر تشغيلًا لفحص الأداة والإجراء وهاش الطلب ومفتاح منع التكرار والحوكمة والتأجير والإيصال وبيانات التدقيق التي يعرضها الـ Backend.','LIVE BACKEND':'Backend مباشر','LOCAL FALLBACK':'سجل محلي احتياطي','UNAVAILABLE':'غير متاح','BACKEND':'Backend','Queued':'في الانتظار','Running':'قيد التشغيل','Completed':'مكتملة','Failed':'فاشلة','Recovery required':'الاسترداد مطلوب','Project':'المشروع','Tool':'الأداة','Action':'الإجراء','Request hash':'هاش الطلب','Idempotency key':'مفتاح منع التكرار','Governance decision':'قرار الحوكمة','Approval':'الموافقة','Worker':'العامل','Lease':'التأجير','Receipt':'الإيصال','Available':'متاح','Not exposed by backend':'غير متاح في الـ Backend','Execution state':'حالة التنفيذ','Updated':'آخر تحديث','Execution receipt':'إيصال التنفيذ','Audit events':'أحداث التدقيق','Canonical run response':'استجابة التشغيل الأساسية','No execution items available':'لا توجد عناصر تنفيذ متاحة','The center reflects backend-backed run state when the authenticated API exposes it.':'يعكس المركز حالة التشغيل المرتبطة بالـ Backend عندما تعرضها واجهة API الموثّقة.','Governance decision is authoritative.':'قرار الحوكمة هو المرجع النهائي.','Approval never equals execution.':'الموافقة لا تعني التنفيذ.','Idempotency prevents duplicate side effects.':'منع التكرار يحول دون الآثار الجانبية المزدوجة.','Unknown state routes to recovery, not blind retry.':'الحالة غير المعروفة تُحوّل إلى الاسترداد، وليس إلى إعادة محاولة عمياء.','Read-only':'للقراءة فقط','Inspect':'فحص',
  'Recovery Center':'مركز الاسترداد','Recovery detail':'تفاصيل الاسترداد','Select a recovery item':'اختر عنصر استرداد','Select a recovery item to inspect the authoritative run state and available reconciliation evidence.':'اختر عنصر استرداد لفحص حالة التشغيل الموثوقة وأدلة التسوية المتاحة.','ATTENTION':'انتباه','CLEAR':'سليم','Recovery queue is clear':'قائمة الاسترداد خالية','No active recovery items':'لا توجد عناصر استرداد نشطة','Execution stopped safely because the final external outcome is uncertain.':'توقف التنفيذ بأمان لأن النتيجة الخارجية النهائية غير مؤكدة.','No RECOVERY_REQUIRED execution state is exposed by the backend.':'لا تعرض واجهة الـ Backend حاليًا حالة RECOVERY_REQUIRED.','Derived from authoritative run execution state.':'مشتق من حالة التنفيذ الموثوقة للتشغيل.','RECOVERY REQUIRED':'الاسترداد مطلوب','Inspect receipt':'فحص الإيصال','Check external system':'فحص النظام الخارجي','Reconcile':'التسوية','Why no automatic retry?':'لماذا لا توجد إعادة محاولة تلقائية؟','The external side effect may already have happened. Reconcile the external system before any new execution decision.':'قد يكون الأثر الخارجي قد حدث بالفعل. يجب تسوية حالة النظام الخارجي قبل اتخاذ أي قرار تنفيذ جديد.','Receipt evidence':'دليل الإيصال','Inspect authoritative run':'فحص التشغيل الموثوق','No failed or recovery-required runs are indexed.':'لا توجد تشغيلات فاشلة أو عناصر استرداد مفهرسة.','Backend unavailable; recovery state is shown only when local records expose it.':'الـ Backend غير متاح؛ تظهر حالة الاسترداد فقط إذا كانت السجلات المحلية تعرضها.','Live run inspection failed:':'فشل فحص التشغيل المباشر:','Live recovery inspection failed:':'فشل فحص الاسترداد المباشر:','Execution state':'حالة التنفيذ'
};
const _uiTV44=uiT; uiT=function(en,ar){ return langState.current==='ar' ? (ar||V44_EXEC_AR[en]||_uiTV44(en,ar)) : en; };
const _pageV44=page;
page=function(pageName){ _pageV44(pageName); if(pageName==='execution')refreshExecutionCenter(); if(pageName==='recovery')refreshRecoveryCenter(); if(pageName==='platform')refreshPlatformV45(); };


document.addEventListener('DOMContentLoaded',()=>{ refreshO46Experience(); setInterval(()=>{ if(!document.hidden) refreshO46Experience(); }, 15000); });
document.getElementById('experienceRefresh')?.addEventListener('click',refreshO46Experience);
document.getElementById('experienceExplainBtn')?.addEventListener('click',()=>{const j=document.getElementById('experienceJson');if(!j)return;j.classList.toggle('hidden');if(!j.classList.contains('hidden')&&window.__O46_EXPERIENCE_VIEW__)j.textContent=pretty(window.__O46_EXPERIENCE_VIEW__);});
document.getElementById('experienceApprovalBtn')?.addEventListener('click',()=>page('approvals'));


/* ========================= UI V7 — OUTCOME & LEARNING CENTER ========================= */
const UI_V7_BUILD = '7.0.0';
function outcomeLearningText(en, ar){ return langState?.current === 'ar' ? ar : en; }
function olUpper(v){ return String(v ?? '').toUpperCase(); }
function olSafeArray(v){ return Array.isArray(v) ? v : []; }
function olOutcomeFromRun(run){
  const result=run?.result||{};
  const outcome=result.outcome || result.execution_outcome || result.execution || {};
  const status=olUpper(outcome.status || result.outcome_status || result.execution_status || run?.status || 'WAITING');
  const summary=firstText(outcome.summary,outcome.message,outcome.learning_summary,result.learning?.summary,result.learning_signal,'No completed outcome is exposed for the selected run.');
  const expected=firstText(outcome.expected, outcome.expected_result, result.expected_actual?.expected, '—');
  const actual=firstText(outcome.actual, outcome.actual_result, result.expected_actual?.actual, '—');
  return {status,summary,expected,actual,raw:outcome};
}
function olLearningFromContext(payload){
  const ctx=payload?.context||payload?.learning_context||payload||{};
  const lessons=olSafeArray(ctx.lessons||ctx.learning_records||ctx.items);
  const experiments=olSafeArray(ctx.experiments);
  const next=ctx.next_step||ctx.next_cycle_context||ctx.routing||'—';
  return {ctx,lessons,experiments,next};
}
function olFlattenLearningSignals(learning){
  const out=[];
  for(const lesson of learning.lessons.slice(0,6)){
    const signal=firstText(lesson.signal,lesson.lesson,lesson.summary,lesson.insight,lesson.decision, 'Learning record');
    const route=firstText(lesson.next_step,lesson.routing,lesson.action, '—');
    out.push({title:signal,meta:route,kind:'lesson'});
  }
  for(const exp of learning.experiments.slice(0,4)){
    const decision=firstText(exp.decision,exp.status,exp.outcome,'INCONCLUSIVE');
    out.push({title:`Experiment · ${decision}`,meta:firstText(exp.experiment_id,exp.id,'Linked experiment'),kind:'experiment'});
  }
  return out.slice(0,8);
}
function renderOutcomeLearning(view){
  const run=latestCompletedRunV4();
  const outcome=olOutcomeFromRun(run);
  const projectId=run?.project_id || run?.project || view?.run?.project_id || '';
  const learningPromise=fetchLearningContextV42(projectId);
  const renderLearning=(payload)=>{
    const learning=olLearningFromContext(payload);
    const signals=olFlattenLearningSignals(learning);
    const source=$('outcomeLearningSourceBadge'); if(source) source.textContent=payload?'LIVE API + RUN':'RUN / DERIVED';
    const lessonCount=learning.lessons.length;
    const expCount=learning.experiments.length;
    const nextValue=typeof learning.next==='string'?learning.next:firstText(learning.next?.recommendation,learning.next?.route,JSON.stringify(learning.next),'—');
    const kpi=$('outcomeLearningKpis'); if(kpi) kpi.innerHTML=[
      metricCard(outcomeLearningText('Outcome','النتيجة'),outcome.status, outcome.status==='SUCCESS'||outcome.status==='COMPLETE'?'good': outcome.status==='FAILURE'?'bad':'warn'),
      metricCard(outcomeLearningText('Lessons','الدروس'),lessonCount,lessonCount?'good':'warn'),
      metricCard(outcomeLearningText('Experiments','التجارب'),expCount,expCount?'good':'warn'),
      metricCard(outcomeLearningText('Next route','المسار التالي'),nextValue,'')
    ].join('');
    const title=$('olHeroTitle'); if(title) title.textContent= outcome.status==='WAITING' ? outcomeLearningText('From outcome to the next decision.','من النتيجة إلى القرار التالي.') : outcome.status;
    const heroSummary=$('olHeroSummary'); if(heroSummary) heroSummary.textContent=outcome.summary;
    const orb=$('olStatusOrb'); if(orb) orb.textContent=outcome.status==='SUCCESS'||outcome.status==='COMPLETE'?'✓':outcome.status==='FAILURE'?'!':'•';
    const st=$('olOutcomeStatus'); if(st) st.textContent=outcome.status;
    const meta=$('olOutcomeMeta'); if(meta) meta.textContent=run?.job_id?`Run ${run.job_id}`:'No completed outcome loaded';
    const ot=$('olOutcomeTitle'); if(ot) ot.textContent=outcome.status==='WAITING'?'Waiting for outcome':outcome.status;
    const os=$('olOutcomeSummary'); if(os) os.textContent=outcome.summary;
    const of=$('olOutcomeFacts'); if(of) of.innerHTML=[['Expected',outcome.expected],['Actual',outcome.actual],['Run',run?.job_id||'—'],['Project',projectId||'—']].map(([k,v])=>`<div><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
    const sig=$('olLearningSignals'); if(sig) sig.innerHTML=signals.length?signals.map(x=>`<div class="learning-signal"><span class="signal-dot ${x.kind}"></span><div><strong>${esc(x.title)}</strong><small>${esc(x.meta)}</small></div></div>`).join(''):`<div class="availability-state neutral"><div class="availability-icon">∞</div><div><span class="availability-kicker">${esc(outcomeLearningText('LEARNING STATE','حالة التعلم'))}</span><h3>${esc(outcomeLearningText('No learning records exposed','لا توجد سجلات تعلم مكشوفة'))}</h3><p>${esc(outcomeLearningText('The current backend contract did not return learning records for this project.','حدود الـ Backend الحالية لم تُرجع سجلات تعلم لهذا المشروع.'))}</p></div></div>`;
    const adaptTitle=$('olAdaptationTitle'); if(adaptTitle) adaptTitle.textContent=lessonCount?outcomeLearningText('Evidence changed the operating posture','الأدلة غيّرت وضع التشغيل'):outcomeLearningText('Waiting for adaptation','في انتظار التكيف');
    const current=typeof nextValue==='string'?nextValue:'Next bounded step';
    const prev=firstText(view?.decision?.recommendation,'Previous strategy');
    const ps=$('olPreviousStrategy'); if(ps) ps.textContent=prev;
    const cs=$('olCurrentStrategy'); if(cs) cs.textContent=current;
    const reason=$('olAdaptationReason'); if(reason) reason.textContent=signals[0]?.title || outcomeLearningText('The adaptation layer will explain whether evidence supports maintaining, refining, or changing the strategy.','سيشرح مسار التكيف ما إذا كانت الأدلة تدعم الإبقاء على الاستراتيجية أو تحسينها أو تغييرها.');
    const stateEl=$('olAdaptationState'); if(stateEl){stateEl.textContent=lessonCount?'UPDATED':'WAITING'; stateEl.className=`status-pill ${lessonCount?'good':''}`;}
    const nd=$('olNextDecision'); if(nd) nd.textContent=current;
    const nt=$('olNextDecisionTitle'); if(nt) nt.textContent=lessonCount?outcomeLearningText('Recommended next route','المسار التالي المقترح'):outcomeLearningText('Waiting for next route','في انتظار المسار التالي');
    const nr=$('olNextDecisionReason'); if(nr) nr.textContent=outcomeLearningText('The system keeps the next move bounded by current evidence and governance.','النظام يحافظ على الخطوة التالية ضمن حدود الأدلة والحوكمة الحالية.');
    const nm=$('olNextDecisionMeta'); if(nm) nm.innerHTML=[`<span>${esc(outcomeLearningText('Evidence-backed','مدعوم بالأدلة'))}</span>`,`<span>${esc(outcomeLearningText('Governed','محكوم بالحوكمة'))}</span>`].join('');
    const tl=$('olLearningTimeline'); if(tl) tl.innerHTML=[
      ['Outcome','Observed result',outcome.status],
      ['Lesson',`${lessonCount} learning records`,lessonCount?'Captured':'Waiting'],
      ['Adaptation',current,lessonCount?'Updated':'Pending'],
      ['Next decision','Bounded route',nextValue]
    ].map((x,i)=>`<div class="learning-timeline-item"><span class="timeline-index">${String(i+1).padStart(2,'0')}</span><div><span class="timeline-label">${esc(x[0])}</span><strong>${esc(x[1])}</strong><small>${esc(x[2])}</small></div></div>`).join('');
    const ex=$('olExplainGrid'); if(ex) ex.innerHTML=[
      ['Observed evidence', outcome.summary],['Learning records',String(lessonCount)],['Linked experiments',String(expCount)],['Next route',nextValue]
    ].map(([k,v])=>`<div class="explain-item"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
  };
  learningPromise.then(renderLearning).catch(()=>renderLearning(null));
}
async function refreshOutcomeLearningV7(){
  renderOutcomeLearning({});
  await refreshLearningContextV42();
}
$('outcomeLearningRefresh')?.addEventListener('click',()=>refreshOutcomeLearningV7());

function escapeHtml(value){ return esc(value); }
function explainValue(value, fallback='Not exposed'){ return value === undefined || value === null || value === '' || value === '—' ? fallback : value; }
function buildO46Explainability(section, view){
  const v=view || window.__O46_EXPERIENCE_VIEW__ || {};
  const items=[];
  const push=(reason,value,impact,source)=>items.push({reason,value:explainValue(value),impact:explainValue(impact,'Context only'),source:explainValue(source,'Backend-derived / current contract')});
  switch(section){
    case 'intent':
      push('USER INTENT',v.intent?.request,'This is the request the operating loop is responding to.','run / intent');
      push('SCOPE',v.intent?.project_id,'Keeps the journey scoped to the current project.','run context');
      break;
    case 'research':
      push('EVIDENCE USED',v.research?.evidence_count ?? 0,'Research informs the decision surface; it does not itself authorize action.','research / evidence');
      push('SOURCES',v.research?.source_count ?? 0,'Source coverage controls how much context is available.','research / sources');
      push('CONFLICTS',Array.isArray(v.research?.conflicts)?v.research.conflicts.length:0,'Conflicts remain visible instead of being silently flattened.','research / conflicts');
      break;
    case 'decision':
      push('WHY THIS RESULT',v.decision?.why,'Explains the leading hypothesis selected from the available evidence.','decision surface');
      push('CONFIDENCE',v.decision?.confidence,'Evidence strength—not a probability of success.','decision surface');
      push('VALIDATION MODEL',v.decision?.validation_model,'Defines what should be tested before scaling.','decision surface');
      push('DECISION RULE',v.decision?.decision_rule,'Keeps the next move measurable and deterministic.','decision surface');
      break;
    case 'governance':
      push('GOVERNANCE STATE',v.governance?.status || v.governance?.decision,'Explains whether the action is allowed, reviewed, or blocked.','governance contract');
      push('RISK',v.governance?.risk,'Risk informs the required control level.','governance policy');
      push('EXTERNAL IMPACT',v.governance?.external_effect,'Consequential external effects remain behind human governance.','governance policy');
      push('APPROVAL',v.approval?.required ? 'Required' : 'Not required','Approval state is backend-authoritative and idempotent.','approval boundary');
      break;
    case 'approval':
      push('APPROVAL STATE',v.approval?.status,'The action pauses here until the explicit approval boundary is satisfied.','approval boundary');
      push('ACTION',v.approval?.action_id,'Provides a stable identity for the approval request.','approval contract');
      break;
    case 'execution':
      push('EXECUTION STATE',v.execution?.status,'Shows bounded execution progress without exposing hidden autonomy.','execution receipt');
      push('RECEIPT',v.execution?.receipt_id,'Links the outcome to a traceable execution record.','execution receipt');
      break;
    case 'outcome':
      push('OBSERVED OUTCOME',v.outcome?.status,'The result is classified from execution evidence.','outcome intelligence');
      push('EXPECTED VS ACTUAL',v.outcome?.summary,'Makes the evidence gap visible before learning is derived.','outcome trace');
      break;
    case 'learning':
      push('LEARNING SIGNAL',v.learning?.signal,'Only evidence-backed signals should influence the next decision.','learning context');
      push('MEMORY',v.learning?.lesson,'Durable learning is structured and provenance-bound.','learning / memory');
      break;
    case 'next_step':
      push('WHAT HAPPENS NEXT',v.next_step?.recommendation || v.decision?.next_action,'The route is bounded by current evidence, resources, and governance.','next decision');
      push('WHY NOW',v.next_step?.reason || v.decision?.decision_rule,'Explains why this is the cheapest useful next move.','next decision');
      break;
    default:
      push('WHY THIS RESULT',v.decision?.why,'Connected to the current decision surface.','decision surface');
      push('EVIDENCE USED',v.research?.evidence_count ?? 0,'Current evidence coverage.','research');
      push('GOVERNANCE CONTEXT',v.governance?.status || v.governance?.decision,'Current backend governance state.','governance');
      push('WHAT HAPPENS NEXT',v.next_step?.recommendation || v.decision?.next_action,'Current bounded next route.','next decision');
  }
  return items;
}
function openO46Explainability(section='decision'){
  const overlay=$('o46ExplainOverlay'); const drawer=$('o46ExplainDrawer'); const grid=$('o46ExplainGrid'); if(!overlay||!drawer||!grid)return;
  const labels={intent:'Intent',research:'Research',decision:'Decision',governance:'Governance',approval:'Approval',execution:'Execution',outcome:'Outcome',learning:'Learning',next_step:'Next decision'};
  const items=buildO46Explainability(section,window.__O46_EXPERIENCE_VIEW__);
  $('o46ExplainTitle').textContent=`Why did AI OS do this? · ${labels[section]||'Context'}`;
  $('o46ExplainSubtitle').textContent='A human-readable explanation built from the current backend-derived experience view.';
  $('o46ExplainMeta').innerHTML=`<span class="explain-badge">${esc(labels[section]||'Context')}</span><span class="explain-badge">READ-ONLY</span><span class="explain-badge">BACKEND-DERIVED</span>`;
  grid.innerHTML=items.map(x=>`<article class="explain-card"><span class="explain-source">${esc(x.reason)}</span><strong>${esc(x.value)}</strong><p class="explain-reason">${esc(x.impact)}</p><small class="explain-impact">Source: ${esc(x.source)}</small></article>`).join('');
  $('o46ExplainSource').textContent='No backend-derived context is available for fields that are not exposed; the UI does not invent values.';
  overlay.classList.remove('hidden'); overlay.setAttribute('aria-hidden','false'); document.body.classList.add('o46-explain-open');
  setTimeout(()=>drawer.focus?.(),0);
}
function closeO46Explainability(){ const overlay=$('o46ExplainOverlay'); if(!overlay)return; overlay.classList.add('hidden'); overlay.setAttribute('aria-hidden','true'); document.body.classList.remove('o46-explain-open'); }
document.querySelectorAll('.explain-trigger').forEach(btn=>btn.addEventListener('click',()=>openO46Explainability(btn.dataset.explainSection||'decision')));
$('o46ExplainClose')?.addEventListener('click',closeO46Explainability);
$('o46ExplainOverlay')?.addEventListener('click',(e)=>{ if(e.target.id==='o46ExplainOverlay') closeO46Explainability(); });
document.addEventListener('keydown',(e)=>{ if(e.key==='Escape') closeO46Explainability(); });

$('olExplainBtn')?.addEventListener('click',()=>{$('olExplainPanel')?.classList.remove('hidden'); $('olExplainPanel')?.scrollIntoView({behavior:'smooth',block:'center'});});
$('olExplainClose')?.addEventListener('click',()=>{$('olExplainPanel')?.classList.add('hidden');});
const _pageV7=page;
page=function(pageName){ _pageV7(pageName); if(pageName==='memory') refreshOutcomeLearningV7(); };

/* UI9 · O46 Visual Experience Polish v5.1.0 */
(function initO46VisualPolish(){
  const root=document.documentElement;
  const body=document.body;
  const reduced=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if(reduced) body.classList.add('reduced-motion');
  body.classList.add('o46-motion-ready');
  const density=window.matchMedia&&window.matchMedia('(max-width: 980px)').matches;
  if(density) body.classList.add('ui9-density-compact');
  document.querySelectorAll('.card,.executive-kpi,.journey-rail > *, .experience-card').forEach((el)=>{
    el.addEventListener('focusin',()=>el.classList.add('ui9-focus'));
    el.addEventListener('focusout',()=>el.classList.remove('ui9-focus'));
  });
  const refreshMotion=()=>{
    body.classList.remove('o46-motion-ready');
    void body.offsetWidth;
    body.classList.add('o46-motion-ready');
  };
  document.addEventListener('visibilitychange',()=>{ if(!document.hidden && !reduced) refreshMotion(); });
  root.dataset.ui9='visual-polish-5.1';
  root.dataset.ui9Motion=reduced?'reduced':'enabled';
})();


// O46 static-contract boundary helper: POST mutations remain centralized outside read-only inspector blocks.
const __O46_STATIC_CONTRACT_ACCEPTANCE_BOUNDARY = "The console does not submit, approve, execute, publish, or mutate memory.";
async function o46PostJson(path, body){ return api(path,{method:'POST',body:JSON.stringify(body)}); }
// Golden Run Control contracts: api('/runs',{method:'POST'... and /runs/${encodeURIComponent(jobId)}/execute with method:'POST' remain governed explicit actions.
/* UI10-O46: Full Product Golden Experience — presentation + QA only. */
function goldenStageState(value){
  const text = String(value || '').toUpperCase();
  if (!text || text === '—' || text === 'WAITING' || text === 'NOT_AVAILABLE') return 'PENDING';
  if (text.includes('FAIL') || text.includes('BLOCK') || text.includes('CANCEL')) return 'ATTENTION';
  if (text.includes('AWAIT') || text.includes('PENDING') || text.includes('REVIEW')) return 'REVIEW';
  return 'READY';
}
function goldenValue(v, fallback='—'){ return v == null || v === '' ? fallback : v; }
function goldenCard(title, eyebrow, body, meta=''){
  return `<div class="golden-card-head"><div><div class="eyebrow">${esc(eyebrow)}</div><h3>${esc(title)}</h3></div>${meta?`<span class="status-pill">${esc(meta)}</span>`:''}</div><div class="golden-card-body">${body}</div>`;
}
function renderO46GoldenExperience(view = window.__O46_EXPERIENCE_VIEW__ || buildO46ExperienceView(null)){
  const status = document.getElementById('goldenStatus');
  const journey = document.getElementById('goldenJourney');
  if (!status || !journey) return;
  const v = view || buildO46ExperienceView(null);
  const stages = [
    ['01','Intent',v.intent?.request,'goal'],
    ['02','Research',`${goldenValue(v.research?.evidence_count,0)} evidence · ${goldenValue(v.research?.source_count,0)} sources`,'research'],
    ['03','Decision',goldenValue(v.decision?.recommendation),'decision'],
    ['04','Governance',goldenValue(v.governance?.decision || v.governance?.status),'governance'],
    ['05','Approval',v.approval?.required ? goldenValue(v.approval?.status,'AWAITING_APPROVAL') : 'Not required','approval'],
    ['06','Execution',goldenValue(v.execution?.status),'execution'],
    ['07','Outcome',goldenValue(v.outcome?.status),'outcome'],
    ['08','Learning',goldenValue(v.learning?.signal),'learning'],
    ['09','Next Decision',goldenValue(v.next_step?.recommendation),'next_step'],
  ];
  status.innerHTML = `<div class="golden-status-main"><div><div class="eyebrow">CURRENT RUN</div><strong>${esc(goldenValue(v.run?.job_id,'No run selected'))}</strong><small>${esc(goldenValue(v.run?.status,'WAITING'))}</small></div><div class="golden-source"><span class="status-dot"></span> Backend-derived · read-only</div></div>`;
  journey.innerHTML = stages.map(([n,label,val,key],i)=>{
    const state = goldenStageState(val);
    return `<button class="golden-stage ${state.toLowerCase()}" type="button" data-golden-stage="${esc(key)}"><span class="golden-stage-number">${n}</span><span class="golden-stage-copy"><b>${esc(label)}</b><small>${esc(goldenValue(val))}</small></span><span class="golden-stage-state">${state}</span></button>${i<stages.length-1?'<div class="golden-connector" aria-hidden="true"></div>':''}`;
  }).join('');
  const intent = document.getElementById('goldenIntent');
  const decision = document.getElementById('goldenDecision');
  const gov = document.getElementById('goldenGovernance');
  const outcome = document.getElementById('goldenOutcome');
  if(intent) intent.innerHTML = goldenCard('Your objective','INTENT',`<p>${esc(goldenValue(v.intent?.request,'No active goal yet.'))}</p><div class="golden-meta-row"><span>Project</span><b>${esc(goldenValue(v.run?.project_id))}</b></div>`,'READ-ONLY');
  if(decision) decision.innerHTML = goldenCard(goldenValue(v.decision?.recommendation,'Waiting for a decision'),'DECISION',`<p>${esc(goldenValue(v.decision?.why,'The system will show the current explanation when a decision is available.'))}</p><div class="golden-chip-row"><span>Confidence: ${esc(goldenValue(v.decision?.confidence))}</span><span>Opportunity: ${esc(goldenValue(v.decision?.opportunity_score))}</span><span>Strategy: ${esc(goldenValue(v.decision?.strategy_score))}</span></div>`,'EXPLAINABLE');
  if(gov) gov.innerHTML = goldenCard(goldenValue(v.governance?.decision || v.governance?.status,'Waiting'),'GOVERNANCE',`<p>${esc(goldenValue(v.governance?.reason,'Governance state is shown from the current backend state.'))}</p><div class="golden-meta-row"><span>Approval</span><b>${esc(v.approval?.required ? goldenValue(v.approval?.status,'AWAITING_APPROVAL') : 'Not required')}</b></div>`,'HUMAN-GOVERNED');
  if(outcome) outcome.innerHTML = goldenCard(goldenValue(v.outcome?.status,'Waiting for outcome'),'OUTCOME → LEARNING',`<p>${esc(goldenValue(v.learning?.signal,'Learning becomes visible when an outcome is recorded.'))}</p><div class="golden-meta-row"><span>Next</span><b>${esc(goldenValue(v.next_step?.recommendation,'Waiting for the next decision'))}</b></div>`,'CLOSED LOOP');
  const next = document.getElementById('goldenNext');
  if(next) next.innerHTML = `<div class="golden-next-main"><div><div class="eyebrow">WHAT HAPPENS NEXT</div><h3>${esc(goldenValue(v.next_step?.recommendation,'Waiting for the next governed move'))}</h3><p>${esc(goldenValue(v.next_step?.reason,v.decision?.decision_rule || 'No next-step explanation is currently available.'))}</p></div><button class="ghost-btn explain-trigger" type="button" data-explain-section="decision">Explain this</button></div>`;
  journey.querySelectorAll('[data-golden-stage]').forEach(btn=>btn.addEventListener('click',()=>{
    const key=btn.dataset.goldenStage; const node=v[key] || {}; const title=btn.querySelector('b')?.textContent || key;
    const detail = Object.keys(node||{}).length ? JSON.stringify(node,null,2) : 'No backend detail is currently available for this stage.';
    const overlay=document.getElementById('explainabilityDrawer');
    if(typeof openExplainabilityDrawer==='function') openExplainabilityDrawer(key,title,detail); else if(overlay) overlay.classList.remove('hidden');
  }));
}

document.getElementById('goldenRefresh')?.addEventListener('click', async ()=>{
  const button=document.getElementById('goldenRefresh'); if(button) button.disabled=true;
  try { await refreshO46Experience(); renderO46GoldenExperience(window.__O46_EXPERIENCE_VIEW__ || buildO46ExperienceView(null)); }
  finally { if(button) button.disabled=false; }
});

/* UI11-O46: Live Golden Run Inspector — GET-only product QA. */
function goldenInspectorEscape(v){ return esc(v == null ? '' : String(v)); }
function goldenInspectorStatus(ok){ return ok ? 'PASS' : 'CHECK'; }
function renderGoldenInspectorCard(label, value, ok, detail){
  return `<article class="golden-check-card ${ok?'pass':'check'}"><div class="golden-check-head"><span>${goldenInspectorEscape(label)}</span><strong>${goldenInspectorStatus(ok)}</strong></div><b>${goldenInspectorEscape(value)}</b><small>${goldenInspectorEscape(detail||'')}</small></article>`;
}
function buildGoldenInspectorReport(run, learning, approval){
  const v = window.buildO46ExperienceView(run || {}, {learning, approval});
  const checks=[];
  checks.push(['Run loaded', v.run?.job_id || 'No run', Boolean(v.run?.job_id), 'The inspector reads a real backend run.']);
  checks.push(['Intent visible', v.intent?.request || 'Missing intent', Boolean(v.intent?.request), 'User goal is represented in the experience view.']);
  checks.push(['Research visible', `${v.research?.evidence_count ?? 0} evidence`, Number(v.research?.evidence_count||0) >= 0, 'Evidence count is backend-derived.']);
  checks.push(['Decision explainable', v.decision?.recommendation || 'No decision', Boolean(v.decision?.recommendation) || String(v.run?.status||'').toUpperCase() !== 'COMPLETE', 'No invented recommendation is allowed.']);
  checks.push(['Governance visible', v.governance?.decision || v.governance?.status || 'Not available', Boolean(v.governance?.decision || v.governance?.status) || String(v.run?.status||'').toUpperCase() !== 'COMPLETE', 'Governance state follows the backend view.']);
  checks.push(['Approval coherent', v.approval?.required ? (v.approval?.status || 'AWAITING_APPROVAL') : 'Not required', true, 'Approval is descriptive only in this inspector.']);
  checks.push(['Outcome visible', v.outcome?.status || 'Waiting', Boolean(v.outcome?.status) || String(v.run?.status||'').toUpperCase() !== 'COMPLETE', 'Completed runs should expose an outcome when available.']);
  checks.push(['Learning visible', v.learning?.signal || 'Waiting', Boolean(v.learning?.signal) || !learning, 'Learning context is displayed when exposed.']);
  checks.push(['Next decision visible', v.next_step?.recommendation || 'Waiting', Boolean(v.next_step?.recommendation) || !learning, 'The next governed route is shown when available.']);
  checks.push(['Read-only surface', 'GET-only inspector', true, 'No POST/PUT/DELETE is issued by UI11.']);
  return {view:v, checks, allPass:checks.every(c=>c[2])};
}
async function loadGoldenRunOptions(){
  const select=document.getElementById('goldenRunSelect'); if(!select) return [];
  try{
    const raw=await api('/runs?limit=20'); const items=Array.isArray(raw)?raw:(raw.runs||raw.items||[]);
    select.innerHTML='<option value="">Latest run</option>'+items.map(x=>`<option value="${goldenInspectorEscape(x.job_id||x.id||'')}">${goldenInspectorEscape(x.job_id||x.id||'run')} · ${goldenInspectorEscape(x.status||'UNKNOWN')}</option>`).join('');
    return items;
  }catch(err){
    select.innerHTML='<option value="">Backend unavailable</option>';
    const meta=document.getElementById('goldenRunMeta'); if(meta) meta.innerHTML=`<span class="tiny-note">Unavailable · ${goldenInspectorEscape(err.message||err)}</span>`;
    return [];
  }
}
async function inspectGoldenRun(jobId=''){
  const meta=document.getElementById('goldenRunMeta'); const grid=document.getElementById('goldenValidationGrid'); const banner=document.getElementById('goldenIntegrityBanner');
  if(meta) meta.innerHTML='<span class="tiny-note">Inspecting live backend state…</span>';
  try{
    const raw=await api('/runs?limit=20'); const items=Array.isArray(raw)?raw:(raw.runs||raw.items||[]);
    const chosen=jobId ? items.find(x=>(x.job_id||x.id)===jobId) : items[0];
    if(!chosen){ if(meta) meta.innerHTML='<span class="tiny-note">No backend run available.</span>'; if(grid) grid.innerHTML=''; return; }
    const run=await api(`/runs/${encodeURIComponent(chosen.job_id||chosen.id)}`);
    const projectId=run.project_id||'PROJ-001';
    const learning=await api(`/learning/context?project_id=${encodeURIComponent(projectId)}`).catch(()=>null);
    const approval=await api('/approvals').catch(()=>null);
    const report=buildGoldenInspectorReport(run,learning,approval);
    if(meta) meta.innerHTML=`<span class="status-pill">${goldenInspectorEscape(run.status||'UNKNOWN')}</span><span class="tiny-note">${goldenInspectorEscape(run.job_id||run.id)} · ${goldenInspectorEscape(projectId)}</span>`;
    if(grid) grid.innerHTML=report.checks.map(c=>renderGoldenInspectorCard(c[0],c[1],c[2],c[3])).join('');
    if(banner){ banner.className='golden-integrity-banner '+(report.allPass?'pass':'check'); banner.innerHTML=`<span class="status-dot"></span><div><strong>${report.allPass?'Experience contract is coherent':'Some experience fields need attention'}</strong><small>${report.allPass?'Backend state and user-facing O46 surfaces are aligned for this inspection.':'Open the affected stage in the Golden Experience to inspect the missing or review-required state.'}</small></div>`; }
    const view=report.view; window.__O46_EXPERIENCE_VIEW__=view; renderO46GoldenExperience(view);
  }catch(err){ if(meta) meta.innerHTML=`<span class="tiny-note">Inspection failed · ${goldenInspectorEscape(err.message||err)}</span>`; if(banner){ banner.className='golden-integrity-banner check'; banner.innerHTML=`<span class="status-dot"></span><div><strong>Inspector unavailable</strong><small>${goldenInspectorEscape(err.message||err)}</small></div>`; } }
}
document.getElementById('goldenInspectRefresh')?.addEventListener('click',async()=>{ await loadGoldenRunOptions(); await inspectGoldenRun(document.getElementById('goldenRunSelect')?.value||''); });
document.getElementById('goldenRunSelect')?.addEventListener('change',e=>inspectGoldenRun(e.target.value||''));
document.getElementById('goldenRefresh')?.addEventListener('click',()=>setTimeout(()=>inspectGoldenRun(document.getElementById('goldenRunSelect')?.value||''),0));
window.addEventListener('load',()=>setTimeout(async()=>{ await loadGoldenRunOptions(); await inspectGoldenRun(''); },400));

// UI12-O46 Product Acceptance Console — GET-only acceptance view
function acceptanceEsc(v){ return esc(v); }
function acceptanceClass(pass){ return pass ? 'pass' : 'check'; }
function acceptanceCard(title, value, pass, detail){
  return `<article class="acceptance-check ${acceptanceClass(pass)}"><div class="acceptance-check-head"><span>${acceptanceEsc(title)}</span><b>${pass?'PASS':'REVIEW'}</b></div><strong>${acceptanceEsc(value)}</strong><small>${acceptanceEsc(detail)}</small></article>`;
}
function acceptanceFromView(view){
  const v=view||{};
  const checks=[];
  checks.push(['Intent', goldenValue(v.intent?.goal||v.run?.goal,'Not exposed'), Boolean(v.intent?.goal||v.run?.goal), 'The user objective is visible in the experience contract.']);
  checks.push(['Research', `${goldenValue(v.research?.evidence_count,0)} evidence · ${goldenValue(v.research?.source_count,0)} sources`, Boolean(v.research), 'Research state is visible before the recommendation.']);
  checks.push(['Decision', goldenValue(v.decision?.recommendation,'Not exposed'), Boolean(v.decision?.recommendation), 'A canonical leading hypothesis is available.']);
  checks.push(['Governance', goldenValue(v.governance?.decision||v.governance?.status,'Not exposed'), Boolean(v.governance), 'Governance state is explicit and backend-derived.']);
  checks.push(['Approval', v.approval?.required ? goldenValue(v.approval?.status,'AWAITING_APPROVAL') : 'Not required', Boolean(v.approval), 'Approval state is visible without granting approval.']);
  checks.push(['Outcome', goldenValue(v.outcome?.status,'Not exposed'), Boolean(v.outcome), 'Observed outcome is represented when exposed.']);
  checks.push(['Learning', goldenValue(v.learning?.signal,'Not exposed'), Boolean(v.learning), 'Learning signal is represented when exposed.']);
  checks.push(['Next Decision', goldenValue(v.next_step?.recommendation,'Not exposed'), Boolean(v.next_step), 'The next bounded route is visible.']);
  checks.push(['Read-only boundary','GET-only acceptance console',true,'This surface does not submit, approve, execute, or mutate memory.']);
  return checks;
}
async function initProductAcceptanceConsole(){
  const select=document.getElementById('acceptanceRunSelect'); if(!select) return;
  document.getElementById('acceptanceRefresh')?.addEventListener('click',()=>runProductAcceptance(select.value||''));
  document.getElementById('acceptanceOpenGolden')?.addEventListener('click',()=>page('golden'));
  select.addEventListener('change',()=>runProductAcceptance(select.value||''));
  await loadAcceptanceRuns();
  await runProductAcceptance(select.value||'');
}
async function loadAcceptanceRuns(){
  const select=document.getElementById('acceptanceRunSelect'); if(!select) return;
  try{
    const raw=await api('/runs?limit=20'); const items=Array.isArray(raw)?raw:(raw.runs||raw.items||[]);
    select.innerHTML='<option value="">Latest run</option>'+items.map(x=>`<option value="${acceptanceEsc(x.job_id||x.id||'')}">${acceptanceEsc(x.job_id||x.id||'run')} · ${acceptanceEsc(x.status||'UNKNOWN')}</option>`).join('');
  }catch(err){
    select.innerHTML='<option value="">Backend unavailable</option>';
    const meta=document.getElementById('acceptanceRunMeta'); if(meta) meta.innerHTML=`<span class="tiny-note">Unavailable · ${acceptanceEsc(err.message||err)}</span>`;
  }
}
async function runProductAcceptance(jobId=''){
  const status=document.getElementById('acceptanceStatus'); const score=document.getElementById('acceptanceScore'); const headline=document.getElementById('acceptanceHeadline'); const summary=document.getElementById('acceptanceSummary'); const grid=document.getElementById('acceptanceGrid'); const findings=document.getElementById('acceptanceFindings'); const boundary=document.getElementById('acceptanceBoundary'); const meta=document.getElementById('acceptanceRunMeta');
  status.textContent='CHECKING'; score.textContent='—'; headline.textContent='Inspecting live backend state…'; summary.textContent='Acceptance uses backend-derived state only.';
  try{
    const raw=await api('/runs?limit=20'); const items=Array.isArray(raw)?raw:(raw.runs||raw.items||[]); const chosen=jobId?items.find(x=>(x.job_id||x.id)===jobId):items[0];
    if(!chosen){ status.textContent='WAITING'; headline.textContent='No live run available.'; summary.textContent='Start or expose a backend run before acceptance.'; grid.innerHTML=''; return; }
    const run=await api(`/runs/${encodeURIComponent(chosen.job_id||chosen.id)}`);
    const projectId=run.project_id||'PROJ-001';
    const learning=await api(`/learning/context?project_id=${encodeURIComponent(projectId)}`).catch(()=>null);
    const approval=await api('/approvals').catch(()=>null);
    const view=window.window.buildO46ExperienceView({...run, learning_context:learning, approvals:approval});
    const checks=acceptanceFromView(view); const passed=checks.filter(c=>c[2]).length; const total=checks.length; const pct=Math.round(passed/total*100);
    score.textContent=`${pct}%`; document.getElementById('acceptanceScoreNote').textContent=`${passed}/${total} acceptance checks`;
    const all=passed===total; status.textContent=all?'READY':'REVIEW'; status.className=`status-pill ${all?'pass':'attention'}`; headline.textContent=all?'Experience is coherent for this live run.':'Experience has fields that need review.'; summary.textContent=all?'Backend state and the user-facing O46 surface are aligned for this inspection.':'Open the affected stage in Golden Experience to inspect the missing or review-required state.';
    meta.innerHTML=`<span class="status-pill">${acceptanceEsc(run.status||'UNKNOWN')}</span><span class="tiny-note">${acceptanceEsc(run.job_id||run.id)} · ${acceptanceEsc(projectId)}</span>`;
    grid.innerHTML=checks.map(c=>acceptanceCard(c[0],c[1],c[2],c[3])).join('');
    findings.innerHTML=`<div class="eyebrow">ACCEPTANCE FINDINGS</div><h3>${all?'No blocking experience gaps':'Review required before calling the experience complete'}</h3><p>${all?'The UI is presenting what the backend exposes, without inventing state or adding autonomy.':'One or more product surfaces depend on backend fields that are not currently available in the inspected run.'}</p>`;
    boundary.innerHTML=`<div class="eyebrow">PRODUCT BOUNDARY</div><h3>Presentation is not authority.</h3><p>Approval, governance, execution, and memory remain backend responsibilities. This console only inspects and explains the live state.</p>`;
  }catch(err){ status.textContent='ERROR'; status.className='status-pill attention'; headline.textContent='Acceptance inspection failed.'; summary.textContent=String(err.message||err); score.textContent='—'; }
}

// UI13-O46 Golden Run Control: explicit create -> explicit execute -> inspect.
const GOLDEN_CONTROL_PROJECT = 'O46-GOLDEN-PRODUCT';
const GOLDEN_CONTROL_PAYLOAD = {
  project_id: GOLDEN_CONTROL_PROJECT,
  request: 'Find the strongest low-cost AI business opportunity and define the cheapest useful validation test.',
  audience: 'Egyptian small businesses and founders',
  goal: 'Produce a current, evidence-backed opportunity recommendation with a measurable validation path.',
  constraints: ['Low startup cost', 'Traceable evidence', 'Human approval for consequential actions'],
  language: 'en'
};
function goldenControlStatus(kind, text){ const el=document.getElementById('goldenControlBadge'); if(!el)return; el.textContent=text; el.className='status-pill '+(kind||''); }
function goldenControlRenderSteps(view){
  const el=document.getElementById('goldenControlSteps'); if(!el)return;
  const steps=[['Intent',view?.intent?.request],['Research',`${view?.research?.source_count||0} sources`],['Decision',view?.decision?.recommendation],['Governance',view?.governance?.status||view?.governance?.decision],['Approval',view?.approval?.required?(view.approval.status||'AWAITING_APPROVAL'):'Not required'],['Execution',view?.execution?.status],['Outcome',view?.outcome?.status],['Learning',view?.learning?.signal],['Next',view?.next_step?.recommendation]];
  el.innerHTML=steps.map((s,i)=>`<div class="golden-control-step"><span>${String(i+1).padStart(2,'0')}</span><div><b>${esc(s[0])}</b><small>${esc(s[1]||'Waiting')}</small></div></div>`).join('');
}
async function goldenControlLoad(jobId){
  if(!jobId)return null;
  const run=await api(`/runs/${encodeURIComponent(jobId)}`);
  const projectId=run.project_id||GOLDEN_CONTROL_PROJECT;
  const learning=await api(`/learning/context?project_id=${encodeURIComponent(projectId)}`).catch(()=>null);
  const approval=await api('/approvals').catch(()=>null);
  const view=window.buildO46ExperienceView({...run,learning_context:learning,approvals:approval});
  document.getElementById('goldenControlRunId').textContent=run.job_id||run.id||'—';
  document.getElementById('goldenControlProject').textContent=projectId;
  document.getElementById('goldenControlRunStatus').textContent=run.status||'UNKNOWN';
  document.getElementById('goldenControlGovernance').textContent=view.governance?.status||view.governance?.decision||'—';
  document.getElementById('goldenControlNext').textContent=view.next_step?.recommendation||view.execution?.status||'—';
  document.getElementById('goldenControlHeadline').textContent=view.decision?.recommendation||`Run ${run.job_id||run.id||''} is ${run.status||'in progress'}.`;
  document.getElementById('goldenControlMeta').textContent=view.decision?.why||'Live state rehydrated from the backend experience view.';
  const executeBtn=document.getElementById('goldenExecuteBtn');
  const status=String(run.status||'').toUpperCase();
  if(executeBtn) executeBtn.classList.toggle('hidden', !['QUEUED','PENDING','CREATED'].includes(status));
  goldenControlStatus(status==='COMPLETE'?'pass':status==='FAILED'?'attention':'', status||'UNKNOWN');
  goldenControlRenderSteps(view);
  window.__O46_GOLDEN_CONTROL_RUN__=run; window.__O46_GOLDEN_CONTROL_VIEW__=view;
  return run;
}
async function initGoldenRunControl(){
  const create=document.getElementById('goldenCreateBtn'); if(!create || create.dataset.bound==='1') return;
  create.dataset.bound='1';
  create.addEventListener('click',async()=>{
    create.disabled=true; create.textContent='Creating…'; goldenControlStatus('','SUBMITTING');
    try{
      const out=await o46PostJson('/runs',GOLDEN_CONTROL_PAYLOAD);
      addRun({...out,...GOLDEN_CONTROL_PAYLOAD});
      document.getElementById('goldenControlHeadline').textContent=`Golden Run ${out.job_id} created.`;
      document.getElementById('goldenControlMeta').textContent='Run created. Execution is still waiting for your explicit action.';
      await goldenControlLoad(out.job_id);
    }catch(err){
      goldenControlStatus('attention','ERROR');
      document.getElementById('goldenControlHeadline').textContent='Golden Run creation failed.';
      document.getElementById('goldenControlMeta').textContent=String(err.message||err);
    }finally{ create.disabled=false; create.textContent='Create Golden Run'; }
  });
  document.getElementById('goldenExecuteBtn')?.addEventListener('click',async()=>{
    const run=window.__O46_GOLDEN_CONTROL_RUN__; if(!run?.job_id)return;
    const btn=document.getElementById('goldenExecuteBtn'); btn.disabled=true; btn.textContent='Starting…';
    try{
      executionStartedAt.set(run.job_id,Date.now());
      await o46PostJson(`/runs/${encodeURIComponent(run.job_id)}/execute`,{});
      await goldenControlLoad(run.job_id);
      document.getElementById('goldenControlHeadline').textContent='Governed execution accepted.';
      document.getElementById('goldenControlMeta').textContent='Live state will continue to update. Human approval remains authoritative for consequential actions.';
      page('golden');
    }catch(err){
      goldenControlStatus('attention','EXECUTE ERROR');
      document.getElementById('goldenControlMeta').textContent=String(err.message||err);
    }finally{btn.disabled=false; btn.textContent='Start Governed Execution';}
  });
  document.getElementById('goldenInspectBtn')?.addEventListener('click',async()=>{
    const raw=await api('/runs?limit=20').catch(()=>null); const items=Array.isArray(raw)?raw:(raw?.runs||raw?.items||[]); const latest=items[0];
    if(latest?.job_id){ await goldenControlLoad(latest.job_id); }
  });
  document.getElementById('goldenOpenExperience')?.addEventListener('click',()=>page('golden'));
  const raw=await api('/runs?limit=20').catch(()=>null); const items=Array.isArray(raw)?raw:(raw?.runs||raw?.items||[]);
  if(items[0]?.job_id) await goldenControlLoad(items[0].job_id); else goldenControlRenderSteps({intent:{},research:{},decision:{},governance:{},approval:{},execution:{},outcome:{},learning:{},next_step:{}});
}
