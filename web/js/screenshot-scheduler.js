/* screenshot-scheduler.js — Screenshot Scheduler | Task 126 | IIFE, escHtml, no CDN, no eval */
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
  let _intervals = [];

  async function api(method, path, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    return res.json();
  }

  async function loadIntervals() {
    const data = await api('GET', '/api/v1/screenshot-scheduler/intervals');
    _intervals = data.intervals || [];
    const sel = document.getElementById('ssc-interval');
    if (sel) {
      sel.innerHTML = _intervals.map(i => `<option value="${escHtml(i)}">${escHtml(i)}</option>`).join('');
    }
  }

  async function loadSchedules() {
    const data = await api('GET', '/api/v1/screenshot-scheduler/schedules');
    const container = document.getElementById('ssc-schedules-list');
    if (!container) return;
    const items = data.schedules || [];
    if (items.length === 0) {
      container.innerHTML = '<div class="ssc-empty">No schedules yet.</div>';
      return;
    }
    container.innerHTML = items.map(s => `
      <div class="ssc-item">
        <div class="ssc-item-info">
          <span class="ssc-item-id">${escHtml(s.schedule_id)}</span>
          <span class="ssc-item-meta">Interval: ${escHtml(s.interval)} | Captures: ${escHtml(String(s.capture_count))} | <span class="ssc-badge ${s.enabled ? 'ssc-badge-success' : 'ssc-badge-muted'}">${s.enabled ? 'enabled' : 'disabled'}</span></span>
          <span class="ssc-item-meta">URL hash: ${escHtml(s.url_hash.substring(0, 16))}...</span>
        </div>
        <div class="ssc-item-actions">
          <button class="ssc-btn ssc-btn-danger ssc-btn-sm" data-delete="${escHtml(s.schedule_id)}">Delete</button>
        </div>
      </div>
    `).join('');
    container.querySelectorAll('[data-delete]').forEach(btn => {
      btn.addEventListener('click', function () {
        deleteSchedule(this.getAttribute('data-delete'));
      });
    });
  }

  async function loadCaptures() {
    const data = await api('GET', '/api/v1/screenshot-scheduler/captures');
    const container = document.getElementById('ssc-captures-list');
    if (!container) return;
    const items = data.captures || [];
    if (items.length === 0) {
      container.innerHTML = '<div class="ssc-empty">No captures yet.</div>';
      return;
    }
    container.innerHTML = items.map(c => `
      <div class="ssc-item">
        <div class="ssc-item-info">
          <span class="ssc-item-id">${escHtml(c.capture_id)}</span>
          <span class="ssc-item-meta">Schedule: ${escHtml(c.schedule_id)}</span>
          <span class="ssc-item-meta">Image hash: ${escHtml(c.image_hash.substring(0, 16))}... | Captured: ${escHtml(c.captured_at)}</span>
        </div>
      </div>
    `).join('');
  }

  async function createSchedule() {
    const url = document.getElementById('ssc-url').value.trim();
    const interval = document.getElementById('ssc-interval').value;
    const msg = document.getElementById('ssc-msg');
    if (!url) { msg.textContent = 'URL is required.'; msg.className = 'ssc-error'; return; }
    const data = await api('POST', '/api/v1/screenshot-scheduler/schedules', { url, interval });
    if (data.schedule) {
      msg.textContent = 'Schedule created: ' + data.schedule.schedule_id;
      msg.className = 'ssc-success';
      document.getElementById('ssc-url').value = '';
      loadSchedules();
    } else {
      msg.textContent = data.error || 'Error creating schedule.';
      msg.className = 'ssc-error';
    }
  }

  async function deleteSchedule(scheduleId) {
    const data = await api('DELETE', '/api/v1/screenshot-scheduler/schedules/' + scheduleId);
    if (data.status === 'deleted') loadSchedules();
  }

  function init() {
    loadIntervals();
    loadSchedules();
    loadCaptures();
    const createBtn = document.getElementById('ssc-create-btn');
    if (createBtn) createBtn.addEventListener('click', createSchedule);
    const refreshCaptures = document.getElementById('ssc-refresh-captures');
    if (refreshCaptures) refreshCaptures.addEventListener('click', loadCaptures);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
