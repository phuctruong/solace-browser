/**
 * schedule-approvals.js — Approval rendering, sign-off sheet, and action handlers
 * Part of the Agent Activity Calendar & Sign-Off Queue
 *
 * Depends on: schedule-core.js (window.SolaceSchedule)
 */

(function () {
  'use strict';

  var S = window.SolaceSchedule;
  var state     = S.state;
  var utils     = S.utils;
  var constants = S.constants;
  var fn        = S.fn;

  // ── Sign-Off Queue Alert ────────────────────────────────────────────────
  function checkPendingQueue() {
    var pending = state.activities.filter(function (a) { return a.status === 'pending_approval'; });
    var alert = document.getElementById('signoffAlert');
    if (!alert) return;
    if (pending.length > 0) {
      alert.style.display = 'flex';
      document.getElementById('signoffCount').textContent = pending.length;
      // YinYang badge
      var badge = document.getElementById('yyPendingBadge');
      if (badge) badge.style.display = '';
    } else {
      alert.style.display = 'none';
      var badge2 = document.getElementById('yyPendingBadge');
      if (badge2) badge2.style.display = 'none';
    }
  }

  // ── Sign-Off Sheet Setup ────────────────────────────────────────────────
  function setupSignOffSheet() {
    var openBtn = document.getElementById('signoffOpenBtn');
    if (openBtn) openBtn.addEventListener('click', openSignOffSheet);
    var closeBtn = document.getElementById('signoffClose');
    if (closeBtn) closeBtn.addEventListener('click', closeSignOffSheet);
    var overlay = document.getElementById('signoffOverlay');
    if (overlay) overlay.addEventListener('click', closeSignOffSheet);
  }

  function openSignOffSheet() {
    var items = document.getElementById('signoffItems');
    var pending = state.activities.filter(function (a) { return a.status === 'pending_approval'; });
    items.innerHTML = '';
    if (!pending.length) {
      items.innerHTML = '<p style="color:#94a3b8;text-align:center;padding:1rem">No pending approvals</p>';
    } else {
      pending.forEach(function (a) {
        var item = document.createElement('div');
        item.className = 'signoff-item';
        var scopeStr = (a.scopes_used || []).map(function (s) {
          // Translate technical scopes to human language
          var scopeMap = { 'gmail:read': 'Read your inbox', 'gmail:modify': 'Archive/label emails',
            'gmail:send': 'Send emails', 'calendar:read': 'Read your calendar', 'calendar:write': 'Update your calendar',
            'linkedin:post': 'Post to LinkedIn', 'slack:read': 'Read Slack messages', 'slack:write': 'Send Slack messages' };
          return scopeMap[s] || s;
        }).join(', ') || 'No specific permissions requested';
        item.innerHTML =
          '<div class="signoff-item__app">' + (constants.APP_EMOJI[a.app_id] || '\uD83D\uDCC4') + ' ' + utils.escapeHtml(a.app_name) + '</div>' +
          '<div class="signoff-item__scope">Permissions: ' + utils.escapeHtml(scopeStr) + '</div>' +
          '<div class="signoff-item__desc"><span class="agent-output__label">Agent output:</span><br>' + utils.escapeHtml(a.output_summary || 'Your agent wants to proceed with this action.') + '</div>' +
          '<div class="signoff-item__footer">' +
            '<button class="approve-btn" data-id="' + a.id + '">\u2705 Approve</button>' +
            '<button class="reject-btn"  data-id="' + a.id + '" style="border:1.5px solid var(--sched-red);opacity:0.85">Decline</button>' +
            '<span class="countdown" id="sheet-cd-' + a.id + '">Take your time</span>' +
          '</div>';
        item.querySelector('.approve-btn').addEventListener('click', function () { approveRun(a.id); });
        item.querySelector('.reject-btn').addEventListener('click', function () { declineRun(a.id); });
        startCountdown(a, item.querySelector('.countdown'));
        items.appendChild(item);
      });
    }
    var sheet = document.getElementById('signoffSheet');
    sheet.style.display = '';
    document.getElementById('signoffOverlay').style.display = '';
    fn.trapFocus(sheet);
  }

  function closeSignOffSheet() {
    document.getElementById('signoffSheet').style.display = 'none';
    document.getElementById('signoffOverlay').style.display = 'none';
    fn.releaseFocusTrap();
  }

  // ── Approvals Tab Rendering ─────────────────────────────────────────────
  function renderApprovals() {
    var waiting = document.getElementById('kanbanWaitingCards');
    var done = document.getElementById('kanbanDoneCards');
    if (!waiting || !done) return;

    // Clear stale countdown intervals before re-rendering (Torvalds: prevent timer leaks)
    Object.keys(state.pendingCountdowns).forEach(function (id) { clearInterval(state.pendingCountdowns[id]); });
    state.pendingCountdowns = {};

    var filtered = fn.getFiltered();
    var pending = filtered.filter(function (a) { return a.status === 'pending_approval' || a.status === 'cooldown'; });
    var approved = filtered.filter(function (a) { return a.status === 'success' && a.approved_by; }).slice(0, constants.MAX_APPROVED_SHOWN);

    waiting.innerHTML = '';
    done.innerHTML = '';

    if (pending.length === 0) {
      waiting.innerHTML = '<div style="color:var(--sched-text-dim);padding:1rem;text-align:center;font-size:0.85rem">No pending approvals \u2014 all your agent\'s actions are running within safe parameters.<br><small style="opacity:0.7">Tier A = read-only (auto-approved) \u00B7 Tier B = writes (needs your OK) \u00B7 Tier C = sensitive (needs your OK + review)</small></div>';
    }
    pending.forEach(function (act) {
      var card = makeApprovalCard(act);
      waiting.appendChild(card);
    });
    approved.forEach(function (act) {
      var card = makeApprovalCard(act);
      done.appendChild(card);
    });

    // Update approval badge
    var badge = document.getElementById('approvalBadge');
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
    var card = document.createElement('div');
    card.className = 'kanban-card';
    var emoji = constants.APP_EMOJI[a.app_id] || '\uD83E\uDD16';
    var time = utils.formatTime(a.started_at);
    var cost = a.cost_usd ? '$' + a.cost_usd.toFixed(4) : '\u2014';
    var scopeStr = (a.scopes_used || []).join(', ') || '\u2014';

    var safeId = utils.escapeHtml(a.id);
    var safeName = utils.escapeHtml(a.app_name || a.app_id);
    var safeStatus = utils.escapeHtml(a.status.replace(/_/g,' '));
    var safeTier = utils.escapeHtml(a.safety_tier || 'A');
    var safeHash = utils.escapeHtml(a.evidence_hash || '');

    card.innerHTML =
      '<div class="kanban-card__app">' + emoji + ' ' + safeName + '</div>' +
      '<div class="kanban-card__meta">' +
        '<span>' + (constants.STATUS_EMOJI[a.status] || '') + ' ' + safeStatus + '</span>' +
        '<span>' + time + '</span>' +
        '<span class="kanban-card__badge badge--' + safeTier + '">' + safeTier + '</span>' +
        (a.cost_usd ? '<span>' + cost + '</span>' : '') +
      '</div>' +
      (a.output_summary ? '<div class="kanban-card__summary"><span class="agent-output__label">Agent output:</span><br>' + utils.escapeHtml(utils.truncate(a.output_summary, 80)) + '</div>' : '') +
      (a.evidence_hash ? '<div class="evidence-hash-row">\uD83D\uDD17 ' + safeHash.slice(0,16) + '\u2026 <button class="copy-hash-btn" title="Copy evidence hash">Copy</button></div>' : '') +
      (a.status === 'pending_approval' ?
        '<div class="kanban-card__actions">' +
          '<span class="countdown" id="cd-' + safeId + '">\u23F3 Calculating\u2026</span><br>' +
          '<button class="approve-btn" data-id="' + safeId + '">\u2705 Approve</button>' +
          '<button class="approve-btn approve-btn--esign" data-id="' + safeId + '" data-esign="1" title="Creates a tamper-evident cryptographic signature of your approval">\uD83D\uDD0F Approve + Sign</button>' +
          '<button class="reject-btn"  data-id="' + safeId + '" style="border:1.5px solid var(--sched-red);opacity:0.85">Decline</button>' +
        '</div>' : '');

    // Copy hash button handler (uses closure, not data attribute — XSS safe)
    var copyBtn = card.querySelector('.copy-hash-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(a.evidence_hash).then(function () {
            e.target.textContent = 'Copied!';
            setTimeout(function () { e.target.textContent = 'Copy'; }, 1500);
          }).catch(function () { e.target.textContent = 'Failed'; setTimeout(function () { e.target.textContent = 'Copy'; }, 1500); });
        } else {
          e.target.textContent = 'N/A';
        }
      });
    }
    var appNameEl = card.querySelector('.kanban-card__app');
    if (appNameEl) {
      appNameEl.addEventListener('click', function () { if (fn.openRunDrawer) fn.openRunDrawer(a); });
    }
    if (a.status === 'pending_approval') {
      startCountdown(a, card.querySelector('.countdown'));
      card.querySelectorAll('.approve-btn').forEach(function (btn) {
        btn.addEventListener('click', function (e) {
          e.stopPropagation();
          approveRun(a.id, btn.dataset.esign === '1');
        });
      });
      var rejectBtn = card.querySelector('.reject-btn');
      if (rejectBtn) {
        rejectBtn.addEventListener('click', function (e) { e.stopPropagation(); declineRun(a.id); });
      }
    }
    return card;
  }

  // ── Approval Actions ────────────────────────────────────────────────────
  function approveRun(id, withEsign) {
    // Part 11 compliance: approver must be uniquely identifiable
    var approverName = localStorage.getItem('sb_user_name') || localStorage.getItem('sb_user_email') || 'local_user';
    var sessionId = sessionStorage.getItem('sb_session_id') || crypto.randomUUID();
    var body = {
      approved_by: approverName,
      device_id: localStorage.getItem('sb_device_id') || (function () { var id = crypto.randomUUID(); localStorage.setItem('sb_device_id', id); return id; })(),
      session_id: sessionId,
      timestamp: new Date().toISOString(),
      esign: !!withEsign,
      csrf_token: state.csrfToken,
    };
    // Persist session_id for this browser session
    if (!sessionStorage.getItem('sb_session_id')) {
      sessionStorage.setItem('sb_session_id', body.session_id);
    }
    fetch('/api/schedule/approve/' + id, { method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body) })
    .then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) throw new Error(data.error || 'Approval failed');
        return data;
      });
    })
    .then(function (data) {
      // If eSign was requested, log the attestation
      if (withEsign && data.esign_hash) {
        var act = state.activities.find(function (x) { return x.id === id; });
        if (act) act.esign_hash = data.esign_hash;
      }
      // Update local state only after confirmed server response
      var a = state.activities.find(function (x) { return x.id === id; });
      if (a) a.status = 'approved';
      closeSignOffSheet();
      fn.loadActivities();
    })
    .catch(function (e) {
      // Torvalds: never swallow errors silently — log and notify user
      console.warn('Approval failed:', e.message || e);
      fn.showErrorBanner('Approval failed. ' + (navigator.onLine ? 'Server may be restarting.' : 'You are offline \u2014 will retry when connected.'));
    });
  }

  function declineRun(id) {
    fetch('/api/schedule/cancel/' + id, { method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ reason: 'user_declined', timestamp: new Date().toISOString(), csrf_token: state.csrfToken }) })
    .then(function (res) {
      return res.json().then(function (data) {
        if (!res.ok) throw new Error(data.error || 'Decline failed');
        return data;
      });
    })
    .then(function () {
      var a = state.activities.find(function (x) { return x.id === id; });
      if (a) a.status = 'cancelled';
      closeSignOffSheet();
      fn.loadActivities();
    })
    .catch(function (e) {
      console.warn('Decline failed:', e.message || e);
      fn.showErrorBanner('Decline failed. ' + (navigator.onLine ? 'Server may be restarting.' : 'You are offline.'));
    });
  }

  // ── Countdown ──────────────────────────────────────────────────────────
  function startCountdown(a, el) {
    if (!el || !a.approval_deadline) return;
    var deadline = new Date(a.approval_deadline).getTime();
    var tick = function () {
      var remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      // Vanessa Van Edwards: reassuring framing, not coercive countdown
      if (el) el.textContent = remaining > 10
        ? 'Take your time \u2014 ' + remaining + 's before safely blocked'
        : remaining + 's \u2014 action will be safely blocked';
      if (remaining <= 0) {
        clearInterval(state.pendingCountdowns[a.id]);
        // Guard: if user already approved/declined while countdown was ticking, skip auto-reject.
        // The local activities array is updated on approve/reject, so check it before firing.
        var current = state.activities.find(function (x) { return x.id === a.id; });
        if (current && current.status === 'pending_approval' && !state.allAgentsPaused) {
          // Auto-block (fail-safe, not fail-punish)
          declineRun(a.id);
        }
      }
    };
    clearInterval(state.pendingCountdowns[a.id]);
    state.pendingCountdowns[a.id] = setInterval(tick, 1000);
    tick();
  }

  // ── Export to namespace ─────────────────────────────────────────────────
  fn.renderApprovals    = renderApprovals;
  fn.checkPendingQueue  = checkPendingQueue;
  fn.setupSignOffSheet  = setupSignOffSheet;
  fn.openSignOffSheet   = openSignOffSheet;
  fn.closeSignOffSheet  = closeSignOffSheet;

})();
