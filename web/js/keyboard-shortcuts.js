/**
 * keyboard-shortcuts.js — Keyboard Shortcuts Panel for Solace Hub (Task 028)
 * Laws:
 *   - No CDN dependencies. No jQuery. No Bootstrap. No Tailwind.
 *   - Port 8888 ONLY (same origin). Banned port omitted from source.
 *   - Dynamic escaping via escHtml() required for all dynamic content.
 *   - Solace Hub only. "Companion App" BANNED.
 *   - All CSS via var(--hub-*) tokens only.
 *   - IIFE pattern.
 */

'use strict';

(function () {
  var TOKEN = localStorage.getItem('solace_token') || '';
  var AUTH_HEADERS = { 'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json' };

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function apiFetch(path, opts) {
    return fetch(path, opts || { headers: AUTH_HEADERS });
  }

  function apiFetchAuth(path, method, body) {
    var opts = { method: method || 'GET', headers: AUTH_HEADERS };
    if (body !== undefined) opts.body = JSON.stringify(body);
    return apiFetch(path, opts);
  }

  // --- Render key combo as kbd elements ---
  function renderKeyCombo(key) {
    var parts = String(key).split('+');
    return parts.map(function (k) { return '<kbd>' + escHtml(k.trim()) + '</kbd>'; }).join('+');
  }

  // --- Render default shortcuts ---
  function renderDefaultShortcuts(shortcuts) {
    var el = document.getElementById('default-shortcuts');
    if (!el) return;
    if (!shortcuts || !shortcuts.length) {
      el.innerHTML = '<div class="empty-state">No default shortcuts defined.</div>';
      return;
    }
    el.innerHTML = shortcuts.map(function (s) {
      return (
        '<div class="shortcut-row shortcut-row--default">' +
          '<div class="shortcut-key">' + renderKeyCombo(s.key) + '</div>' +
          '<div class="shortcut-desc">' + escHtml(s.description || '') + '</div>' +
          '<span class="shortcut-badge">default</span>' +
        '</div>'
      );
    }).join('');
  }

  // --- Render custom shortcuts ---
  function renderCustomShortcuts(shortcuts) {
    var el = document.getElementById('custom-shortcuts');
    if (!el) return;
    if (!shortcuts || !shortcuts.length) {
      el.innerHTML = '<div class="empty-state">No custom shortcuts yet.</div>';
      return;
    }
    el.innerHTML = shortcuts.map(function (s) {
      var sid = escHtml(s.id || s.shortcut_id || '');
      return (
        '<div class="shortcut-row">' +
          '<div class="shortcut-key">' + renderKeyCombo(s.key) + '</div>' +
          '<div class="shortcut-desc">' + escHtml(s.description || '') + '</div>' +
          '<button class="btn-delete" data-id="' + sid + '">Delete</button>' +
        '</div>'
      );
    }).join('');
    el.querySelectorAll('.btn-delete').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = btn.getAttribute('data-id');
        deleteShortcut(id);
      });
    });
  }

  // --- Load all shortcuts ---
  function loadShortcuts() {
    apiFetch('/api/v1/keyboard-shortcuts')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        renderDefaultShortcuts(d.defaults || d.default_shortcuts || []);
        renderCustomShortcuts(d.custom || d.custom_shortcuts || []);
      })
      .catch(function () {
        var el = document.getElementById('default-shortcuts');
        if (el) el.innerHTML = '<div class="empty-state">Could not load shortcuts.</div>';
      });
  }

  // --- Delete custom shortcut ---
  function deleteShortcut(id) {
    if (!id) return;
    if (!confirm('Delete this custom shortcut?')) return;
    apiFetchAuth('/api/v1/keyboard-shortcuts/' + encodeURIComponent(id), 'DELETE')
      .then(function (r) {
        if (!r.ok) throw new Error('Delete failed (' + r.status + ')');
        loadShortcuts();
      })
      .catch(function (e) { alert('Failed to delete shortcut: ' + e.message); });
  }

  // --- Add shortcut modal ---
  function openModal() {
    var modal = document.getElementById('modal-add-shortcut');
    var keyInp = document.getElementById('input-key');
    var err = document.getElementById('modal-ks-error');
    if (modal) modal.style.display = 'flex';
    if (keyInp) { keyInp.value = ''; keyInp.focus(); }
    if (err) { err.style.display = 'none'; err.textContent = ''; }
    var descInp = document.getElementById('input-desc');
    var actInp = document.getElementById('input-action');
    if (descInp) descInp.value = '';
    if (actInp) actInp.value = '';
  }

  function closeModal() {
    var modal = document.getElementById('modal-add-shortcut');
    if (modal) modal.style.display = 'none';
  }

  function confirmAdd() {
    var keyInp = document.getElementById('input-key');
    var descInp = document.getElementById('input-desc');
    var actInp = document.getElementById('input-action');
    var err = document.getElementById('modal-ks-error');
    var key = (keyInp ? keyInp.value : '').trim();
    var desc = (descInp ? descInp.value : '').trim();
    var action = (actInp ? actInp.value : '').trim();

    if (!key) {
      if (err) { err.textContent = 'Key combination is required.'; err.style.display = ''; }
      return;
    }
    if (!desc) {
      if (err) { err.textContent = 'Description is required.'; err.style.display = ''; }
      return;
    }
    var payload = { key: key, description: desc };
    if (action) payload.action = action;

    apiFetchAuth('/api/v1/keyboard-shortcuts', 'POST', payload)
      .then(function (r) {
        if (r.status === 400) return r.json().then(function (d) { throw new Error(d.error || 'Bad request'); });
        if (r.status === 409) return r.json().then(function (d) { throw new Error(d.error || 'Conflict'); });
        if (!r.ok) throw new Error('Add failed (' + r.status + ')');
        return r.json();
      })
      .then(function () { closeModal(); loadShortcuts(); })
      .catch(function (e) {
        if (err) { err.textContent = e.message; err.style.display = ''; }
      });
  }

  // --- Global ? key handler ---
  document.addEventListener('keydown', function (e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === '?' || (e.shiftKey && e.key === '/')) {
      var page = document.querySelector('.ks-page');
      if (page) page.style.display = page.style.display === 'none' ? '' : '';
    }
  });

  // --- Bind buttons ---
  var btnAdd = document.getElementById('btn-add-shortcut');
  var btnCancel = document.getElementById('btn-cancel-shortcut');
  var btnConfirm = document.getElementById('btn-confirm-shortcut');
  var overlay = document.getElementById('modal-add-shortcut');

  if (btnAdd) btnAdd.addEventListener('click', openModal);
  if (btnCancel) btnCancel.addEventListener('click', closeModal);
  if (btnConfirm) btnConfirm.addEventListener('click', confirmAdd);
  if (overlay) {
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeModal();
    });
  }

  loadShortcuts();
})();
