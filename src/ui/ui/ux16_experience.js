/* UI16 — Real Data & UX Audit: hydrate the existing O46 executive experience from the authenticated backend. */
(function(){
  'use strict';

  const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const text = (v, fallback='—') => v === undefined || v === null || v === '' ? fallback : String(v);
  const arr = v => Array.isArray(v) ? v : [];

  async function api(path, opts={}) {
    if (typeof window.api === 'function') return window.api(path, opts);
    const base = (sessionStorage.getItem('aios.apiBase') || '/api').replace(/\/$/, '');
    const token = sessionStorage.getItem('aios.bearer') || '';
    const headers = {'Content-Type':'application/json'};
    if (token) headers.Authorization = 'Bearer ' + token;
    const r = await fetch(base + path, {...opts, headers:{...headers, ...(opts.headers||{})}});
    const p = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(p?.error?.reason || p?.reason || p?.status || ('HTTP ' + r.status));
    return p;
  }

  function stamp(v){
    return Date.parse(v || '') || 0;
  }

  function listRuns(raw){
    const xs = Array.isArray(raw) ? raw : (raw?.runs || raw?.items || []);
    return xs.filter(Boolean).sort((a,b) => {
      const sa = Math.max(stamp(a.updated_at), stamp(a.completed_at), stamp(a.created_at), stamp(a.timestamp));
      const sb = Math.max(stamp(b.updated_at), stamp(b.completed_at), stamp(b.created_at), stamp(b.timestamp));
      return sb - sa;
    });
  }

  async function latestRun(){
    const preferred = sessionStorage.getItem('aios.lastJobId') || localStorage.getItem('aios.lastJobId');
    if (preferred) {
      try { return await api('/runs/' + encodeURIComponent(preferred)); } catch {}
    }
    const raw = await api('/runs?limit=25');
    const runs = listRuns(raw);
    const preferred = sessionStorage.getItem('aios.lastJobId') || localStorage.getItem('aios.lastJobId');
    const picked = preferred ? runs.find(r => (r.job_id || r.id) === preferred) : null;
    const candidate = picked || runs[0] || null;
    if (!candidate) return null;
    const id = candidate.job_id || candidate.id;
    if (!id || candidate.result || candidate.decision_surface || candidate.request) return candidate;
    try { return await api('/runs/' + encodeURIComponent(id)); } catch { return candidate; }
  }

  function unwrap(run){
    const root = run || {};
    const result = root.result || root.run_result || root.output || {};
    const d = root.decision_surface || root.decision || result.decision_surface || result.decision || result.business_decision || {};
    const evidence = root.evidence || root.research || result.evidence || result.research || {};
    const gov = root.governance || result.governance || {};
    const approval = root.approval || result.approval || {};
    const outcome = root.outcome || result.outcome || {};
    const learning = root.learning || result.learning || {};
    const execution = root.execution || result.execution || {};
    const request = root.request || result.request || '';
    return {
      run: root,
      result,
      request,
      decision: {
        recommendation:d.recommendation || d.title || d.recommended_product || d.recommended_direction,
        why:d.why_this_direction || d.why || d.rationale,
        problem:d.customer_problem || d.problem,
        customer:d.target_customer || d.customer || d.audience,
        validation:d.validation_model,
        longTerm:d.long_term_product_model,
        mvp:d.mvp_direction,
        firstTest:d.first_validation_test,
        threshold:d.success_threshold,
        rule:d.decision_rule,
        next:d.next_action,
        promise:d.customer_outcome || d.promise,
        positioning:d.positioning,
        opportunity:d.opportunity_score,
        strategy:d.strategy_score,
        confidence:d.confidence,
        boundary:d.market_evidence_boundary || d.evidence_boundary,
        localEvidence:d.local_evidence
      },
      evidence,
      gov,
      approval,
      outcome,
      learning,
      execution
    };
  }

  function setText(id, value, fallback='—'){
    const el = document.getElementById(id);
    if (el) el.textContent = text(value, fallback);
  }

  function setHtml(id, value){
    const el = document.getElementById(id);
    if (el) el.innerHTML = value;
  }

  function stateBadge(state){
    const v = String(state || 'WAITING').toUpperCase();
    if (['COMPLETE','PASS','READY','GO','APPROVED'].includes(v)) return 'PASS';
    if (['FAILED','BLOCK','NO-GO','CANCELLED'].includes(v)) return 'BLOCKED';
    if (['QUEUED','RUNNING','PENDING','REVIEW','REFINE','AWAITING_APPROVAL'].includes(v)) return 'REVIEW';
    return v;
  }

  function evidenceCount(e){
    return e?.evidence_count ?? e?.count ?? (Array.isArray(e?.evidence) ? e.evidence.length : Array.isArray(e?.items) ? e.items.length : undefined);
  }

  function sourceCount(e){
    return e?.source_count ?? e?.sources_count ?? (Array.isArray(e?.sources) ? e.sources.length : Array.isArray(e?.source_items) ? e.source_items.length : undefined);
  }

  function bind(v){
    const run = v.run || {};
    const d = v.decision;
    const status = run.status || 'WAITING';
    const approvalStatus = v.approval?.status || v.approval?.decision || v.gov?.approval || 'PENDING';
    const govStatus = v.gov?.status || v.gov?.decision || approvalStatus || 'PENDING';

    setText('experienceSource', `Live run · ${run.job_id || run.id || 'backend'}`);
    setText('executiveRecommendation', d.recommendation, 'Waiting for a decision');
    setText('executiveWhy', d.why, 'No rationale exposed by the current run.');
    setText('executiveConfidence', d.confidence, '—');
    setText('executiveConfidenceNote', d.confidence ? 'Evidence strength' : 'No confidence exposed');
    setText('executiveOpportunity', d.opportunity);
    setText('executiveStrategy', d.strategy);
    setText('executiveEvidenceCount', evidenceCount(v.evidence));
    setText('executiveSourceCount', sourceCount(v.evidence));
    setText('executiveConflictCount', v.evidence?.conflict_count ?? v.evidence?.conflicts?.length ?? 0);
    setText('executiveGovernanceState', govStatus, 'PENDING');
    setText('executiveGovernanceNote', v.gov?.reason || v.gov?.reason_code || 'Backend governance state');
    setText('executiveNextAction', d.next, 'Review the current decision surface');
    setText('executiveNextReason', d.rule || d.firstTest || 'Use the current evidence and validation rule to decide the next move.');
    setText('executiveRunState', stateBadge(status));
    setText('executiveRunMeta', `${run.project_id || '—'} · ${run.job_id || run.id || '—'}`);

    setText('experienceDecisionTitle', d.recommendation, 'No decision yet');
    setText('experienceDecisionStatus', stateBadge(status));
    setText('experienceDecisionWhy', d.why, 'No rationale exposed by the current run.');
    setText('experienceNextAction', d.next);
    setText('experienceDecisionRule', d.rule);
    setText('experienceEvidenceScore', d.confidence);
    setText('experienceGovernanceTitle', govStatus === 'PENDING' ? 'Human review boundary active' : 'Governance state');
    setText('experienceGovernanceStatus', stateBadge(approvalStatus));
    setText('experienceGovernanceAction', v.gov?.action_type || 'Consequential action remains human-governed');
    setText('experienceGovernanceReason', v.gov?.reason || 'The backend remains authoritative for approval and policy decisions.');
    setText('experienceOutcomeTitle', v.outcome?.status || 'Awaiting observed outcome');
    setText('experienceOutcomeSummary', v.outcome?.summary || v.outcome?.message || (status === 'COMPLETE' ? 'Run completed; inspect outcome evidence and validation loop.' : 'Outcome will appear after execution is observed.'));
    setText('experienceLearningSignal', v.learning?.signal || v.learning?.lesson || '—');
    setText('experienceNextDecision', v.learning?.next_step || v.learning?.next_decision || d.next || '—');

    const statHost = document.getElementById('experienceDecisionStats');
    if (statHost) {
      statHost.innerHTML = [
        ['Target customer', d.customer],
        ['Validation model', d.validation],
        ['Long-term product', d.longTerm],
        ['Opportunity', d.opportunity],
        ['Strategy', d.strategy],
        ['Confidence', d.confidence]
      ].map(([k,val]) => `<div class="experience-mini-stat"><span>${esc(k)}</span><strong>${esc(text(val))}</strong></div>`).join('');
    }

    const mini = document.getElementById('experienceEvidenceMini');
    if (mini) {
      mini.innerHTML = [
        ['Sources', sourceCount(v.evidence)],
        ['Evidence', evidenceCount(v.evidence)],
        ['Local', d.localEvidence],
        ['Boundary', d.boundary]
      ].map(([k,val]) => `<div><span>${esc(k)}</span><strong>${esc(text(val))}</strong></div>`).join('');
    }

    const list = document.getElementById('experienceEvidenceList');
    if (list) {
      const items = arr(v.evidence?.evidence || v.evidence?.items || v.evidence?.claims).slice(0,8);
      list.innerHTML = items.length ? items.map((x,i) => `<div class="experience-list-row"><b>${esc(x.claim || x.title || x.name || `Evidence ${i+1}`)}</b><small>${esc(x.source || x.source_id || x.type || 'backend evidence')}</small></div>`).join('') : `<div class="experience-empty-inline">${esc(d.localEvidence || 'Evidence items are not exposed in the current run payload.')}</div>`;
    }

    const trace = document.getElementById('experienceTraceChips');
    if (trace) {
      trace.innerHTML = [
        ['Run', run.job_id || run.id],
        ['Status', status],
        ['Recommendation', d.recommendation],
        ['Validation', d.validation],
        ['Governance', govStatus],
        ['Approval', approvalStatus]
      ].map(([k,val]) => `<span class="trace-chip"><b>${esc(k)}</b>${esc(text(val))}</span>`).join('');
    }

    const fill = document.getElementById('experienceEvidenceFill');
    if (fill) {
      const n = typeof d.confidence === 'number' ? Math.max(0, Math.min(1, d.confidence)) : null;
      fill.style.width = n == null ? '0%' : Math.round(n * 100) + '%';
    }

    const nextHero = document.getElementById('nextActionText');
    if (nextHero) nextHero.textContent = text(d.next, 'Review the current operating state');

    const checked = document.getElementById('execChecked');
    if (checked) checked.textContent = new Date().toLocaleTimeString();
  }

  async function hydrate(){
    try {
      const run = await latestRun();
      if (!run) {
        setText('experienceSource','Backend ready · no run available');
        return null;
      }
      sessionStorage.setItem('aios.lastJobId', run.job_id || run.id || '');
      const full = run.job_id || run.id ? await api('/runs/' + encodeURIComponent(run.job_id || run.id)).catch(() => run) : run;
      const v = unwrap(full);
      bind(v);
      return v;
    } catch (e) {
      setText('experienceSource','Backend ready · data unavailable');
      setText('executiveRecommendation','Backend data unavailable');
      setText('executiveWhy', e.message || 'The current run could not be hydrated safely.');
      return null;
    }
  }

  function installRefresh(){
    const b = document.getElementById('experienceRefresh');
    if (b && !b.dataset.ui16Bound) {
      b.dataset.ui16Bound = '1';
      b.addEventListener('click', async () => {
        b.disabled = true;
        try { await hydrate(); } finally { b.disabled = false; }
      });
    }
  }

  async function boot(){
    await hydrate();
    installRefresh();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else setTimeout(boot, 0);
})();
