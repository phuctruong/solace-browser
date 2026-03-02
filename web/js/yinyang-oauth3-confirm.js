/**
 * YinYang OAuth3 Confirmation Dialog — Solace Browser
 * v1.0.0 | Auth: 65537
 *
 * Intercepts navigation to solaceagi.com/auth/* and any OAuth3 redirect.
 * Shows a confirmation popup with:
 *   - Scopes being requested
 *   - Current budget remaining
 *   - 3 benefits of OAuth3 (time-bounded, revocable, audited)
 *   - Budget adjustment inline
 *   - Proceed / Cancel / Adjust Budget buttons
 *   - 15-second countdown then auto-cancels (fail-closed)
 *
 * Standard: Paper 09 — YinYang Tutorial + Fun Pack + MCP (Auth: 65537)
 */

const YinyangOAuth3Confirm = (() => {
  'use strict';

  const YY_GIF = '/images/yinyang/yinyang-loading-128.gif';
  const COUNTDOWN_SECONDS = 15;

  // Patterns that trigger the confirmation dialog
  const TRIGGER_PATTERNS = [
    /solaceagi\.com\/auth\//,
    /\/auth\/login/,
    /\/auth\/browser-register/,
    /oauth.*redirect/i,
  ];

  // Default English strings
  const STRINGS = {
    title: 'OAuth3 Authorization &#128274;',
    subtitle: "You're about to leave Solace Browser to authorize an app.",
    scope_label: 'Requesting scopes:',
    budget_label: 'Current budget:',
    benefits_title: 'Why OAuth3 is safe:',
    benefits: [
      '&#9201; Time-bounded — token expires automatically',
      '&#128683; Revocable — cancel any time from Settings',
      '&#128203; Evidence-sealed — every action audit-logged',
    ],
    btn_proceed: 'Proceed',
    btn_cancel: 'Cancel',
    btn_adjust: 'Adjust Budget',
    countdown: 'Auto-cancels in {seconds}s',
    budget_adjust_label: 'New budget ($):',
    budget_save: 'Save & Proceed',
  };

  let _overlay = null;
  let _countdownTimer = null;
  let _pendingHref = null;
  let _countdownLeft = COUNTDOWN_SECONDS;
  let _resolveCallback = null;

  // ---------------------------------------------------------------------------
  // Fetch current budget from server
  // ---------------------------------------------------------------------------
  async function _getBudget() {
    try {
      const resp = await fetch('/api/budget', { signal: AbortSignal.timeout(2000) });
      if (resp.ok) {
        const data = await resp.json();
        return data.remaining_usd !== undefined ? `$${data.remaining_usd.toFixed(2)}` : 'Unlimited';
      }
    } catch (_) {}
    return 'Not set';
  }

  // ---------------------------------------------------------------------------
  // Parse scopes from URL query param
  // ---------------------------------------------------------------------------
  function _parseScopes(href) {
    try {
      const url = new URL(href, window.location.origin);
      const scopes = url.searchParams.get('scopes') || url.searchParams.get('scope') || '';
      if (!scopes) return ['browser.navigate', 'browser.screenshot']; // defaults
      return scopes.split(/[,\s]+/).filter(Boolean);
    } catch (_) {
      return ['browser.navigate'];
    }
  }

  // ---------------------------------------------------------------------------
  // Build overlay DOM
  // ---------------------------------------------------------------------------
  async function _buildOverlay(href, budget) {
    const scopes = _parseScopes(href);
    const scopeItems = scopes.map(s => `<span class="yyO3-scope-chip">${s}</span>`).join(' ');
    const benefitItems = STRINGS.benefits.map(b => `<li>${b}</li>`).join('');

    const div = document.createElement('div');
    div.id = 'yyOAuth3Confirm';
    div.className = 'yyO3-overlay';
    div.setAttribute('role', 'alertdialog');
    div.setAttribute('aria-modal', 'true');
    div.setAttribute('aria-label', 'OAuth3 Authorization Confirmation');

    div.innerHTML = `
      <div class="yyO3-card">
        <div class="yyO3-header">
          <img class="yyO3-gif" src="${YY_GIF}" alt="Yinyang" width="48" height="48">
          <h2 class="yyO3-title">${STRINGS.title}</h2>
        </div>
        <p class="yyO3-subtitle">${STRINGS.subtitle}</p>

        <div class="yyO3-section">
          <div class="yyO3-label">${STRINGS.scope_label}</div>
          <div class="yyO3-scopes">${scopeItems}</div>
        </div>

        <div class="yyO3-section">
          <div class="yyO3-label">${STRINGS.budget_label} <strong class="yyO3-budget-val">${budget}</strong></div>
        </div>

        <div class="yyO3-section">
          <div class="yyO3-label">${STRINGS.benefits_title}</div>
          <ul class="yyO3-benefits">${benefitItems}</ul>
        </div>

        <div class="yyO3-budget-adjust" id="yyO3-adjust-panel" style="display:none">
          <label class="yyO3-label">${STRINGS.budget_adjust_label}</label>
          <div class="yyO3-adjust-row">
            <input type="number" class="yyO3-input" id="yyO3-budget-input" min="0.01" step="0.01" value="5.00">
            <button class="yyO3-btn yyO3-btn--primary" id="yyO3-save-budget">${STRINGS.budget_save}</button>
          </div>
        </div>

        <div class="yyO3-btns">
          <button class="yyO3-btn yyO3-btn--ghost" id="yyO3-cancel">${STRINGS.btn_cancel}</button>
          <button class="yyO3-btn yyO3-btn--outline" id="yyO3-adjust">${STRINGS.btn_adjust}</button>
          <button class="yyO3-btn yyO3-btn--primary" id="yyO3-proceed">
            ${STRINGS.btn_proceed} <span class="yyO3-countdown" id="yyO3-countdown"></span>
          </button>
        </div>
      </div>
    `;

    return div;
  }

  // ---------------------------------------------------------------------------
  // Start countdown (15s → auto-cancel)
  // ---------------------------------------------------------------------------
  function _startCountdown() {
    _countdownLeft = COUNTDOWN_SECONDS;
    _updateCountdown();
    _countdownTimer = setInterval(() => {
      _countdownLeft--;
      _updateCountdown();
      if (_countdownLeft <= 0) {
        _cancel();
      }
    }, 1000);
  }

  function _updateCountdown() {
    const el = document.getElementById('yyO3-countdown');
    if (el) {
      el.textContent = ` (${_countdownLeft}s)`;
      if (_countdownLeft <= 5) el.style.color = 'var(--sb-danger)';
    }
  }

  function _stopCountdown() {
    if (_countdownTimer) {
      clearInterval(_countdownTimer);
      _countdownTimer = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  function _cancel() {
    _stopCountdown();
    _close();
    if (_resolveCallback) _resolveCallback(false);
  }

  function _proceed() {
    _stopCountdown();
    _close();
    if (_resolveCallback) _resolveCallback(true);
  }

  function _close() {
    if (_overlay) {
      _overlay.classList.add('yyO3-overlay--exit');
      setTimeout(() => {
        if (_overlay && _overlay.parentNode) {
          _overlay.parentNode.removeChild(_overlay);
        }
        _overlay = null;
      }, 250);
    }
  }

  // ---------------------------------------------------------------------------
  // Public: show confirmation dialog
  // Returns Promise<boolean> — true = proceed, false = cancelled
  // ---------------------------------------------------------------------------
  async function confirm(href, options = {}) {
    const budget = options.budget || (await _getBudget());
    _pendingHref = href;

    _overlay = await _buildOverlay(href, budget);
    document.body.appendChild(_overlay);
    requestAnimationFrame(() => _overlay.classList.add('yyO3-overlay--visible'));

    // Wire buttons
    document.getElementById('yyO3-proceed').addEventListener('click', _proceed);
    document.getElementById('yyO3-cancel').addEventListener('click', _cancel);
    document.getElementById('yyO3-adjust').addEventListener('click', () => {
      const panel = document.getElementById('yyO3-adjust-panel');
      if (panel) panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
      _stopCountdown(); // pause countdown while adjusting budget
      const countdown = document.getElementById('yyO3-countdown');
      if (countdown) countdown.textContent = '';
    });
    document.getElementById('yyO3-save-budget').addEventListener('click', async () => {
      const input = document.getElementById('yyO3-budget-input');
      const newBudget = parseFloat(input.value);
      if (!isNaN(newBudget) && newBudget > 0) {
        try {
          await fetch('/api/budget', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ budget_usd: newBudget }),
          });
        } catch (_) {}
      }
      _proceed();
    });

    // Keyboard
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') _cancel();
      if (e.key === 'Enter') _proceed();
    }, { once: true });

    _startCountdown();

    return new Promise((resolve) => {
      _resolveCallback = resolve;
    });
  }

  // ---------------------------------------------------------------------------
  // Auto-intercept: patch window.location navigation
  // ---------------------------------------------------------------------------
  function intercept() {
    // Intercept <a> clicks that match trigger patterns
    document.addEventListener('click', async (e) => {
      const anchor = e.target.closest('a[href]');
      if (!anchor) return;
      const href = anchor.href;
      if (!href) return;
      if (!TRIGGER_PATTERNS.some(p => p.test(href))) return;

      e.preventDefault();
      e.stopPropagation();

      const proceed = await confirm(href);
      if (proceed) {
        window.location.href = href;
      }
    }, { capture: true });
  }

  return { confirm, intercept };
})();

// Auto-intercept on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', YinyangOAuth3Confirm.intercept);
} else {
  YinyangOAuth3Confirm.intercept();
}
