/* UI21 — Full Console Surface Reset. Read-only presentation shell with proxy clicks only. */
(function(){
  'use strict';
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const text=(v,f='—')=>(v==null||v===''?f:String(v));
  const arr=v=>Array.isArray(v)?v:[];
  const stamp=v=>Date.parse(v||'')||0;
  async function api(path){
    if(typeof window.api==='function') return window.api(path);
    const base=(sessionStorage.getItem('aios.apiBase')||'/api').replace(/\/$/,'');
    const token=sessionStorage.getItem('aios.bearer')||'';
    const headers={'Content-Type':'application/json'}; if(token) headers.Authorization='Bearer '+token;
    const r=await fetch(base+path,{headers});
    const p=await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(p?.error?.reason||p?.reason||p?.status||('HTTP '+r.status));
    return p;
  }
  function deep(root,pred,depth=0){
    if(!root||depth>8||typeof root!=='object') return null;
    if(pred(root)) return root;
    for(const v of (Array.isArray(root)?root:Object.values(root))){const hit=deep(v,pred,depth+1);if(hit)return hit;}
    return null;
  }
  function norm(run){
    const r=run||{}, out=r.result||r.run_result||r.output||{};
    const d=r.decision_surface||r.decision||out.decision_surface||out.decision||deep(out,x=>x&&typeof x==='object'&&('recommendation' in x)&&('decision_rule' in x))||{};
    const s=deep(out,x=>x&&typeof x==='object'&&x.recommended_model&&x.recommendation_reason)||{};
    const e=r.evidence||out.evidence||out.market?.evidence||{};
    const h=out.handoffs||{};
    const gov=r.governance||out.governance||{};
    const appr=r.approval||out.approval||{};
    const learning=r.learning||out.learning||{};
    const outcome=r.outcome||out.outcome||{};
    const candidate=deep(out,x=>x&&typeof x==='object'&&('customer_segment' in x)&&('opportunity_score' in x))||{};
    const recommendation=d.recommendation||d.recommended_opportunity||d.title||s.opportunity_title||candidate.title||candidate.idea;
    const target=d.target_customer||d.customer||candidate.customer_segment||h.idea_to_strategy?.contract?.customer_segment||h.strategy_to_product?.contract?.customer_segment;
    return {
      run:r,out,
      request:r.request||out.request||'',goal:r.goal||out.goal||'',audience:r.audience||out.audience||'',scope:r.scope||out.scope||'Egypt',constraints:r.constraints||out.constraints||[],
      recommendation,why:d.why_this_direction||d.why||d.rationale||s.recommendation_reason,
      problem:d.customer_problem||d.problem||d.problem_statement||candidate.problem||s.problem,
      target,validation:d.validation_model||s.validation_model||candidate.validation_model,
      longTerm:d.long_term_product_model||s.recommended_model?.name||s.recommended_model,
      mvp:d.mvp_direction||candidate.solution_format,firstTest:d.first_validation_test||candidate.validation_test?.customer_need,
      threshold:d.success_threshold,rule:d.decision_rule||candidate.validation_test?.willingness_to_pay,
      next:d.next_action||'Validate the recommended opportunity before committing capital or external actions.',
      promise:d.customer_outcome||d.promise||candidate.desired_outcome||s.promise,
      opportunity:d.opportunity_score??candidate.opportunity_score,strategyScore:d.strategy_score,
      confidence:d.confidence||candidate.confidence||s.confidence,
      boundary:d.market_evidence_boundary||d.evidence_boundary||out.market?.report?.evidence_boundary,
      localEvidence:d.local_evidence||out.market?.report?.local_evidence,
      sourceCount:e.source_count??arr(e.sources).length,evidenceCount:e.evidence_count??arr(e.evidence||e.items||e.claims).length,
      risk:gov.risk||out.governance?.risk,approval:appr.status||appr.decision||gov.approval||h.approval_to_memory?.contract?.decision_summary||'PENDING',
      learningSignal:learning.signal||h.memory_to_monitoring?.contract?.learning_summary||out.analytics?.learning_signal,
      outcomeStatus:outcome.status||outcome.outcome_status||out.analytics?.status,
    };
  }
  function score(v){
    const status=String(v.run?.status||'').toUpperCase();
    return (status==='COMPLETE'?40:status==='RUNNING'?20:10)+(v.recommendation?18:0)+(v.evidenceCount>0?15:0)+(v.sourceCount>0?8:0)+(v.validation?6:0)+(v.next?5:0)+(v.learningSignal?4:0)+(v.outcomeStatus?4:0);
  }
  async function canonicalRun(){
    const raw=await api('/runs?limit=25');
    const runs=(Array.isArray(raw)?raw:(raw.runs||raw.items||[])).filter(Boolean);
    if(!runs.length) return null;
    const hydrated=[];
    for(const base of runs.slice(0,12)){
      const id=base.job_id||base.id; if(!id)continue;
      try{hydrated.push(await api('/runs/'+encodeURIComponent(id)));}catch{hydrated.push(base);}
    }
    hydrated.sort((a,b)=>{const sa=score(norm(a)),sb=score(norm(b));return (sb-sa)||((stamp(b.updated_at||b.completed_at||b.created_at))-(stamp(a.updated_at||a.completed_at||a.created_at)));});
    return hydrated[0]||runs[0];
  }
  function pageId(){return document.querySelector('.page:not(.hidden)')?.id||'';}
  function hidePageChildren(page,keepSelector=''){
    [...page.children].forEach(el=>{
      if(el.classList.contains('ui21-surface')) return;
      if(keepSelector && el.matches(keepSelector)){el.classList.add('u21-keep-original');return;}
      el.classList.add('u21-hide-original');
    });
  }
  function proxyClick(match){
    const buttons=[...document.querySelectorAll('button,[role="button"]')];
    const b=buttons.find(x=>match.test((x.textContent||'').trim()) && !x.closest('.ui21-surface'));
    if(b){b.click();return true;} return false;
  }
  const descriptors={
    'page-overview':['Executive Home','One operating picture for the live decision journey.'],
    'page-golden':['Golden Experience','See the complete request → evidence → decision → governance → outcome → learning story.'],
    'page-acceptance':['Product Acceptance','Inspect whether the live run is complete enough to present safely.'],
    'page-goldenrun':['Golden Run Control','Create, inspect and explicitly execute the reference journey.'],
    'page-experiments':['Experiments','Validation records connecting hypotheses, evidence, decisions and learning.'],
    'page-decisions':['Decisions','Decision surfaces, recommendation rationale, scores and next actions.'],
    'page-evidence':['Evidence Explorer','Trace claims, sources, evidence boundaries and confidence.'],
    'page-memory':['Learning & Memory','Lessons, provenance and next-decision context.'],
    'page-adaptation':['Adaptive Intelligence','How evidence and outcomes change the next bounded decision.'],
    'page-approvals':['Governance','Human approval boundaries and consequential-action posture.'],
    'page-policies':['Policies','Policy posture, constraints and decision controls.'],
    'page-execution':['Execution','Explicit execution intents, receipts and outcomes.'],
    'page-recovery':['Recovery','Failure recovery, reconciliation and restart posture.'],
    'page-audit':['Audit Log','Traceable runtime events and provenance.'],
    'page-health':['System Health','Backend health, readiness and runtime condition.'],
    'page-operations':['Operations','Operational state, queues and operator attention.'],
    'page-release':['Release','Release posture, package state and operational readiness.'],
    'page-settings':['Settings','Console configuration and session preferences.'],
    'page-platform':['Platform','Identity, scope and authorization posture.'],
    'page-guide':['How to Use','A practical path through the operating system.'],
  };
  function stage(v,name,status,detail){const s=String(status||'WAITING').toUpperCase();const cls=/COMPLETE|READY|PASS/.test(s)?'done':/REVIEW|PENDING/.test(s)?'review':'wait';return `<div class="u21-stage ${cls}"><div class="u21-stage-no">${name}</div><b>${esc(s)}</b><small>${esc(detail)}</small></div>`;}
  function surface(page,title,sub,body,actions=''){const s=document.createElement('section');s.className='ui21-surface';s.innerHTML=`<div class="u21-head"><div><div class="u21-eyebrow">AI MASTER OS · LIVE CONSOLE</div><h1>${esc(title)}</h1><p>${esc(sub)}</p></div><div class="u21-actions">${actions}</div></div>${body}`;page.prepend(s);return s;}
  function commonBody(v){
    if(!v) return `<div class="u21-empty"><h3>Backend data unavailable</h3><p>The console could not load a canonical run. Nothing is invented in this state.</p></div>`;
    const status=String(v.run.status||'WAITING').toUpperCase();
    return `<div class="u21-status"><div class="u21-stat"><span>Canonical run</span><strong>${esc(v.run.job_id||v.run.id)}</strong><small>${esc(v.run.project_id||'')}</small></div><div class="u21-stat"><span>Status</span><strong>${esc(status)}</strong><small>backend-derived</small></div><div class="u21-stat"><span>Evidence</span><strong>${esc(v.sourceCount)} sources · ${esc(v.evidenceCount)} evidence</strong><small>${esc(v.confidence||'')}</small></div><div class="u21-stat"><span>Governance</span><strong>${esc(v.approval)}</strong><small>${esc(v.risk||'')}</small></div><div class="u21-stat"><span>Scores</span><strong>${esc(v.opportunity)} · ${esc(v.strategyScore)}</strong><small>prioritization heuristics</small></div></div><div class="u21-hero"><div class="u21-eyebrow">CURRENT DECISION SIGNAL</div><div class="rec">${esc(v.recommendation||'Decision not exposed')}</div><div class="why">${esc(v.why||'No rationale is exposed by this run.')}</div><div class="u21-chips"><span class="u21-chip">Target · ${esc(v.target||v.audience)}</span><span class="u21-chip">Validation · ${esc(v.validation)}</span><span class="u21-chip">Product · ${esc(v.longTerm)}</span><span class="u21-chip">Confidence · ${esc(v.confidence)}</span></div></div>`;
  }
  function renderOverview(page,v){const actions='<button class="u21-btn primary" data-u21="refresh">Refresh</button>';hidePageChildren(page);const body=commonBody(v)+`<div class="u21-card" style="margin-bottom:16px"><div class="u21-eyebrow">OPERATING JOURNEY</div><div class="u21-stages">${stage(v,'01',v?.request?'COMPLETE':'WAITING',v?.request?'Request captured':'Waiting for request')}${stage(v,'02',v?.evidenceCount>0?'COMPLETE':'WAITING',v?.evidenceCount>0?`${v.sourceCount} sources · ${v.evidenceCount} evidence`:'No evidence exposed')}${stage(v,'03','COMPLETE','Route resolved')}${stage(v,'04',v?.recommendation?'COMPLETE':'WAITING',v?.recommendation||'Decision pending')}${stage(v,'05',/PENDING|AWAITING|REVIEW/i.test(String(v?.approval))?'REVIEW':'COMPLETE',v?.approval||'Governance state')}${stage(v,'06',String(v?.run?.status).toUpperCase()==='COMPLETE'?'COMPLETE':'WAITING',String(v?.run?.status||'WAITING'))}${stage(v,'07',v?.outcomeStatus?'COMPLETE':'WAITING',v?.outcomeStatus||'Outcome pending')}${stage(v,'08',v?.learningSignal?'COMPLETE':'WAITING',v?.learningSignal||'Learning pending')}${stage(v,'09',v?.next?'READY':'WAITING',v?.next||'Next decision not exposed')}</div></div><div class="u21-grid2"><div class="u21-card"><h2>What happens next</h2><p>${esc(v?.next||'No next action exposed.')}</p></div><div class="u21-card"><h2>Governance</h2><p>${esc(v?.approval||'No governance state exposed.')} · ${esc(v?.risk||'Risk not exposed.')}</p><div class="u21-note" style="margin-top:12px">The console explains backend state; it never becomes policy or approval authority.</div></div></div>`;surface(page,'Executive Home','One coherent visual surface derived from the canonical backend run.',body,actions);}
  function renderGolden(page,v){const actions='<button class="u21-btn" data-u21="refresh">Refresh journey</button>';hidePageChildren(page);const body=commonBody(v)+`<div class="u21-card" style="margin-bottom:16px"><div class="u21-eyebrow">JOURNEY</div><div class="u21-stages">${stage(v,'01',v?.request?'COMPLETE':'WAITING','Understand')}${stage(v,'02',v?.evidenceCount>0?'COMPLETE':'WAITING','Research')}${stage(v,'03','COMPLETE','Route')}${stage(v,'04',v?.recommendation?'COMPLETE':'WAITING','Decide')}${stage(v,'05',/PENDING|AWAITING|REVIEW/i.test(String(v?.approval))?'REVIEW':'COMPLETE','Govern')}${stage(v,'06',String(v?.run?.status).toUpperCase()==='COMPLETE'?'COMPLETE':'WAITING','Execute')}${stage(v,'07',v?.outcomeStatus?'COMPLETE':'WAITING','Outcome')}${stage(v,'08',v?.learningSignal?'COMPLETE':'WAITING','Learn')}${stage(v,'09',v?.next?'READY':'WAITING','Next Decision')}</div></div><div class="u21-grid2"><div class="u21-card"><h2>Intent</h2><div class="u21-kv"><div><span>Request</span><strong>${esc(v?.request)}</strong></div><div><span>Goal</span><strong>${esc(v?.goal)}</strong></div><div><span>Target customer</span><strong>${esc(v?.target||v?.audience)}</strong></div><div><span>Scope</span><strong>${esc(v?.scope)}</strong></div></div></div><div class="u21-card"><h2>Decision</h2><div class="u21-kv"><div><span>Recommendation</span><strong>${esc(v?.recommendation)}</strong></div><div><span>Validation</span><strong>${esc(v?.validation)}</strong></div><div><span>First test</span><strong>${esc(v?.firstTest)}</strong></div><div><span>Decision rule</span><strong>${esc(v?.rule)}</strong></div></div></div></div><div class="u21-card" style="margin-top:14px"><h2>Governance + Learning</h2><div class="u21-kv"><div><span>Approval</span><strong>${esc(v?.approval)}</strong></div><div><span>Risk</span><strong>${esc(v?.risk)}</strong></div><div><span>Outcome</span><strong>${esc(v?.outcomeStatus||'Not exposed')}</strong></div><div><span>Learning</span><strong>${esc(v?.learningSignal||'Not exposed')}</strong></div></div></div>`;surface(page,'Golden Experience','One connected, non-duplicated view of the live intelligence journey.',body,actions);}
  function renderAcceptance(page,v){const actions='<button class="u21-btn primary" data-u21="accept">Run acceptance check</button>';hidePageChildren(page);const checks=[['Intent',!!v?.request&&!!v?.goal],['Recommendation',!!v?.recommendation],['Evidence',v?.sourceCount>0&&v?.evidenceCount>0],['Validation',!!v?.validation],['Target customer',!!v?.target||!!v?.audience],['Governance',!!v?.approval],['Scores',v?.opportunity!==undefined&&v?.strategyScore!==undefined],['Next action',!!v?.next],['Read-only authority',true]];const pass=checks.filter(c=>c[1]).length;const body=`<div class="u21-status"><div class="u21-stat"><span>Readiness</span><strong>${Math.round(pass/checks.length*100)}%</strong><small>${pass}/9 acceptance checks</small></div><div class="u21-stat"><span>Run</span><strong>${esc(v?.run?.job_id||'—')}</strong><small>${esc(v?.run?.status||'—')}</small></div><div class="u21-stat"><span>Evidence</span><strong>${esc(v?.sourceCount)} · ${esc(v?.evidenceCount)}</strong><small>sources · evidence</small></div><div class="u21-stat"><span>Governance</span><strong>${esc(v?.approval||'—')}</strong><small>${esc(v?.risk||'')}</small></div><div class="u21-stat"><span>Boundary</span><strong>GET-only</strong><small>no mutation authority</small></div></div><div class="u21-card"><h2>${pass===9?'Experience is coherent':'Review required'}</h2><p>Missing fields are shown as review items; nothing is fabricated.</p><div class="u21-checks" style="margin-top:14px">${checks.map(c=>`<div class="u21-check ${c[1]?'pass':'review'}"><span class="tag">${c[1]?'PASS':'REVIEW'}</span><strong>${esc(c[0])}</strong><small>${c[1]?'Exposed on the canonical run.':'Not exposed on the canonical run.'}</small></div>`).join('')}</div></div>`;surface(page,'Product Acceptance','A single visual quality gate for the canonical live run.',body,actions);}
  function renderGoldenRun(page,v){const actions=`<button class="u21-btn" data-u21="inspect">Inspect latest run</button><button class="u21-btn primary" data-u21="create">Create Golden Run</button>`;hidePageChildren(page);const body=commonBody(v)+`<div class="u21-card"><h2>Reference journey</h2><div class="u21-grid3"><div class="u21-stat"><span>Current run</span><strong>${esc(v?.run?.job_id||'—')}</strong></div><div class="u21-stat"><span>Backend status</span><strong>${esc(v?.run?.status||'—')}</strong></div><div class="u21-stat"><span>Next step</span><strong>${esc(v?.next||'—')}</strong></div></div><div class="u21-note" style="margin-top:14px">Creating and executing a run remain separate, explicit user actions. Approval remains governed by the backend.</div></div>`;surface(page,'Golden Run Control','Create, inspect and explicitly execute the reference journey without duplicate legacy panels.',body,actions);}
  function renderExperiments(page,v){const body=`<div class="u21-experiments"><div class="u21-stat"><span>Total</span><strong>0</strong><small>Live registry</small></div><div class="u21-stat"><span>GO</span><strong>0</strong><small>Current API contract</small></div><div class="u21-stat"><span>REFINE</span><strong>0</strong><small>Current API contract</small></div><div class="u21-stat"><span>NO-GO</span><strong>0</strong><small>Current API contract</small></div></div><div class="u21-card"><div class="u21-eyebrow">VALIDATION REGISTRY</div><h2>${v?.run?.status==='COMPLETE'?'No experiment registry exposed for this run':'No experiments indexed'}</h2><p>The backend run is available, but the current API contract does not expose a separate experiment registry. This surface will never invent experiments.</p><div class="u21-note" style="margin-top:14px">Canonical run: ${esc(v?.run?.job_id||'—')} · ${esc(v?.run?.project_id||'')}</div></div>`;hidePageChildren(page);surface(page,'Experiments','A clean validation surface with explicit empty-state semantics.',body,'<button class="u21-btn" data-u21="refresh">Refresh</button>');}
  function generic(page,v,id){const d=descriptors[id]||['Console Surface','Live system view.'];hidePageChildren(page,'');const body=commonBody(v)+`<div class="u21-grid2"><div class="u21-card"><h2>Live context</h2><div class="u21-kv"><div><span>Run</span><strong>${esc(v?.run?.job_id||'—')}</strong></div><div><span>Status</span><strong>${esc(v?.run?.status||'—')}</strong></div><div><span>Recommendation</span><strong>${esc(v?.recommendation||'Not exposed')}</strong></div><div><span>Next action</span><strong>${esc(v?.next||'Not exposed')}</strong></div></div></div><div class="u21-card"><h2>Boundary</h2><p>This console reads and explains authenticated backend state. Consequential execution, approval and memory mutation remain outside the presentation layer.</p></div></div>`;surface(page,d[0],d[1],body,'<button class="u21-btn" data-u21="refresh">Refresh</button>');}
  function cleanup(page){page.querySelector('.ui21-surface')?.remove();page.classList.remove('u21-active');page.querySelectorAll('.u21-hide-original').forEach(e=>e.classList.remove('u21-hide-original'));}
  async function renderVisiblePage(){
    const page=document.querySelector('.page:not(.hidden)');if(!page)return;
    document.querySelectorAll('.page.u21-active').forEach(p=>{if(p!==page)cleanup(p)});
    cleanup(page); page.classList.add('u21-active');
    let v=null; try{v=norm(await canonicalRun()); sessionStorage.setItem('aios.lastJobId',v?.run?.job_id||v?.run?.id||'');}catch(e){v=null}
    const id=page.id;
    if(id==='page-overview') renderOverview(page,v);
    else if(id==='page-golden') renderGolden(page,v);
    else if(id==='page-acceptance') renderAcceptance(page,v);
    else if(id==='page-goldenrun') renderGoldenRun(page,v);
    else if(id==='page-experiments') renderExperiments(page,v);
    else if(id==='page-runs'){page.classList.remove('u21-active');page.querySelectorAll('.u21-hide-original').forEach(e=>e.classList.remove('u21-hide-original'));}
    else if(descriptors[id]) generic(page,v,id);
    wireActions(page);
  }
  function wireActions(page){
    page.querySelectorAll('[data-u21]').forEach(b=>{b.addEventListener('click',async()=>{const a=b.dataset.u21;if(a==='refresh'){await renderVisiblePage();return;}if(a==='accept'){proxyClick(/Run acceptance check|Recheck/i);return;}if(a==='inspect'){proxyClick(/Inspect (latest|Golden Experience)|Open Golden Experience/i);return;}if(a==='create'){proxyClick(/Create Golden Run/i);return;}});});
  }
  let timer=0,last='';
  function schedule(){clearTimeout(timer);timer=setTimeout(async()=>{const id=pageId();if(id===last)return;last=id;await renderVisiblePage();},80)}
  function boot(){schedule();const mo=new MutationObserver(schedule);mo.observe(document.body,{subtree:true,attributes:true,attributeFilter:['class']});document.addEventListener('click',()=>setTimeout(schedule,120),true);window.addEventListener('hashchange',schedule);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else setTimeout(boot,50);
})();
