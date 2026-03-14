// Diagram: 02-dashboard-login
/* social-share-tracker.js — Social Share Tracker | Task 137 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_SHARES    = '/api/v1/social-share/shares';
  var API_STATS     = '/api/v1/social-share/stats';
  var API_PLATFORMS = '/api/v1/social-share/platforms';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('sst-status');
    if (el) el.textContent = msg;
  }

  function authHeader() {
    return { Authorization: 'Bearer ' + (window._solaceToken || '') };
  }

  function loadPlatforms() {
    fetch(API_PLATFORMS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('sst-platform');
        if (sel) {
          sel.innerHTML = (data.platforms || []).map(function (p) {
            return '<option value="' + escHtml(p) + '">' + escHtml(p) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading platforms: ' + err.message); });
  }

  function loadShares() {
    fetch(API_SHARES, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('sst-list');
        if (!el) return;
        var shares = data.shares || [];
        if (shares.length === 0) { el.innerHTML = '<p>No shares yet.</p>'; return; }
        el.innerHTML = shares.slice().reverse().map(function (s) {
          return '<div class="sst-item">' +
            '<div>' +
              '<span class="sst-platform-badge">' + escHtml(s.platform) + '</span>' +
              escHtml(s.share_id) + ' — ' + escHtml(s.shared_at) +
            '</div>' +
            '<button class="sst-btn sst-btn-danger" data-id="' + escHtml(s.share_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteShare(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading shares: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('sst-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="sst-stat-card"><div class="sst-stat-value">' + escHtml(String(data.total_shares || 0)) + '</div><div class="sst-stat-label">Total Shares</div></div>' +
          '<div class="sst-stat-card"><div class="sst-stat-value">' + escHtml(String(data.top_platform || '—')) + '</div><div class="sst-stat-label">Top Platform</div></div>';
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function deleteShare(id) {
    fetch(API_SHARES + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeader(),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadShares(); loadStats(); setStatus('Share deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadPlatforms();
    loadShares();
    loadStats();

    var form = document.getElementById('sst-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var payload = {
          url: document.getElementById('sst-url').value.trim(),
          title: document.getElementById('sst-title').value.trim(),
          platform: document.getElementById('sst-platform').value,
          message: document.getElementById('sst-message').value.trim(),
        };
        fetch(API_SHARES, {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeader()),
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Share recorded: ' + data.share.share_id);
            form.reset();
            loadShares();
            loadStats();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
