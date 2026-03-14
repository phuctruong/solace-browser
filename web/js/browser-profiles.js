// Diagram: 02-dashboard-login
/**
 * browser-profiles.js — Browser Profile Manager for Solace Hub (Task 025)
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

  var AVATAR_COLORS = ['blue', 'green', 'red', 'purple', 'orange', 'teal'];

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtDate(ts) {
    if (!ts) return '';
    try { return new Date(ts * 1000).toLocaleDateString(); } catch (e) { return String(ts); }
  }

  function apiFetch(path, opts) {
    return fetch(path, opts || {});
  }

  function apiFetchAuth(path, method, body) {
    var opts = { method: method || 'GET', headers: AUTH_HEADERS };
    if (body !== undefined) opts.body = JSON.stringify(body);
    return apiFetch(path, opts);
  }

  // --- Active profile banner ---
  function renderActiveBanner(profile) {
    var banner = document.getElementById('active-profile-banner');
    if (!banner) return;
    if (!profile) { banner.style.display = 'none'; return; }
    banner.style.display = '';
    banner.textContent = 'Active profile: ' + escHtml(profile.name || profile.id);
  }

  // --- Profile card HTML ---
  function profileCardHtml(profile, activeId) {
    var color = AVATAR_COLORS.includes(profile.avatar_color) ? profile.avatar_color : 'blue';
    var initial = (profile.name || 'P')[0].toUpperCase();
    var isActive = profile.id === activeId || profile.profile_id === activeId;
    var pid = escHtml(profile.id || profile.profile_id || '');
    return (
      '<div class="profile-card' + (isActive ? ' profile-card--active' : '') + '" data-id="' + pid + '">' +
        '<div class="profile-avatar avatar--' + escHtml(color) + '">' + escHtml(initial) + '</div>' +
        '<div class="profile-name">' + escHtml(profile.name || 'Unnamed') + '</div>' +
        '<div class="profile-meta">Created: ' + escHtml(fmtDate(profile.created_at)) + '</div>' +
        (isActive ? '<div class="profile-meta" style="color:var(--hub-accent)">Active</div>' : '') +
        '<div class="profile-actions">' +
          (!isActive ? '<button class="btn-activate" data-action="activate" data-id="' + pid + '">Activate</button>' : '') +
          '<button class="btn-danger" data-action="delete" data-id="' + pid + '">Delete</button>' +
        '</div>' +
      '</div>'
    );
  }

  // --- Load and render ---
  function loadProfiles() {
    var grid = document.getElementById('profiles-list');
    if (grid) grid.innerHTML = '<div class="empty-state">Loading profiles...</div>';

    var activeId = '';

    apiFetch('/api/v1/profiles/active')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var ap = d.active_profile;
        if (ap) {
          activeId = ap.id || ap.profile_id || '';
          renderActiveBanner(ap);
        } else {
          renderActiveBanner(null);
        }
      })
      .catch(function () { renderActiveBanner(null); })
      .then(function () {
        return apiFetch('/api/v1/browser/profiles');
      })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var profiles = d.profiles || [];
        if (!grid) return;
        if (!profiles.length) {
          grid.innerHTML = '<div class="empty-state">No profiles yet. Create one to get started.</div>';
          return;
        }
        grid.innerHTML = profiles.map(function (p) { return profileCardHtml(p, activeId); }).join('');
        grid.querySelectorAll('[data-action]').forEach(function (btn) {
          btn.addEventListener('click', function () {
            var action = btn.getAttribute('data-action');
            var id = btn.getAttribute('data-id');
            if (action === 'activate') activateProfile(id);
            else if (action === 'delete') deleteProfile(id);
          });
        });
      })
      .catch(function () {
        if (grid) grid.innerHTML = '<div class="empty-state">Could not load profiles.</div>';
      });
  }

  // --- Activate ---
  function activateProfile(id) {
    apiFetchAuth('/api/v1/browser/profiles/' + encodeURIComponent(id) + '/activate', 'POST')
      .then(function (r) {
        if (!r.ok) throw new Error('activate failed');
        loadProfiles();
      })
      .catch(function (e) { alert('Failed to activate profile: ' + e.message); });
  }

  // --- Delete ---
  function deleteProfile(id) {
    if (!confirm('Delete this profile? This cannot be undone.')) return;
    apiFetchAuth('/api/v1/browser/profiles/' + encodeURIComponent(id), 'DELETE')
      .then(function (r) {
        if (!r.ok) throw new Error('delete failed');
        loadProfiles();
      })
      .catch(function (e) { alert('Failed to delete profile: ' + e.message); });
  }

  // --- New profile modal ---
  function openModal() {
    var modal = document.getElementById('modal-new');
    var input = document.getElementById('input-name');
    var err = document.getElementById('modal-error');
    if (modal) { modal.style.display = 'flex'; }
    if (input) { input.value = ''; input.focus(); }
    if (err) { err.style.display = 'none'; err.textContent = ''; }
  }

  function closeModal() {
    var modal = document.getElementById('modal-new');
    if (modal) modal.style.display = 'none';
  }

  function confirmCreate() {
    var input = document.getElementById('input-name');
    var select = document.getElementById('select-avatar');
    var err = document.getElementById('modal-error');
    var name = (input ? input.value : '').trim();
    var color = select ? select.value : 'blue';

    if (!name || name.length > 64) {
      if (err) { err.textContent = 'Name must be 1-64 characters.'; err.style.display = ''; }
      return;
    }
    if (!AVATAR_COLORS.includes(color)) {
      if (err) { err.textContent = 'Invalid avatar colour.'; err.style.display = ''; }
      return;
    }

    apiFetchAuth('/api/v1/browser/profiles', 'POST', { name: name, avatar_color: color })
      .then(function (r) {
        if (r.status === 400) return r.json().then(function (d) { throw new Error(d.error || 'Bad request'); });
        if (!r.ok) throw new Error('Create failed (' + r.status + ')');
        return r.json();
      })
      .then(function () {
        closeModal();
        loadProfiles();
      })
      .catch(function (e) {
        if (err) { err.textContent = e.message; err.style.display = ''; }
      });
  }

  // --- Bind events ---
  var btnNew = document.getElementById('btn-new-profile');
  var btnCancel = document.getElementById('btn-cancel-new');
  var btnConfirm = document.getElementById('btn-confirm-new');
  var modalOverlay = document.getElementById('modal-new');
  var inputName = document.getElementById('input-name');

  if (btnNew) btnNew.addEventListener('click', openModal);
  if (btnCancel) btnCancel.addEventListener('click', closeModal);
  if (btnConfirm) btnConfirm.addEventListener('click', confirmCreate);
  if (inputName) inputName.addEventListener('keydown', function (e) { if (e.key === 'Enter') confirmCreate(); });
  if (modalOverlay) {
    modalOverlay.addEventListener('click', function (e) {
      if (e.target === modalOverlay) closeModal();
    });
  }

  loadProfiles();
})();
