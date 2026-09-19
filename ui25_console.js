/* UI25 — Final structured-data presentation repair. Read-only UI overlay. */
(function(){
  'use strict';
  function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function parseMaybe(v){
    if(v==null)return null;
    if(typeof v==='object')return v;
    if(typeof v!=='string')return v;
    const t=v.trim();
    if(!t)return '';
    if((t[0]==='{'||t[0]==='[')){
      try{return JSON.parse(t);}catch{}
    }
    return t;
  }
  function summary(v,depth=0){
    if(depth>6||v==null)return '';
    const p=parseMaybe(v);
    if(p===null||p===undefined)return '';
    if(typeof p==='string')return p.trim();
    if(Array.isArray(p))return p.map(x=>summary(x,depth+1)).filter(Boolean).slice(0,3).join(' · ');
    if(typeof p==='object'){
      const keys=['summary','learning_summary','lesson_summary','signal','observed_bottleneck','message','next_test','recommendation','decision_summary','description'];
      for(const k of keys){if(p[k]){const s=summary(p[k],depth+1);if(s)return s;}}
      for(const k of ['learning','lesson','context','next_step','feedback']){if(p[k]){const s=summary(p[k],depth+1);if(s)return s;}}
    }
    return '';
  }
  function shortLearning(text){
    const s=summary(text);
    if(!s)return 'Learning signal not exposed.';
    return s.length>220?s.slice(0,217)+'…':s;
  }
  function repairLearning(root){
    if(!root)return;
    root.querySelectorAll('.u24-learning-copy, .u24-step small, .u24-chip, .u24-row span, .u24-panel p').forEach(el=>{
      const t=(el.textContent||'').trim();
      if(!t)return;
      const lower=t.toLowerCase();
      const looksLearning=/lesson_id|learning_summary|observed_bottleneck|source_refs/.test(lower) || (t[0]==='{'&&t.includes(':'));
      if(looksLearning){
        const next=shortLearning(t);
        if(next && next!==t){el.textContent=next;el.setAttribute('data-u25-cleaned','true');}
      }
    });
    const steps=root.querySelectorAll('.u24-step');
    if(steps[7]){
      const small=steps[7].querySelector('small');
      if(small)small.textContent=shortLearning(small.textContent);
    }
  }
  function addLearningSummaryPanel(page){
    if(!page || page.querySelector('.u25-learning-summary'))return;
    const id=page.id;
    if(id!=='page-overview'&&id!=='page-golden'&&id!=='page-memory'&&id!=='page-adaptation')return;
    const title=id==='page-adaptation'?'Adaptive signal':'Learning signal';
    const panel=document.createElement('section');
    panel.className='u25-learning-summary';
    panel.innerHTML='<div class="u25-learning-grid"><div><span class="u25-eyebrow">'+title+'</span><h3>What the system learned</h3><p class="u25-learning-value">'+esc('Loading backend-derived signal…')+'</p></div><div><span class="u25-eyebrow">Next bounded test</span><h3>What happens next</h3><p class="u25-next-value">'+esc('Loading next step…')+'</p></div></div>';
    const anchor=page.querySelector('.u24-ext')||page.querySelector('.u24-section')||page.querySelector('.u24-context');
    if(anchor)anchor.insertAdjacentElement('afterend',panel); else page.appendChild(panel);
  }
  function findLearningText(){
    const candidates=[
      document.querySelector('.page:not(.hidden) .u24-step:nth-child(8) small'),
      document.querySelector('.page:not(.hidden) .u24-learning-copy'),
      document.querySelector('.page:not(.hidden) .u24-chip')
    ].filter(Boolean);
    for(const el of candidates){const t=(el.textContent||'').trim();if(t)return summary(t);}
    return '';
  }
  function findNextText(){
    const el=document.querySelector('.page:not(.hidden) .u24-step:nth-child(9) small');
    return el?summary(el.textContent):'';
  }
  function hydratePanel(){
    document.querySelectorAll('.u25-learning-summary').forEach(p=>{
      const a=p.querySelector('.u25-learning-value'); const n=p.querySelector('.u25-next-value');
      const l=findLearningText(); const nx=findNextText();
      if(a && l)a.textContent=l.length>220?l.slice(0,217)+'…':l;
      if(n && nx)n.textContent=nx;
    });
  }
  function run(){
    const pages=document.querySelectorAll('.page:not(.hidden)');
    pages.forEach(p=>{repairLearning(p);addLearningSummaryPanel(p);});
    hydratePanel();
  }
  document.addEventListener('DOMContentLoaded',()=>setTimeout(run,300));
  window.addEventListener('load',()=>setTimeout(run,500));
  document.addEventListener('click',e=>{if(e.target.closest('.nav-item[data-page]'))setTimeout(run,500);},true);
  window.addEventListener('hashchange',()=>setTimeout(run,500));
  const mo=new MutationObserver(()=>{clearTimeout(mo.t);mo.t=setTimeout(run,180);});
  mo.observe(document.documentElement,{subtree:true,childList:true});
  setTimeout(run,900);
})();
