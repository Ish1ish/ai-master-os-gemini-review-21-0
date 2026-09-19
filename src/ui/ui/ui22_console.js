/* UI22 — Deterministic single-page visibility + state text cleanup. Read-only. */
(function(){
  'use strict';
  const visiblePages = () => [...document.querySelectorAll('.page')];
  function targetPage(){
    const nav = document.querySelector('.nav-item.active[data-page]');
    if(nav) return document.getElementById('page-'+nav.dataset.page);
    return document.querySelector('.page:not(.hidden)') || document.querySelector('.page');
  }
  function enforceSingleton(){
    const target = targetPage();
    if(!target) return;
    for(const p of visiblePages()){
      const keep = p===target;
      p.classList.toggle('u22-visible-force', keep);
      p.classList.toggle('u22-hidden-force', !keep);
      p.classList.toggle('hidden', !keep);
      if(keep) p.removeAttribute('aria-hidden'); else p.setAttribute('aria-hidden','true');
    }
    window.__AIOS_UI22_ACTIVE_PAGE = target.id;
  }
  function cleanLearningText(){
    document.querySelectorAll('.u21-stage small, .u21-card p, .u21-check small').forEach(el=>{
      const t=(el.textContent||'').trim();
      if(t.length>180){ el.textContent=t.slice(0,177)+'…'; el.dataset.trimmed='true'; el.classList.add('u22-stage-detail'); }
    });
  }
  let timer=0;
  function schedule(){clearTimeout(timer);timer=setTimeout(()=>{enforceSingleton();cleanLearningText();},40)}
  function boot(){
    enforceSingleton(); cleanLearningText();
    const mo=new MutationObserver(schedule);
    mo.observe(document.body,{subtree:true,attributes:true,attributeFilter:['class','style']});
    document.addEventListener('click',()=>setTimeout(schedule,100),true);
    window.addEventListener('hashchange',schedule);
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',boot); else setTimeout(boot,50);
})();
