/**
 * schedule-evidence.js — ROI panel, history, eSign, run drawer, and sync banner
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

  // ── ROI Panel ───────────────────────────────────────────────────────────
  function updateROIPanel(periodDays) {
    const days = periodDays || 7;
    const cutoff = Date.now() - days * 24 * 3600 * 1000;
    const periodActivities = state.activities.filter(function (a) {
      return a.started_at && new Date(a.started_at) > cutoff && a.status === 'success';
    });
    const totalCost      = periodActivities.reduce(function (s, a) { return s + (a.cost_usd || 0); }, 0);
    const totalTokens    = periodActivities.reduce(function (s, a) { return s + (a.tokens_used || 0); }, 0);
    const hasTokenData   = periodActivities.some(function (a) { return a.tokens_used > 0; });
    const replayCount    = periodActivities.filter(function (a) { return a.recipe_hit; }).length;

    // Token savings: market average rate vs Solace (Together.ai Llama 3.3)
    const gpt4Cost       = totalTokens * constants.MARKET_RATE_PER_TOKEN;
    const tokenSavings   = gpt4Cost - totalCost;

    // Time savings: estimated manual time per task -> hourly rate baseline
    const humanHours     = (periodActivities.length * constants.MANUAL_MINUTES_PER_TASK) / 60;
    const netSavings     = humanHours * constants.HOURLY_RATE_USD - totalCost;

    // Recipe hit rate
    const hitRate        = periodActivities.length > 0
      ? Math.round((replayCount / periodActivities.length) * 100)
      : 0;

    // Streak calculation — O(n + 365) using Set lookup instead of O(365*n) array scan
    let streak = 0;
    const today = new Date();
    const earlyMorning = today.getHours() < constants.STREAK_GRACE_HOUR;
    today.setHours(0, 0, 0, 0);
    const successDates = new Set();
    state.activities.forEach(function (a) {
      if (a.started_at && a.status === 'success') {
        const d = new Date(a.started_at);
        successDates.add(d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'));
      }
    });
    for (let i = 0; i < constants.MAX_STREAK_DAYS; i++) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const ds = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
      if (successDates.has(ds)) { streak++; }
      else if (i === 0 && earlyMorning) { continue; }
      else { break; }
    }

    // Update badge label
    const badge = document.getElementById('savingsBadge');
    if (badge) {
      badge.textContent = constants.PERIOD_LABELS[days] || (days + ' days');
    }

    utils.setText('roiRuns',       periodActivities.length + ' runs');
    utils.setText('roiTimeSaved',  humanHours.toFixed(1) + ' hrs (est.)');
    utils.setText('roiTasks',      hasTokenData
      ? periodActivities.length + ' tasks'
      : '\u2014');
    utils.setText('roiTokenSaved', tokenSavings > 0
      ? '$' + tokenSavings.toFixed(2)
      : tokenSavings < 0 ? '-$' + Math.abs(tokenSavings).toFixed(2) : '$0.00');
    utils.setText('roiCost',       totalCost < 0.01 ? '< 1\u00A2' : '$' + totalCost.toFixed(2));
    utils.setText('roiNet',        netSavings > 0 ? '+$' + netSavings.toFixed(0) : netSavings < 0 ? '-$' + Math.abs(netSavings).toFixed(0) : '$0');

    // Ekman: honest color — green for positive, red for negative, neutral for zero
    const netEl = document.getElementById('roiNet');
    const netNum = netEl ? netEl.querySelector('.roi-num') : null;
    if (netNum) netNum.style.color = netSavings > 0 ? '#10b981' : netSavings < 0 ? '#ef4444' : '';

    // Streak with escalating emoji (Rory Sutherland: milestones need ceremony)
    const streakEmoji = streak >= 60 ? '\uD83D\uDC09' : streak >= 30 ? '\uD83C\uDFC6' : streak >= 14 ? '\u26A1' : streak >= 7 ? '\uD83D\uDD25' : '\uD83C\uDF31';
    utils.setText('roiStreak',     streak + ' days ' + streakEmoji);

    // Hit rate progress bar
    const bar = document.getElementById('roiHitBar');
    const pct = document.getElementById('roiHitPct');
    if (bar) {
      bar.style.width = hitRate + '%';
      bar.parentElement.setAttribute('aria-valuenow', Math.round(hitRate));
    }
    if (pct) pct.textContent = hitRate + '%';
  }

  // ── Flagged Runs (post-hoc dispute) ───────────────────────────────────
  function getFlaggedRuns() {
    try { return JSON.parse(localStorage.getItem('sb_flagged_runs') || '{}'); } catch (_) { return {}; }
  }

  function setFlaggedRun(runId, reason) {
    const flagged = getFlaggedRuns();
    flagged[runId] = { reason: reason, timestamp: new Date().toISOString() };
    try { localStorage.setItem('sb_flagged_runs', JSON.stringify(flagged)); } catch (_) { /* Safari private browsing may throw */ }
  }

  // ── History View ────────────────────────────────────────────────────────
  function renderHistory() {
    const tbody = document.getElementById('activityTableBody');
    if (!tbody) return;
    const filtered = fn.getFiltered().filter(function (a) { return a.started_at && !a._schedule; }).sort(
      function (a, b) { return new Date(b.started_at) - new Date(a.started_at); }
    );
    if (!filtered.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="table-loading">Your first run will appear here. Once your agent starts working, you\'ll have a full audit trail of everything it did \u2014 with cryptographic evidence.</td></tr>';
      return;
    }
    tbody.innerHTML = '';
    const flaggedRuns = getFlaggedRuns();
    filtered.slice(0, constants.MAX_HISTORY_ROWS).forEach(function (act) {
      const tr = document.createElement('tr');
      const emoji = constants.APP_EMOJI[act.app_id] || '\uD83D\uDCC4';
      const safeName = utils.escapeHtml(act.app_name || act.app_id);
      const safeStatus = utils.escapeHtml((act.status || '').replace(/_/g,' '));
      const isFlagged = !!flaggedRuns[act.id];
      tr.innerHTML =
        '<td>' + emoji + ' ' + safeName + '</td>' +
        '<td><span class="status-badge status-badge--' + utils.simplifyStatus(act.status) + '">' + (constants.STATUS_EMOJI[act.status] || '') + ' ' + safeStatus + '</span></td>' +
        '<td>' + utils.escapeHtml(utils.formatTime(act.started_at)) + '</td>' +
        '<td>' + utils.formatDuration(act.duration_ms) + '</td>' +
        '<td>' + (act.cost_usd ? '$' + Number(act.cost_usd).toFixed(4) : '\u2014') + '</td>' +
        '<td>' + (act.evidence_hash
          ? '<span class="evidence-hash-cell" title="Click to copy">\uD83D\uDD17 ' + utils.escapeHtml(act.evidence_hash.slice(0,12)) + '\u2026 \uD83D\uDCCB</span>'
          : '\u2014') + '</td>' +
        '<td><button class="flag-btn' + (isFlagged ? ' flag-btn--flagged' : '') + '" title="' + (isFlagged ? 'Flagged as ' + utils.escapeHtml(flaggedRuns[act.id].reason) : 'Flag this run as incorrect or misaligned') + '" style="background:none;border:none;cursor:pointer;font-size:0.85rem;padding:2px 6px;border-radius:4px;' + (isFlagged ? 'color:#ef4444;font-weight:600' : 'color:var(--sched-text-dim,#94a3b8);opacity:0.7') + '">' + (isFlagged ? '\uD83D\uDEA9' : '\u2691') + '</button></td>';
      // Click-to-copy hash via event listener (not inline onclick — XSS safe)
      const hashEl = tr.querySelector('.evidence-hash-cell');
      if (hashEl) {
        hashEl.style.cursor = 'pointer';
        hashEl.addEventListener('click', function (e) {
          e.stopPropagation();
          const originalText = hashEl.innerHTML;
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(act.evidence_hash).then(function () {
              hashEl.textContent = 'Copied!';
              setTimeout(function () { hashEl.innerHTML = originalText; }, 1500);
            }).catch(function () {
              hashEl.textContent = 'Copy failed';
              setTimeout(function () { hashEl.innerHTML = originalText; }, 1500);
            });
          }
        });
      }
      // Flag button for post-hoc dispute (inline form, not alert/prompt — consistent UX)
      const flagBtn = tr.querySelector('.flag-btn');
      if (flagBtn) {
        flagBtn.addEventListener('click', function (e) {
          e.stopPropagation();
          if (flaggedRuns[act.id]) {
            // Already flagged — show info via tooltip (no blocking alert)
            flagBtn.title = 'Flagged as "' + flaggedRuns[act.id].reason + '" on ' + flaggedRuns[act.id].timestamp.split('T')[0];
            return;
          }
          // Inline flag form instead of blocking prompt()
          const existing = tr.querySelector('.flag-inline-form');
          if (existing) { existing.remove(); return; } // toggle off
          const formTd = document.createElement('td');
          formTd.colSpan = 7;
          formTd.className = 'flag-inline-form';
          formTd.innerHTML = '<div style="display:flex;gap:6px;align-items:center;padding:6px 8px;background:rgba(239,68,68,0.08);border-radius:6px">' +
            '<input type="text" class="flag-input" placeholder="Reason (e.g. wrong email sent)" style="flex:1;background:var(--sched-card-bg);border:1px solid var(--sched-border);color:var(--sched-text);border-radius:4px;padding:4px 8px;font-size:0.8rem">' +
            '<button class="flag-submit" style="background:var(--sched-red);color:#fff;border:none;border-radius:4px;padding:4px 10px;font-size:0.8rem;cursor:pointer">Flag</button>' +
            '<button class="flag-cancel" style="background:none;border:1px solid var(--sched-border);color:var(--sched-text-dim);border-radius:4px;padding:4px 8px;font-size:0.8rem;cursor:pointer">Cancel</button>' +
          '</div>';
          const formRow = document.createElement('tr');
          formRow.appendChild(formTd);
          tr.parentNode.insertBefore(formRow, tr.nextSibling);
          const input = formTd.querySelector('.flag-input');
          input.focus();
          formTd.querySelector('.flag-submit').addEventListener('click', function () {
            const reason = input.value.trim();
            if (reason) {
              setFlaggedRun(act.id, reason);
              flagBtn.textContent = '\uD83D\uDEA9';
              flagBtn.classList.add('flag-btn--flagged');
              flagBtn.title = 'Flagged as ' + reason;
            }
            formRow.remove();
          });
          formTd.querySelector('.flag-cancel').addEventListener('click', function () { formRow.remove(); });
          input.addEventListener('keydown', function (ke) {
            if (ke.key === 'Enter') formTd.querySelector('.flag-submit').click();
            if (ke.key === 'Escape') formRow.remove();
          });
        });
      }
      tr.addEventListener('click', function () { openRunDrawer(act); });
      tbody.appendChild(tr);
    });
  }

  // ── eSign View ──────────────────────────────────────────────────────────
  function renderEsign() {
    // Update eSign stats from upcoming data + cloud chain status
    const esignData = state.upcoming.find(function (u) { return u.type === 'esign'; });
    const part11Data = state.upcoming.find(function (u) { return u.type === 'part11'; });

    // Fetch cloud chain status (non-blocking)
    fetch('/api/cloud/esign/chain-status').then(function (r) { return r.ok ? r.json() : null; }).then(function (chain) {
      if (chain && chain.total_signatures !== undefined) {
        const totalEl = document.getElementById('esignTotal');
        if (totalEl) totalEl.textContent = chain.total_signatures;
      }
    }).catch(function (e) {
      console.debug('Cloud eSign chain status unavailable:', e.message || e);
      let warnEl = document.getElementById('esignCloudWarn');
      if (!warnEl) {
        warnEl = document.createElement('small');
        warnEl.id = 'esignCloudWarn';
        warnEl.style.cssText = 'color:var(--sched-text-dim);font-size:0.7rem';
        const statsEl = document.getElementById('esignStats');
        if (statsEl) statsEl.appendChild(warnEl);
      }
      warnEl.textContent = 'Cloud chain verification unavailable';
    });

    const totalEl = document.getElementById('esignTotal');
    const monthEl = document.getElementById('esignThisMonth');
    const remainEl = document.getElementById('esignRemaining');
    if (totalEl) totalEl.textContent = esignData ? (esignData.attestation_count || 0) : 0;
    if (monthEl) monthEl.textContent = esignData ? (esignData.this_month || 0) : 0;
    // Tier-aware remaining display
    const tier = state.cloudStatus.tier || localStorage.getItem('sb_esign_tier') || 'free';
    const limit = constants.TIER_ESIGN_LIMITS[tier] || 0;
    const used = esignData ? (esignData.attestation_count || 0) : 0;
    const remaining = limit === Infinity ? '\u221E' : Math.max(0, limit - used);
    if (remainEl) {
      if (tier === 'free' && remaining === 0) {
        remainEl.textContent = '\u2014';
        remainEl.title = 'Available on Starter and Pro tiers';
      } else {
        remainEl.textContent = remaining;
      }
    }

    // Render recent attestations
    const listEl = document.getElementById('esignList');
    const esignRuns = fn.getFiltered().filter(function (a) { return a.esign_hash || a.esign_attestation; });
    if (listEl) {
      if (esignRuns.length === 0) {
        const tierMsg = (tier === 'free')
          ? 'Starter and Pro tiers include cryptographic signatures that make your AI actions legally verifiable. <a href="/pricing">Learn more</a>'
          : 'No signed approvals yet. When you use "Approve + Sign," you create a tamper-evident record of your decision.';
        listEl.innerHTML = '<p class="timeline-empty">' + tierMsg + '</p>';
      } else {
        listEl.innerHTML = esignRuns.slice(0, constants.MAX_ESIGN_SHOWN).map(function (a) {
          const emoji = constants.APP_EMOJI[a.app_id] || '\uD83D\uDCC4';
          return '<div class="upcoming-item">' +
            '<span class="upcoming-item__emoji">\uD83D\uDD0F</span>' +
            '<div class="upcoming-item__info">' +
              '<div class="upcoming-item__name">' + emoji + ' ' + utils.escapeHtml(a.app_name || a.app_id) + '</div>' +
              '<div class="upcoming-item__detail">' + utils.escapeHtml(utils.formatTime(a.started_at)) + ' \u00B7 <span class="esign-hash-inline">' + utils.escapeHtml((a.esign_hash || '').slice(0,16)) + '\u2026</span></div>' +
            '</div>' +
            '<span class="upcoming-item__status">\u2705 Signed</span>' +
          '</div>';
        }).join('');
      }
    }

    // Render Part 11 evidence chain status
    const part11El = document.getElementById('part11Status');
    if (part11El) {
      if (part11Data && part11Data.status === 'active') {
        part11El.innerHTML =
          '<div class="upcoming-item">' +
            '<span class="upcoming-item__emoji">\uD83D\uDD17</span>' +
            '<div class="upcoming-item__info">' +
              '<div class="upcoming-item__name">Evidence Chain Active</div>' +
              '<div class="upcoming-item__detail">' + (part11Data.chain_entries || 0) + ' entries \u00B7 ' + (part11Data.mode || 'data') + ' mode \u00B7 SHA-256 hashed</div>' +
            '</div>' +
            '<span class="upcoming-item__status">\u2705 ' + part11Data.mode + '</span>' +
          '</div>' +
          '<div class="upcoming-item">' +
            '<span class="upcoming-item__emoji">\uD83D\uDCCB</span>' +
            '<div class="upcoming-item__info">' +
              '<div class="upcoming-item__name">ALCOA+ Compliance</div>' +
              '<div class="upcoming-item__detail" title="Attributable (who did it) \u00B7 Legible (readable) \u00B7 Contemporaneous (real-time) \u00B7 Original (first record) \u00B7 Accurate (verified correct)">ALCOA+ Ready: who, what, when \u2014 tamper-evident</div>' +
            '</div>' +
            '<span class="upcoming-item__status">\u2705</span>' +
          '</div>';
      } else {
        part11El.innerHTML = '<p class="timeline-empty">Part 11 creates a compliance-ready evidence record of every agent action. Full Part 11 compliance requires identity verification (Pro tier). Enable it in Settings \u2192 Compliance if you need compliance-grade audit trails.</p>';
      }
    }
  }

  // ── Run Detail Drawer ──────────────────────────────────────────────────
  function setupRunDrawer() {
    const closeBtn = document.getElementById('drawerClose');
    if (closeBtn) closeBtn.addEventListener('click', closeRunDrawer);
    const overlay = document.getElementById('runOverlay');
    if (overlay) overlay.addEventListener('click', closeRunDrawer);
  }

  function openRunDrawer(a) {
    const emoji = constants.APP_EMOJI[a.app_id] || '\uD83D\uDCC4';
    const titleEl = document.getElementById('drawerTitle');
    if (titleEl) titleEl.textContent = emoji + ' ' + (a.app_name || a.app_id);
    const body = document.getElementById('drawerBody');
    const fields = [
      { label: 'Status',   val: (constants.STATUS_EMOJI[a.status] || '') + ' ' + utils.escapeHtml((a.status || '').replace(/_/g,' ')) },
      { label: 'Time',     val: utils.escapeHtml(utils.formatTime(a.started_at)) },
      { label: 'Duration', val: utils.formatDuration(a.duration_ms) },
      { label: 'Cost',     val: a.cost_usd ? '$' + Number(a.cost_usd).toFixed(6) : '\u2014' },
      { label: 'Tokens',   val: a.tokens_used ? Number(a.tokens_used).toLocaleString() : '\u2014' },
      { label: 'Safety',   val: 'Tier ' + utils.escapeHtml(a.safety_tier || 'A') },
      { label: 'Scopes',   val: utils.escapeHtml((a.scopes_used || []).join(', ') || '\u2014') },
      { label: 'Agent output', val: '<div style="background:var(--sched-surface,#1e293b);border:1px solid var(--sched-border,#334155);border-radius:6px;padding:8px 10px;font-size:0.85rem">' + utils.escapeHtml(a.output_summary || '\u2014') + '</div>' },
    ];
    if (a.evidence_hash) {
      fields.push({ label: 'Evidence Hash', val: '<span class="drawer-hash">' + utils.escapeHtml(a.evidence_hash) + '</span>' });
    }
    if ((a.cross_app_triggers || []).length) {
      fields.push({ label: 'Triggers', val: utils.escapeHtml(a.cross_app_triggers.join(' \u2192 ')) });
    }
    if (a.screenshot_url || a.screenshot_path) {
      const imgSrc = a.screenshot_url || a.screenshot_path;
      fields.push({ label: 'Screenshot', val: '<img src="' + utils.escapeHtml(imgSrc) + '" alt="Evidence screenshot" class="drawer-screenshot" loading="lazy">' });
    }
    if (a._demo) {
      fields.push({ label: 'Note', val: '\u2728 Preview \u2014 your real evidence will appear here after your first run' });
    }
    body.innerHTML = fields.map(function (f) {
      return '<div class="drawer-field">' +
        '<div class="drawer-field__label">' + f.label + '</div>' +
        '<div class="drawer-field__val">' + f.val + '</div>' +
      '</div>';
    }).join('');
    const drawer = document.getElementById('runDrawer');
    drawer.style.display = 'flex';
    document.getElementById('runOverlay').style.display = '';
    fn.trapFocus(drawer);
  }

  function closeRunDrawer() {
    document.getElementById('runDrawer').style.display = 'none';
    document.getElementById('runOverlay').style.display = 'none';
    fn.releaseFocusTrap();
  }

  // ── Sync Banner ─────────────────────────────────────────────────────────
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
      banner.innerHTML = '\uD83D\uDCE1 <strong>Offline</strong> \u2014 changes will sync when back online' +
        (state.cloudStatus.offline_queue_count > 0 ? ' (' + state.cloudStatus.offline_queue_count + ' pending)' : '');
    } else if (state.cloudStatus.connected) {
      banner.className = 'sync-banner sync-banner--connected';
      const tier = VALID_TIERS[state.cloudStatus.tier] || 'Free';
      banner.innerHTML = '\u2601\uFE0F Connected to solaceagi.com \u00B7 <strong>' + tier + '</strong> tier';
    } else {
      banner.className = 'sync-banner sync-banner--local';
      banner.innerHTML = '\uD83D\uDCBB Local mode \u2014 <a href="https://solaceagi.com/login" target="_blank" rel="noopener noreferrer">Connect to solaceagi.com</a> for cloud sync + eSign';
    }
  }

  // ── Export to namespace ─────────────────────────────────────────────────
  fn.updateROIPanel    = updateROIPanel;
  fn.renderHistory     = renderHistory;
  fn.renderEsign       = renderEsign;
  fn.setupRunDrawer    = setupRunDrawer;
  fn.openRunDrawer     = openRunDrawer;
  fn.closeRunDrawer    = closeRunDrawer;
  fn.renderSyncBanner  = renderSyncBanner;

})();
