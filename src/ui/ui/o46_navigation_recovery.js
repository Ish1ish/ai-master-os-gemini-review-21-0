/* O46 Navigation Recovery v1
   UI-only fail-safe navigation bridge.
   Does not touch backend APIs, auth, governance, or execution.
*/
(function () {
  'use strict';

  if (window.__O46_NAVIGATION_RECOVERY__) return;
  window.__O46_NAVIGATION_RECOVERY__ = true;

  function showPage(page) {
    if (!page) return;
    var target = document.getElementById('page-' + page);
    if (!target) return;

    document.querySelectorAll('.page').forEach(function (p) {
      p.classList.toggle('hidden', p !== target);
    });

    document.querySelectorAll('.nav-item[data-page]').forEach(function (item) {
      var active = item.dataset.page === page;
      item.classList.toggle('active', active);
      if (active) {
        item.setAttribute('aria-current', 'page');
      } else {
        item.removeAttribute('aria-current');
      }
    });

    window.dispatchEvent(new CustomEvent('aios:page-changed', {
      detail: { page: page }
    }));
  }

  window.__O46_SHOW_PAGE__ = showPage;

  if (typeof window.page !== 'function') {
    window.page = showPage;
  }

  document.addEventListener('click', function (event) {
    var nav = event.target.closest && event.target.closest('.nav-item[data-page]');
    var jump = event.target.closest && event.target.closest('[data-page-jump]');
    var u15 = event.target.closest && event.target.closest('[data-u15-nav]');

    var page = nav ? nav.dataset.page :
               jump ? jump.dataset.pageJump :
               u15 ? u15.dataset.u15Nav : null;

    if (!page) return;

    showPage(page);
  }, true);

  function initialize() {
    var active = document.querySelector('.nav-item.active[data-page]');
    showPage(active ? active.dataset.page : 'overview');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize, { once: true });
  } else {
    initialize();
  }
})();
