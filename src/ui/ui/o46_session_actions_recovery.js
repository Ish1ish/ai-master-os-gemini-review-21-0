/* O46 Session Actions Recovery v1
   UI-only bridge for Save / Test / Clear session controls.
   Secret-safe: token is only read from the local password input and stored in sessionStorage;
   it is never logged, rendered, or included in error text.
*/
(function () {
  'use strict';

  if (window.__O46_SESSION_ACTIONS_RECOVERY__) return;
  window.__O46_SESSION_ACTIONS_RECOVERY__ = true;

  function el(id) {
    return document.getElementById(id);
  }

  function msg(text, ok) {
    var node = el('sessionMsg');
    if (!node) return;
    node.textContent = String(text || '');
    node.dataset.state = ok ? 'ok' : 'error';
  }

  function normalizeToken(value) {
    var token = String(value || '').trim();
    if (token.toLowerCase().startsWith('bearer ')) {
      token = token.slice(7).trim();
    }
    return token;
  }

  function apiBase() {
    return (el('apiBase')?.value || '/api').trim().replace(/\/+$/, '') || '/api';
  }

  function bind() {
    var save = el('saveSession');
    var test = el('testSession');
    var clear = el('clearSession');

    if (save && !save.dataset.o46SessionActionBound) {
      save.dataset.o46SessionActionBound = '1';
      save.addEventListener('click', function () {
        var token = normalizeToken(el('bearerToken')?.value);
        sessionStorage.setItem('aios.apiBase', apiBase());

        if (!token) {
          msg('Bearer token is required.', false);
          return;
        }

        sessionStorage.setItem('aios.bearer', token);
        msg('Session saved locally.', true);
      });
    }

    if (test && !test.dataset.o46SessionActionBound) {
      test.dataset.o46SessionActionBound = '1';
      test.addEventListener('click', async function () {
        var token = normalizeToken(el('bearerToken')?.value) || sessionStorage.getItem('aios.bearer') || '';
        var base = apiBase();

        if (!token) {
          msg('Bearer token is required.', false);
          return;
        }

        test.disabled = true;
        var previous = test.textContent;
        test.textContent = 'Testing…';

        try {
          var response = await fetch(base + '/identity/me', {
            method: 'GET',
            headers: {
              'Accept': 'application/json',
              'Authorization': 'Bearer ' + token
            }
          });

          var payload = await response.json().catch(function () { return {}; });

          if (!response.ok) {
            msg('Session test failed: HTTP ' + response.status + '.', false);
            return;
          }

          sessionStorage.setItem('aios.apiBase', base);
          sessionStorage.setItem('aios.bearer', token);
          msg('Session test passed.', true);
        } catch (error) {
          msg('Session test failed: network or API unavailable.', false);
        } finally {
          test.disabled = false;
          test.textContent = previous;
        }
      });
    }

    if (clear && !clear.dataset.o46SessionActionBound) {
      clear.dataset.o46SessionActionBound = '1';
      clear.addEventListener('click', function () {
        sessionStorage.removeItem('aios.bearer');
        sessionStorage.removeItem('aios.apiBase');
        var input = el('bearerToken');
        if (input) input.value = '';
        var base = el('apiBase');
        if (base) base.value = '/api';
        msg('Local session cleared.', true);
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
