/* UI19 — Full Console Visual Polish + Live Surface Repair */
(function(){
  'use strict';
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const txt=(v,f='Not exposed')=>(v===undefined||v===null||v===''?f:String(v));
  const arr=v=>Array.isArray(v)?v:[];
  const api=async(path,opts={})=>{
    if(typeof window.api==='function') return window.api(path,opts);
    const base=(sessionStorage.getItem('aios.apiBase')||'/api').replace(/\/$/,'');
    const token=sessionStorage.getItem('aios.bearer')||'';
    const headers={'Content-Type':'application/json'}; if(token) headers.Authorization='Bearer '+token;
    const r=await fetch(base+path,{...opts,headers:{...headers,...(opts.headers||{})}});
    const p=await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(p?.error?.reason||p?.reason||p?.status||`HTTP ${r.status}`);
    return p;
  };
  const stamp=v=>Date.parse(v||'')||0;
  const runsOf=raw=>(Array.isArray(raw)?raw:(raw?.runs||raw?.items||[])).filter(Boolean).sort((a,b)=>stamp(b.updated_at||b.completed_at||b.created_at)-stamp(a.updated_at||a.completed_at||a.created_at));

  async function getRuns(){return runsOf(await api('/runs?limit=25'));}
  async function getBestRun(){
    const runs=await getRuns();
    if(!runs.length) return null;
    const complete=runs.find(r=>String(r.status||'').toUpperCase()==='COMPLETE');
    const preferredId=sessionStorage.getItem('aios.lastJobId')||localStorage.getItem('aios.lastJobId');
    const preferred=runs.find(r=>(r.job_id||r.id)===preferredId);
    const chosen=complete||preferred||runs[0];
    const id=chosen.job_id||chosen.id;
    if(id){try{return await api('/runs/'+encodeURIComponent(id));}catch{}}
    return chosen;
  }

  function deepFind(root, predicate, depth=0){
    if(!root||depth>5||typeof root!=='object') return null;
    if(predicate(root)) return root;
    const vals=Array.isArray(root)?root:Object.values(root);
    for(const v of vals){const hit=deepFind(v,predicate,depth+1);if(hit)return hit;}
    return null;
  }
  function normalize(run){
    const root=run||{}; const result=root.result||{};
    const d=root.decision_surface||root.decision||result.decision_surface||result.decision||result.business_decision||deepFind(result,x=>x&&typeof x==='object'&&('recommendation' in x)&&('decision_rule' in x))||{};
    const market=result.market||{};
    const evidence=root.evidence||market.evidence||result.evidence||result.research||{};
    const gov=root.governance||result.governance||{};
    const approval=root.approval||result.approval||{};
    const outcome=root.outcome||result.outcome||{};
    const learning=root.learning||result.learning||{};
    const handoffs=result.handoffs||{};
    const memory=handoffs.memory_to_monitoring?.contract||{};
    return {
      run:root,result,d,evidence,gov,approval,outcome,learning,memory,handoffs,
      request:root.request||result.request||'',goal:root.goal||result.goal||'',audience:root.audience||result.audience||'',scope:root.scope||result.scope||'Egypt',constraints:root.constraints||result.constraints||[],
      recommendation:d.recommendation||d.title||d.recommended_opportunity||d.recommended_direction,
      why:d.why_this_direction||d.why||d.rationale,
      problem:d.customer_problem||d.problem||d.problem_statement,
      target:d.target_customer||d.customer||d.audience,
      validation:d.validation_model,
      longTerm:d.long_term_product_model,
      mvp:d.mvp_direction,
      firstTest:d.first_validation_test,
      threshold:d.success_threshold,
      rule:d.decision_rule,
      next:d.next_action,
      promise:d.customer_outcome||d.promise,
      opportunity:d.opportunity_score,
      strategy:d.strategy_score,
      confidence:d.confidence,
      boundary:d.market_evidence_boundary||d.evidence_boundary,
      localEvidence:d.local_evidence,
      sourceCount:evidence.source_count??arr(evidence.sources).length,
      evidenceCount:evidence.evidence_count??arr(evidence.evidence).length,
      risk:gov.risk||result.governance?.risk,
      approvalStatus:approval.status||approval.decision||gov.approval||'PENDING'
    };
  }
  window.buildO46ExperienceView=window.buildO46ExperienceView||function(run){return normalize(run)};
  window.AIOS_UI19={version:'UI19.0',getBestRun,getRuns,normalize};

  const set=(id,v,f='—')=>{const e=document.getElementById(id);if(e)e.textContent=txt(v,f)};
  const html=(id,v)=>{const e=document.getElementById(id);if(e)e.innerHTML=v};
  function state(v){
    const s=String(v||'WAITING').toUpperCase();
    return ['COMPLETE','PASS','READY','GO','APPROVED'].includes(s)?'complete':(['FAILED','BLOCK','NO-GO','CANCELLED'].includes(s)?'review':(['QUEUED','RUNNING','PENDING','REVIEW','REFINE','AWAITING_APPROVAL'].includes(s)?'review':'wait'));
  }
  function stage(name,idx,st,sub){return `<div class="u19-stage ${state(st)}"><div><span class="u19-stage-num">${String(idx).padStart(2,'0')}</span><div class="u19-stage-title">${esc(name)}</div></div><div class="u19-stage-state">${esc(sub||st||'Waiting')}</div></div>`}
  function stageStates(v){
    const complete=v.run?.status==='COMPLETE';
    const research=v.result?.market?.status||v.result?.market?.report?.evidence_boundary;
    const decide=v.recommendation?'COMPLETE':'WAITING';
    const gov=(String(v.approvalStatus).toUpperCase()==='PENDING'||String(v.approvalStatus).toUpperCase()==='AWAITING_APPROVAL')?'REVIEW':'COMPLETE';
    const outcome=v.outcome?.status||v.result?.analytics?.event_summary?.total_events?'OBSERVED':'WAITING';
    const learn=v.learning?.signal||v.memory?.memory_status?'WRITTEN':'WAITING';
    return [
      ['Understand',v.request?'COMPLETE':'WAITING',v.request?'Request captured':'Waiting for request'],
      ['Research',research?'COMPLETE':'WAITING',research?'Evidence assembled':'Waiting for evidence'],
      ['Route',v.handoffs?.market_to_idea?.qa?.status||'COMPLETE','Engine path resolved'],
      ['Decide',decide,v.recommendation||'Decision pending'],
      ['Govern',gov,gov==='REVIEW'?'Human gate active':'Policy state resolved'],
      ['Execute',complete?'COMPLETE':'WAITING',complete?'Run completed':'Awaiting explicit execution'],
      ['Outcome',outcome,outcome==='OBSERVED'?'Outcome evidence available':'Outcome pending'],
      ['Learn',learn,learn==='WRITTEN'?'Learning recorded':'Learning pending'],
      ['Next Decision',v.next?'READY':'WAITING',v.next||'Next decision not yet exposed']
    ];
  }

  async function renderGolden(run){
    const v=normalize(run); document.getElementById('page-golden')?.classList.add('u19-ready');
    const journey=document.getElementById('goldenJourney');
    if(journey) journey.innerHTML=stageStates(v).map((s,i)=>stage(s[0],i+1,s[1],s[2])).join('');
    html('goldenStatus',`<div class="u19-panel-grid"><div class="u19-kv"><span>Run</span><strong>${esc(v.run.job_id||v.run.id)}</strong></div><div class="u19-kv"><span>Status</span><strong>${esc(v.run.status||'UNKNOWN')}</strong></div><div class="u19-kv"><span>Project</span><strong>${esc(v.run.project_id)}</strong></div><div class="u19-kv"><span>Evidence</span><strong>${esc(v.sourceCount)} sources · ${esc(v.evidenceCount)} evidence</strong></div></div>`);
    html('goldenIntent',`<div class="eyebrow">INTENT</div><h3>What the run was asked to solve</h3><div class="u19-kv-grid"><div class="u19-kv"><span>Request</span><strong>${esc(v.request)}</strong></div><div class="u19-kv"><span>Goal</span><strong>${esc(v.goal)}</strong></div><div class="u19-kv"><span>Target customer</span><strong>${esc(v.target)}</strong></div><div class="u19-kv"><span>Scope</span><strong>${esc(v.scope)}</strong></div></div>`);
    html('goldenDecision',`<div class="eyebrow">DECISION</div><h3>${esc(v.recommendation||'Decision not exposed')}</h3><p>${esc(v.why||'The backend has not exposed a rationale for this run.')}</p><div class="u19-kv-grid" style="margin-top:12px"><div class="u19-kv"><span>Validation</span><strong>${esc(v.validation)}</strong></div><div class="u19-kv"><span>Long-term model</span><strong>${esc(v.longTerm)}</strong></div><div class="u19-kv"><span>Opportunity</span><strong>${esc(v.opportunity)}</strong></div><div class="u19-kv"><span>Strategy</span><strong>${esc(v.strategy)}</strong></div></div>`);
    html('goldenGovernance',`<div class="eyebrow">GOVERNANCE</div><h3>Human control remains explicit</h3><div class="u19-kv-grid"><div class="u19-kv"><span>Risk</span><strong>${esc(v.risk)}</strong></div><div class="u19-kv"><span>Approval</span><strong>${esc(v.approvalStatus)}</strong></div><div class="u19-kv"><span>Boundary</span><strong>${esc(v.boundary)}</strong></div><div class="u19-kv"><span>Authority</span><strong>Backend policy / approval boundary</strong></div></div>`);
    html('goldenOutcome',`<div class="eyebrow">OUTCOME & LEARNING</div><h3>${esc(v.outcome?.status||'No observed outcome')}</h3><p>${esc(v.outcome?.summary||v.outcome?.message||'Outcome evidence will appear here when exposed.')}</p><div class="u19-meta-row"><span class="u19-chip">Learning · ${esc(v.learning?.signal||v.memory?.memory_status||'Not exposed')}</span><span class="u19-chip">Next · ${esc(v.next||'Not exposed')}</span></div>`);
    html('goldenNext',`<div class="eyebrow">NEXT ACTION</div><h3>${esc(v.next||'Review the decision surface')}</h3><p>${esc(v.rule||v.firstTest||'Use the exposed validation model and decision rule before consequential actions.')}</p>`);

    const sel=document.getElementById('goldenRunSelect');
    if(sel){
      const rs=await getRuns().catch(()=>[]); const current=v.run.job_id||v.run.id; sel.innerHTML=`<option value="${esc(current||'')}">Latest useful run · ${esc(current||'—')}</option>`+rs.filter(r=>(r.job_id||r.id)!==current).map(r=>`<option value="${esc(r.job_id||r.id)}">${esc(r.project_id||'Run')} · ${esc(r.job_id||r.id)} · ${esc(r.status||'')}</option>`).join('');
      if(current) sel.value=current;
      if(!sel.dataset.u19Bound){sel.dataset.u19Bound='1';sel.addEventListener('change',async()=>{const id=sel.value;if(!id)return;const rr=await api('/runs/'+encodeURIComponent(id));renderGolden(rr);renderInspector(rr)});}
    }
    renderInspector(run);
  }
  function renderInspector(run){
    const v=normalize(run), grid=document.getElementById('goldenValidationGrid');if(!grid)return;
    const checks=[
      ['Run identity',!!v.run.job_id||!!v.run.id,'Backend run can be identified.'],
      ['Intent',!!v.request&&!!v.goal&&!!v.target,'Request, goal and customer are exposed.'],
      ['Recommendation',!!v.recommendation,'Decision recommendation is exposed.'],
      ['Evidence',v.sourceCount>0&&v.evidenceCount>0,`${v.sourceCount} sources · ${v.evidenceCount} evidence.`],
      ['Validation',!!v.validation&&!!v.firstTest,'Validation model and first test are exposed.'],
      ['Governance',!!v.approvalStatus,'Approval state is visible.'],
      ['Outcome',!!v.outcome?.status||!!v.result?.analytics,'Outcome/analytics state exposed.'],
      ['Learning',!!v.learning?.signal||!!v.memory?.memory_status,'Learning state exposed.'],
      ['Authority',true,'UI remains read/inspect-first.']
    ];
    grid.innerHTML=checks.map(c=>`<div class="u19-check ${c[1]?'pass':'review'}"><span class="state">${c[1]?'PASS':'REVIEW'}</span><b>${esc(c[0])}</b><small>${esc(c[2])}</small></div>`).join('');
    const meta=document.getElementById('goldenRunMeta');if(meta)meta.innerHTML=`<span class="u19-chip">${esc(v.run.job_id||v.run.id)}</span><span class="u19-chip">${esc(v.run.status||'UNKNOWN')}</span><span class="u19-chip">${esc(v.project_id||v.run.project_id||'')}</span>`;
    const banner=document.getElementById('goldenIntegrityBanner');if(banner)banner.innerHTML=`<span class="status-dot"></span><div><strong>${checks.every(c=>c[1])?'Experience aligned with live run':'Live run loaded with review items'}</strong><small>Read-only QA derived from the backend state; no policy or approval authority is added.</small></div>`;
  }

  async function refreshGolden(){try{const r=await getBestRun();if(r)await renderGolden(r)}catch(e){const s=document.getElementById('goldenStatus');if(s)s.innerHTML=`<div class="u19-empty"><span class="u19-empty-dot"></span><div><b>Live run could not be loaded</b><small>${esc(e.message||e)}</small></div></div>`;}}

  async function renderAcceptance(run){
    const v=normalize(run), checks=[
      ['Semantic mapping',!!v.recommendation,'Recommendation/decision surface'],['Target customer',!!v.target,'Target customer field'],['Validation model',!!v.validation,'Validation mode'],['Long-term product',!!v.longTerm,'Product model distinction'],['Evidence boundary',!!v.boundary||v.evidenceCount>0,'Evidence scope'],['Scores',v.opportunity!==undefined&&v.strategy!==undefined,'Numeric score propagation'],['Governance',!!v.approvalStatus,'Governance state'],['Closed loop',!!v.learning?.signal||!!v.next,'Outcome/learning route'],['Read-only authority',true,'UI does not mutate governance authority']
    ];
    const pass=checks.filter(x=>x[1]).length;
    const score=document.getElementById('acceptanceScore'); if(score)score.textContent=`${pass}/${checks.length}`;
    const status=document.getElementById('acceptanceStatus'); if(status)status.textContent=pass===checks.length?'PASS':'REVIEW';
    const headline=document.getElementById('acceptanceHeadline'); if(headline)headline.textContent=pass===checks.length?'Experience is coherent':'Review items remain on the live surface';
    const note=document.getElementById('acceptanceSummary'); if(note)note.textContent=`${pass}/${checks.length} checks pass for ${v.run.job_id||v.run.id||'the selected run'}.`;
    const grid=document.getElementById('acceptanceGrid'); if(grid)grid.innerHTML=checks.map(c=>`<div class="u19-check ${c[1]?'pass':'review'}"><span class="state">${c[1]?'PASS':'REVIEW'}</span><b>${esc(c[0])}</b><small>${esc(c[2])}</small></div>`).join('');
    const meta=document.getElementById('acceptanceRunMeta'); if(meta)meta.innerHTML=`<span class="u19-chip">${esc(v.run.job_id||v.run.id)}</span><span class="u19-chip">${esc(v.run.status||'UNKNOWN')}</span>`;
    const hero=document.getElementById('acceptanceHero'); if(hero)hero.classList.add('u19-safe');
    const findings=document.getElementById('acceptanceFindings'); if(findings)findings.innerHTML=`<div class="eyebrow">FINDINGS</div><h3>What the live run exposes</h3><div class="u19-kv-grid"><div class="u19-kv"><span>Recommendation</span><strong>${esc(v.recommendation)}</strong></div><div class="u19-kv"><span>Target customer</span><strong>${esc(v.target)}</strong></div><div class="u19-kv"><span>Next action</span><strong>${esc(v.next)}</strong></div><div class="u19-kv"><span>Decision rule</span><strong>${esc(v.rule)}</strong></div></div>`;
    const boundary=document.getElementById('acceptanceBoundary'); if(boundary)boundary.innerHTML=`<div class="eyebrow">BOUNDARY</div><h3>Read-only product authority</h3><p>The surface explains backend state; it does not approve, publish, spend, send, or alter governance policy.</p>`;
  }
  async function refreshAcceptance(){try{const r=await getBestRun();if(r)await renderAcceptance(r)}catch(e){const h=document.getElementById('acceptanceHeadline');if(h)h.textContent='Acceptance data unavailable';const s=document.getElementById('acceptanceSummary');if(s)s.textContent=String(e.message||e);}}

  function enhanceGoldenControl(){
    const ids=['goldenControlStatus','goldenControlHeadline','goldenControlRunId','goldenControlProject','goldenControlRunStatus','goldenControlGovernance','goldenControlNext'];
    if(!ids.some(id=>document.getElementById(id)))return;
    getBestRun().then(r=>{
      if(!r)return;const v=normalize(r);
      set('goldenControlHeadline',v.run.status==='COMPLETE'?'Latest reference run is complete':'Current reference run loaded');
      set('goldenControlRunId',v.run.job_id||v.run.id);set('goldenControlProject',v.run.project_id);set('goldenControlRunStatus',v.run.status);set('goldenControlGovernance',v.approvalStatus);set('goldenControlNext',v.next||v.firstTest||'Review the decision surface');
      const steps=document.getElementById('goldenControlSteps');if(steps)steps.innerHTML=stageStates(v).map((s,i)=>stage(s[0],i+1,s[1],s[2])).join('');
    });
  }

  function enhanceExperiments(){
    const host=document.querySelector('#page-experiments .u19-registry-state')||document.querySelector('#page-experiments .u15-empty');
    if(!host)return;
    if(!host.parentElement.querySelector('.u19-registry-state')){
      const box=document.createElement('div');box.className='u19-registry-state u19-empty';box.innerHTML='<span class="u19-empty-dot"></span><div><b>Experiment registry is currently read-only and empty.</b><small>The current API contract does not expose experiment records for this workspace. The console will not invent entries.</small></div>';host.parentElement.appendChild(box);
    }
  }

  function visualHygiene(){
    document.querySelectorAll('.page').forEach(p=>p.classList.add('u19-ready'));
    document.querySelectorAll('.u15-host').forEach(h=>h.classList.add('u19-mounted'));
    enhanceGoldenControl();enhanceExperiments();
  }

  async function boot(){
    visualHygiene();
    if(document.getElementById('goldenExperience')) await refreshGolden();
    if(document.getElementById('productAcceptance')) await refreshAcceptance();
    const gb=document.getElementById('goldenRefresh'); if(gb&&!gb.dataset.u19Bound){gb.dataset.u19Bound='1';gb.addEventListener('click',refreshGolden)}
    const ab=document.getElementById('acceptanceRefresh'); if(ab&&!ab.dataset.u19Bound){ab.dataset.u19Bound='1';ab.addEventListener('click',refreshAcceptance)}
    const gr=document.getElementById('goldenInspectRefresh'); if(gr&&!gr.dataset.u19Bound){gr.dataset.u19Bound='1';gr.addEventListener('click',refreshGolden)}
  }
  document.addEventListener('DOMContentLoaded',()=>setTimeout(boot,120));
  setTimeout(()=>{try{visualHygiene();enhanceGoldenControl();enhanceExperiments()}catch{}},900);
  window.addEventListener('hashchange',()=>setTimeout(()=>{visualHygiene();if(document.getElementById('goldenExperience'))refreshGolden();if(document.getElementById('productAcceptance'))refreshAcceptance();},120));
})();
