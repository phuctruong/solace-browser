/**
 * schedule-core.js — Shared state, constants, utilities, and boot logic
 * Part of the Agent Activity Calendar & Sign-Off Queue
 *
 * Designed by: Jony Ive (simplicity) · Vanessa Van Edwards (trust) ·
 *              Russell Brunson (engagement) · Rory Sutherland (ROI) ·
 *              Seth Godin (permission)
 *
 * Data source: GET /api/schedule (reads ~/.solace/audit/*.jsonl)
 * Sign-off: POST /api/schedule/approve/:id, POST /api/schedule/cancel/:id
 */

/**
 * @typedef {Object} Activity
 * @property {string}  id               - Unique run identifier
 * @property {string}  app_id           - Machine-readable app slug (e.g. 'gmail-inbox-triage')
 * @property {string}  [app_name]       - Human-readable app name
 * @property {string}  status           - One of: success, failed, pending_approval, cooldown, cancelled, scheduled, queued, running, approved
 * @property {string}  [started_at]     - ISO 8601 timestamp of run start
 * @property {number}  [duration_ms]    - Run duration in milliseconds
 * @property {number}  [cost_usd]       - LLM cost in USD
 * @property {number}  [tokens_used]    - Total tokens consumed
 * @property {string}  [evidence_hash]  - SHA-256 evidence chain hash
 * @property {string}  [esign_hash]     - eSign attestation hash (if signed)
 * @property {boolean} [esign_attestation] - Whether eSign attestation exists
 * @property {string}  [output_summary] - Agent's output summary text
 * @property {string}  [safety_tier]    - Safety tier: A (read), B (write), C (sensitive)
 * @property {string[]} [scopes_used]   - OAuth3 scopes exercised during run
 * @property {string}  [approved_by]    - Who approved this run
 * @property {string}  [approval_deadline] - ISO 8601 deadline for auto-block
 * @property {boolean} [recipe_hit]     - Whether a cached recipe was replayed
 * @property {string}  [schedule_pattern] - Cron/schedule pattern label
 * @property {string[]} [cross_app_triggers] - Cross-app trigger chain
 * @property {boolean} [_schedule]      - Internal flag: generated from upcoming schedule
 * @property {boolean} [_demo]          - Internal flag: preview/demo entry
 */

(function () {
  'use strict';

  // ── Constants (Kernighan: no magic numbers) ────────────────────────────────
  const constants = {
    POLL_INTERVAL_MS:        30000,
    COUNTDOWN_TICK_MS:       1000,
    MAX_STREAK_DAYS:         365,
    STREAK_GRACE_HOUR:       10,     // don't break streak before 10am
    ALL_TIME_DAYS:           9999,
    MANUAL_MINUTES_PER_TASK: parseInt(localStorage.getItem('sb_manual_minutes') || '30', 10) || 30,
    HOURLY_RATE_USD:         parseInt(localStorage.getItem('sb_hourly_rate') || '30', 10) || 30,
    MAX_HISTORY_ROWS:        200,
    MAX_APPROVED_SHOWN:      20,
    MAX_ESIGN_SHOWN:         20,
    MAX_KEEPALIVE_SHOWN:     4,
    MAX_PILLS_PER_DAY:       3,
    MARKET_RATE_PER_TOKEN:   0.007 / 1000,   // market average blended rate 2026
    SOLACE_RATE_PER_TOKEN:   0.00035 / 1000,  // Together.ai Llama 3.3
    MAX_POLL_FAILURES:       3,
  };

  constants.PERIOD_DAYS        = { week: 7, month: 30, all: constants.ALL_TIME_DAYS };
  constants.PERIOD_LABELS      = { 7: 'This Week', 30: 'This Month', [constants.ALL_TIME_DAYS]: 'All Time' };
  constants.PERIOD_LABELS_LOWER = { 7: 'this week', 30: 'this month', [constants.ALL_TIME_DAYS]: 'all time' };
  constants.TIER_ESIGN_LIMITS  = { free: 0, starter: 100, pro: Infinity, enterprise: Infinity };

  // ── Emoji Maps ─────────────────────────────────────────────────────────────
  constants.STATUS_EMOJI = {
    success:          '\u2705',
    failed:           '\u274C',
    pending_approval: '\u23F3',
    cooldown:         '\uD83D\uDD50',
    cancelled:        '\uD83D\uDEAB',
    scheduled:        '\uD83D\uDCC5',
    queued:           '\uD83D\uDCE5',
    running:          '\u26A1',
  };

  constants.APP_EMOJI = {
    'gmail-inbox-triage':    '\uD83D\uDCE7',
    'linkedin-poster':       '\uD83D\uDD17',
    'morning-brief':         '\uD83C\uDF05',
    'slack-triage':          '\uD83D\uDCAC',
    'github-issue-triage':   '\uD83D\uDC19',
    'twitter-poster':        '\uD83D\uDC26',
    'weekly-digest':         '\uD83D\uDCCA',
    'focus-timer':           '\u23F1\uFE0F',
    'calendar-brief':        '\uD83D\uDCC5',
    'whatsapp-responder':    '\uD83D\uDCF1',
    'youtube-script-writer': '\uD83C\uDFAC',
  };

  // ── State ──────────────────────────────────────────────────────────────────
  const state = {
    activities:               [],
    currentView:              localStorage.getItem('sb_schedule_view') || 'upcoming',
    calOffset:                0,      // months from now
    pendingCountdowns:        {},     // run_id -> interval ID
    pollIntervalId:           null,   // track polling interval for cleanup
    consecutivePollFailures:  0,      // Vogels: circuit breaker on poll failures
    allAgentsPaused:          false,  // kill switch: when true, no auto-approvals
    upcoming:                 [],
    cloudStatus:              { connected: false, tier: 'free', offline_queue_count: 0 },
    csrfToken:                '',
    activeFocusTrap:          null,
  };

  // ── XSS Prevention (Torvalds: never trust server data in innerHTML) ───────
  function escapeHtml(str) {
    if (str == null) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  function formatTime(iso) {
    if (!iso) return '\u2014';
    try {
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) {
        return 'Today ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' '
           + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (_) { return iso; }
  }

  function formatDuration(ms) {
    if (!ms) return '\u2014';
    if (ms < 60000) return (ms / 1000).toFixed(0) + 's';
    if (ms < 3600000) return (ms / 60000).toFixed(1) + 'm';
    return (ms / 3600000).toFixed(1) + 'h';
  }

  function truncate(str, n) {
    if (str == null) return '';
    return str.length > n ? str.slice(0, n) + '\u2026' : str;
  }

  function simplifyStatus(s) {
    if (!s) return 'past';
    if (s === 'success' || s === 'approved') return 'success';
    if (s === 'failed')           return 'failed';
    if (s.startsWith('pending'))  return 'pending';
    if (s === 'scheduled' || s === 'queued') return 'scheduled';
    if (s === 'cancelled')        return 'cancelled';
    return 'past';  // unknown status -> neutral, not silently 'cancelled'
  }

  function makePill(a) {
    const pill = document.createElement('div');
    const emoji = constants.APP_EMOJI[a.app_id] || '\uD83D\uDCC4';
    const name = (a.app_name || a.app_id || '').replace(/-/g,' ').split(' ').slice(0,2).join(' ');
    const status = a.status || 'unknown';
    pill.className = 'app-pill app-pill--' + status.replace(/_/g,'-').split('-')[0];
    // Handle status classes
    if (a.status === 'pending_approval') pill.className = 'app-pill app-pill--pending';
    else if (a.status === 'scheduled' || a.status === 'queued') pill.className = 'app-pill app-pill--future';
    pill.textContent = emoji + ' ' + name;
    pill.title = (a.app_name || '') + ' \u2014 ' + a.status + ' @ ' + formatTime(a.started_at);
    return pill;
  }

  function setText(id, val) {
    const el = document.getElementById(id);
    const num = el ? el.querySelector('.roi-num') : null;
    if (num) num.textContent = val;
  }

  // ── Utilities object ──────────────────────────────────────────────────────
  const utils = {
    escapeHtml:      escapeHtml,
    formatTime:      formatTime,
    formatDuration:  formatDuration,
    truncate:        truncate,
    simplifyStatus:  simplifyStatus,
    makePill:        makePill,
    setText:         setText,
  };

  // ── Shared function registry (populated by modules) ───────────────────────
  const fn = {};

  // ── Namespace ─────────────────────────────────────────────────────────────
  window.SolaceSchedule = {
    state:     state,
    utils:     utils,
    constants: constants,
    fn:        fn,
  };

  // ── Focus Trap (WCAG: prevent tabbing outside open modals) ──────────────
  function trapFocus(containerEl) {
    releaseFocusTrap();
    const handler = function (e) {
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
    state.activeFocusTrap = { el: containerEl, handler: handler };
    // Move focus into the container
    const firstFocusable = containerEl.querySelector('button:not([disabled]), [href], input:not([disabled])');
    if (firstFocusable) firstFocusable.focus();
  }

  function releaseFocusTrap() {
    if (state.activeFocusTrap) {
      state.activeFocusTrap.el.removeEventListener('keydown', state.activeFocusTrap.handler);
      state.activeFocusTrap = null;
    }
  }

  fn.trapFocus = trapFocus;
  fn.releaseFocusTrap = releaseFocusTrap;

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
    banner.insertAdjacentText('beforeend', '\u2139\uFE0F ' + msg + ' ');
    const actions = document.createElement('span');
    actions.className = 'error-banner__actions';
    const retryBtn = document.createElement('button');
    retryBtn.className = 'error-banner__btn error-banner__btn--retry';
    retryBtn.textContent = 'Retry';
    retryBtn.addEventListener('click', function () { loadActivities(); });
    const dismissBtn = document.createElement('button');
    dismissBtn.className = 'error-banner__btn error-banner__btn--dismiss';
    dismissBtn.textContent = 'Dismiss';
    dismissBtn.addEventListener('click', function () { banner.remove(); });
    actions.appendChild(retryBtn);
    actions.appendChild(dismissBtn);
    banner.appendChild(actions);
  }

  function hideErrorBanner() {
    const banner = document.getElementById('errorBanner');
    if (banner) banner.remove();
  }

  fn.showErrorBanner = showErrorBanner;
  fn.hideErrorBanner = hideErrorBanner;

  // ── Filters ────────────────────────────────────────────────────────────────
  function populateFilters() {
    const sel = document.getElementById('filterApp');
    if (!sel) return;
    const existing = new Set([].slice.call(sel.options).map(function (o) { return o.value; }));
    const seen = new Set();
    state.activities.forEach(function (a) {
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
    const statusSel = document.getElementById('filterStatus');
    if (statusSel) statusSel.onchange = renderCurrentView;
  }

  function getFiltered() {
    const appFilter    = (document.getElementById('filterApp') || {}).value || '';
    const statusFilter = (document.getElementById('filterStatus') || {}).value || '';
    return state.activities.filter(function (a) {
      if (appFilter    && a.app_id !== appFilter)    return false;
      if (statusFilter && a.status !== statusFilter) return false;
      return true;
    });
  }

  fn.getFiltered = getFiltered;

  // ── View Switching ─────────────────────────────────────────────────────────
  function setupViewTabs() {
    var tabs = [].slice.call(document.querySelectorAll('.view-tab'));
    tabs.forEach(function (btn, idx) {
      btn.addEventListener('click', function () {
        state.currentView = btn.dataset.view;
        try { localStorage.setItem('sb_schedule_view', state.currentView); } catch (_) { /* Safari private browsing may throw */ }
        tabs.forEach(function (b) {
          b.classList.toggle('view-tab--active', b.dataset.view === state.currentView);
          b.setAttribute('aria-selected', b.dataset.view === state.currentView);
          b.tabIndex = b.dataset.view === state.currentView ? 0 : -1;
        });
        renderCurrentView();
      });
      // Arrow key navigation (WCAG keyboard support)
      btn.addEventListener('keydown', function (e) {
        var next;
        if (e.key === 'ArrowRight') next = tabs[(idx + 1) % tabs.length];
        else if (e.key === 'ArrowLeft') next = tabs[(idx - 1 + tabs.length) % tabs.length];
        if (next) { e.preventDefault(); next.focus(); next.click(); }
      });
    });
    // Activate saved view
    var activeTab = document.querySelector('.view-tab[data-view="' + state.currentView + '"]');
    if (activeTab) {
      activeTab.classList.add('view-tab--active');
      activeTab.setAttribute('aria-selected', 'true');
      activeTab.tabIndex = 0;
    }
    // Set non-active tabs to tabIndex -1
    tabs.filter(function (t) { return t !== activeTab; }).forEach(function (t) { t.tabIndex = -1; });
  }

  function renderGreeting() {
    var greetEl = document.getElementById('scheduleGreeting');
    if (!greetEl) {
      greetEl = document.createElement('div');
      greetEl.id = 'scheduleGreeting';
      greetEl.className = 'sched-greeting';
      var shell = document.querySelector('.schedule-shell');
      if (shell) shell.insertBefore(greetEl, shell.firstChild);
    }
    var name = localStorage.getItem('sb_user_name') || localStorage.getItem('sb_user_email') || '';
    var hour = new Date().getHours();
    var timeGreet = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
    greetEl.textContent = name ? timeGreet + ', ' + name : timeGreet;
  }

  function renderCurrentView() {
    // Warm greeting (Van Edwards: warmth before competence)
    renderGreeting();
    document.querySelectorAll('.schedule-view').forEach(function (v) { v.style.display = 'none'; });
    var viewMap = {
      upcoming:  'viewUpcoming',
      approvals: 'viewApprovals',
      history:   'viewHistory',
      esign:     'viewEsign',
    };
    var id = viewMap[state.currentView];
    if (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = '';
    }
    if (state.currentView === 'upcoming'  && fn.renderUpcoming)  fn.renderUpcoming();
    if (state.currentView === 'approvals' && fn.renderApprovals) fn.renderApprovals();
    if (state.currentView === 'history'   && fn.renderHistory)   fn.renderHistory();
    if (state.currentView === 'esign'     && fn.renderEsign)     fn.renderEsign();
  }

  fn.renderCurrentView = renderCurrentView;

  // ── Period Toggle (7d / 30d / All-time) ────────────────────────────────────
  function setupPeriodToggle() {
    // Restore saved period
    var savedPeriod = localStorage.getItem('sb_schedule_period') || 'week';
    var savedBtn = document.querySelector('.period-btn[data-period="' + savedPeriod + '"]');
    if (savedBtn) {
      document.querySelectorAll('.period-btn').forEach(function (b) { b.classList.remove('period-btn--active'); });
      savedBtn.classList.add('period-btn--active');
    }
    var periodBtns = [].slice.call(document.querySelectorAll('.period-btn'));
    periodBtns.forEach(function (btn, idx) {
      btn.addEventListener('click', function () {
        periodBtns.forEach(function (b) { b.classList.remove('period-btn--active'); });
        btn.classList.add('period-btn--active');
        var period = btn.dataset.period;
        try { localStorage.setItem('sb_schedule_period', period); } catch (_) { /* Safari private browsing may throw */ }
        if (fn.updateROIPanel) fn.updateROIPanel(constants.PERIOD_DAYS[period] || 7);
      });
      // Arrow key navigation for radio group (WCAG)
      btn.addEventListener('keydown', function (e) {
        var next;
        if (e.key === 'ArrowRight') next = periodBtns[(idx + 1) % periodBtns.length];
        else if (e.key === 'ArrowLeft') next = periodBtns[(idx - 1 + periodBtns.length) % periodBtns.length];
        if (next) { e.preventDefault(); next.focus(); next.click(); }
      });
    });
  }

  // ── Pause All Agents (Kill Switch) ──────────────────────────────────────
  function setupPauseAllButton() {
    var toolbar = document.querySelector('.schedule-toolbar') || document.querySelector('.schedule-shell');
    if (!toolbar) return;
    var btn = document.createElement('button');
    btn.id = 'pauseAllBtn';
    btn.className = 'pause-all-btn';
    btn.textContent = '\u23F8 Pause All Agents';
    btn.addEventListener('click', function () {
      if (!state.allAgentsPaused && !confirm('Pause all agents? No actions will be auto-approved until you resume.')) return;
      state.allAgentsPaused = !state.allAgentsPaused;
      btn.textContent = state.allAgentsPaused ? '\u25B6 Resume Agents' : '\u23F8 Pause All Agents';
      btn.classList.toggle('pause-all-btn--active', state.allAgentsPaused);
      renderPauseBanner();
    });
    toolbar.appendChild(btn);
  }

  function renderPauseBanner() {
    var banner = document.getElementById('pauseBanner');
    if (state.allAgentsPaused) {
      if (!banner) {
        banner = document.createElement('div');
        banner.id = 'pauseBanner';
        banner.className = 'pause-banner';
        var shell = document.querySelector('.schedule-shell');
        if (shell) shell.insertBefore(banner, shell.firstChild);
      }
      banner.textContent = '\u23F8 All agents paused \u2014 no actions will be auto-approved. Click "Resume Agents" to continue.';
    } else if (banner) {
      banner.remove();
    }
  }

  // ── Poll Scheduling with Circuit Breaker (Vogels/Gregg) ─────────────────
  function schedulePoll() {
    if (state.pollIntervalId) clearTimeout(state.pollIntervalId);
    // Exponential backoff: 30s, 60s, 300s (5min) after consecutive failures
    var backoffMs = state.consecutivePollFailures >= constants.MAX_POLL_FAILURES
      ? 300000  // 5 min backoff when circuit is open
      : constants.POLL_INTERVAL_MS * Math.pow(2, Math.min(state.consecutivePollFailures, 2));
    state.pollIntervalId = setTimeout(function () {
      if (!document.hidden) {
        loadActivities();
      }
      schedulePoll();
    }, backoffMs);
  }

  // ── Offline / Sync Management ────────────────────────────────────────────
  function setupOfflineSync() {
    // Listen for online/offline events
    window.addEventListener('online', function () {
      flushOfflineQueue();
      loadCloudStatus();
    });
    window.addEventListener('offline', function () {
      state.cloudStatus.connected = false;
      if (fn.renderSyncBanner) fn.renderSyncBanner();
    });
  }

  function loadCloudStatus() {
    Promise.all([
      fetch('/api/cloud/sync/status'),
      fetch('/api/cloud/user/tier'),
    ]).then(function (results) {
      var syncRes = results[0];
      var tierRes = results[1];
      var syncPromise = syncRes.ok ? syncRes.json() : Promise.resolve(null);
      var tierPromise = tierRes.ok ? tierRes.json() : Promise.resolve(null);
      return Promise.all([syncPromise, tierPromise]);
    }).then(function (data) {
      var syncData = data[0];
      var tierData = data[1];
      if (syncData) {
        state.cloudStatus.connected = syncData.connected;
        state.cloudStatus.offline_queue_count = syncData.offline_queue_count || 0;
        state.cloudStatus.last_push = syncData.last_push;
        state.cloudStatus.last_pull = syncData.last_pull;
      }
      if (tierData) {
        state.cloudStatus.tier = tierData.tier || 'free';
        try { localStorage.setItem('sb_esign_tier', state.cloudStatus.tier); } catch (_) { /* Safari private browsing may throw */ }
      }
      if (fn.renderSyncBanner) fn.renderSyncBanner();
    }).catch(function (e) {
      state.cloudStatus.connected = false;
      console.debug('loadCloudStatus failed:', e.message || e);
      if (fn.renderSyncBanner) fn.renderSyncBanner();
    });
  }

  function flushOfflineQueue() {
    fetch('/api/offline/flush', { method: 'POST',
      headers: { 'Content-Type': 'application/json' }, body: '{}' })
    .then(function (res) {
      if (res.ok) return res.json();
      return null;
    }).then(function (data) {
      if (data && data.flushed > 0) {
        state.cloudStatus.offline_queue_count = data.remaining;
        if (fn.renderSyncBanner) fn.renderSyncBanner();
      }
    }).catch(function (e) { console.debug('Offline queue flush failed:', e.message || e); });
  }

  fn.loadCloudStatus = loadCloudStatus;

  // ── Data Loading ───────────────────────────────────────────────────────────
  function loadActivities() {
    // Load past activities (audit log)
    var activitiesPromise = fetch('/api/schedule').then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }).then(function (data) {
      state.activities = data.activities || data || [];
      state.csrfToken = data.csrf_token || '';
      state.consecutivePollFailures = 0;  // Reset circuit breaker on success
      hideErrorBanner();
    }).catch(function (e) {
      state.consecutivePollFailures++;
      state.activities = [];
      var msg = state.consecutivePollFailures >= constants.MAX_POLL_FAILURES
        ? 'Server unreachable \u2014 polling slowed to every 5 minutes. Will resume when connected.'
        : 'Failed to load schedule data. ' + (navigator.onLine ? 'Server may be restarting.' : 'You are offline.');
      showErrorBanner(msg);
    });

    // Load upcoming schedules (app crons + keep-alive + Part 11 + eSign)
    var upcomingPromise = fetch('/api/schedule/upcoming').then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }).then(function (data) {
      state.upcoming = data.upcoming || [];
      if (fn.renderOperationsPanel) fn.renderOperationsPanel(data.summary || {});
    }).catch(function (e) {
      state.upcoming = [];
      console.debug('schedule/upcoming failed:', e.message || e);
    });

    return Promise.all([activitiesPromise, upcomingPromise]).then(function () {
      // Convert upcoming schedules into calendar-visible entries
      var getNextRunTime = fn.getNextRunTime || function () { return new Date().toISOString(); };
      var scheduleActivities = state.upcoming
        .filter(function (u) { return u.type === 'app_schedule'; })
        .map(function (u) {
          return {
            id: 'sched-' + u.app_id,
            app_id: u.app_id,
            app_name: u.app_id.replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); }),
            status: 'scheduled',
            schedule_pattern: u.pattern_label || u.pattern,
            started_at: getNextRunTime(u.pattern),
            _schedule: true,
          };
        });

      state.activities = state.activities.concat(scheduleActivities);

      populateFilters();
      renderCurrentView();
      if (fn.updateROIPanel) fn.updateROIPanel();
      if (fn.checkPendingQueue) fn.checkPendingQueue();
    });
  }

  fn.loadActivities = loadActivities;

  // ── Boot ───────────────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    setupViewTabs();
    if (fn.setupNavButtons) fn.setupNavButtons();
    if (fn.setupSignOffSheet) fn.setupSignOffSheet();
    if (fn.setupRunDrawer) fn.setupRunDrawer();
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (fn.closeSignOffSheet) fn.closeSignOffSheet();
        if (fn.closeRunDrawer) fn.closeRunDrawer();
      }
    });
    setupPeriodToggle();
    setupOfflineSync();
    setupPauseAllButton();
    loadActivities();
    loadCloudStatus();
    // Visibility-aware polling with circuit breaker (Torvalds + Vogels)
    schedulePoll();
  });

})();
