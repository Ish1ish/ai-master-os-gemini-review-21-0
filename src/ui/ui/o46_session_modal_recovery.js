/* O46 Session Modal Recovery v1
   UI-only recovery for the topbar Session button.
   Opens/closes the existing sessionModal. Does not read, print, or request secrets.
*/
(function () {
  'use strict';

  if (window.__O46_SESSION_MODAL_RECOVERY__) return;
  window.__O46_SESSION_MODAL_RECOVERY__ = true;

  function openSession() {
    var modal = document.getElementById('sessionModal');
    if (!modal) return;
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
    var apiBase = document.getElementById('apiBase');
    if (apiBase && !apiBase.value) apiBase.value = '/api';
  }

  function closeSession() {
    var modal = document.getElementById('sessionModal');
    if (!modal) return;
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
  }

  function bind() {
    var auth = document.getElementById('authBtn');
    var close = document.getElementById('closeModal');

    if (auth && !auth.dataset.o46SessionBound) {
      auth.dataset.o46SessionBound = '1';
      auth.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        openSession();
      }, true);
    }

    if (close && !close.dataset.o46SessionBound) {
      close.dataset.o46SessionBound = '1';
      close.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        closeSession();
      }, true);
    }

    var modal = document.getElementById('sessionModal');
    if (modal && !modal.dataset.o46BackdropBound) {
      modal.dataset.o46BackdropBound = '1';
      modal.addEventListener('click', function (event) {
        if (event.target === modal) closeSession();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind, { once: true });
  } else {
    bind();
  }

  window.addEventListener('aios:page-changed', bind);
})();
