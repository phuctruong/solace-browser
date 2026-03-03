/**
 * schedule.js — Agent Activity Calendar & Sign-Off Queue
 * Designed by: Jony Ive (simplicity) · Vanessa Van Edwards (trust) ·
 *              Russell Brunson (engagement) · Rory Sutherland (ROI) ·
 *              Seth Godin (permission)
 *
 * Data source: GET /api/schedule (reads ~/.solace/audit/*.jsonl)
 * Sign-off: POST /api/schedule/approve/:id, POST /api/schedule/cancel/:id
 */

(function () {
  'use strict';

  // ── State ──────────────────────────────────────────────────────────────────
  let activities = [];
  let currentView = localStorage.getItem('sb_schedule_view') || 'calendar';
  let calOffset = 0;  // months from now
  let pendingCountdowns = {};  // run_id → interval ID

  const STATUS_EMOJI = {
    success:          '✅',
    failed:           '❌',
    pending_approval: '⏳',
    cooldown:         '🕐',
    cancelled:        '🚫',
    scheduled:        '📅',
    queued:           '📥',
    running:          '⚡',
  };

  const APP_EMOJI = {
    'gmail-inbox-triage':  '📧',
    'linkedin-poster':     '🔗',
    'morning-brief':       '🌅',
    'slack-triage':        '💬',
    'github-issue-triage': '🐙',
    'twitter-poster':      '🐦',
    'weekly-digest':       '📊',
    'focus-timer':         '⏱️',
    'calendar-brief':      '📅',
    'whatsapp-responder':  '📱',
    'youtube-script-writer': '🎬',
  };

  // ── Boot ───────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    setupViewTabs();
    setupNavButtons();
    setupSignOffSheet();
    setupRunDrawer();
    loadActivities();
    setInterval(loadActivities, 30_000);  // refresh every 30s
  });

  // ── Data Loading ───────────────────────────────────────────────────────────
  async function loadActivities() {
    try {
      const res = await fetch('/api/schedule');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      activities = data.activities || data || [];
    } catch (e) {
      // Show empty state gracefully
      activities = generateDemoActivities();
    }
    populateFilters();
    renderCurrentView();
    updateROIPanel();
    checkPendingQueue();
  }

  // Demo data for fresh install (Rory: show VALUE even before first run)
  function generateDemoActivities() {
    const now = new Date();
    const demo = [];
    const apps = [
      { id: 'gmail-inbox-triage',  name: 'Gmail Inbox Triage',  safety: 'B' },
      { id: 'morning-brief',       name: 'Morning Brief',        safety: 'A' },
      { id: 'linkedin-poster',     name: 'LinkedIn Poster',      safety: 'C' },
      { id: 'weekly-digest',       name: 'Weekly Digest',        safety: 'A' },
      { id: 'focus-timer',         name: 'Focus Timer',          safety: 'A' },
    ];
    const statuses = ['success', 'success', 'success', 'failed', 'success'];
    for (let i = 0; i < 12; i++) {
      const app = apps[i % apps.length];
      const d = new Date(now);
      d.setDate(d.getDate() - Math.floor(i * 1.5));
      d.setHours(8 + (i % 4));
      demo.push({
        id: `demo-${i}`,
        app_id:   app.id,
        app_name: app.name,
        status:   statuses[i % statuses.length],
        safety_tier: app.safety,
        started_at: d.toISOString(),
        duration_ms: 15000 + i * 3000,
        cost_usd: 0.0007 + i * 0.0002,
        tokens_used: 1200 + i * 300,
        output_summary: `Processed ${10 + i * 5} items successfully.`,
        scopes_used: ['read.inbox'],
        cross_app_triggers: i % 3 === 0 ? ['linkedin-poster'] : [],
        evidence_hash: 'sha256:' + Math.random().toString(16).slice(2),
        _demo: true,
      });
    }
    // Add a pending approval
    demo.push({
      id: 'demo-pending',
      app_id: 'linkedin-poster',
      app_name: 'LinkedIn Poster',
      status: 'pending_approval',
      safety_tier: 'C',
      started_at: new Date().toISOString(),
      duration_ms: 0,
      cost_usd: 0,
      output_summary: 'Draft post ready: "The future of AI delegation is here — OAuth3 makes it safe."',
      scopes_used: ['linkedin.posts.write'],
      approval_deadline: new Date(Date.now() + 15000).toISOString(),
      _demo: true,
    });
    // Add a scheduled future item
    const future = new Date();
    future.setDate(future.getDate() + 1);
    future.setHours(8, 0, 0, 0);
    demo.push({
      id: 'demo-future',
      app_id: 'morning-brief',
      app_name: 'Morning Brief',
      status: 'scheduled',
      safety_tier: 'A',
      started_at: future.toISOString(),
      schedule_pattern: 'daily@08:00',
      _demo: true,
    });
    return demo;
  }

  // ── Filters ────────────────────────────────────────────────────────────────
  function populateFilters() {
    const sel = document.getElementById('filterApp');
    if (!sel) return;
    const existing = new Set([...sel.options].map(o => o.value));
    const seen = new Set();
    activities.forEach(a => {
      if (!seen.has(a.app_id)) {
        seen.add(a.app_id);
        if (!existing.has(a.app_id)) {
          const opt = document.createElement('option');
          opt.value = a.app_id;
          opt.textContent = a.app_name || a.app_id;
          sel.appendChild(opt);
        }
      }
    });
    sel.onchange = renderCurrentView;
    document.getElementById('filterStatus').onchange = renderCurrentView;
  }

  function getFiltered() {
    const appFilter    = document.getElementById('filterApp')?.value || '';
    const statusFilter = document.getElementById('filterStatus')?.value || '';
    return activities.filter(a => {
      if (appFilter    && a.app_id !== appFilter)    return false;
      if (statusFilter && a.status !== statusFilter) return false;
      return true;
    });
  }

  // ── View Switching ─────────────────────────────────────────────────────────
  function setupViewTabs() {
    document.querySelectorAll('.view-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        currentView = btn.dataset.view;
        localStorage.setItem('sb_schedule_view', currentView);
        document.querySelectorAll('.view-tab').forEach(b => {
          b.classList.toggle('view-tab--active', b.dataset.view === currentView);
          b.setAttribute('aria-selected', b.dataset.view === currentView);
        });
        renderCurrentView();
      });
    });
    // Activate saved view
    const activeTab = document.querySelector(`.view-tab[data-view="${currentView}"]`);
    if (activeTab) {
      activeTab.classList.add('view-tab--active');
      activeTab.setAttribute('aria-selected', 'true');
    }
  }

  function renderCurrentView() {
    document.querySelectorAll('.schedule-view').forEach(v => v.style.display = 'none');
    const viewMap = {
      calendar: 'viewCalendar',
      kanban:   'viewKanban',
      timeline: 'viewTimeline',
      list:     'viewList',
    };
    const id = viewMap[currentView];
    if (id) document.getElementById(id).style.display = '';
    if (currentView === 'calendar') renderCalendar();
    if (currentView === 'kanban')   renderKanban();
    if (currentView === 'timeline') renderTimeline();
    if (currentView === 'list')     renderList();
  }

  // ── CALENDAR VIEW ──────────────────────────────────────────────────────────
  function setupNavButtons() {
    document.getElementById('calPrev')?.addEventListener('click', () => { calOffset--; renderCalendar(); });
    document.getElementById('calNext')?.addEventListener('click', () => { calOffset++; renderCalendar(); });
  }

  function renderCalendar() {
    const now = new Date();
    const d = new Date(now.getFullYear(), now.getMonth() + calOffset, 1);
    const year = d.getFullYear();
    const month = d.getMonth();

    const label = d.toLocaleString('default', { month: 'long', year: 'numeric' });
    document.getElementById('calMonthLabel').textContent = label;

    // Build day map
    const dayMap = {};
    getFiltered().forEach(a => {
      const ds = a.started_at ? a.started_at.split('T')[0] : null;
      if (!ds) return;
      if (!dayMap[ds]) dayMap[ds] = [];
      dayMap[ds].push(a);
    });

    // Grid: header row was static HTML, build day cells
    const grid = document.getElementById('calGrid');
    // Remove existing day cells (keep header row = first 7 children)
    const headers = [...grid.children].slice(0, 7);
    grid.innerHTML = '';
    headers.forEach(h => grid.appendChild(h));

    // First day of month (Mon=0…Sun=6)
    let firstDay = (new Date(year, month, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;

    // Empty cells before 1st
    for (let i = 0; i < firstDay; i++) {
      const cell = document.createElement('div');
      cell.className = 'cal-cell cal-cell--empty';
      grid.appendChild(cell);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const ds = `${year}-${String(month + 1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
      const cell = document.createElement('div');
      cell.className = 'cal-cell' + (ds === todayStr ? ' cal-cell--today' : '');

      const dateNum = document.createElement('div');
      dateNum.className = 'cal-date';
      dateNum.textContent = day;
      cell.appendChild(dateNum);

      const dayActivities = dayMap[ds] || [];
      const shown = dayActivities.slice(0, 3);
      shown.forEach(a => {
        const pill = makePill(a);
        pill.addEventListener('click', () => openRunDrawer(a));
        cell.appendChild(pill);
      });
      if (dayActivities.length > 3) {
        const overflow = document.createElement('div');
        overflow.className = 'cal-overflow';
        overflow.textContent = `+${dayActivities.length - 3} more`;
        cell.appendChild(overflow);
      }
      grid.appendChild(cell);
    }
  }

  function makePill(a) {
    const pill = document.createElement('div');
    const emoji = APP_EMOJI[a.app_id] || '🤖';
    const name = (a.app_name || a.app_id || '').replace(/-/g,' ').split(' ').slice(0,2).join(' ');
    pill.className = `app-pill app-pill--${a.status.replace(/_/g,'-').split('-')[0]}`;
    // Handle status classes
    if (a.status === 'pending_approval') pill.className = 'app-pill app-pill--pending';
    else if (a.status === 'scheduled' || a.status === 'queued') pill.className = 'app-pill app-pill--future';
    pill.textContent = `${emoji} ${name}`;
    pill.title = `${a.app_name} — ${a.status} @ ${formatTime(a.started_at)}`;
    return pill;
  }

  // ── KANBAN VIEW ────────────────────────────────────────────────────────────
  function renderKanban() {
    const cols = {
      queued:           ['queued', 'running'],
      running:          ['running'],
      pending_approval: ['pending_approval', 'cooldown'],
      done:             ['success', 'failed', 'cancelled'],
    };
    const filtered = getFiltered();
    const containers = {
      queued:  document.getElementById('kanbanQueuedCards'),
      running: document.getElementById('kanbanRunningCards'),
      waiting: document.getElementById('kanbanWaitingCards'),
      done:    document.getElementById('kanbanDoneCards'),
    };
    Object.values(containers).forEach(c => { if (c) c.innerHTML = ''; });

    filtered.slice().reverse().forEach(a => {
      const card = makeKanbanCard(a);
      let target = containers.done;
      if (a.status === 'queued')           target = containers.queued;
      else if (a.status === 'running')     target = containers.running;
      else if (a.status === 'pending_approval' || a.status === 'cooldown')
                                           target = containers.waiting;
      if (target) target.appendChild(card);
    });
  }

  function makeKanbanCard(a) {
    const card = document.createElement('div');
    card.className = 'kanban-card';
    const emoji = APP_EMOJI[a.app_id] || '🤖';
    const time  = formatTime(a.started_at);
    const cost  = a.cost_usd ? `$${a.cost_usd.toFixed(4)}` : '—';

    card.innerHTML = `
      <div class="kanban-card__app">${emoji} ${a.app_name || a.app_id}</div>
      <div class="kanban-card__meta">
        <span>${STATUS_EMOJI[a.status] || ''} ${a.status.replace(/_/g,' ')}</span>
        <span>${time}</span>
        <span class="kanban-card__badge badge--${a.safety_tier || 'A'}">${a.safety_tier || 'A'}</span>
        ${a.cost_usd ? `<span>${cost}</span>` : ''}
      </div>
      ${a.output_summary ? `<div style="font-size:0.75rem;color:#94a3b8;margin-top:6px">${truncate(a.output_summary, 80)}</div>` : ''}
      ${a.status === 'pending_approval' ? `
        <div style="margin-top:8px">
          <span class="countdown" id="cd-${a.id}">⏳ 15s remaining</span><br>
          <button class="approve-btn" data-id="${a.id}">✅ Approve</button>
          <button class="reject-btn"  data-id="${a.id}">✕ Reject</button>
        </div>` : ''}
    `;

    card.querySelector('.kanban-card__app').addEventListener('click', () => openRunDrawer(a));
    if (a.status === 'pending_approval') {
      startCountdown(a, card.querySelector('.countdown'));
      card.querySelector('.approve-btn').addEventListener('click', e => { e.stopPropagation(); approveRun(a.id); });
      card.querySelector('.reject-btn').addEventListener('click',  e => { e.stopPropagation(); rejectRun(a.id);  });
    }
    return card;
  }

  // ── TIMELINE VIEW ──────────────────────────────────────────────────────────
  function renderTimeline() {
    const container = document.getElementById('timelineContainer');
    const filtered = getFiltered().filter(a => a.started_at).sort(
      (a, b) => new Date(b.started_at) - new Date(a.started_at)
    );
    if (!filtered.length) {
      container.innerHTML = '<p class="timeline-empty">No activity yet — run your first app to see its timeline here.</p>';
      return;
    }
    container.innerHTML = '';
    filtered.forEach(a => {
      const node = document.createElement('div');
      node.className = `timeline-node timeline-node--${simplifyStatus(a.status)}`;
      const emoji = APP_EMOJI[a.app_id] || '🤖';
      const chains = (a.cross_app_triggers || []).length > 0
        ? `<div class="timeline-node__chain">→ triggers: ${a.cross_app_triggers.join(', ')}</div>`
        : '';
      node.innerHTML = `
        <div class="timeline-node__app">${emoji} ${a.app_name || a.app_id}</div>
        <div class="timeline-node__time">${STATUS_EMOJI[a.status] || ''} ${a.status.replace(/_/g,' ')} · ${formatTime(a.started_at)} · ${formatDuration(a.duration_ms)}</div>
        ${chains}
        ${a.output_summary ? `<div style="font-size:0.75rem;color:#94a3b8;margin-top:4px">${truncate(a.output_summary, 100)}</div>` : ''}
      `;
      node.addEventListener('click', () => openRunDrawer(a));
      container.appendChild(node);
    });
  }

  // ── LIST VIEW ──────────────────────────────────────────────────────────────
  function renderList() {
    const tbody = document.getElementById('activityTableBody');
    const filtered = getFiltered().filter(a => a.started_at).sort(
      (a, b) => new Date(b.started_at) - new Date(a.started_at)
    );
    if (!filtered.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="table-loading">No activity yet.</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    filtered.forEach(a => {
      const tr = document.createElement('tr');
      const emoji = APP_EMOJI[a.app_id] || '🤖';
      tr.innerHTML = `
        <td>${emoji} ${a.app_name || a.app_id}</td>
        <td><span class="status-badge status-badge--${simplifyStatus(a.status)}">${STATUS_EMOJI[a.status]||''} ${a.status.replace(/_/g,' ')}</span></td>
        <td>${formatTime(a.started_at)}</td>
        <td>${formatDuration(a.duration_ms)}</td>
        <td>${a.cost_usd ? '$' + a.cost_usd.toFixed(4) : '—'}</td>
        <td>
          ${a.status === 'pending_approval'
            ? `<button class="approve-btn" data-id="${a.id}">Approve</button>
               <button class="reject-btn"  data-id="${a.id}">Reject</button>`
            : '<button class="reject-btn" style="opacity:.6">Detail</button>'}
        </td>
      `;
      tr.addEventListener('click', () => openRunDrawer(a));
      tr.querySelectorAll('.approve-btn').forEach(b => b.addEventListener('click', e => { e.stopPropagation(); approveRun(a.id); }));
      tr.querySelectorAll('.reject-btn').forEach(b => {
        if (a.status === 'pending_approval') b.addEventListener('click', e => { e.stopPropagation(); rejectRun(a.id); });
      });
      tbody.appendChild(tr);
    });
  }

  // ── ROI PANEL ──────────────────────────────────────────────────────────────
  function updateROIPanel() {
    const weekAgo = Date.now() - 7 * 24 * 3600 * 1000;
    const weekActivities = activities.filter(a => a.started_at && new Date(a.started_at) > weekAgo && a.status === 'success');
    const totalCost = weekActivities.reduce((s, a) => s + (a.cost_usd || 0), 0);
    const totalDuration = weekActivities.reduce((s, a) => s + (a.duration_ms || 15000), 0);
    // Each run would take ~30min manually
    const humanHours = (weekActivities.length * 30) / 60;
    const savings = humanHours * 30 - totalCost;

    // Streak calculation (consecutive days with at least one run)
    let streak = 0;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    for (let i = 0; i < 30; i++) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const ds = d.toISOString().split('T')[0];
      const hasRun = activities.some(a => a.started_at && a.started_at.startsWith(ds) && a.status === 'success');
      if (hasRun) streak++;
      else if (i > 0) break;
    }

    setText('roiRuns',      weekActivities.length + ' runs');
    setText('roiTimeSaved', humanHours.toFixed(1) + ' hrs');
    setText('roiCost',      '$' + totalCost.toFixed(2));
    setText('roiNet',       savings > 0 ? '+$' + savings.toFixed(0) : '$0');
    setText('roiStreak',    streak + ' days 🔥');
  }

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.querySelector('.roi-num').textContent = val;
  }

  // ── SIGN-OFF QUEUE ─────────────────────────────────────────────────────────
  function checkPendingQueue() {
    const pending = activities.filter(a => a.status === 'pending_approval');
    const alert = document.getElementById('signoffAlert');
    if (!alert) return;
    if (pending.length > 0) {
      alert.style.display = 'flex';
      document.getElementById('signoffCount').textContent = pending.length;
      // YinYang badge
      const badge = document.getElementById('yyPendingBadge');
      if (badge) badge.style.display = '';
    } else {
      alert.style.display = 'none';
      const badge = document.getElementById('yyPendingBadge');
      if (badge) badge.style.display = 'none';
    }
  }

  function setupSignOffSheet() {
    document.getElementById('signoffOpenBtn')?.addEventListener('click', openSignOffSheet);
    document.getElementById('signoffClose')?.addEventListener('click',   closeSignOffSheet);
    document.getElementById('signoffOverlay')?.addEventListener('click', closeSignOffSheet);
  }

  function openSignOffSheet() {
    const items = document.getElementById('signoffItems');
    const pending = activities.filter(a => a.status === 'pending_approval');
    items.innerHTML = '';
    if (!pending.length) {
      items.innerHTML = '<p style="color:#94a3b8;text-align:center;padding:1rem">No pending approvals</p>';
    } else {
      pending.forEach(a => {
        const item = document.createElement('div');
        item.className = 'signoff-item';
        const scopeStr = (a.scopes_used || []).join(', ') || 'unknown scope';
        item.innerHTML = `
          <div class="signoff-item__app">${APP_EMOJI[a.app_id]||'🤖'} ${a.app_name}</div>
          <div class="signoff-item__scope">Scope: ${scopeStr}</div>
          <div class="signoff-item__desc">${a.output_summary || 'Ready to execute.'}</div>
          <div class="signoff-item__footer">
            <button class="approve-btn" data-id="${a.id}">✅ Approve</button>
            <button class="reject-btn"  data-id="${a.id}">✕ Reject</button>
            <span class="countdown" id="sheet-cd-${a.id}">⏳ 15s</span>
          </div>
        `;
        item.querySelector('.approve-btn').addEventListener('click', () => approveRun(a.id));
        item.querySelector('.reject-btn').addEventListener('click',  () => rejectRun(a.id));
        startCountdown(a, item.querySelector('.countdown'));
        items.appendChild(item);
      });
    }
    document.getElementById('signoffSheet').style.display = '';
    document.getElementById('signoffOverlay').style.display = '';
  }

  function closeSignOffSheet() {
    document.getElementById('signoffSheet').style.display = 'none';
    document.getElementById('signoffOverlay').style.display = 'none';
  }

  // ── APPROVAL ACTIONS ───────────────────────────────────────────────────────
  async function approveRun(id) {
    try {
      const res = await fetch(`/api/schedule/approve/${id}`, { method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ approved_by: 'user', timestamp: new Date().toISOString() }) });
      const data = await res.json();
    } catch (e) { /* demo mode: just update local state */ }
    // Update local state
    const a = activities.find(x => x.id === id);
    if (a) a.status = 'success';
    closeSignOffSheet();
    loadActivities();
  }

  async function rejectRun(id) {
    try {
      await fetch(`/api/schedule/cancel/${id}`, { method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ reason: 'user_rejected', timestamp: new Date().toISOString() }) });
    } catch (e) {}
    const a = activities.find(x => x.id === id);
    if (a) a.status = 'cancelled';
    closeSignOffSheet();
    loadActivities();
  }

  // ── COUNTDOWN ─────────────────────────────────────────────────────────────
  function startCountdown(a, el) {
    if (!el || !a.approval_deadline) return;
    const deadline = new Date(a.approval_deadline).getTime();
    const tick = () => {
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      if (el) el.textContent = `⏳ ${remaining}s remaining`;
      if (remaining <= 0) {
        clearInterval(pendingCountdowns[a.id]);
        // Auto-reject
        rejectRun(a.id);
      }
    };
    clearInterval(pendingCountdowns[a.id]);
    pendingCountdowns[a.id] = setInterval(tick, 1000);
    tick();
  }

  // ── RUN DETAIL DRAWER ──────────────────────────────────────────────────────
  function setupRunDrawer() {
    document.getElementById('drawerClose')?.addEventListener('click',  closeRunDrawer);
    document.getElementById('runOverlay')?.addEventListener('click', closeRunDrawer);
  }

  function openRunDrawer(a) {
    const emoji = APP_EMOJI[a.app_id] || '🤖';
    document.getElementById('drawerTitle').textContent = `${emoji} ${a.app_name || a.app_id}`;
    const body = document.getElementById('drawerBody');
    const fields = [
      { label: 'Status',   val: `${STATUS_EMOJI[a.status]||''} ${a.status.replace(/_/g,' ')}` },
      { label: 'Time',     val: formatTime(a.started_at) },
      { label: 'Duration', val: formatDuration(a.duration_ms) },
      { label: 'Cost',     val: a.cost_usd ? '$' + a.cost_usd.toFixed(6) : '—' },
      { label: 'Tokens',   val: a.tokens_used ? a.tokens_used.toLocaleString() : '—' },
      { label: 'Safety',   val: `Tier ${a.safety_tier || 'A'}` },
      { label: 'Scopes',   val: (a.scopes_used || []).join(', ') || '—' },
      { label: 'Output',   val: a.output_summary || '—' },
    ];
    if (a.evidence_hash) {
      fields.push({ label: 'Evidence Hash', val: `<span class="drawer-hash">${a.evidence_hash}</span>` });
    }
    if ((a.cross_app_triggers || []).length) {
      fields.push({ label: 'Triggers', val: a.cross_app_triggers.join(' → ') });
    }
    if (a._demo) {
      fields.push({ label: 'Note', val: '⚠️ Demo data — run an app to see real evidence' });
    }
    body.innerHTML = fields.map(f =>
      `<div class="drawer-field">
        <div class="drawer-field__label">${f.label}</div>
        <div class="drawer-field__val">${f.val}</div>
      </div>`
    ).join('');
    document.getElementById('runDrawer').style.display = 'flex';
    document.getElementById('runOverlay').style.display = '';
  }

  function closeRunDrawer() {
    document.getElementById('runDrawer').style.display = 'none';
    document.getElementById('runOverlay').style.display = 'none';
  }

  // ── Helpers ────────────────────────────────────────────────────────────────
  function formatTime(iso) {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) {
        return 'Today ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' '
           + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  }

  function formatDuration(ms) {
    if (!ms) return '—';
    if (ms < 60000) return (ms / 1000).toFixed(0) + 's';
    return (ms / 60000).toFixed(1) + 'm';
  }

  function truncate(str, n) {
    return str && str.length > n ? str.slice(0, n) + '…' : str;
  }

  function simplifyStatus(s) {
    if (!s) return 'past';
    if (s === 'success')          return 'success';
    if (s === 'failed')           return 'failed';
    if (s.startsWith('pending'))  return 'pending';
    if (s === 'scheduled' || s === 'queued') return 'scheduled';
    return 'cancelled';
  }

})();
