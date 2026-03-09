/* Accessibility Checker — Task 087 */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var panel = document.getElementById('ac-panel');
  var status = document.getElementById('ac-status');

  function setStatus(msg) { status.textContent = msg; }

  function renderScans(scans) {
    if (!scans.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No scans recorded.</p>';
      return;
    }
    panel.innerHTML = scans.map(function (s) {
      return '<div class="ac-item">'
        + '<div class="ac-item-id">' + escHtml(s.scan_id) + '</div>'
        + '<div class="ac-item-meta">WCAG: ' + escHtml(s.wcag_level)
        + ' | Pass: ' + escHtml(s.pass_count)
        + ' | Fail: ' + escHtml(s.fail_count)
        + ' | Score: <span class="ac-score">' + escHtml(s.score) + '%</span></div>'
        + '</div>';
    }).join('');
  }

  function renderLevels(levels) {
    panel.innerHTML = '<p class="ac-item-meta">WCAG levels: ' + escHtml(levels.join(', ')) + '</p>';
  }

  function loadScans() {
    fetch('/api/v1/accessibility/scans')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderScans(data.scans || []);
        setStatus('Scans loaded: ' + (data.total || 0));
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  function loadLevels() {
    fetch('/api/v1/accessibility/wcag-levels')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderLevels(data.wcag_levels || []);
        setStatus('Levels loaded');
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  document.getElementById('btn-ac-scans').addEventListener('click', loadScans);
  document.getElementById('btn-ac-levels').addEventListener('click', loadLevels);

  loadScans();
})();
