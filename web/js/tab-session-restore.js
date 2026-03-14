// Diagram: 02-dashboard-login
/* tab-session-restore.js — Tab Session Restore | Task 127 | IIFE, escHtml, no CDN, no eval */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  const BASE = '';
  const TAGS = ['work', 'research', 'shopping', 'reading', 'media', 'social', 'other'];

  async function api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    return res.json();
  }

  async function loadSessions() {
    const data = await api('GET', '/api/v1/tab-sessions/sessions');
    const container = document.getElementById('tsr-sessions-list');
    if (!container) return;
    const items = data.sessions || [];
    if (items.length === 0) {
      container.innerHTML = '<div class="tsr-empty">No saved sessions yet.</div>';
      return;
    }
    container.innerHTML = items.map(s => `
      <div class="tsr-item">
        <div class="tsr-item-info">
          <span class="tsr-item-id">${escHtml(s.session_id)}</span>
          <span class="tsr-item-meta">Tabs: ${escHtml(String(s.tab_count))} | Tag: ${escHtml(s.tag)} | Restores: ${escHtml(String(s.restore_count))}</span>
          <span class="tsr-item-meta">Saved: ${escHtml(s.saved_at)}</span>
        </div>
        <div class="tsr-item-actions">
          <button class="tsr-btn tsr-btn-success tsr-btn-sm" data-restore="${escHtml(s.session_id)}">Restore</button>
          <button class="tsr-btn tsr-btn-danger tsr-btn-sm" data-delete="${escHtml(s.session_id)}">Delete</button>
        </div>
      </div>
    `).join('');
    container.querySelectorAll('[data-restore]').forEach(btn => {
      btn.addEventListener('click', function () {
        restoreSession(this.getAttribute('data-restore'));
      });
    });
    container.querySelectorAll('[data-delete]').forEach(btn => {
      btn.addEventListener('click', function () {
        deleteSession(this.getAttribute('data-delete'));
      });
    });
  }

  async function loadStats() {
    const data = await api('GET', '/api/v1/tab-sessions/stats');
    const container = document.getElementById('tsr-stats');
    if (!container) return;
    container.innerHTML = `
      <div class="tsr-stats-grid">
        <div class="tsr-stat-card"><div class="tsr-stat-value">${escHtml(String(data.total_sessions))}</div><div class="tsr-stat-label">Sessions</div></div>
        <div class="tsr-stat-card"><div class="tsr-stat-value">${escHtml(String(data.total_restores))}</div><div class="tsr-stat-label">Restores</div></div>
        <div class="tsr-stat-card"><div class="tsr-stat-value">${escHtml(String(data.avg_tab_count))}</div><div class="tsr-stat-label">Avg Tabs</div></div>
      </div>
    `;
  }

  async function createSession() {
    const name = document.getElementById('tsr-name').value.trim();
    const tabCount = parseInt(document.getElementById('tsr-tab-count').value, 10);
    const tag = document.getElementById('tsr-tag').value;
    const msg = document.getElementById('tsr-msg');
    if (!name) { msg.textContent = 'Session name is required.'; msg.className = 'tsr-error'; return; }
    if (!tabCount || tabCount < 1) { msg.textContent = 'Tab count must be >= 1.'; msg.className = 'tsr-error'; return; }
    const data = await api('POST', '/api/v1/tab-sessions/sessions', { session_name: name, tab_count: tabCount, tag });
    if (data.session) {
      msg.textContent = 'Session saved: ' + data.session.session_id;
      msg.className = 'tsr-success';
      document.getElementById('tsr-name').value = '';
      document.getElementById('tsr-tab-count').value = '1';
      loadSessions();
      loadStats();
    } else {
      msg.textContent = data.error || 'Error saving session.';
      msg.className = 'tsr-error';
    }
  }

  async function restoreSession(sessionId) {
    const data = await api('POST', '/api/v1/tab-sessions/sessions/' + sessionId + '/restore', {});
    if (data.restore) {
      loadSessions();
      loadStats();
    }
  }

  async function deleteSession(sessionId) {
    const data = await api('DELETE', '/api/v1/tab-sessions/sessions/' + sessionId);
    if (data.status === 'deleted') {
      loadSessions();
      loadStats();
    }
  }

  function populateTags() {
    const sel = document.getElementById('tsr-tag');
    if (!sel) return;
    sel.innerHTML = TAGS.map(t => `<option value="${escHtml(t)}">${escHtml(t)}</option>`).join('');
  }

  function init() {
    populateTags();
    loadSessions();
    loadStats();
    const saveBtn = document.getElementById('tsr-save-btn');
    if (saveBtn) saveBtn.addEventListener('click', createSession);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
