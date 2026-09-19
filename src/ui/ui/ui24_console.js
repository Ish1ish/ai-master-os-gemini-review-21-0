/* UI24 — Unified Console Experience. Presentation-first, backend-derived, explicit-action preserving. */
(function(){
  'use strict';
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const s=v=>(v==null||v==='')?'—':String(v);
  const arr=v=>Array.isArray(v)?v:[];
  const stamp=v=>Date.parse(v||'')||0;
  const api=async path=>{
    if(typeof window.api==='function') return window.api(path);
    const base=(sessionStorage.getItem('aios.apiBase')||'/api').replace(/\/$/,'');
    const token=sessionStorage.getItem('aios.bearer')||'';
    const h={'Content-Type':'application/json'}; if(token) h.Authorization='Bearer '+token;
    const r=await fetch(base+path,{headers:h}); const p=await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(p?.error?.reason||p?.reason||p?.status||('HTTP '+r.status)); return p;
  };
  function deep(root,pred,depth=0){if(!root||depth>8||typeof root!=='object')return null;if(pred(root))return root;for(const v of Object.values(root)){const h=deep(v,pred,depth+1);if(h)return h;}return null;}
  function summaryValue(v){
    if(v==null) return '';
    if(typeof v==='string'){
      const t=v.trim(); if(!t)return '';
      if((t[0]==='{'||t[0]==='[')){
        try{return summaryValue(JSON.parse(t));}catch{}
      }
      return t;
    }
    if(Array.isArray(v)) return v.slice(0,3).map(summaryValue).filter(Boolean).join(' · ');
    if(typeof v==='object'){
      for(const k of ['summary','signal','lesson_summary','learning_summary','message','next_test','recommendation','route','decision_summary']) if(v[k]){const x=summaryValue(v[k]);if(x)return x;}
      const nested=v.learning||v.lesson||v.context||v.next_step; if(nested){const x=summaryValue(nested);if(x)return x;}
    }
    return '';
  }
  function normalize(run,learning,approvals){
    const r=run||{}, out=r.result||r.run_result||r.output||{};
    const d=r.decision_surface||r.decision||out.decision_surface||out.decision||deep(out,x=>x&&typeof x==='object'&&('recommendation' in x)&&('decision_rule' in x))||{};
    const candidate=deep(out,x=>x&&typeof x==='object'&&('customer_segment' in x)&&('opportunity_score' in x))||{};
    const e=r.evidence||out.evidence||out.market?.evidence||{};
    const gov=r.governance||out.governance||{};
    const appr=r.approval||out.approval||{};
    const learningObj=r.learning||out.learning||{};
    const outcome=r.outcome||out.outcome||{};
    const experiments=out.experiments||r.experiments||deep(out,x=>x&&typeof x==='object'&&Array.isArray(x.experiments))||{};
    const recommendation=d.recommendation||d.recommended_opportunity||d.title||candidate.title||candidate.idea;
    const target=d.target_customer||d.customer||candidate.customer_segment||out.target_customer||out.audience;
    const rawLearning=learningObj.signal||learningObj.summary||learningObj.learning_summary||learningObj.lesson||deep(out,x=>x&&typeof x==='object'&&('learning_signal' in x))?.learning_signal||summaryValue(learningObj)||summaryValue(learning);
    return {
      run:r,request:r.request||out.request,goal:r.goal||out.goal,audience:r.audience||out.audience,scope:r.scope||out.scope||'Egypt',constraints:r.constraints||out.constraints||[],recommendation,
      why:d.why_this_direction||d.why||d.rationale||candidate.evidence_summary,problem:d.customer_problem||d.problem||candidate.problem,
      target,validation:d.validation_model||candidate.validation_model||candidate.validation_test?.customer_need,longTerm:d.long_term_product_model||candidate.business_model||candidate.solution_format,
      mvp:d.mvp_direction||candidate.solution_format,firstTest:d.first_validation_test||candidate.validation_test?.customer_need,threshold:d.success_threshold,rule:d.decision_rule||candidate.validation_test?.willingness_to_pay,
      next:d.next_action||candidate.validation_test?.customer_need||'Validate the recommended opportunity before committing capital or external actions.',promise:d.customer_outcome||d.promise||candidate.desired_outcome,
      opportunity:d.opportunity_score??candidate.opportunity_score,strategyScore:d.strategy_score,confidence:d.confidence||candidate.confidence,
      boundary:d.market_evidence_boundary||d.evidence_boundary||out.market?.report?.evidence_boundary,localEvidence:d.local_evidence||out.market?.report?.local_evidence,
      sourceCount:e.source_count??arr(e.sources).length,evidenceCount:e.evidence_count??arr(e.evidence||e.items||e.claims).length, sources:arr(e.sources), conflicts:arr(e.conflicts),
      risk:gov.risk||out.governance?.risk,approval:appr.status||appr.decision||gov.approval||'PENDING',approvalObj:appr,
      learningSignal:rawLearning,outcomeStatus:outcome.status||outcome.outcome_status||out.analytics?.status,learning:learningObj,learningContext:learning,
      experiments:Array.isArray(experiments)?experiments:(experiments.experiments||[]),policies:out.policies||r.policies||null,analytics:out.analytics||r.analytics||null
    };
  }
  function score(v){const st=String(v.run?.status||'').toUpperCase();return (st==='COMPLETE'?40:st==='RUNNING'?20:10)+(v.recommendation?18:0)+(v.evidenceCount>0?15:0)+(v.sourceCount>0?8:0)+(v.validation?6:0)+(v.next?5:0)+(v.learningSignal?4:0)+(v.outcomeStatus?4:0);}
  async function canonicalRun(){
    const raw=await api('/runs?limit=25'); const runs=(Array.isArray(raw)?raw:(raw.runs||raw.items||[])).filter(Boolean); if(!runs.length)return null;
    const candidates=[]; for(const base of runs.slice(0,12)){const id=base.job_id||base.id;if(!id)continue;try{candidates.push(await api('/runs/'+encodeURIComponent(id)));}catch{candidates.push(base);}}
    candidates.sort((a,b)=>score(normalize(b))-score(normalize(a)) || stamp(b.updated_at||b.completed_at||b.created_at)-stamp(a.updated_at||a.completed_at||a.created_at)); return candidates[0]||runs[0];
  }
  function pageVisible(){return document.querySelector('.page:not(.hidden)');}
  function stripOldOverlays(){
    document.querySelectorAll('.ui21-surface').forEach(e=>e.remove());
    document.querySelectorAll('.page').forEach(p=>{p.classList.remove('u21-active');p.querySelectorAll('.u21-hide-original').forEach(e=>e.classList.remove('u21-hide-original'));p.querySelectorAll('.u21-keep-original').forEach(e=>e.classList.remove('u21-keep-original'));});
  }
  function enforceSingle(){
    const activeNav=document.querySelector('.nav-item.active[data-page]'); const wanted=activeNav?document.getElementById('page-'+activeNav.dataset.page):pageVisible(); if(!wanted)return;
    document.querySelectorAll('.page').forEach(p=>{if(p===wanted){p.classList.remove('u22-hidden-force');p.classList.remove('hidden');p.removeAttribute('aria-hidden');}else{p.classList.remove('u22-visible-force');p.classList.add('hidden');p.setAttribute('aria-hidden','true');}});
  }
  function contextHtml(v){
    if(!v)return `<div class="u24-context"><div class="u24-card u24-live"><span class="u24-live-dot"></span><div><strong>Backend data unavailable</strong><small>No canonical run was exposed. Nothing is invented.</small></div></div></div>`;
    const status=String(v.run.status||'WAITING').toUpperCase();
    return `<div class="u24-context"><div class="u24-card u24-live"><span class="u24-live-dot"></span><div><strong>${esc(v.run.job_id||v.run.id||'—')}</strong><small>${esc(v.run.project_id||'')} · ${esc(status)} · backend-derived</small></div></div><div class="u24-card"><span>Decision</span><strong>${esc(v.recommendation||'Not exposed')}</strong><small>${esc(v.confidence||'Confidence not exposed')}</small></div><div class="u24-card"><span>Evidence</span><strong>${esc(v.sourceCount)} sources · ${esc(v.evidenceCount)} evidence</strong><small>${esc(v.boundary||'Evidence boundary not exposed')}</small></div><div class="u24-card"><span>Governance</span><strong>${esc(v.approval)}</strong><small>${esc(v.risk||'Risk not exposed')}</small></div><div class="u24-card"><span>Scores</span><strong>${esc(v.opportunity)} · ${esc(v.strategyScore)}</strong><small>Prioritization heuristics</small></div></div>`;
  }
  function mountContext(page,v){page.querySelector('.u24-context')?.remove();const div=document.createElement('div');div.innerHTML=contextHtml(v);page.prepend(div.firstElementChild);}
  function stage(label,state,detail,n){const s=String(state||'WAITING').toUpperCase();const cls=/COMPLETE|READY|PASS/.test(s)?'done':/REVIEW|PENDING|AWAITING/.test(s)?'review':'pending';return `<div class="u24-step ${cls}"><div class="u24-step-num">${String(n).padStart(2,'0')}</div><b>${esc(label)}</b><small>${esc(detail||s)}</small></div>`;}
  function runSection(v){
    const gov=/PENDING|AWAITING|REVIEW/i.test(String(v.approval||''))?'REVIEW':'COMPLETE';
    return `<section class="u24-section"><div class="u24-section-head"><div><h3>Canonical operating journey</h3><p>One run, one source of truth, one visual story.</p></div><span class="u24-pulse"><span class="u24-live-dot"></span>${esc(String(v.run?.status||'WAITING').toUpperCase())}</span></div><div class="u24-timeline">${stage('Understand',v.request?'COMPLETE':'WAITING',v.request||'Request not exposed',1)}${stage('Research',v.evidenceCount>0?'COMPLETE':'WAITING',`${v.sourceCount||0} sources · ${v.evidenceCount||0} evidence`,2)}${stage('Route','COMPLETE','Engine path resolved',3)}${stage('Decide',v.recommendation?'COMPLETE':'WAITING',v.recommendation||'Decision not exposed',4)}${stage('Govern',gov,`${v.approval||'Not exposed'}${v.risk?` · risk ${v.risk}`:''}`,5)}${stage('Execute',String(v.run?.status||'').toUpperCase()==='COMPLETE'?'COMPLETE':'WAITING',String(v.run?.status||'Waiting'),6)}${stage('Outcome',v.outcomeStatus?'COMPLETE':'WAITING',v.outcomeStatus||'Outcome not exposed',7)}${stage('Learn',v.learningSignal?'COMPLETE':'WAITING',v.learningSignal||'Learning not exposed',8)}${stage('Next Decision',v.next?'READY':'WAITING',v.next||'Next action not exposed',9)}</div></section>`;
  }
  function insertAfterContext(page,html){page.querySelector('.u24-extra')?.remove();const holder=document.createElement('div');holder.className='u24-extra';holder.innerHTML=html;const ctx=page.querySelector('.u24-context');ctx?.after(holder);}
  function enhanceLearningText(){
    const nodes=document.querySelectorAll('#experienceLearningSignal,#olHeroSummary,#olOutcomeSummary,#goldenOutcome p,.golden-summary-grid .card p');
    nodes.forEach(n=>{const raw=(n.textContent||'').trim();if(raw.startsWith('{')||raw.startsWith('["')||raw.includes('lesson_id')){const v=summaryValue(raw);if(v)n.textContent=v;}});
  }
  function enhanceExperiments(page,v){
    // Replace only the experiment registry surface; do not touch other operational pages.
    page.querySelectorAll('.u24-experiment-rebuild').forEach(e=>e.remove());
    [...page.children].forEach(el=>{if(el.id!=='page-experiments' && !el.classList.contains('u24-context')) el.classList.add('u24-hide-redundant');});
    const items=arr(v?.experiments);const box=document.createElement('section');box.className='u24-section u24-experiment-rebuild';
    const body=items.length?`<div class="u24-list">${items.map((x,i)=>`<div class="u24-row"><b>EXP-${String(i+1).padStart(2,'0')}</b><span>${esc(x.hypothesis||x.title||'Experiment')}</span><small>${esc(x.primary_metric||x.metric||'Metric not exposed')}</small></div>`).join('')}</div>`:`<div class="u24-empty"><h3>No experiment registry exposed for this run</h3><p>The backend run is available, but this API contract does not expose a separate experiment registry. AI Master OS will not invent experiments.</p></div>`;
    box.innerHTML=`<div class="u24-panel"><div class="u24-eyebrow">VALIDATION REGISTRY</div><h3>Experiments connected to the canonical run</h3>${body}</div>`;page.appendChild(box);
  }
  function enhancePage(page,v){
    if(!page)return; stripOldOverlays(); mountContext(page,v);
    const id=page.id;
    if(id==='page-overview') insertAfterContext(page,runSection(v)+`<section class="u24-section"><div class="u24-grid"><div class="u24-panel"><h3>What the system recommends</h3><p>${esc(v.recommendation||'No recommendation exposed.')}</p><div class="u24-chip-row"><span class="u24-chip">Target · ${esc(v.target||v.audience)}</span><span class="u24-chip">Validation · ${esc(v.validation)}</span><span class="u24-chip">Product · ${esc(v.longTerm)}</span><span class="u24-chip">Confidence · ${esc(v.confidence)}</span></div></div><div class="u24-panel"><h3>What happens next</h3><p>${esc(v.next)}</p><div class="u24-chip-row"><span class="u24-chip ${/PENDING|REVIEW/i.test(String(v.approval))?'u24-review':'u24-good'}">Governance · ${esc(v.approval)}</span><span class="u24-chip">Risk · ${esc(v.risk)}</span></div></div></div></section>`);
    else if(id==='page-golden') insertAfterContext(page,runSection(v)+`<section class="u24-section"><div class="u24-grid"><div class="u24-panel"><h3>Intent + validation</h3><div class="u24-kv"><div><label>Request</label><strong>${esc(v.request)}</strong></div><div><label>Goal</label><strong>${esc(v.goal)}</strong></div><div><label>Target customer</label><strong>${esc(v.target||v.audience)}</strong></div><div><label>First test</label><strong>${esc(v.firstTest)}</strong></div></div></div><div class="u24-panel"><h3>Decision + learning</h3><div class="u24-kv"><div><label>Recommendation</label><strong>${esc(v.recommendation)}</strong></div><div><label>Decision rule</label><strong>${esc(v.rule)}</strong></div><div><label>Outcome</label><strong>${esc(v.outcomeStatus||'Not exposed')}</strong></div><div><label>Learning</label><strong class="u24-learning-copy">${esc(v.learningSignal||'Not exposed')}</strong></div></div></div></div></section>`);
    else if(id==='page-acceptance') insertAfterContext(page,`<section class="u24-section"><div class="u24-banner"><div><strong>Acceptance is descriptive, not authoritative.</strong><p>The console inspects the canonical run; it never grants approval, execution or memory authority.</p></div><span class="u24-pulse">GET-ONLY</span></div></section>`);
    else if(id==='page-goldenrun') insertAfterContext(page,runSection(v)+`<section class="u24-section"><div class="u24-grid"><div class="u24-panel"><h3>Canonical reference</h3><div class="u24-kv"><div><label>Run</label><strong>${esc(v.run?.job_id)}</strong></div><div><label>Status</label><strong>${esc(v.run?.status)}</strong></div><div><label>Next action</label><strong>${esc(v.next)}</strong></div><div><label>Governance</label><strong>${esc(v.approval)}</strong></div></div></div><div class="u24-panel"><h3>Control boundary</h3><p>Create and execute remain explicit user actions. Approval is backend-controlled and consequential effects remain human-governed.</p></div></div></section>`);
    else if(id==='page-experiments') enhanceExperiments(page,v);
    else if(id==='page-memory') insertAfterContext(page,`<section class="u24-section"><div class="u24-grid"><div class="u24-panel"><h3>What was learned</h3><p>${esc(v.learningSignal||'No learning signal is exposed for the canonical run.')}</p></div><div class="u24-panel"><h3>Next bounded decision</h3><p>${esc(v.next)}</p></div></div></section>`);
    else if(id==='page-adaptation') insertAfterContext(page,`<section class="u24-section"><div class="u24-grid"><div class="u24-panel"><h3>Adaptive posture</h3><p>Positive/negative learning must be backed by observed outcomes. The current canonical signal is:</p><div class="u24-chip-row"><span class="u24-chip">Learning · ${esc(v.learningSignal||'Not exposed')}</span><span class="u24-chip">Outcome · ${esc(v.outcomeStatus||'Not exposed')}</span></div></div><div class="u24-panel"><h3>Next bounded move</h3><p>${esc(v.next)}</p></div></div></section>`);
    else if(id==='page-evidence') insertAfterContext(page,`<section class="u24-section"><div class="u24-grid"><div class="u24-panel"><h3>Evidence boundary</h3><p>${esc(v.boundary||'Evidence boundary not exposed by the canonical run.')}</p></div><div class="u24-panel"><h3>Local evidence</h3><p>${esc(v.localEvidence||'Local evidence summary not exposed.')}</p></div></div></section>`);
    else if(id==='page-decisions') insertAfterContext(page,`<section class="u24-section"><div class="u24-panel"><h3>Decision snapshot</h3><div class="u24-kv"><div><label>Recommendation</label><strong>${esc(v.recommendation)}</strong></div><div><label>Why</label><strong>${esc(v.why)}</strong></div><div><label>Success threshold</label><strong>${esc(v.threshold)}</strong></div><div><label>Decision rule</label><strong>${esc(v.rule)}</strong></div></div></div></section>`);
    else if(id==='page-approvals') insertAfterContext(page,`<section class="u24-section"><div class="u24-banner"><div><strong>${esc(v.approval||'PENDING')}</strong><p>${esc(v.risk||'Risk not exposed')} · Human review remains required before consequential external action.</p></div><span class="u24-pulse">BACKEND AUTHORITY</span></div></section>`);
    else if(id==='page-policies') insertAfterContext(page,`<section class="u24-section"><div class="u24-panel"><h3>Policy posture for the canonical run</h3><div class="u24-grid3"><div class="u24-card"><span>External action</span><strong>Human-gated</strong><small>Not granted by the UI.</small></div><div class="u24-card"><span>Memory mutation</span><strong>Backend-controlled</strong><small>Presentation layer cannot authorize it.</small></div><div class="u24-card"><span>Auditability</span><strong>Traceable</strong><small>Run state should remain attributable.</small></div></div></div></section>`);
    else if(id==='page-audit') insertAfterContext(page,`<section class="u24-section"><div class="u24-panel"><h3>Canonical run trace</h3><div class="u24-list">${[['Created',v.run?.created_at],['Updated',v.run?.updated_at],['Completed',v.run?.completed_at]].filter(x=>x[1]).map(x=>`<div class="u24-row"><b>${esc(x[0])}</b><span>${esc(x[1])}</span><small>backend-derived</small></div>`).join('')||'<div class="u24-empty"><h3>No audit events exposed</h3><p>The API does not expose a separate audit event stream for this run.</p></div>'}</div></div></section>`);
    else if(id==='page-guide') insertAfterContext(page,`<section class="u24-section"><div class="u24-grid"><div class="u24-panel"><h3>Recommended operator flow</h3><div class="u24-list">${[['01','Create a governed run','Start with request, goal and target customer.'],['02','Inspect evidence','Confirm sources, evidence count and boundary.'],['03','Review the decision','Read recommendation, rationale, validation model and rule.'],['04','Review governance','Consequential actions remain behind the human gate.'],['05','Capture outcome and learning','Use observed evidence for the next bounded decision.']].map(x=>`<div class="u24-row"><b>${x[0]}</b><span>${esc(x[1])}</span><small>${esc(x[2])}</small></div>`).join('')}</div></div><div class="u24-panel"><h3>Golden run in this console</h3><p>Every major surface should point back to the same canonical run, not manufacture its own state.</p></div></div></section>`);
    else if(id==='page-platform'||id==='page-settings'||id==='page-health'||id==='page-operations'||id==='page-release'||id==='page-execution'||id==='page-recovery') insertAfterContext(page,`<section class="u24-section"><div class="u24-banner"><div><strong>Canonical run context</strong><p>${esc(v.run?.job_id||'No run selected')} · ${esc(v.run?.status||'WAITING')} · ${esc(v.recommendation||'No recommendation exposed')}</p></div><span class="u24-pulse">READ / INSPECT</span></div></section>`);
    page.classList.add('u24-final'); enhanceLearningText();
  }
  let cached=null,busy=false,lastPage='';
  async function refresh(){if(busy)return;busy=true;try{cached=normalize(await canonicalRun(),null,null);}catch{cached=null}finally{busy=false}}
  async function boot(){stripOldOverlays();enforceSingle();await refresh();const p=pageVisible();if(p)enhancePage(p,cached||normalize(null,null,null));}
  function schedule(){clearTimeout(schedule.t);schedule.t=setTimeout(async()=>{enforceSingle();const p=pageVisible();if(!p)return;const id=p.id;if(id!==lastPage){lastPage=id;await refresh();}enhancePage(p,cached||normalize(null,null,null));},120);}
  document.addEventListener('click',e=>{const nav=e.target.closest('.nav-item[data-page]');if(nav)setTimeout(schedule,160);},true);
  document.addEventListener('DOMContentLoaded',boot);window.addEventListener('load',()=>setTimeout(schedule,250));window.addEventListener('hashchange',schedule);
  if(document.readyState!=='loading')setTimeout(boot,80);
})();
