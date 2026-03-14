// Diagram: 02-dashboard-login
/* auto-translate.js — Auto Translate | Task 128 | IIFE, escHtml, no CDN, no eval */
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
  let _languages = [];
  const ENGINES = ['google', 'deepl', 'azure', 'aws', 'local'];

  async function api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    return res.json();
  }

  async function loadLanguages() {
    const data = await api('GET', '/api/v1/auto-translate/languages');
    _languages = data.languages || [];
    ['atr-source', 'atr-target'].forEach(id => {
      const sel = document.getElementById(id);
      if (sel) {
        sel.innerHTML = _languages.map(l => `<option value="${escHtml(l)}">${escHtml(l)}</option>`).join('');
      }
    });
  }

  function populateEngines() {
    const sel = document.getElementById('atr-engine');
    if (!sel) return;
    sel.innerHTML = ENGINES.map(e => `<option value="${escHtml(e)}">${escHtml(e)}</option>`).join('');
  }

  async function loadPreferences() {
    const data = await api('GET', '/api/v1/auto-translate/preferences');
    const container = document.getElementById('atr-prefs-list');
    if (!container) return;
    const items = data.preferences || [];
    if (items.length === 0) {
      container.innerHTML = '<div class="atr-empty">No preferences yet.</div>';
      return;
    }
    container.innerHTML = items.map(p => `
      <div class="atr-item">
        <div class="atr-item-info">
          <span class="atr-item-id">${escHtml(p.pref_id)}</span>
          <span class="atr-item-meta"><span class="atr-lang-pair">${escHtml(p.source_language)} &rarr; ${escHtml(p.target_language)}</span> <span class="atr-engine-badge">${escHtml(p.engine)}</span></span>
          <span class="atr-item-meta">Auto: ${p.auto_enabled ? 'yes' : 'no'} | Created: ${escHtml(p.created_at)}</span>
        </div>
        <div class="atr-item-actions">
          <button class="atr-btn atr-btn-danger atr-btn-sm" data-delete="${escHtml(p.pref_id)}">Delete</button>
        </div>
      </div>
    `).join('');
    container.querySelectorAll('[data-delete]').forEach(btn => {
      btn.addEventListener('click', function () {
        deletePref(this.getAttribute('data-delete'));
      });
    });
  }

  async function loadStats() {
    const data = await api('GET', '/api/v1/auto-translate/stats');
    const container = document.getElementById('atr-stats');
    if (!container) return;
    const byEngine = data.by_engine || {};
    const engineLines = Object.keys(byEngine).map(k => `${escHtml(k)}: ${escHtml(String(byEngine[k]))}`).join(', ');
    container.innerHTML = `
      <div class="atr-stats-grid">
        <div class="atr-stat-card"><div class="atr-stat-value">${escHtml(String(data.total_translations))}</div><div class="atr-stat-label">Translations</div></div>
        <div class="atr-stat-card"><div class="atr-stat-value">${escHtml(String(data.total_words))}</div><div class="atr-stat-label">Words</div></div>
      </div>
      ${engineLines ? '<p class="atr-item-meta" style="margin-top:0.5rem">By engine: ' + engineLines + '</p>' : ''}
    `;
  }

  async function createPref() {
    const source = document.getElementById('atr-source').value;
    const target = document.getElementById('atr-target').value;
    const engine = document.getElementById('atr-engine').value;
    const site = document.getElementById('atr-site').value.trim();
    const msg = document.getElementById('atr-msg');
    const data = await api('POST', '/api/v1/auto-translate/preferences', {
      source_language: source,
      target_language: target,
      engine,
      site_domain: site,
    });
    if (data.preference) {
      msg.textContent = 'Preference saved: ' + data.preference.pref_id;
      msg.className = 'atr-success';
      document.getElementById('atr-site').value = '';
      loadPreferences();
      loadStats();
    } else {
      msg.textContent = data.error || 'Error saving preference.';
      msg.className = 'atr-error';
    }
  }

  async function deletePref(prefId) {
    const data = await api('DELETE', '/api/v1/auto-translate/preferences/' + prefId);
    if (data.status === 'deleted') loadPreferences();
  }

  function init() {
    loadLanguages();
    populateEngines();
    loadPreferences();
    loadStats();
    const saveBtn = document.getElementById('atr-save-btn');
    if (saveBtn) saveBtn.addEventListener('click', createPref);
    const refreshStats = document.getElementById('atr-refresh-stats');
    if (refreshStats) refreshStats.addEventListener('click', loadStats);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
