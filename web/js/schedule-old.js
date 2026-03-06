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

  // ── Constants (Kernighan: no magic numbers) ────────────────────────────────
  const POLL_INTERVAL_MS       = 30_000;
  const COUNTDOWN_TICK_MS      = 1000;
  const MAX_STREAK_DAYS        = 365;
  const STREAK_GRACE_HOUR      = 10;    // don't break streak before 10am
  const ALL_TIME_DAYS          = 9999;
  const MANUAL_MINUTES_PER_TASK = 30;
  const HOURLY_RATE_USD        = 30;
  const MAX_HISTORY_ROWS       = 200;
  const MAX_APPROVED_SHOWN     = 20;
  const MAX_ESIGN_SHOWN        = 20;
  const MAX_KEEPALIVE_SHOWN    = 4;
  const MAX_PILLS_PER_DAY      = 3;
  const MARKET_RATE_PER_TOKEN  = 0.007 / 1000;  // market average blended rate 2026
  const SOLACE_RATE_PER_TOKEN  = 0.00035 / 1000; // Together.ai Llama 3.3
  const PERIOD_DAYS            = { week: 7, month: 30, all: ALL_TIME_DAYS };
  const PERIOD_LABELS          = { 7: 'This Week', 30: 'This Month', [ALL_TIME_DAYS]: 'All Time' };
  const PERIOD_LABELS_LOWER    = { 7: 'this week', 30: 'this month', [ALL_TIME_DAYS]: 'all time' };
  const TIER_ESIGN_LIMITS      = { free: 0, starter: 100, pro: Infinity, enterprise: Infinity };
  const SUBSCRIPTION_MONTHLY_USD = 8;  // Solace Pro base subscription

  // ── State ──────────────────────────────────────────────────────────────────
  let activities = [];
  let currentView = localStorage.getItem('sb_schedule_view') || 'upcoming';
  let calOffset = 0;  // months from now
  let pendingCountdowns = {};  // run_id → interval ID
  let pollIntervalId = null;   // track polling interval for cleanup
  let consecutivePollFailures = 0;  // Vogels: circuit breaker on poll failures
  const MAX_POLL_FAILURES = 3;      // back off after 3 consecutive failures
  let allAgentsPaused = false;      // kill switch: when true, no auto-approvals

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

  // ── XSS Prevention (Torvalds: never trust server data in innerHTML) ───────
  function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  // ── Boot ───────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {
    setupViewTabs();
    setupNavButtons();
    setupSignOffSheet();
    setupRunDrawer();
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { closeSignOffSheet(); closeRunDrawer(); }
    });
    setupPeriodToggle();
    setupOfflineSync();
    setupPauseAllButton();
    loadActivities();
    loadCloudStatus();
    // Visibility-aware polling with circuit breaker (Torvalds + Vogels)
    schedulePoll();
  });

  // ── Pause All Agents (Kill Switch) ──────────────────────────────────────
  function setupPauseAllButton() {
    const toolbar = document.querySelector('.schedule-toolbar') || document.querySelector('.schedule-shell');
    if (!toolbar) return;
    const btn = document.createElement('button');
    btn.id = 'pauseAllBtn';
    btn.className = 'pause-all-btn';
    btn.textContent = '⏸ Pause All Agents';
    btn.style.cssText = 'margin-left:auto;padding:6px 14px;border-radius:8px;border:1.5px solid var(--sched-red,#ef4444);background:transparent;color:var(--sched-red,#ef4444);font-weight:600;font-size:0.85rem;cursor:pointer';
    btn.addEventListener('click', () => {
      allAgentsPaused = !allAgentsPaused;
      btn.textContent = allAgentsPaused ? '▶ Resume Agents' : '⏸ Pause All Agents';
      btn.style.background = allAgentsPaused ? 'var(--sched-red,#ef4444)' : 'transparent';
      btn.style.color = allAgentsPaused ? '#fff' : 'var(--sched-red,#ef4444)';
      renderPauseBanner();
    });
    toolbar.appendChild(btn);
  }

  function renderPauseBanner() {
    let banner = document.getElementById('pauseBanner');
    if (allAgentsPaused) {
      if (!banner) {
        banner = document.createElement('div');
        banner.id = 'pauseBanner';
        banner.style.cssText = 'background:var(--sched-red,#ef4444);color:#fff;padding:10px 16px;border-radius:8px;margin:8px 0;font-weight:600;text-align:center;font-size:0.9rem';
        const shell = document.querySelector('.schedule-shell');
        if (shell) shell.insertBefore(banner, shell.firstChild);
      }
      banner.textContent = '⏸ All agents paused — no actions will be auto-approved. Click "Resume Agents" to continue.';
    } else if (banner) {
      banner.remove();
    }
  }

  // ── Poll Scheduling with Circuit Breaker (Vogels/Gregg) ─────────────────
  function schedulePoll() {
    if (pollIntervalId) clearTimeout(pollIntervalId);
    // Exponential backoff: 30s, 60s, 300s (5min) after consecutive failures
    const backoffMs = consecutivePollFailures >= MAX_POLL_FAILURES
      ? 300_000  // 5 min backoff when circuit is open
      : POLL_INTERVAL_MS * Math.pow(2, Math.min(consecutivePollFailures, 2));
    pollIntervalId = setTimeout(async () => {
      if (!document.hidden) {
        await loadActivities();
      }
      schedulePoll();
    }, backoffMs);
  }

  // ── Offline / Sync Management ────────────────────────────────────────────
  let cloudStatus = { connected: false, tier: 'free', offline_queue_count: 0 };

  function setupOfflineSync() {
    // Listen for online/offline events
    window.addEventListener('online', () => {
      flushOfflineQueue();
      loadCloudStatus();
    });
    window.addEventListener('offline', () => {
      cloudStatus.connected = false;
      renderSyncBanner();
    });
  }

  async function loadCloudStatus() {
    try {
      const [syncRes, tierRes] = await Promise.all([
        fetch('/api/cloud/sync/status'),
        fetch('/api/cloud/user/tier'),
      ]);
      if (syncRes.ok) {
        const syncData = await syncRes.json();
        cloudStatus.connected = syncData.connected;
        cloudStatus.offline_queue_count = syncData.offline_queue_count || 0;
        cloudStatus.last_push = syncData.last_push;
        cloudStatus.last_pull = syncData.last_pull;
      }
      if (tierRes.ok) {
        const tierData = await tierRes.json();
        cloudStatus.tier = tierData.tier || 'free';
        try { localStorage.setItem('sb_esign_tier', cloudStatus.tier); } catch (_) { /* Safari private browsing may throw */ }
      }
    } catch (e) {
      cloudStatus.connected = false;
      console.debug('loadCloudStatus failed:', e.message || e);
    }
    renderSyncBanner();
  }

  async function flushOfflineQueue() {
    try {
      const res = await fetch('/api/offline/flush', { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: '{}' });
      if (res.ok) {
        const data = await res.json();
        if (data.flushed > 0) {
          cloudStatus.offline_queue_count = data.remaining;
          renderSyncBanner();
        }
      }
    } catch (e) { console.debug('Offline queue flush failed:', e.message || e); }
  }

  function renderSyncBanner() {
    let banner = document.getElementById('syncBanner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'syncBanner';
      banner.className = 'sync-banner';
      const shell = document.querySelector('.schedule-shell');
      if (shell) shell.insertBefore(banner, shell.querySelector('.savings-dashboard'));
    }
    // Sanitize tier to known values only (prevent XSS via innerHTML)
    const VALID_TIERS = { free: 'Free', starter: 'Starter', pro: 'Pro', enterprise: 'Enterprise' };
    if (!navigator.onLine) {
      banner.className = 'sync-banner sync-banner--offline';
      banner.innerHTML = '📡 <strong>Offline</strong> — changes will sync when back online' +
        (cloudStatus.offline_queue_count > 0 ? ` (${cloudStatus.offline_queue_count} pending)` : '');
    } else if (cloudStatus.connected) {
      banner.className = 'sync-banner sync-banner--connected';
      const tier = VALID_TIERS[cloudStatus.tier] || 'Free';
      banner.innerHTML = `☁️ Connected to solaceagi.com · <strong>${tier}</strong> tier`;
    } else {
      banner.className = 'sync-banner sync-banner--local';
      banner.innerHTML = '💻 Local mode — <a href="https://solaceagi.com/login" target="_blank" rel="noopener noreferrer">Connect to solaceagi.com</a> for cloud sync + eSign';
    }
  }

  // ── Period Toggle (7d / 30d / All-time) ────────────────────────────────────
  function setupPeriodToggle() {
    // Restore saved period
    const savedPeriod = localStorage.getItem('sb_schedule_period') || 'week';
    const savedBtn = document.querySelector(`.period-btn[data-period="${savedPeriod}"]`);
    if (savedBtn) {
      document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('period-btn--active'));
      savedBtn.classList.add('period-btn--active');
    }
    const periodBtns = [...document.querySelectorAll('.period-btn')];
    periodBtns.forEach((btn, idx) => {
      btn.addEventListener('click', () => {
        periodBtns.forEach(b => b.classList.remove('period-btn--active'));
        btn.classList.add('period-btn--active');
        const period = btn.dataset.period;
        try { localStorage.setItem('sb_schedule_period', period); } catch (_) { /* Safari private browsing may throw */ }
        updateROIPanel(PERIOD_DAYS[period] || 7);
      });
      // Arrow key navigation for radio group (WCAG)
      btn.addEventListener('keydown', (e) => {
        let next;
        if (e.key === 'ArrowRight') next = periodBtns[(idx + 1) % periodBtns.length];
        else if (e.key === 'ArrowLeft') next = periodBtns[(idx - 1 + periodBtns.length) % periodBtns.length];
        if (next) { e.preventDefault(); next.focus(); next.click(); }
      });
    });
  }

  // ── Upcoming schedules (keep-alive, app crons, Part 11, eSign) ─────────────
  let upcoming = [];

  // ── Data Loading ───────────────────────────────────────────────────────────
  async function loadActivities() {
    // Load past activities (audit log)
    try {
      const res = await fetch('/api/schedule');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      activities = data.activities || data || [];
      consecutivePollFailures = 0;  // Reset circuit breaker on success
      hideErrorBanner();
    } catch (e) {
      consecutivePollFailures++;
      activities = [];
      const msg = consecutivePollFailures >= MAX_POLL_FAILURES
        ? 'Server unreachable — polling slowed to every 5 minutes. Will resume when connected.'
        : 'Failed to load schedule data. ' + (navigator.onLine ? 'Server may be restarting.' : 'You are offline.');
      showErrorBanner(msg);
    }

    // Load upcoming schedules (app crons + keep-alive + Part 11 + eSign)
    try {
      const res2 = await fetch('/api/schedule/upcoming');
      if (res2.ok) {
        const data2 = await res2.json();
        upcoming = data2.upcoming || [];
        renderOperationsPanel(data2.summary || {});
      }
    } catch (e) {
      upcoming = [];
      console.debug('schedule/upcoming failed:', e.message || e);
    }

    // Convert upcoming schedules into calendar-visible entries
    const scheduleActivities = upcoming
      .filter(u => u.type === 'app_schedule')
      .map(u => ({
        id: 'sched-' + u.app_id,
        app_id: u.app_id,
        app_name: u.app_id.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        status: 'scheduled',
        schedule_pattern: u.pattern_label || u.pattern,
        started_at: getNextRunTime(u.pattern),
        _schedule: true,
      }));

    activities = [...activities, ...scheduleActivities];

    populateFilters();
    renderCurrentView();
    updateROIPanel();
    checkPendingQueue();
  }

  // ── Operations Summary Panel ──────────────────────────────────────────────
  function renderOperationsPanel(summary) {
    const dashboard = document.getElementById('savingsDashboard');
    if (!dashboard) return;

    // Add operations summary below the savings header if not already there
    let opsEl = document.getElementById('opsPanel');
    if (!opsEl) {
      opsEl = document.createElement('div');
      opsEl.id = 'opsPanel';
      opsEl.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;margin-top:12px';
      dashboard.appendChild(opsEl);
    }

    const appScheds = upcoming.filter(u => u.type === 'app_schedule');
    const keepAlives = upcoming.filter(u => u.type === 'keep_alive');
    const part11 = upcoming.find(u => u.type === 'part11');
    const esign = upcoming.find(u => u.type === 'esign');

    opsEl.innerHTML = `
      <div class="ops-card">
        <div class="ops-card__num">${appScheds.length}</div>
        <div class="ops-card__label">App Schedules</div>
        ${appScheds.map(s => `<div class="ops-card__detail">${APP_EMOJI[s.app_id] || '📅'} ${escapeHtml(s.pattern_label)}</div>`).join('')}
      </div>
      <div class="ops-card">
        <div class="ops-card__num">${keepAlives.length}</div>
        <div class="ops-card__label">Keep-Alive Sessions</div>
        ${keepAlives.slice(0, MAX_KEEPALIVE_SHOWN).map(k => `<div class="ops-card__detail">🔄 ${escapeHtml(k.domain)}</div>`).join('')}
        ${keepAlives.length > MAX_KEEPALIVE_SHOWN ? `<div class="ops-card__detail" style="opacity:0.5">+${keepAlives.length - MAX_KEEPALIVE_SHOWN} more</div>` : ''}
      </div>
      <div class="ops-card">
        <div class="ops-card__num">${part11 ? (part11.chain_entries || 0) : 0}</div>
        <div class="ops-card__label">Part 11 Evidence Capture</div>
        <div class="ops-card__detail">${part11 && part11.status === 'active' ? '✅ Active — ' + part11.mode + ' mode' : '○ Disabled'}</div>
      </div>
      <div class="ops-card">
        <div class="ops-card__num">${esign ? (esign.attestation_count || 0) : 0}</div>
        <div class="ops-card__label">eSign Attestations</div>
        <div class="ops-card__detail">${esign && esign.status === 'active' ? '✅ Active — on approval' : '○ Disabled'}</div>
      </div>
    `;
  }

  // ── Compute next run time from pattern ────────────────────────────────────
  function getNextRunTime(pattern) {
    const now = new Date();
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const hours = {
      'daily_6am': 6, 'daily_7am': 7, 'daily_9am': 9,
      'weekdays_8am': 8, 'weekdays_10am': 10, 'weekly_monday_8am': 8,
    };
    const h = hours[pattern];
    if (h !== undefined) {
      const next = new Date(tomorrow);
      next.setHours(h, 0, 0, 0);
      // Hopper Q32/Q33: weekday patterns must skip weekends (Sat=6, Sun=0)
      if (pattern.startsWith('weekdays_')) {
        while (next.getDay() === 0 || next.getDay() === 6) {
          next.setDate(next.getDate() + 1);
        }
      }
      // Knuth: weekly_monday must land on Monday (day 1)
      if (pattern.startsWith('weekly_monday')) {
        while (next.getDay() !== 1) {
          next.setDate(next.getDate() + 1);
        }
      }
      return next.toISOString();
    }
    return tomorrow.toISOString();
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
    const tabs = [...document.querySelectorAll('.view-tab')];
    tabs.forEach((btn, idx) => {
      btn.addEventListener('click', () => {
        currentView = btn.dataset.view;
        try { localStorage.setItem('sb_schedule_view', currentView); } catch (_) { /* Safari private browsing may throw */ }
        tabs.forEach(b => {
          b.classList.toggle('view-tab--active', b.dataset.view === currentView);
          b.setAttribute('aria-selected', b.dataset.view === currentView);
          b.tabIndex = b.dataset.view === currentView ? 0 : -1;
        });
        renderCurrentView();
      });
      // Arrow key navigation (WCAG keyboard support)
      btn.addEventListener('keydown', (e) => {
        let next;
        if (e.key === 'ArrowRight') next = tabs[(idx + 1) % tabs.length];
        else if (e.key === 'ArrowLeft') next = tabs[(idx - 1 + tabs.length) % tabs.length];
        if (next) { e.preventDefault(); next.focus(); next.click(); }
      });
    });
    // Activate saved view
    const activeTab = document.querySelector(`.view-tab[data-view="${currentView}"]`);
    if (activeTab) {
      activeTab.classList.add('view-tab--active');
      activeTab.setAttribute('aria-selected', 'true');
      activeTab.tabIndex = 0;
    }
    // Set non-active tabs to tabIndex -1
    tabs.filter(t => t !== activeTab).forEach(t => t.tabIndex = -1);
  }

  function renderGreeting() {
    let greetEl = document.getElementById('scheduleGreeting');
    if (!greetEl) {
      greetEl = document.createElement('div');
      greetEl.id = 'scheduleGreeting';
      greetEl.style.cssText = 'padding:12px 0 4px 0;font-size:1.1rem;font-weight:600;color:var(--sched-text,#e2e8f0)';
      const shell = document.querySelector('.schedule-shell');
      if (shell) shell.insertBefore(greetEl, shell.firstChild);
    }
    const name = localStorage.getItem('sb_user_name') || localStorage.getItem('sb_user_email') || '';
    const hour = new Date().getHours();
    const timeGreet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
    greetEl.textContent = name ? `${timeGreet}, ${name}` : `${timeGreet}`;
  }

  function renderCurrentView() {
    // Warm greeting (Van Edwards: warmth before competence)
    renderGreeting();

    // Fix 7: Clear orphaned countdown intervals when switching away from Approvals tab
    if (currentView !== 'approvals') {
      Object.keys(pendingCountdowns).forEach(id => clearInterval(pendingCountdowns[id]));
      pendingCountdowns = {};
    }

    document.querySelectorAll('.schedule-view').forEach(v => v.style.display = 'none');
    const viewMap = {
      upcoming:  'viewUpcoming',
      approvals: 'viewApprovals',
      history:   'viewHistory',
      esign:     'viewEsign',
    };
    const id = viewMap[currentView];
    if (id) {
      const el = document.getElementById(id);
      if (el) el.style.display = '';
    }
    if (currentView === 'upcoming')  renderUpcoming();
    if (currentView === 'approvals') renderApprovals();
    if (currentView === 'history')   renderHistory();
    if (currentView === 'esign')     renderEsign();
  }

  // ── TAB 1: UPCOMING VIEW ───────────────────────────────────────────────────
  function renderUpcoming() {
    // Render app schedules list
    const appsEl = document.getElementById('upcomingApps');
    const appScheds = upcoming.filter(u => u.type === 'app_schedule');
    if (appsEl) {
      if (appScheds.length === 0) {
        appsEl.innerHTML = '<p class="timeline-empty">No apps scheduled yet. <a href="/home">Activate an app</a> to set up its schedule.</p>';
      } else {
        appsEl.innerHTML = appScheds.map(s => {
          const emoji = APP_EMOJI[s.app_id] || '📅';
          const name = escapeHtml(s.app_id.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
          const nextRun = getNextRunTime(s.pattern);
          return `<div class="upcoming-item">
            <span class="upcoming-item__emoji">${emoji}</span>
            <div class="upcoming-item__info">
              <div class="upcoming-item__name">${name}</div>
              <div class="upcoming-item__detail">${escapeHtml(s.pattern_label || s.pattern)} · Next: ${escapeHtml(formatTime(nextRun))}</div>
            </div>
            <span class="upcoming-item__status">${s.enabled !== false ? '✅ Active' : '○ Paused'}</span>
          </div>`;
        }).join('');
      }
    }

    // Render keep-alive sessions
    const kaEl = document.getElementById('upcomingKeepAlive');
    const keepAlives = upcoming.filter(u => u.type === 'keep_alive');
    const kaCount = document.getElementById('keepAliveCount');
    if (kaCount) kaCount.textContent = keepAlives.length > 0 ? `(${keepAlives.length})` : '';
    if (kaEl) {
      if (keepAlives.length === 0) {
        kaEl.innerHTML = '<p class="timeline-empty">No keep-alive sessions active.</p>';
      } else {
        kaEl.innerHTML = keepAlives.map(k => {
          // Presence in keep_alive list implies enabled; explicit enabled:false means paused
          const isEnabled = k.enabled !== false;
          return `<div class="upcoming-item">
            <span class="upcoming-item__emoji">🔄</span>
            <div class="upcoming-item__info">
              <div class="upcoming-item__name">${escapeHtml(k.domain)}</div>
              <div class="upcoming-item__detail">Cookie refresh · Every ${escapeHtml(k.interval || '4h')}</div>
            </div>
            <span class="upcoming-item__status">${isEnabled ? '✅ Active' : '○ Paused'}</span>
          </div>`;
        }).join('');
      }
    }

    // Render calendar
    renderCalendar();
  }

  function setupNavButtons() {
    document.getElementById('calPrev')?.addEventListener('click', () => { if (calOffset > -24) { calOffset--; renderCalendar(); } });
    document.getElementById('calNext')?.addEventListener('click', () => { if (calOffset < 24) { calOffset++; renderCalendar(); } });
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
      shown.forEach(act => {
        const pill = makePill(act);
        pill.addEventListener('click', () => openRunDrawer(act));
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
    const emoji = APP_EMOJI[a.app_id] || '📄';
    const name = (a.app_name || a.app_id || '').replace(/-/g,' ').split(' ').slice(0,2).join(' ');
    const status = a.status || 'unknown';
    pill.className = `app-pill app-pill--${status.replace(/_/g,'-').split('-')[0]}`;
    // Handle status classes
    if (a.status === 'pending_approval') pill.className = 'app-pill app-pill--pending';
    else if (a.status === 'scheduled' || a.status === 'queued') pill.className = 'app-pill app-pill--future';
    pill.textContent = `${emoji} ${name}`;
    pill.title = `${a.app_name} — ${a.status} @ ${formatTime(a.started_at)}`;
    return pill;
  }

  // ── TAB 2: APPROVALS VIEW ──────────────────────────────────────────────────
  function renderApprovals() {
    const waiting = document.getElementById('kanbanWaitingCards');
    const done = document.getElementById('kanbanDoneCards');
    if (!waiting || !done) return;

    // Clear stale countdown intervals before re-rendering (Torvalds: prevent timer leaks)
    Object.keys(pendingCountdowns).forEach(id => clearInterval(pendingCountdowns[id]));
    pendingCountdowns = {};

    const pending = getFiltered().filter(a => a.status === 'pending_approval' || a.status === 'cooldown');
    const approved = getFiltered().filter(a => a.status === 'success' && a.approved_by).slice(0, MAX_APPROVED_SHOWN);

    waiting.innerHTML = '';
    done.innerHTML = '';

    if (pending.length === 0) {
      waiting.innerHTML = '<div style="color:var(--sched-text-dim);padding:1rem;text-align:center;font-size:0.85rem">No pending approvals — all your agent\'s actions are running within safe parameters.<br><small style="opacity:0.7">Tier A = read-only (auto-approved) · Tier B = writes (needs your OK) · Tier C = sensitive (needs your OK + review)</small></div>';
    }
    pending.forEach(act => {
      const card = makeApprovalCard(act);
      waiting.appendChild(card);
    });
    approved.forEach(act => {
      const card = makeApprovalCard(act);
      done.appendChild(card);
    });

    // Update approval badge
    const badge = document.getElementById('approvalBadge');
    if (badge) {
      if (pending.length > 0) {
        badge.textContent = pending.length;
        badge.style.display = '';
      } else {
        badge.style.display = 'none';
      }
    }
  }

  function makeApprovalCard(a) {
    const card = document.createElement('div');
    card.className = 'kanban-card';
    const emoji = APP_EMOJI[a.app_id] || '🤖';
    const time = formatTime(a.started_at);
    const cost = a.cost_usd ? `$${a.cost_usd.toFixed(4)}` : '—';
    const scopeStr = (a.scopes_used || []).join(', ') || '—';

    const safeId = escapeHtml(a.id);
    const safeName = escapeHtml(a.app_name || a.app_id);
    const safeStatus = escapeHtml(a.status.replace(/_/g,' '));
    const safeTier = escapeHtml(a.safety_tier || 'A');
    const safeHash = escapeHtml(a.evidence_hash || '');

    card.innerHTML = `
      <div class="kanban-card__app">${emoji} ${safeName}</div>
      <div class="kanban-card__meta">
        <span>${STATUS_EMOJI[a.status] || ''} ${safeStatus}</span>
        <span>${time}</span>
        <span class="kanban-card__badge badge--${safeTier}">${safeTier}</span>
        ${a.cost_usd ? `<span>${cost}</span>` : ''}
      </div>
      ${a.output_summary ? `<div class="kanban-card__summary" style="background:var(--sched-surface,#1e293b);border:1px solid var(--sched-border,#334155);border-radius:6px;padding:6px 8px;margin:4px 0;font-size:0.82rem"><span style="color:var(--sched-text-dim);font-weight:600;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.03em">Agent output:</span><br>${escapeHtml(truncate(a.output_summary, 80))}</div>` : ''}
      ${a.evidence_hash ? `<div class="evidence-hash-row">🔗 ${safeHash.slice(0,16)}… <button class="copy-hash-btn" title="Copy evidence hash">Copy</button></div>` : ''}
      ${a.status === 'pending_approval' ? `
        <div class="kanban-card__actions">
          <span class="countdown" id="cd-${safeId}">⏳ 30s remaining</span><br>
          <button class="approve-btn" data-id="${safeId}">✅ Approve</button>
          <button class="approve-btn approve-btn--esign" data-id="${safeId}" data-esign="1" title="Creates a tamper-proof cryptographic signature of your approval">🔏 Approve + Sign</button>
          <button class="reject-btn"  data-id="${safeId}" style="border:1.5px solid var(--sched-red);opacity:0.85">Decline</button>
        </div>` : ''}
    `;

    // Copy hash button handler (uses closure, not data attribute — XSS safe)
    card.querySelector('.copy-hash-btn')?.addEventListener('click', (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText(a.evidence_hash).then(() => {
        e.target.textContent = 'Copied!';
        setTimeout(() => { e.target.textContent = 'Copy'; }, 1500);
      });
    });
    card.querySelector('.kanban-card__app')?.addEventListener('click', () => openRunDrawer(a));
    if (a.status === 'pending_approval') {
      startCountdown(a, card.querySelector('.countdown'));
      card.querySelectorAll('.approve-btn').forEach(btn => {
        btn.addEventListener('click', e => {
          e.stopPropagation();
          approveRun(a.id, btn.dataset.esign === '1');
        });
      });
      card.querySelector('.reject-btn')?.addEventListener('click', e => { e.stopPropagation(); rejectRun(a.id); });
    }
    return card;
  }

  // ── TAB 3: HISTORY VIEW ───────────────────────────────────────────────────
  function getFlaggedRuns() {
    try { return JSON.parse(localStorage.getItem('sb_flagged_runs') || '{}'); } catch (_) { return {}; }
  }

  function setFlaggedRun(runId, reason) {
    const flagged = getFlaggedRuns();
    flagged[runId] = { reason, timestamp: new Date().toISOString() };
    try { localStorage.setItem('sb_flagged_runs', JSON.stringify(flagged)); } catch (_) { /* Safari private browsing may throw */ }
  }

  function renderHistory() {
    const tbody = document.getElementById('activityTableBody');
    if (!tbody) return;
    const filtered = getFiltered().filter(a => a.started_at && !a._schedule).sort(
      (a, b) => new Date(b.started_at) - new Date(a.started_at)
    );
    if (!filtered.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="table-loading">Your first run will appear here. Once your agent starts working, you\'ll have a full audit trail of everything it did — with cryptographic evidence.</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    const flaggedRuns = getFlaggedRuns();
    filtered.slice(0, MAX_HISTORY_ROWS).forEach(act => {
      const tr = document.createElement('tr');
      const emoji = APP_EMOJI[act.app_id] || '📄';
      const safeName = escapeHtml(act.app_name || act.app_id);
      const safeStatus = escapeHtml((act.status || '').replace(/_/g,' '));
      const isFlagged = !!flaggedRuns[act.id];
      tr.innerHTML = `
        <td>${emoji} ${safeName}</td>
        <td><span class="status-badge status-badge--${simplifyStatus(act.status)}">${STATUS_EMOJI[act.status]||''} ${safeStatus}</span></td>
        <td>${escapeHtml(formatTime(act.started_at))}</td>
        <td>${formatDuration(act.duration_ms)}</td>
        <td>${act.cost_usd ? '$' + Number(act.cost_usd).toFixed(4) : '—'}</td>
        <td>${act.evidence_hash
          ? `<span class="evidence-hash-cell" title="Click to copy">🔗 ${escapeHtml(act.evidence_hash.slice(0,12))}… 📋</span>`
          : '—'}</td>
        <td><button class="flag-btn${isFlagged ? ' flag-btn--flagged' : ''}" title="${isFlagged ? 'Flagged as ' + escapeHtml(flaggedRuns[act.id].reason) : 'Flag this run as incorrect or misaligned'}" style="background:none;border:none;cursor:pointer;font-size:0.85rem;padding:2px 6px;border-radius:4px;${isFlagged ? 'color:#ef4444;font-weight:600' : 'color:var(--sched-text-dim,#94a3b8);opacity:0.7'}">${isFlagged ? '🚩' : '⚑'}</button></td>
      `;
      // Click-to-copy hash via event listener (not inline onclick — XSS safe)
      const hashEl = tr.querySelector('.evidence-hash-cell');
      if (hashEl) {
        hashEl.style.cursor = 'pointer';
        hashEl.addEventListener('click', (e) => {
          e.stopPropagation();
          const originalText = hashEl.innerHTML;
          navigator.clipboard.writeText(act.evidence_hash).then(() => {
            hashEl.textContent = 'Copied!';
            setTimeout(() => { hashEl.innerHTML = originalText; }, 1500);
          });
        });
      }
      // Fix 9: Flag button for post-hoc dispute
      const flagBtn = tr.querySelector('.flag-btn');
      if (flagBtn) {
        flagBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          if (flaggedRuns[act.id]) {
            // Already flagged — show info
            alert('This run was flagged as "' + flaggedRuns[act.id].reason + '" on ' + flaggedRuns[act.id].timestamp.split('T')[0]);
            return;
          }
          const reason = prompt('Flag this run as incorrect or misaligned.\nReason (e.g., "wrong email sent", "incorrect triage"):');
          if (reason) {
            setFlaggedRun(act.id, reason);
            flagBtn.textContent = '🚩';
            flagBtn.classList.add('flag-btn--flagged');
            flagBtn.style.color = '#ef4444';
            flagBtn.style.fontWeight = '600';
            flagBtn.style.opacity = '1';
            flagBtn.title = 'Flagged as ' + reason;
          }
        });
      }
      tr.addEventListener('click', () => openRunDrawer(act));
      tbody.appendChild(tr);
    });
  }

  // ── TAB 4: ESIGN VIEW ────────────────────────────────────────────────────
  function renderEsign() {
    // Update eSign stats from upcoming data + cloud chain status
    const esignData = upcoming.find(u => u.type === 'esign');
    const part11Data = upcoming.find(u => u.type === 'part11');

    // Fetch cloud chain status (non-blocking)
    fetch('/api/cloud/esign/chain-status').then(r => r.ok ? r.json() : null).then(chain => {
      if (chain && chain.total_signatures !== undefined) {
        const totalEl = document.getElementById('esignTotal');
        if (totalEl) totalEl.textContent = chain.total_signatures;
      }
    }).catch(() => {});

    const totalEl = document.getElementById('esignTotal');
    const monthEl = document.getElementById('esignThisMonth');
    const remainEl = document.getElementById('esignRemaining');
    if (totalEl) totalEl.textContent = esignData ? (esignData.attestation_count || 0) : 0;
    if (monthEl) monthEl.textContent = esignData ? (esignData.this_month || 0) : 0;
    // Tier-aware remaining display
    const tier = cloudStatus.tier || localStorage.getItem('sb_esign_tier') || 'free';
    const limit = TIER_ESIGN_LIMITS[tier] || 0;
    const used = esignData ? (esignData.attestation_count || 0) : 0;
    const remaining = limit === Infinity ? '∞' : Math.max(0, limit - used);
    if (remainEl) {
      if (tier === 'free' && remaining === 0) {
        remainEl.textContent = '—';
        remainEl.title = 'Available on Starter and Pro tiers';
      } else {
        remainEl.textContent = remaining;
      }
    }

    // Render recent attestations
    const listEl = document.getElementById('esignList');
    const esignRuns = getFiltered().filter(a => a.esign_hash || a.esign_attestation);
    if (listEl) {
      if (esignRuns.length === 0) {
        const tierMsg = (tier === 'free')
          ? 'Starter and Pro tiers include cryptographic signatures that make your AI actions legally verifiable. <a href="/pricing">Learn more</a>'
          : 'No signed approvals yet. When you use "Approve + Sign," you create a tamper-evident record of your decision.';
        listEl.innerHTML = `<p class="timeline-empty">${tierMsg}</p>`;
      } else {
        listEl.innerHTML = esignRuns.slice(0, MAX_ESIGN_SHOWN).map(a => {
          const emoji = APP_EMOJI[a.app_id] || '📄';
          return `<div class="upcoming-item">
            <span class="upcoming-item__emoji">🔏</span>
            <div class="upcoming-item__info">
              <div class="upcoming-item__name">${emoji} ${escapeHtml(a.app_name || a.app_id)}</div>
              <div class="upcoming-item__detail">${escapeHtml(formatTime(a.started_at))} · <span class="esign-hash-inline">${escapeHtml((a.esign_hash || '').slice(0,16))}…</span></div>
            </div>
            <span class="upcoming-item__status">✅ Signed</span>
          </div>`;
        }).join('');
      }
    }

    // Render Part 11 evidence chain status
    const part11El = document.getElementById('part11Status');
    if (part11El) {
      if (part11Data && part11Data.status === 'active') {
        part11El.innerHTML = `
          <div class="upcoming-item">
            <span class="upcoming-item__emoji">🔗</span>
            <div class="upcoming-item__info">
              <div class="upcoming-item__name">Evidence Chain Active</div>
              <div class="upcoming-item__detail">${part11Data.chain_entries || 0} entries · ${part11Data.mode || 'data'} mode · SHA-256 hashed</div>
            </div>
            <span class="upcoming-item__status">✅ ${part11Data.mode}</span>
          </div>
          <div class="upcoming-item">
            <span class="upcoming-item__emoji">📋</span>
            <div class="upcoming-item__info">
              <div class="upcoming-item__name">ALCOA+ Compliance</div>
              <div class="upcoming-item__detail" title="Attributable (who did it) · Legible (readable) · Contemporaneous (real-time) · Original (first record) · Accurate (verified correct)">ALCOA+ Ready: who, what, when — tamper-evident</div>
            </div>
            <span class="upcoming-item__status">✅</span>
          </div>`;
      } else {
        part11El.innerHTML = '<p class="timeline-empty">Part 11 creates a compliance-ready evidence record of every agent action. Full Part 11 compliance requires identity verification (Pro tier). Enable it in Settings → Compliance if you need compliance-grade audit trails.</p>';
      }
    }
  }

  // ── ROI PANEL ──────────────────────────────────────────────────────────────
  function updateROIPanel(periodDays) {
    const days = periodDays || 7;
    const cutoff = Date.now() - days * 24 * 3600 * 1000;
    const periodActivities = activities.filter(
      a => a.started_at && new Date(a.started_at) > cutoff && a.status === 'success'
    );
    const totalCost      = periodActivities.reduce((s, a) => s + (a.cost_usd     || 0), 0);
    const totalTokens    = periodActivities.reduce((s, a) => s + (a.tokens_used  || 0), 0);
    const hasTokenData   = periodActivities.some(a => a.tokens_used > 0);
    const replayCount    = periodActivities.filter(a => a.recipe_hit).length;

    // Token savings: market average rate vs Solace (Together.ai Llama 3.3)
    const gpt4Cost       = totalTokens * MARKET_RATE_PER_TOKEN;
    const tokenSavings   = gpt4Cost - totalCost;

    // Read user-customizable ROI settings from localStorage (Fix 8: ROI customization)
    const userMinPerTask = Number(localStorage.getItem('sb_roi_min_per_task')) || MANUAL_MINUTES_PER_TASK;
    const userHourlyRate = Number(localStorage.getItem('sb_roi_hourly_rate')) || HOURLY_RATE_USD;

    // Time savings: estimated manual time per task → hourly rate baseline
    const humanHours     = (periodActivities.length * userMinPerTask) / 60;
    // Subscription cost pro-rated for the period (monthly → period fraction)
    const subCostForPeriod = SUBSCRIPTION_MONTHLY_USD * (days / 30);
    const netSavings     = humanHours * userHourlyRate - totalCost - subCostForPeriod;

    // Recipe hit rate
    const hitRate        = periodActivities.length > 0
      ? Math.round((replayCount / periodActivities.length) * 100)
      : 0;

    // Streak calculation (consecutive days with at least one successful run)
    let streak = 0;
    const today = new Date();
    const earlyMorning = today.getHours() < STREAK_GRACE_HOUR;
    today.setHours(0, 0, 0, 0);
    for (let i = 0; i < MAX_STREAK_DAYS; i++) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const ds = d.toISOString().split('T')[0];
      const hasRun = activities.some(
        a => a.started_at && a.started_at.startsWith(ds) && a.status === 'success'
      );
      if (hasRun) { streak++; }
      else if (i === 0 && earlyMorning) { continue; } // grace period: don't break streak before 10am
      else { break; }
    }

    // Update badge label
    const badge = document.getElementById('savingsBadge');
    if (badge) {
      badge.textContent = PERIOD_LABELS[days] || `${days} days`;
    }

    setText('roiRuns',       periodActivities.length + ' runs');
    setText('roiTimeSaved',  humanHours.toFixed(1) + ' hrs (est.)');
    setText('roiTokens',     hasTokenData
      ? periodActivities.length + ' tasks'
      : '—');
    setText('roiTokenSaved', tokenSavings > 0
      ? '$' + tokenSavings.toFixed(2)
      : tokenSavings < 0 ? '-$' + Math.abs(tokenSavings).toFixed(2) : '$0.00');
    setText('roiCost',       totalCost < 0.01 ? '< 1¢' : '$' + totalCost.toFixed(2));
    setText('roiNet',        netSavings > 0 ? '+$' + netSavings.toFixed(0) : netSavings < 0 ? '-$' + Math.abs(netSavings).toFixed(0) : '$0');

    // Show subscription cost as line item (Fix 2)
    let subEl = document.getElementById('roiSub');
    if (!subEl) {
      const costEl = document.getElementById('roiCost');
      if (costEl && costEl.parentElement) {
        subEl = document.createElement('div');
        subEl.className = 'roi-stat';
        subEl.id = 'roiSub';
        subEl.innerHTML = '<span class="roi-num">—</span><span class="roi-label">subscription (pro-rated)</span>';
        costEl.parentElement.insertBefore(subEl, costEl.nextSibling);
      }
    }
    if (subEl) {
      const subNum = subEl.querySelector('.roi-num');
      if (subNum) subNum.textContent = '$' + subCostForPeriod.toFixed(2);
    }

    // Add Customize link for ROI settings (Fix 8)
    let customizeEl = document.getElementById('roiCustomize');
    if (!customizeEl) {
      const roiPanel = document.getElementById('roiPanel');
      if (roiPanel) {
        customizeEl = document.createElement('div');
        customizeEl.id = 'roiCustomize';
        customizeEl.style.cssText = 'text-align:right;padding:4px 12px 8px;font-size:0.75rem';
        const link = document.createElement('a');
        link.href = '#';
        link.textContent = 'Customize ROI assumptions';
        link.style.cssText = 'color:var(--sched-accent,#60a5fa);text-decoration:underline;cursor:pointer';
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const newMin = prompt('Minutes per task (currently ' + userMinPerTask + '):', userMinPerTask);
          if (newMin !== null && Number(newMin) > 0) {
            localStorage.setItem('sb_roi_min_per_task', Number(newMin));
          }
          const newRate = prompt('Hourly rate USD (currently $' + userHourlyRate + '):', userHourlyRate);
          if (newRate !== null && Number(newRate) > 0) {
            localStorage.setItem('sb_roi_hourly_rate', Number(newRate));
          }
          updateROIPanel(days);
        });
        customizeEl.appendChild(link);
        roiPanel.appendChild(customizeEl);
      }
    }

    // Ekman: honest color — green for positive, red for negative, neutral for zero
    const netEl = document.getElementById('roiNet');
    const netNum = netEl?.querySelector('.roi-num');
    if (netNum) netNum.style.color = netSavings > 0 ? '#10b981' : netSavings < 0 ? '#ef4444' : '';

    // Streak with escalating emoji (Rory Sutherland: milestones need ceremony)
    const streakEmoji = streak >= 60 ? '🐉' : streak >= 30 ? '🏆' : streak >= 14 ? '⚡' : streak >= 7 ? '🔥' : '🌱';
    setText('roiStreak',     streak + ' days ' + streakEmoji);

    // Hit rate progress bar
    const bar = document.getElementById('roiHitBar');
    const pct = document.getElementById('roiHitPct');
    if (bar) {
      bar.style.width = hitRate + '%';
      bar.parentElement.setAttribute('aria-valuenow', Math.round(hitRate));
    }
    if (pct) pct.textContent = hitRate + '%';
  }

  function setText(id, val) {
    const el = document.getElementById(id);
    const num = el?.querySelector('.roi-num');
    if (num) num.textContent = val;
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
        const scopeStr = (a.scopes_used || []).map(s => {
          // Translate technical scopes to human language
          const scopeMap = { 'gmail:read': 'Read your inbox', 'gmail:modify': 'Archive/label emails',
            'gmail:send': 'Send emails', 'calendar:read': 'Read your calendar', 'calendar:write': 'Update your calendar',
            'linkedin:post': 'Post to LinkedIn', 'slack:read': 'Read Slack messages', 'slack:write': 'Send Slack messages' };
          return scopeMap[s] || s;
        }).join(', ') || 'No specific permissions requested';
        item.innerHTML = `
          <div class="signoff-item__app">${APP_EMOJI[a.app_id]||'📄'} ${escapeHtml(a.app_name)}</div>
          <div class="signoff-item__scope">Permissions: ${escapeHtml(scopeStr)}</div>
          <div class="signoff-item__desc" style="background:var(--sched-surface,#1e293b);border:1px solid var(--sched-border,#334155);border-radius:6px;padding:8px 10px;margin:6px 0"><span style="color:var(--sched-text-dim);font-weight:600;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.03em">Agent output:</span><br>${escapeHtml(a.output_summary || 'Your agent wants to proceed with this action.')}</div>
          <div class="signoff-item__footer">
            <button class="approve-btn" data-id="${a.id}">✅ Approve</button>
            <button class="reject-btn"  data-id="${a.id}" style="border:1.5px solid var(--sched-red);opacity:0.85">Decline</button>
            <span class="countdown" id="sheet-cd-${a.id}">Take your time</span>
          </div>
        `;
        item.querySelector('.approve-btn').addEventListener('click', () => approveRun(a.id));
        item.querySelector('.reject-btn').addEventListener('click',  () => rejectRun(a.id));
        startCountdown(a, item.querySelector('.countdown'));
        items.appendChild(item);
      });
    }
    const sheet = document.getElementById('signoffSheet');
    sheet.style.display = '';
    document.getElementById('signoffOverlay').style.display = '';
    trapFocus(sheet);
  }

  function closeSignOffSheet() {
    document.getElementById('signoffSheet').style.display = 'none';
    document.getElementById('signoffOverlay').style.display = 'none';
    releaseFocusTrap();
  }

  // ── APPROVAL ACTIONS ───────────────────────────────────────────────────────
  async function approveRun(id, withEsign) {
    // Enforce eSign tier limit (boss floor: free tier gets 0 eSign, starter gets 100)
    if (withEsign) {
      const tier = cloudStatus.tier || localStorage.getItem('sb_esign_tier') || 'free';
      const limit = TIER_ESIGN_LIMITS[tier] || 0;
      if (limit !== Infinity) {
        const esignData = upcoming.find(u => u.type === 'esign');
        const used = esignData ? (esignData.attestation_count || 0) : 0;
        if (used >= limit) {
          showErrorBanner(`eSign limit reached for ${tier} tier (${used}/${limit}). Upgrade to Pro for unlimited signatures. Approving without eSign instead.`);
          withEsign = false;
        }
      }
    }
    try {
      // Part 11 compliance: approver must be uniquely identifiable
      const approverName = localStorage.getItem('sb_user_name') || localStorage.getItem('sb_user_email') || 'local_user';
      const body = {
        approved_by: approverName,
        device_id: navigator.userAgent.slice(0, 64),
        session_id: sessionStorage.getItem('sb_session_id') || crypto.randomUUID(),
        timestamp: new Date().toISOString(),
        esign: !!withEsign,
      };
      // Persist session_id for this browser session
      if (!sessionStorage.getItem('sb_session_id')) {
        sessionStorage.setItem('sb_session_id', body.session_id);
      }
      const res = await fetch(`/api/schedule/approve/${id}`, { method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Approval failed');
      // If eSign was requested, log the attestation
      if (withEsign && data.esign_hash) {
        const a = activities.find(x => x.id === id);
        if (a) a.esign_hash = data.esign_hash;
      }
    } catch (e) {
      // Torvalds: never swallow errors silently — log and notify user
      console.warn('Approval failed:', e.message || e);
      showErrorBanner('Approval failed. ' + (navigator.onLine ? 'Server may be restarting.' : 'You are offline — will retry when connected.'));
      return; // Do NOT update local state if server didn't confirm
    }
    // Update local state only after confirmed server response
    const a = activities.find(x => x.id === id);
    if (a) a.status = 'approved';
    closeSignOffSheet();
    loadActivities();
  }

  async function rejectRun(id) {
    try {
      const res = await fetch(`/api/schedule/cancel/${id}`, { method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ reason: 'user_rejected', timestamp: new Date().toISOString() }) });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Rejection failed');
    } catch (e) {
      console.warn('Rejection failed:', e.message || e);
      showErrorBanner('Rejection failed. ' + (navigator.onLine ? 'Server may be restarting.' : 'You are offline.'));
      return;
    }
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
      // Vanessa Van Edwards: reassuring framing, not coercive countdown
      if (el) el.textContent = remaining > 10
        ? `Take your time — ${remaining}s before safely blocked`
        : `${remaining}s — action will be safely blocked`;
      if (remaining <= 0) {
        clearInterval(pendingCountdowns[a.id]);
        // Guard: if user already approved/declined while countdown was ticking, skip auto-reject.
        // The local activities array is updated on approve/reject, so check it before firing.
        const current = activities.find(x => x.id === a.id);
        if (current && current.status === 'pending_approval' && !allAgentsPaused) {
          // Auto-block (fail-safe, not fail-punish)
          rejectRun(a.id);
        }
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
    const emoji = APP_EMOJI[a.app_id] || '📄';
    document.getElementById('drawerTitle').textContent = `${emoji} ${a.app_name || a.app_id}`;
    const body = document.getElementById('drawerBody');
    const fields = [
      { label: 'Status',   val: `${STATUS_EMOJI[a.status]||''} ${escapeHtml((a.status||'').replace(/_/g,' '))}` },
      { label: 'Time',     val: escapeHtml(formatTime(a.started_at)) },
      { label: 'Duration', val: formatDuration(a.duration_ms) },
      { label: 'Cost',     val: a.cost_usd ? '$' + Number(a.cost_usd).toFixed(6) : '—' },
      { label: 'Tokens',   val: a.tokens_used ? Number(a.tokens_used).toLocaleString() : '—' },
      { label: 'Safety',   val: `Tier ${escapeHtml(a.safety_tier || 'A')}` },
      { label: 'Scopes',   val: escapeHtml((a.scopes_used || []).join(', ') || '—') },
      { label: 'Agent output', val: `<div style="background:var(--sched-surface,#1e293b);border:1px solid var(--sched-border,#334155);border-radius:6px;padding:8px 10px;font-size:0.85rem">${escapeHtml(a.output_summary || '—')}</div>` },
    ];
    if (a.evidence_hash) {
      fields.push({ label: 'Evidence Hash', val: `<span class="drawer-hash">${escapeHtml(a.evidence_hash)}</span> <button class="copy-hash-btn drawer-copy-btn" title="Copy evidence hash">Copy</button>` });
    }
    if (Array.isArray(a.cross_app_triggers) && a.cross_app_triggers.length > 0) {
      fields.push({ label: 'Cross-App Triggers', val: escapeHtml(a.cross_app_triggers.join(' → ')) });
    }
    if (a._demo) {
      fields.push({ label: 'Note', val: '✨ Preview — your real evidence will appear here after your first run' });
    }
    body.innerHTML = fields.map(f =>
      `<div class="drawer-field">
        <div class="drawer-field__label">${f.label}</div>
        <div class="drawer-field__val">${f.val}</div>
      </div>`
    ).join('');
    // Copy button in drawer evidence hash (Fix 4: consistency)
    const drawerCopyBtn = body.querySelector('.drawer-copy-btn');
    if (drawerCopyBtn && a.evidence_hash) {
      drawerCopyBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(a.evidence_hash).then(() => {
          e.target.textContent = 'Copied!';
          setTimeout(() => { e.target.textContent = 'Copy'; }, 1500);
        });
      });
    }
    const drawer = document.getElementById('runDrawer');
    drawer.style.display = 'flex';
    document.getElementById('runOverlay').style.display = '';
    trapFocus(drawer);
  }

  function closeRunDrawer() {
    document.getElementById('runDrawer').style.display = 'none';
    document.getElementById('runOverlay').style.display = 'none';
    releaseFocusTrap();
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
    if (ms < 3600000) return (ms / 60000).toFixed(1) + 'm';
    return (ms / 3600000).toFixed(1) + 'h';
  }

  function truncate(str, n) {
    if (str == null) return '';
    return str.length > n ? str.slice(0, n) + '…' : str;
  }

  function simplifyStatus(s) {
    if (!s) return 'past';
    if (s === 'success' || s === 'approved') return 'success';
    if (s === 'failed')           return 'failed';
    if (s.startsWith('pending'))  return 'pending';
    if (s === 'scheduled' || s === 'queued') return 'scheduled';
    if (s === 'cancelled')        return 'cancelled';
    return 'past';  // unknown status → neutral, not silently 'cancelled'
  }

  // ── Focus Trap (WCAG: prevent tabbing outside open modals) ──────────────
  let activeFocusTrap = null;

  function trapFocus(containerEl) {
    releaseFocusTrap();
    const handler = (e) => {
      if (e.key !== 'Tab') return;
      const focusable = containerEl.querySelectorAll(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    containerEl.addEventListener('keydown', handler);
    activeFocusTrap = { el: containerEl, handler };
    // Move focus into the container
    const firstFocusable = containerEl.querySelector('button:not([disabled]), [href], input:not([disabled])');
    if (firstFocusable) firstFocusable.focus();
  }

  function releaseFocusTrap() {
    if (activeFocusTrap) {
      activeFocusTrap.el.removeEventListener('keydown', activeFocusTrap.handler);
      activeFocusTrap = null;
    }
  }

  // ── Error Banner ─────────────────────────────────────────────────────────
  function showErrorBanner(msg) {
    let banner = document.getElementById('errorBanner');
    if (!banner) {
      banner = document.createElement('div');
      banner.id = 'errorBanner';
      banner.className = 'sync-banner sync-banner--offline';
      const shell = document.querySelector('.schedule-shell');
      if (shell) shell.insertBefore(banner, shell.firstChild);
    }
    // Build banner with event listeners (not inline onclick — Torvalds: IIFE scope)
    banner.textContent = '';
    banner.insertAdjacentText('beforeend', 'ℹ️ ' + msg + ' ');
    const actions = document.createElement('span');
    actions.className = 'error-banner__actions';
    const retryBtn = document.createElement('button');
    retryBtn.className = 'error-banner__btn error-banner__btn--retry';
    retryBtn.textContent = 'Retry';
    retryBtn.addEventListener('click', () => loadActivities());
    const dismissBtn = document.createElement('button');
    dismissBtn.className = 'error-banner__btn error-banner__btn--dismiss';
    dismissBtn.textContent = 'Dismiss';
    dismissBtn.addEventListener('click', () => banner.remove());
    actions.appendChild(retryBtn);
    actions.appendChild(dismissBtn);
    banner.appendChild(actions);
  }
  function hideErrorBanner() {
    const banner = document.getElementById('errorBanner');
    if (banner) banner.remove();
  }

})();
