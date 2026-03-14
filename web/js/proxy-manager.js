// Diagram: 02-dashboard-login
/* Proxy Manager — Task 089 */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var panel = document.getElementById('pm-panel');
  var status = document.getElementById('pm-status');

  function setStatus(msg) { status.textContent = msg; }

  function renderProfiles(profiles) {
    if (!profiles.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No proxy profiles configured.</p>';
      return;
    }
    panel.innerHTML = profiles.map(function (p) {
      return '<div class="pm-item">'
        + '<div class="pm-item-info">'
        + '<span class="pm-item-id">' + escHtml(p.profile_id) + '</span>'
        + '<span class="pm-item-meta">Protocol: ' + escHtml(p.protocol) + ' | Port: ' + escHtml(p.port) + '</span>'
        + '</div>'
        + '<button class="pm-btn-activate" data-id="' + escHtml(p.profile_id) + '" data-action="activate">Activate</button>'
        + '</div>';
    }).join('');
  }

  function renderActive(active) {
    if (!active) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No active proxy.</p>';
      return;
    }
    panel.innerHTML = '<div class="pm-item"><div class="pm-item-info">'
      + '<span class="pm-item-id">' + escHtml(active.profile_id) + '</span>'
      + '<span class="pm-item-meta">Protocol: ' + escHtml(active.protocol) + ' | Port: ' + escHtml(active.port) + '</span>'
      + '</div></div>';
  }

  function loadProfiles() {
    fetch('/api/v1/proxy-manager/profiles')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderProfiles(data.profiles || []);
        setStatus('Profiles: ' + (data.total || 0));
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadActive() {
    fetch('/api/v1/proxy-manager/active')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderActive(data.active);
        setStatus('Active proxy loaded');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadProtocols() {
    fetch('/api/v1/proxy-manager/protocols')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        panel.innerHTML = '<p class="pm-item-meta">Protocols: ' + escHtml((data.protocols || []).join(', ')) + '</p>';
        setStatus('Protocols loaded');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  document.getElementById('btn-pm-profiles').addEventListener('click', loadProfiles);
  document.getElementById('btn-pm-active').addEventListener('click', loadActive);
  document.getElementById('btn-pm-protocols').addEventListener('click', loadProtocols);

  panel.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-action="activate"]');
    if (!btn) { return; }
    var profileId = btn.getAttribute('data-id');
    fetch('/api/v1/proxy-manager/profiles/' + encodeURIComponent(profileId) + '/activate', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function () { setStatus('Activated: ' + escHtml(profileId)); loadProfiles(); })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  loadProfiles();
})();
