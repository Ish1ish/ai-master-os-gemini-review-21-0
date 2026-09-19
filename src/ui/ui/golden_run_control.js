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
  const view=buildO46ExperienceView({...run,learning_context:learning,approvals:approval});
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
      const out=await api('/runs',{method:'POST',body:JSON.stringify(GOLDEN_CONTROL_PAYLOAD)});
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
      await api(`/runs/${encodeURIComponent(run.job_id)}/execute`,{method:'POST',body:JSON.stringify({})});
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
