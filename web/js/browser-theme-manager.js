// Diagram: 02-dashboard-login
/* browser-theme-manager.js — Browser Theme Manager | Task 132 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_THEMES = '/api/v1/theme-manager/themes';
  var API_ACTIVE = '/api/v1/theme-manager/active';
  var API_TYPES  = '/api/v1/theme-manager/theme-types';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('btm-status');
    if (el) el.textContent = msg;
  }

  function loadThemeTypes() {
    fetch(API_TYPES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var types = data.theme_types || [];
        var accents = data.accent_colors || [];
        var tSel = document.getElementById('btm-type');
        if (tSel) {
          tSel.innerHTML = types.map(function (t) {
            return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
          }).join('');
        }
        var aSel = document.getElementById('btm-accent');
        if (aSel) {
          aSel.innerHTML = accents.map(function (a) {
            return '<option value="' + escHtml(a) + '">' + escHtml(a) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading theme types: ' + err.message); });
  }

  function loadActive() {
    fetch(API_ACTIVE, { headers: { Authorization: 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('btm-active');
        if (!el) return;
        if (data.error) { el.textContent = 'No active theme'; return; }
        var t = data.theme;
        el.textContent = t.theme_type + ' / ' + t.accent_color + ' (' + t.theme_id + ')';
      })
      .catch(function (err) { setStatus('Error loading active theme: ' + err.message); });
  }

  function loadThemes() {
    fetch(API_THEMES, { headers: { Authorization: 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('btm-list');
        if (!el) return;
        var themes = data.themes || [];
        if (themes.length === 0) { el.innerHTML = '<p>No themes yet.</p>'; return; }
        el.innerHTML = themes.map(function (t) {
          return '<div class="btm-item' + (t.is_active ? ' active' : '') + '">' +
            '<span>' + escHtml(t.theme_type) + ' / ' + escHtml(t.accent_color) + (t.is_active ? ' (active)' : '') + '</span>' +
            '<div style="display:flex;gap:0.5rem;">' +
            '<button class="btm-btn btm-btn-success" data-activate="' + escHtml(t.theme_id) + '">Activate</button>' +
            '<button class="btm-btn btm-btn-danger" data-id="' + escHtml(t.theme_id) + '">Delete</button>' +
            '</div>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteTheme(btn.getAttribute('data-id')); });
        });
        el.querySelectorAll('button[data-activate]').forEach(function (btn) {
          btn.addEventListener('click', function () { activateTheme(btn.getAttribute('data-activate')); });
        });
      })
      .catch(function (err) { setStatus('Error loading themes: ' + err.message); });
  }

  function deleteTheme(id) {
    fetch(API_THEMES + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { Authorization: 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadThemes(); loadActive(); setStatus('Deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  function activateTheme(id) {
    fetch(API_THEMES + '/' + encodeURIComponent(id) + '/activate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (window._solaceToken || '') },
      body: JSON.stringify({}),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { setStatus('Error: ' + data.error); return; }
        setStatus('Activated: ' + id);
        loadThemes();
        loadActive();
      })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadThemeTypes();
    loadActive();
    loadThemes();

    var form = document.getElementById('btm-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var payload = {
          name: document.getElementById('btm-name').value.trim(),
          theme_type: document.getElementById('btm-type').value,
          accent_color: document.getElementById('btm-accent').value,
        };
        fetch(API_THEMES, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + (window._solaceToken || '') },
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Created: ' + data.theme.theme_id);
            form.reset();
            loadThemes();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
