// Diagram: 02-dashboard-login
/* tab-organizer.js — Tab Organizer | Task 099 | IIFE + escHtml */
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  const API = '/api/v1/tab-organizer';

  async function loadWorkspaces() {
    const res = await fetch(API + '/workspaces');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('to-workspaces-list');
    if (!list) return;
    list.innerHTML = data.workspaces.map(w =>
      `<div class="to-item"><span>${escHtml(w.workspace_id)}</span> <span>tabs: ${escHtml(String(w.tab_count))}</span></div>`
    ).join('');
  }

  async function loadStatuses() {
    const res = await fetch(API + '/tab-statuses');
    if (!res.ok) return;
    const data = await res.json();
    const el = document.getElementById('to-statuses');
    if (!el) return;
    el.innerHTML = data.statuses.map(s =>
      `<span class="to-badge">${escHtml(s)}</span>`
    ).join('');
  }

  function init() {
    loadWorkspaces();
    loadStatuses();
    const btn = document.getElementById('to-create-ws-btn');
    if (btn) {
      btn.addEventListener('click', async function () {
        await fetch(API + '/workspaces', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name_hash: '' }),
        });
        loadWorkspaces();
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
