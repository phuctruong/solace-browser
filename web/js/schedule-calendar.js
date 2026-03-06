/**
 * schedule-calendar.js — Calendar rendering, upcoming view, and operations panel
 * Part of the Agent Activity Calendar & Sign-Off Queue
 *
 * Depends on: schedule-core.js (window.SolaceSchedule)
 */

(function () {
  'use strict';

  const S = window.SolaceSchedule;
  const state     = S.state;
  const utils     = S.utils;
  const constants = S.constants;
  const fn        = S.fn;

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
    if (pattern && pattern !== 'manual') console.warn('Unrecognized schedule pattern:', pattern);
    return tomorrow.toISOString();
  }

  // ── Calendar Navigation ─────────────────────────────────────────────────
  function setupNavButtons() {
    const prevBtn = document.getElementById('calPrev');
    if (prevBtn) {
      prevBtn.addEventListener('click', function () {
        if (state.calOffset > -24) { state.calOffset--; renderCalendar(); }
      });
    }
    const nextBtn = document.getElementById('calNext');
    if (nextBtn) {
      nextBtn.addEventListener('click', function () {
        if (state.calOffset < 24) { state.calOffset++; renderCalendar(); }
      });
    }
  }

  // ── Calendar Rendering ──────────────────────────────────────────────────
  function renderCalendar() {
    const now = new Date();
    const d = new Date(now.getFullYear(), now.getMonth() + state.calOffset, 1);
    const year = d.getFullYear();
    const month = d.getMonth();

    const label = d.toLocaleString('default', { month: 'long', year: 'numeric' });
    const monthLabel = document.getElementById('calMonthLabel');
    if (monthLabel) monthLabel.textContent = label;

    // Build day map
    const dayMap = {};
    fn.getFiltered().forEach(function (a) {
      const ds = a.started_at ? (function (iso) { const d = new Date(iso); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); })(a.started_at) : null;
      if (!ds) return;
      if (!dayMap[ds]) dayMap[ds] = [];
      dayMap[ds].push(a);
    });

    // Grid: header row was static HTML, build day cells
    const grid = document.getElementById('calGrid');
    if (!grid) return;
    // Remove existing day cells (keep header row = first 7 children)
    const headers = [].slice.call(grid.children).slice(0, 7);
    grid.innerHTML = '';
    headers.forEach(function (h) { grid.appendChild(h); });

    // First day of month (Mon=0...Sun=6)
    const firstDay = (new Date(year, month, 1).getDay() + 6) % 7;
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const todayStr = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2,'0') + '-' + String(now.getDate()).padStart(2,'0');

    // Empty cells before 1st
    for (let i = 0; i < firstDay; i++) {
      const emptyCell = document.createElement('div');
      emptyCell.className = 'cal-cell cal-cell--empty';
      grid.appendChild(emptyCell);
    }

    for (let day = 1; day <= daysInMonth; day++) {
      const ds = year + '-' + String(month + 1).padStart(2,'0') + '-' + String(day).padStart(2,'0');
      const cell = document.createElement('div');
      cell.className = 'cal-cell' + (ds === todayStr ? ' cal-cell--today' : '');

      const dateNum = document.createElement('div');
      dateNum.className = 'cal-date';
      dateNum.textContent = day;
      cell.appendChild(dateNum);

      const dayActivities = dayMap[ds] || [];
      const shown = dayActivities.slice(0, constants.MAX_PILLS_PER_DAY);
      shown.forEach(function (act) {
        const pill = utils.makePill(act);
        pill.addEventListener('click', function () { if (fn.openRunDrawer) fn.openRunDrawer(act); });
        cell.appendChild(pill);
      });
      if (dayActivities.length > constants.MAX_PILLS_PER_DAY) {
        const overflow = document.createElement('div');
        overflow.className = 'cal-overflow';
        overflow.textContent = '+' + (dayActivities.length - constants.MAX_PILLS_PER_DAY) + ' more';
        cell.appendChild(overflow);
      }
      grid.appendChild(cell);
    }
  }

  // ── Upcoming View ───────────────────────────────────────────────────────
  function renderUpcoming() {
    // Render app schedules list
    const appsEl = document.getElementById('upcomingApps');
    const appScheds = state.upcoming.filter(function (u) { return u.type === 'app_schedule'; });
    if (appsEl) {
      if (appScheds.length === 0) {
        appsEl.innerHTML = '<p class="timeline-empty">No apps scheduled yet. <a href="/home">Activate an app</a> to set up its schedule.</p>';
      } else {
        appsEl.innerHTML = appScheds.map(function (s) {
          const emoji = constants.APP_EMOJI[s.app_id] || '\uD83D\uDCC5';
          const name = utils.escapeHtml(s.app_id.replace(/-/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); }));
          const nextRun = getNextRunTime(s.pattern);
          return '<div class="upcoming-item">' +
            '<span class="upcoming-item__emoji">' + emoji + '</span>' +
            '<div class="upcoming-item__info">' +
              '<div class="upcoming-item__name">' + name + '</div>' +
              '<div class="upcoming-item__detail">' + utils.escapeHtml(s.pattern_label || s.pattern) + ' \u00B7 Next: ' + utils.escapeHtml(utils.formatTime(nextRun)) + '</div>' +
            '</div>' +
            '<span class="upcoming-item__status">' + (s.enabled !== false ? '\u2705 Active' : '\u25CB Paused') + '</span>' +
          '</div>';
        }).join('');
      }
    }

    // Render keep-alive sessions
    const kaEl = document.getElementById('upcomingKeepAlive');
    const keepAlives = state.upcoming.filter(function (u) { return u.type === 'keep_alive'; });
    const kaCount = document.getElementById('keepAliveCount');
    if (kaCount) kaCount.textContent = keepAlives.length > 0 ? '(' + keepAlives.length + ')' : '';
    if (kaEl) {
      if (keepAlives.length === 0) {
        kaEl.innerHTML = '<p class="timeline-empty">No keep-alive sessions active.</p>';
      } else {
        kaEl.innerHTML = keepAlives.map(function (k) {
          // Presence in keep_alive list implies enabled; explicit enabled:false means paused
          const isEnabled = k.enabled !== false;
          return '<div class="upcoming-item">' +
            '<span class="upcoming-item__emoji">\uD83D\uDD04</span>' +
            '<div class="upcoming-item__info">' +
              '<div class="upcoming-item__name">' + utils.escapeHtml(k.domain) + '</div>' +
              '<div class="upcoming-item__detail">Cookie refresh \u00B7 Every ' + utils.escapeHtml(k.interval || '4h') + '</div>' +
            '</div>' +
            '<span class="upcoming-item__status">' + (isEnabled ? '\u2705 Active' : '\u25CB Paused') + '</span>' +
          '</div>';
        }).join('');
      }
    }

    // Render calendar
    renderCalendar();
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
      opsEl.className = 'ops-panel';
      dashboard.appendChild(opsEl);
    }

    const appScheds = state.upcoming.filter(function (u) { return u.type === 'app_schedule'; });
    const keepAlives = state.upcoming.filter(function (u) { return u.type === 'keep_alive'; });
    const part11 = state.upcoming.find(function (u) { return u.type === 'part11'; });
    const esign = state.upcoming.find(function (u) { return u.type === 'esign'; });

    opsEl.innerHTML =
      '<div class="ops-card">' +
        '<div class="ops-card__num">' + appScheds.length + '</div>' +
        '<div class="ops-card__label">App Schedules</div>' +
        appScheds.map(function (s) { return '<div class="ops-card__detail">' + (constants.APP_EMOJI[s.app_id] || '\uD83D\uDCC5') + ' ' + utils.escapeHtml(s.pattern_label) + '</div>'; }).join('') +
      '</div>' +
      '<div class="ops-card">' +
        '<div class="ops-card__num">' + keepAlives.length + '</div>' +
        '<div class="ops-card__label">Keep-Alive Sessions</div>' +
        keepAlives.slice(0, constants.MAX_KEEPALIVE_SHOWN).map(function (k) { return '<div class="ops-card__detail">\uD83D\uDD04 ' + utils.escapeHtml(k.domain) + '</div>'; }).join('') +
        (keepAlives.length > constants.MAX_KEEPALIVE_SHOWN ? '<div class="ops-card__detail" style="opacity:0.5">+' + (keepAlives.length - constants.MAX_KEEPALIVE_SHOWN) + ' more</div>' : '') +
      '</div>' +
      '<div class="ops-card">' +
        '<div class="ops-card__num">' + (part11 ? (part11.chain_entries || 0) : 0) + '</div>' +
        '<div class="ops-card__label">Part 11 Evidence Capture</div>' +
        '<div class="ops-card__detail">' + (part11 && part11.status === 'active' ? '\u2705 Active \u2014 ' + part11.mode + ' mode' : '\u25CB Disabled') + '</div>' +
      '</div>' +
      '<div class="ops-card">' +
        '<div class="ops-card__num">' + (esign ? (esign.attestation_count || 0) : 0) + '</div>' +
        '<div class="ops-card__label">eSign Attestations</div>' +
        '<div class="ops-card__detail">' + (esign && esign.status === 'active' ? '\u2705 Active \u2014 on approval' : '\u25CB Disabled') + '</div>' +
      '</div>';
  }

  // ── Export to namespace ─────────────────────────────────────────────────
  fn.getNextRunTime         = getNextRunTime;
  fn.setupNavButtons        = setupNavButtons;
  fn.renderCalendar         = renderCalendar;
  fn.renderUpcoming         = renderUpcoming;
  fn.renderOperationsPanel  = renderOperationsPanel;

})();
