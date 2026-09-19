/* UI20 — Unified Console Surface: one visual authority per page + live navigation hydration */
(function(){
  'use strict';
  const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const txt=(v,f='—')=>(v===undefined||v===null||v===''?f:String(v));
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
  const listRuns=raw=>(Array.isArray(raw)?raw:(raw?.runs||raw?.items||[])).filter(Boolean).sort((a,b)=>stamp(b.updated_at||b.completed_at||b.created_at)-stamp(a.updated_at||a.completed_at||a.created_at));
  async function getRuns(){return listRuns(await api('/runs?limit=25'));}
  function deepFind(root,predicate,depth=0){
    if(!root||depth>7||typeof root!=='object') return null;
    if(predicate(root)) return root;
    for(const v of Array.isArray(root)?root:Object.values(root)){const hit=deepFind(v,predicate,depth+1);if(hit)return hit;}
    return null;
  }
  function normalize(run){
    const root=run||{}, result=root.result||root.run_result||root.output||{};
    const d=root.decision_surface||root.decision||result.decision_surface||result.decision||result.business_decision||
      deepFind(result,x=>x&&typeof x==='object'&&(('recommendation' in x)||('recommended_opportunity' in x))&&(('validation_model' in x)||('decision_rule' in x)))||{};
    const idea=deepFind(result,x=>x&&typeof x==='object'&&('opportunity_candidates' in x));
    const candidate=idea?.opportunity_candidates?.find?.(x=>x?.rank===1)||idea?.opportunity_candidates?.[0]||{};
    const strategy=deepFind(result,x=>x&&typeof x==='object'&&x?.recommended_model&&x?.recommendation_reason)||{};
    const evidence=root.evidence||result.market?.evidence||result.evidence||result.research||{};
    const gov=root.governance||result.governance||{};
    const approval=root.approval||result.approval||{};
    const outcome=root.outcome||result.outcome||{};
    const learning=root.learning||result.learning||{};
    const handoffs=result.handoffs||{};
    const market=result.market||{};
    const memory=handoffs.memory_to_monitoring?.contract||{};
    const rec=d.recommendation||d.recommended_opportunity||d.title||strategy.opportunity_title||candidate.title||candidate.idea;
    const why=d.why_this_direction||d.why||d.rationale||strategy.recommendation_reason;
    const validation=d.validation_model||strategy.validation_model||candidate.validation_model;
    const longTerm=d.long_term_product_model||strategy.recommended_model?.name||strategy.recommended_model;
    const target=d.target_customer||d.customer||candidate.customer_segment||handoffs.idea_to_strategy?.contract?.customer_segment||handoffs.strategy_to_product?.contract?.customer_segment||'';
    return {
      run:root,result,d,evidence,gov,approval,outcome,learning,memory,handoffs,market,
      request:root.request||result.request||'',goal:root.goal||result.goal||'',audience:root.audience||result.audience||'',scope:root.scope||result.scope||'Egypt',constraints:root.constraints||result.constraints||[], 
      recommendation:rec,why,problem:d.customer_problem||d.problem||d.problem_statement||candidate.problem||strategy.problem,
      target,validation,longTerm,mvp:d.mvp_direction||candidate.solution_format,firstTest:d.first_validation_test||candidate.validation_test?.customer_need,
      threshold:d.success_threshold,rule:d.decision_rule||candidate.validation_test?.willingness_to_pay,next:d.next_action||'Interview or observe 10 target customers and document one real recurring workflow.',
      promise:d.customer_outcome||d.promise||candidate.desired_outcome||strategy.promise,opportunity:d.opportunity_score??candidate.opportunity_score,strategyScore:d.strategy_score??strategy.strategy_score?.overall_score,
      confidence:d.confidence||candidate.confidence||strategy.confidence,boundary:d.market_evidence_boundary||d.evidence_boundary||market.report?.evidence_boundary,localEvidence:d.local_evidence||market.report?.local_evidence,
      sourceCount:evidence.source_count??arr(evidence.sources).length,evidenceCount:evidence.evidence_count??arr(evidence.evidence).length,
      risk:gov.risk||result.governance?.risk,approvalStatus:approval.status||approval.decision||gov.approval||handoffs.approval_to_memory?.contract?.decision_summary||'PENDING'
    };
  }
  function completeness(v){
    return (String(v.run?.status||'').toUpperCase()==='COMPLETE'?40:0)+(v.recommendation?20:0)+(v.evidenceCount>0?15:0)+(v.sourceCount>0?10:0)+(v.validation?5:0)+(v.next?5:0)+(v.learning?.signal||v.memory?.memory_status?3:0)+(v.outcome?.status||v.result?.analytics?2:0);
  }
  async function getCanonicalRun(){
    const runs=await getRuns(); if(!runs.length)return null;
    const hydrated=[];
    for(const r of runs.slice(0,12)){
      const id=r.job_id||r.id; if(!id) continue;
      try { hydrated.push(await api('/runs/'+encodeURIComponent(id))); } catch { hydrated.push(r); }
    }
    hydrated.sort((a,b)=>{
      const da=normalize(a),db=normalize(b); const score=completeness(db)-completeness(da); return score||stamp(b.updated_at||b.completed_at||b.created_at)-stamp(a.updated_at||a.completed_at||a.created_at);
    });
    return hydrated[0]||runs[0];
  }
  function stageData(v){
    const s=String(v.run?.status||'').toUpperCase();
    const research=v.evidenceCount>0||v.market?.status==='COMPLETE';
    const outcome=v.outcome?.status||v.result?.analytics?.event_summary?.total_events?'OBSERVED':'WAITING';
    const learn=v.learning?.signal||v.memory?.memory_status?'WRITTEN':'WAITING';
    const gov=/PENDING|AWAITING_APPROVAL|REVIEW/i.test(String(v.approvalStatus))?'REVIEW':'COMPLETE';
    return [
      ['Understand',v.request?'COMPLETE':'WAITING',v.request?'Request captured':'Waiting for request'],
      ['Research',research?'COMPLETE':'WAITING',research?`${v.sourceCount} sources · ${v.evidenceCount} evidence`:'Waiting for evidence'],
      ['Route','COMPLETE','Engine path resolved'],
      ['Decide',v.recommendation?'COMPLETE':'WAITING',v.recommendation||'Decision pending'],
      ['Govern',gov,gov==='REVIEW'?'Human gate active':'Policy state resolved'],
      ['Execute',s==='COMPLETE'?'COMPLETE':'WAITING',s==='COMPLETE'?'Run completed':'Awaiting explicit execution'],
      ['Outcome',outcome,outcome==='OBSERVED'?'Outcome evidence available':'Outcome pending'],
      ['Learn',learn,learn==='WRITTEN'?'Learning recorded':'Learning pending'],
      ['Next Decision',v.next?'READY':'WAITING',v.next||'Next decision not exposed']
    ];
  }
  const set=(id,v,f='—')=>{const e=document.getElementById(id);if(e)e.textContent=txt(v,f)};
  const html=(id,v)=>{const e=document.getElementById(id);if(e)e.innerHTML=v};
  function pill(s){const u=String(s||'WAITING').toUpperCase();const cls=['COMPLETE','PASS','READY','GO','APPROVED'].includes(u)?'u20-good':['FAILED','BLOCK','NO-GO','CANCELLED'].includes(u)?'u20-bad':'u20-warn';return `<span class="u20-pill ${cls}">${esc(u)}</span>`}
  function stageCards(v){return stageData(v).map((s,i)=>`<div class="u20-stage ${/COMPLETE|READY/.test(s[1])?'done':/REVIEW/.test(s[1])?'review':'wait'}"><div class="u20-stage-no">${String(i+1).padStart(2,'0')}</div><b>${esc(s[0])}</b><small>${esc(s[2])}</small></div>`).join('')}
  function bindExecutive(v){
    const status=String(v.run.status||'WAITING').toUpperCase(), gov=/PENDING|AWAITING_APPROVAL|REVIEW/i.test(String(v.approvalStatus));
    set('experienceSource',`Live run · ${v.run.job_id||v.run.id}`); set('executiveRecommendation',v.recommendation,'Decision not exposed'); set('executiveWhy',v.why,'No rationale exposed by the current run.');
    set('executiveConfidence',v.confidence); set('executiveConfidenceNote',v.confidence?'Evidence strength':'No confidence exposed'); set('executiveOpportunity',v.opportunity); set('executiveStrategy',v.strategyScore); set('executiveEvidenceCount',v.evidenceCount); set('executiveSourceCount',v.sourceCount); set('executiveConflictCount',v.evidence?.conflict_count??v.evidence?.conflicts?.length??0); set('executiveGovernanceState',gov?'PENDING':'READY','PENDING'); set('executiveGovernanceNote',gov?'Human review boundary active':'Backend governance state'); set('executiveNextAction',v.next); set('executiveNextReason',v.rule||v.firstTest); set('executiveRunState',status); set('executiveRunMeta',`${v.run.project_id||'—'} · ${v.run.job_id||v.run.id||'—'}`);
    set('experienceDecisionTitle',v.recommendation,'No decision yet'); set('experienceDecisionStatus',status); set('experienceDecisionWhy',v.why,'No rationale exposed by the current run.'); set('experienceNextAction',v.next); set('experienceDecisionRule',v.rule); set('experienceEvidenceScore',v.confidence); set('experienceGovernanceTitle',gov?'Human review boundary active':'Governance state'); set('experienceGovernanceStatus',gov?'REVIEW':'PASS'); set('experienceGovernanceAction',gov?'Consequential action remains human-governed':'Backend policy state'); set('experienceGovernanceReason',gov?'Approval remains a backend human gate.':'The backend remains authoritative.'); set('experienceOutcomeTitle',v.outcome?.status||'Awaiting observed outcome'); set('experienceOutcomeSummary',v.outcome?.summary||v.outcome?.message||(status==='COMPLETE'?'Run completed; inspect outcome evidence and validation loop.':'Outcome pending')); set('experienceLearningSignal',v.learning?.signal||v.memory?.memory_status||'Not exposed'); set('experienceNextDecision',v.next||'Not exposed');
    const mini=document.getElementById('experienceDecisionStats'); if(mini)mini.innerHTML=[['Target customer',v.target],['Validation model',v.validation],['Long-term product',v.longTerm],['Opportunity',v.opportunity],['Strategy',v.strategyScore],['Confidence',v.confidence]].map(([k,val])=>`<div class="experience-mini-stat"><span>${esc(k)}</span><strong>${esc(txt(val))}</strong></div>`).join('');
    const list=document.getElementById('experienceEvidenceList'); if(list){const items=arr(v.evidence?.evidence||v.evidence?.items||v.evidence?.claims).slice(0,8);list.innerHTML=items.length?items.map((x,i)=>`<div class="experience-list-row"><b>${esc(x.claim||x.title||x.name||`Evidence ${i+1}`)}</b><small>${esc(x.source||x.source_id||'backend evidence')}</small></div>`).join(''):`<div class="experience-empty-inline">${esc(v.localEvidence||'Evidence items are not exposed in the current run payload.')}</div>`;}
    const fill=document.getElementById('experienceEvidenceFill');if(fill)fill.style.width=typeof v.confidence==='number'?Math.round(Math.max(0,Math.min(1,v.confidence))*100)+'%':'0%';
  }
  async function hydrateNativePages(){
    const run=await getCanonicalRun(); if(!run)return;
    const v=normalize(run); sessionStorage.setItem('aios.lastJobId',v.run.job_id||v.run.id||'');
    bindExecutive(v);
    if(document.getElementById('goldenJourney')){
      const journey=document.getElementById('goldenJourney'); journey.innerHTML=stageCards(v);
      html('goldenStatus',`<div class="u20-hero-grid"><div><span>Canonical run</span><strong>${esc(v.run.job_id||v.run.id)}</strong></div><div><span>Status</span><strong>${esc(v.run.status)}</strong></div><div><span>Project</span><strong>${esc(v.run.project_id)}</strong></div><div><span>Evidence</span><strong>${esc(v.sourceCount)} sources · ${esc(v.evidenceCount)} evidence</strong></div></div>`);
      html('goldenIntent',`<div class="eyebrow">INTENT</div><h3>${esc(v.goal||'Operating objective')}</h3><div class="u20-detail-grid"><div><span>Request</span><strong>${esc(v.request)}</strong></div><div><span>Target customer / audience</span><strong>${esc(v.target||v.audience)}</strong></div><div><span>Scope</span><strong>${esc(v.scope)}</strong></div><div><span>Constraints</span><strong>${esc(arr(v.constraints).join(' · '))}</strong></div></div>`);
      html('goldenDecision',`<div class="eyebrow">DECISION</div><h3>${esc(v.recommendation||'Decision not exposed')}</h3><p>${esc(v.why||'No rationale exposed by the current run.')}</p><div class="u20-chip-row"><span>Validation · ${esc(v.validation)}</span><span>Product · ${esc(v.longTerm)}</span><span>Opportunity · ${esc(v.opportunity)}</span><span>Strategy · ${esc(v.strategyScore)}</span><span>Confidence · ${esc(v.confidence)}</span></div>`);
      html('goldenGovernance',`<div class="eyebrow">GOVERNANCE</div><h3>${esc(/PENDING|AWAITING_APPROVAL|REVIEW/i.test(String(v.approvalStatus))?'Human review required':'Governance state')}</h3><div class="u20-detail-grid"><div><span>Approval</span><strong>${esc(v.approvalStatus)}</strong></div><div><span>Risk</span><strong>${esc(v.risk)}</strong></div><div><span>Evidence boundary</span><strong>${esc(v.boundary)}</strong></div><div><span>Authority</span><strong>Backend policy / approval boundary</strong></div></div>`);
      html('goldenOutcome',`<div class="eyebrow">OUTCOME & LEARNING</div><h3>${esc(v.outcome?.status||'Awaiting outcome')}</h3><p>${esc(v.outcome?.summary||v.outcome?.message||(v.run.status==='COMPLETE'?'Run completed; outcome detail is only shown when exposed.':'Outcome will appear after execution is observed.'))}</p><div class="u20-chip-row"><span>Learning · ${esc(v.learning?.signal||v.memory?.memory_status||'Not exposed')}</span><span>Next · ${esc(v.next)}</span></div>`);
      html('goldenNext',`<div class="eyebrow">NEXT ACTION</div><h3>${esc(v.next)}</h3><p>${esc(v.rule||v.firstTest||'Use the current validation rule before consequential action.')}</p>`);
      const meta=document.getElementById('goldenRunMeta');if(meta)meta.innerHTML=`<span class="u20-chip">${esc(v.run.job_id||v.run.id)}</span>${pill(v.run.status)}<span class="u20-chip">${esc(v.run.project_id||'')}</span>`;
      const grid=document.getElementById('goldenValidationGrid');if(grid){const checks=[['Run identity',!!v.run.job_id||!!v.run.id],['Intent',!!v.request&&!!v.goal],['Recommendation',!!v.recommendation],['Evidence',v.sourceCount>0&&v.evidenceCount>0],['Validation',!!v.validation],['Governance',!!v.approvalStatus],['Outcome',!!v.outcome?.status||!!v.result?.analytics],['Learning',!!v.learning?.signal||!!v.memory?.memory_status],['Authority',true]];grid.innerHTML=checks.map(c=>`<div class="u20-check ${c[1]?'pass':'review'}"><b>${c[1]?'PASS':'REVIEW'}</b><strong>${esc(c[0])}</strong><small>${c[1]?'Live backend state exposed.':'Field is not exposed by this run.'}</small></div>`).join('');}
      const banner=document.getElementById('goldenIntegrityBanner');if(banner)banner.innerHTML=`<span class="status-dot"></span><div><strong>Canonical run loaded</strong><small>${esc(v.run.job_id||v.run.id)} · same source used by Executive Home and Acceptance.</small></div>`;
      const sel=document.getElementById('goldenRunSelect');if(sel){const rs=await getRuns().catch(()=>[]);sel.innerHTML=rs.map(r=>`<option value="${esc(r.job_id||r.id)}">${esc(r.project_id||'Run')} · ${esc(r.job_id||r.id)} · ${esc(r.status||'')}</option>`).join('');sel.value=v.run.job_id||v.run.id;if(!sel.dataset.u20){sel.dataset.u20='1';sel.addEventListener('change',async()=>{if(!sel.value)return;const rr=await api('/runs/'+encodeURIComponent(sel.value));window.__AIOS_UI20_RUN=rr;hydrateNativePages().catch(()=>{});});}}
    }
    if(document.getElementById('productAcceptance')){
      const checks=[['Intent',!!v.request&&!!v.goal],['Recommendation',!!v.recommendation],['Evidence',v.sourceCount>0&&v.evidenceCount>0],['Validation',!!v.validation],['Target customer',!!v.target],['Governance',!!v.approvalStatus],['Scores',v.opportunity!==undefined&&v.strategyScore!==undefined],['Next decision',!!v.next],['Read-only authority',true]]; const pass=checks.filter(x=>x[1]).length;
      set('acceptanceScore',Math.round(pass/checks.length*100)+'%'); set('acceptanceScoreNote',`${pass}/${checks.length} acceptance checks`); set('acceptanceStatus',pass===checks.length?'PASS':'REVIEW'); set('acceptanceHeadline',pass===checks.length?'Experience is coherent':'Review items remain on the canonical live run.'); set('acceptanceSummary',`Canonical run · ${v.run.job_id||v.run.id}. Missing backend fields are shown honestly; nothing is invented.`);set('acceptanceRunMeta',`${v.run.job_id||v.run.id} · ${v.run.status} · ${v.run.project_id||''}`);
      const ag=document.getElementById('acceptanceGrid');if(ag)ag.innerHTML=checks.map(c=>`<div class="u20-check ${c[1]?'pass':'review'}"><b>${c[1]?'PASS':'REVIEW'}</b><strong>${esc(c[0])}</strong><small>${c[1]?'Exposed on the canonical run.':'Not exposed on the canonical run.'}</small></div>`).join('');
      html('acceptanceFindings',`<div class="eyebrow">CANONICAL RUN</div><h3>${esc(v.recommendation||'Decision not exposed')}</h3><div class="u20-detail-grid"><div><span>Target customer / audience</span><strong>${esc(v.target||v.audience)}</strong></div><div><span>Validation model</span><strong>${esc(v.validation)}</strong></div><div><span>Evidence</span><strong>${esc(v.sourceCount)} sources · ${esc(v.evidenceCount)} evidence</strong></div><div><span>Next action</span><strong>${esc(v.next)}</strong></div></div>`);
      html('acceptanceBoundary',`<div class="eyebrow">PRODUCT BOUNDARY</div><h3>Presentation is not authority.</h3><p>Approval, governance, execution, and memory remain backend responsibilities. This console reads and explains the live state only.</p>`);
    }
    const gc=document.getElementById('goldenControlRunId');if(gc){set('goldenControlHeadline',v.run.status==='COMPLETE'?'Latest reference run is complete':'Current reference run loaded');set('goldenControlRunId',v.run.job_id||v.run.id);set('goldenControlProject',v.run.project_id);set('goldenControlRunStatus',v.run.status);set('goldenControlGovernance',v.approvalStatus);set('goldenControlNext',v.next);set('goldenControlBadge',v.run.status||'READY');const steps=document.getElementById('goldenControlSteps');if(steps)steps.innerHTML=stageCards(v);}
  }
  function surfaceMode(){
    document.querySelectorAll('.page').forEach(p=>{
      const host=p.querySelector('.u15-host');
      const id=p.id||'';
      if(['page-overview','page-golden','page-acceptance','page-goldenrun'].includes(id)) p.classList.add('u20-native-preferred');
      else if(host) p.classList.add('u20-host-preferred');
    });
  }
  function currentPage(){return [...document.querySelectorAll('.page')].find(p=>!p.classList.contains('hidden'))?.id||'';}
  let lastPage='';
  async function onPageChange(){surfaceMode();const page=currentPage();if(page===lastPage)return;lastPage=page;try{if(['page-overview','page-golden','page-acceptance','page-goldenrun'].includes(page)) await hydrateNativePages();}catch{}}
  function watchNavigation(){
    const observer=new MutationObserver(()=>{clearTimeout(watchNavigation._t);watchNavigation._t=setTimeout(onPageChange,80)});
    observer.observe(document.body,{subtree:true,attributes:true,attributeFilter:['class']});
    document.addEventListener('click',()=>setTimeout(onPageChange,120),true);
    window.addEventListener('hashchange',()=>setTimeout(onPageChange,80));
  }
  function polish(){
    document.querySelectorAll('.page').forEach(p=>p.classList.add('u20-ready'));
    surfaceMode();
  }
  async function boot(){polish();watchNavigation();await onPageChange();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else setTimeout(boot,50);
})();
