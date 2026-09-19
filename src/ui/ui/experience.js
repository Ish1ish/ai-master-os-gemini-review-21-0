/* O46 UI-1: Unified Experience View Model + Experience Shell */
const O46_EXPERIENCE_BUILD = '1.0.0';
const O46_EXPERIENCE_DASHBOARD_BUILD = '1.1.0';
const O46_EXPERIENCE_RUN_STORY_BUILD = '1.2.0';
const EX_STAGE_KEYS = ['intent','research','decision','governance','approval','execution','outcome','learning','next_step'];
const exVal = (v, fallback='—') => (v === undefined || v === null || v === '' ? fallback : v);
const exStatus = (node) => String(node?.status || node?.state || node?.decision || 'NOT_AVAILABLE').toUpperCase();
const exArray = (v) => Array.isArray(v) ? v : [];
const exFirst = (...vals) => vals.find(v => v !== undefined && v !== null && v !== '');
function buildO46ExperienceView(run, extras={}) {
  const r = run || {};
  const result = r.result || r.output || r.data || {};
  const decisionSurface = result.decision_surface || result.decision || r.decision_surface || {};
  const market = result.market || result.research || {};
  const governance = result.governance || r.governance || {};
  const approval = extras.approval || result.approval || r.approval || {};
  const execution = result.execution || r.execution || {};
  const outcome = result.outcome || r.outcome || {};
  const learning = extras.learning || result.learning || r.learning || {};
  const experiment = extras.experiment || result.experiment || {};
  const evidence = result.evidence || market.evidence || {};
  const next = exFirst(learning.next_decision, learning.next_step, result.next_decision, result.next_step, r.next_step, {});
  const intent = result.intent || r.intent || { request: r.request || r.base_request || '' };
  const sources = exArray(market.sources || market.evidence_refs || evidence.refs || evidence.sources);
  const localEvidence = exArray(evidence.local || evidence.local_evidence || market.local_evidence);
  const conflicts = exArray(evidence.conflicts || market.conflicts);
  return {
    run: { job_id:exVal(r.job_id), project_id:exVal(r.project_id), status:exStatus(r), created_at:exVal(r.created_at), updated_at:exVal(r.updated_at) },
    intent: { request:exVal(intent.request || intent.base_request, 'No request captured'), goal:exVal(intent.goal), audience:exVal(intent.audience), language:exVal(intent.language) },
    research: { status:exStatus(market), source_count:exFirst(market.source_count, market.sources_count, sources.length, 0), evidence_count:exFirst(evidence.count, evidence.evidence_count, localEvidence.length, 0), sources, local_evidence:localEvidence, conflicts, summary:exFirst(market.summary, market.report?.summary, evidence.summary) },
    decision: { recommendation:exFirst(decisionSurface.recommendation, decisionSurface.recommended_direction, result.recommendation, result.strategy?.recommended_model_name), why:exFirst(decisionSurface.why_this_direction, decisionSurface.rationale, result.strategy?.rationale), customer_problem:exFirst(decisionSurface.customer_problem, result.positioning?.problem), target_customer:exFirst(decisionSurface.target_customer, result.positioning?.target_customer), validation_model:exFirst(decisionSurface.validation_model, result.validation?.recommended_model), long_term_product_model:decisionSurface.long_term_product_model, mvp_direction:decisionSurface.mvp_direction, first_validation_test:decisionSurface.first_validation_test, success_threshold:decisionSurface.success_threshold, decision_rule:decisionSurface.decision_rule, next_action:decisionSurface.next_action, opportunity_score:exFirst(decisionSurface.opportunity_score, result.opportunity_score), strategy_score:exFirst(decisionSurface.strategy_score, result.strategy_score), confidence:exFirst(decisionSurface.confidence, result.confidence), evidence_boundary:exFirst(decisionSurface.market_evidence_boundary, decisionSurface.evidence_boundary) },
    governance: { status:exStatus(governance), decision:exFirst(governance.decision, governance.status, r.governance_decision), risk:exFirst(governance.risk, governance.risk_level), action_type:exFirst(governance.action_type, governance.action), reason:exFirst(governance.reason, governance.reason_code), policy_version:exFirst(governance.policy_version, governance.policy), external_effect:exFirst(governance.external_effect, governance.external), authoritative:governance.governance_authoritative },
    approval: { status:exStatus(approval), required:exFirst(approval.required, governance.approval_required, approval.status === 'AWAITING_APPROVAL'), action_id:exFirst(approval.action_id, approval.intent_id, governance.action_id), reason:exFirst(approval.reason, governance.reason), decision:exFirst(approval.decision), idempotent:approval.idempotent },
    execution: { status:exStatus(execution), tool:exFirst(execution.tool, execution.tool_name), action:exFirst(execution.action, execution.action_type), request_hash:execution.request_hash, idempotency_key:execution.idempotency_key, receipt:execution.receipt, worker:execution.worker, lease:execution.lease, external_action_executed:exFirst(execution.external_action_executed, r.external_action_executed, false) },
    outcome: { status:exStatus(outcome), expected_actual:exFirst(outcome.expected_actual, outcome.comparison), success:outcome.success, summary:exFirst(outcome.summary, outcome.result, outcome.message) },
    learning: { status:exStatus(learning), signal:exFirst(learning.learning_signal, learning.signal), lesson:exFirst(learning.lesson, learning.insight), decision_impact:exFirst(learning.decision_impact, learning.impact), context_id:exFirst(learning.context_id, extras.learning?.context_id), memory_mutated:exFirst(learning.memory_mutated, learning.o43_memory_mutated, false) },
    next_step: { status:exStatus(next), recommendation:exFirst(next.recommendation, next.action, next.next_action), route:exFirst(next.route, next.routing), reason:exFirst(next.reason, next.rationale) },
    provenance: { run_id:exVal(r.job_id), trace_id:exFirst(r.trace_id, result.trace_id, governance.trace_id, outcome.trace_id), evidence_refs:exFirst(result.evidence_refs, decisionSurface.evidence_refs, []), provider:exFirst(r.provider, result.provider, result.provenance?.provider), prompt_hash:result.provenance?.prompt_hash, raw_output_hash:result.provenance?.raw_output_hash }
  };
}

function renderO46RunStory(view) {
  const root = document.getElementById('o46RunStory');
  if (!root || !view) return;
  const stageDefs = [
    ['intent','Intent','The request the system received.',view.intent.request],
    ['research','Research','What the system investigated.',view.research.summary || `${view.research.source_count || 0} sources · ${view.research.evidence_count || 0} evidence`],
    ['decision','Decision','The leading hypothesis selected from evidence.',view.decision.recommendation || 'No decision yet'],
    ['governance','Governance','Risk, policy and external-effect evaluation.',view.governance.decision || view.governance.status || 'Waiting'],
    ['approval','Approval','Whether a human gate is required.',view.approval.required ? (view.approval.status || 'AWAITING_APPROVAL') : 'Not required'],
    ['execution','Execution','The bounded execution state.',view.execution.status || 'Waiting'],
    ['outcome','Outcome','What actually happened.',view.outcome.summary || view.outcome.status || 'Waiting'],
    ['learning','Learning','What the result changes for the next cycle.',view.learning.lesson || view.learning.signal || 'Waiting'],
    ['next_step','Next','The next governed move.',view.next_step.recommendation || view.next_step.route || 'Waiting']
  ];
  const current = stageDefs.findIndex(x => exStatus(view[x[0]]) !== 'NOT_AVAILABLE');
  root.innerHTML = `\
    <div class="run-story-head">\
      <div><div class="eyebrow">RUN STORY</div><h3>Watch the intelligence journey</h3><p>From your request to the next decision, every stage is connected to the same backend-derived run.</p></div>\
      <div class="run-story-status"><span class="run-story-pulse"></span><span>${esc(view.run.status || 'WAITING')}</span></div>\
    </div>\
    <div class="run-story-track">${stageDefs.map(([key,label,desc,value],i)=>{\
      const state = i===current ? 'active' : (i<current ? 'complete' : 'upcoming');\
      return `<button type="button" class="run-story-node ${state}" data-story-stage="${esc(key)}">\
        <span class="run-story-node-index">${String(i+1).padStart(2,'0')}</span>\
        <span class="run-story-node-copy"><b>${esc(label)}</b><small>${esc(value || '—')}</small></span>\
      </button>`;\
    }).join('')}</div>\
    <div class="run-story-detail" id="runStoryDetail"></div>\
  `;
  const details = {
    intent: ['Intent', view.intent.request, `Goal: ${view.intent.goal || '—'}`],
    research: ['Research', view.research.summary || 'Evidence collection and market intelligence', `${view.research.source_count || 0} sources · ${view.research.evidence_count || 0} evidence · ${view.research.conflicts?.length || 0} conflicts`],
    decision: ['Decision', view.decision.recommendation || 'No decision yet', `Why: ${view.decision.why || '—'}`],
    governance: ['Governance', view.governance.decision || view.governance.status || 'Waiting', `Risk: ${view.governance.risk || '—'} · Policy: ${view.governance.policy_version || '—'} · External: ${view.governance.external_effect || '—'}`],
    approval: ['Approval', view.approval.required ? (view.approval.status || 'AWAITING_APPROVAL') : 'Not required', view.approval.reason || 'No human approval is required for this path.'],
    execution: ['Execution', view.execution.status || 'Waiting', `Tool: ${view.execution.tool || '—'} · Receipt: ${view.execution.receipt || '—'}`],
    outcome: ['Outcome', view.outcome.status || 'Waiting', view.outcome.summary || 'Outcome evidence will appear after execution completes.'],
    learning: ['Learning', view.learning.signal || view.learning.lesson || 'Waiting', `Impact: ${view.learning.decision_impact || '—'} · Memory mutated: ${view.learning.memory_mutated ? 'yes' : 'no'}`],
    next_step: ['Next', view.next_step.recommendation || view.next_step.route || 'Waiting', view.next_step.reason || 'The system will surface the next governed move.']
  };
  const detail = document.getElementById('runStoryDetail');
  const show = (key) => { const d=details[key] || details.intent; if(detail) detail.innerHTML=`<div class="run-story-detail-label">${esc(d[0])}</div><h4>${esc(d[1] || '—')}</h4><p>${esc(d[2] || '—')}</p>`; };
  root.querySelectorAll('[data-story-stage]').forEach(btn=>btn.addEventListener('click',()=>show(btn.dataset.storyStage)));
  show(stageDefs[current>=0?current:0]?.[0] || 'intent');
}
window.renderO46RunStory = renderO46RunStory;

window.buildO46ExperienceView = buildO46ExperienceView;
window.O46_EXPERIENCE_BUILD = O46_EXPERIENCE_BUILD;
window.O46_EXPERIENCE_DASHBOARD_BUILD = O46_EXPERIENCE_DASHBOARD_BUILD;
window.O46_EXPERIENCE_RUN_STORY_BUILD = O46_EXPERIENCE_RUN_STORY_BUILD;
