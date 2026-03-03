/**
 * YinYang Dual Rail — Solace Browser
 * v1.0.0 | Auth: 65537
 *
 * Implements Paper 04: Yinyang Dual Rail — Browser Integration
 *
 * Bottom rail: always-visible 36px companion bar
 *   Collapsed: ☯ Yinyang | $X.XX | Belt | N actions ── [▲]
 *   Expanded:  chat history + input field (300px)
 *   Shortcut:  Ctrl+Y toggle, Ctrl+Shift+Y focus, Escape collapse
 *
 * Top rail: shown only during automation execution
 *   Injected via FSM state updates from solace_browser_server.py
 *   Hidden during idle browsing
 *
 * Chat: POST /api/yinyang/chat (server.py, OpenRouter backend)
 */

/* global YinyangDelight */

const YinyangRail = (() => {
  'use strict';

  const STORAGE_KEY_EXPANDED = 'yy_rail_expanded';
  const STORAGE_KEY_BELT = 'yy_belt';
  const STORAGE_KEY_CREDITS = 'yy_credits';
  const STORAGE_KEY_ACTIONS = 'yy_actions';

  let _rail = null;
  let _expanded = localStorage.getItem(STORAGE_KEY_EXPANDED) === 'true';
  let _sending = false;

  // ─── Bottom rail ──────────────────────────────────────────────
  function _getStats() {
    return {
      credits: parseFloat(localStorage.getItem(STORAGE_KEY_CREDITS) || '0').toFixed(2),
      belt: localStorage.getItem(STORAGE_KEY_BELT) || 'White Belt',
      actions: parseInt(localStorage.getItem(STORAGE_KEY_ACTIONS) || '0', 10),
    };
  }

  function _buildRail() {
    const el = document.createElement('div');
    el.id = 'yyRail';
    el.className = 'yy-bottom-rail' + (_expanded ? ' is-expanded' : '');
    el.setAttribute('role', 'complementary');
    el.setAttribute('aria-label', 'Yinyang Assistant');

    const s = _getStats();
    const creditsClass = parseFloat(s.credits) < 0.5 ? ' yy-bottom-rail__credits--low' : '';

    el.innerHTML = `
      <div class="yy-bottom-rail__header" id="yyRailHeader" tabindex="0" role="button"
           aria-expanded="${_expanded}" aria-controls="yyRailBody">
        <div class="yy-bottom-rail__credits${creditsClass}">
          <img class="yy-logo-img" src="/images/yinyang/yinyang-logo-32.png" alt="Yinyang" width="20" height="20">
          <span class="yy-name">Yinyang</span>
          <span id="yyCredits">$${s.credits}</span>
          <span id="yyBelt">${s.belt}</span>
          <span id="yyActions">${s.actions} actions</span>
        </div>
        <span id="yyToggleIcon" aria-hidden="true">${_expanded ? '&#9660;' : '&#9650;'}</span>
      </div>
      <div class="yy-bottom-rail__body" id="yyRailBody" aria-live="polite"></div>
      <div class="yy-bottom-rail__input" id="yyRailInput">
        <img class="yy-input-logo" src="/images/yinyang/yinyang-logo-32.png" alt="" width="22" height="22" aria-hidden="true">
        <input type="text" id="yyInput" placeholder="Ask Yinyang anything&#8230;" autocomplete="off" spellcheck="false"
               aria-label="Message Yinyang">
        <button id="yySend" aria-label="Send message">Ask</button>
      </div>
    `;

    // Show/hide body + input based on initial state
    _applyExpandState(el);

    return el;
  }

  function _applyExpandState(el) {
    const body = el.querySelector('#yyRailBody');
    const input = el.querySelector('#yyRailInput');
    const icon = el.querySelector('#yyToggleIcon');
    const header = el.querySelector('#yyRailHeader');
    if (_expanded) {
      el.classList.add('is-expanded');
      body.style.display = '';
      input.style.display = '';
      if (icon) icon.innerHTML = '&#9660;';
      if (header) header.setAttribute('aria-expanded', 'true');
    } else {
      el.classList.remove('is-expanded');
      body.style.display = 'none';
      input.style.display = 'none';
      if (icon) icon.innerHTML = '&#9650;';
      if (header) header.setAttribute('aria-expanded', 'false');
    }
  }

  function _toggle() {
    _expanded = !_expanded;
    localStorage.setItem(STORAGE_KEY_EXPANDED, _expanded);
    _applyExpandState(_rail);
    if (_expanded) {
      setTimeout(() => _rail.querySelector('#yyInput').focus(), 50);
    }
  }

  function _collapse() {
    if (_expanded) _toggle();
  }

  // ─── Stats refresh ────────────────────────────────────────────
  function _refreshStats() {
    if (!_rail) return;
    const s = _getStats();
    const creditsEl = _rail.querySelector('#yyCredits');
    const beltEl = _rail.querySelector('#yyBelt');
    const actionsEl = _rail.querySelector('#yyActions');
    const creditsDiv = _rail.querySelector('.yy-bottom-rail__credits');
    if (creditsEl) creditsEl.textContent = `$${s.credits}`;
    if (beltEl) beltEl.textContent = s.belt;
    if (actionsEl) actionsEl.textContent = `${s.actions} actions`;
    if (creditsDiv) {
      if (parseFloat(s.credits) < 0.5) creditsDiv.classList.add('yy-bottom-rail__credits--low');
      else creditsDiv.classList.remove('yy-bottom-rail__credits--low');
    }
  }

  // ─── Chat ─────────────────────────────────────────────────────
  function _appendMsg(text, role) {
    const body = _rail.querySelector('#yyRailBody');
    if (!body) return;
    const msg = document.createElement('div');
    msg.className = `yy-msg yy-msg--${role}`;
    msg.textContent = text;
    body.appendChild(msg);
    body.scrollTop = body.scrollHeight;
  }

  async function _sendMessage() {
    const input = _rail.querySelector('#yyInput');
    const btn = _rail.querySelector('#yySend');
    const text = input.value.trim();
    if (!text || _sending) return;

    _sending = true;
    input.value = '';
    btn.disabled = true;
    btn.textContent = '...';

    _appendMsg(text, 'user');

    try {
      const res = await fetch('/api/yinyang/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          context: {
            page: window.location.pathname,
            credits: localStorage.getItem(STORAGE_KEY_CREDITS) || '0',
            belt: localStorage.getItem(STORAGE_KEY_BELT) || 'White',
            locale: localStorage.getItem('sb_locale') || 'en',
          },
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const msg = err.error || err.hint || `Error ${res.status}`;
        _appendMsg(`⚠️ ${msg}`, 'assistant');
      } else {
        const data = await res.json();
        const reply = data.reply || data.message || data.content || '(no response)';
        _appendMsg(reply, 'assistant');
        // Update actions counter
        const count = parseInt(localStorage.getItem(STORAGE_KEY_ACTIONS) || '0', 10) + 1;
        localStorage.setItem(STORAGE_KEY_ACTIONS, count);
        _refreshStats();
        // Delight on first message
        if (count === 1 && typeof YinyangDelight !== 'undefined') {
          YinyangDelight.celebrate('first_chat');
        }
      }
    } catch (err) {
      _appendMsg(`⚠️ ${err.message || 'Network error'}`, 'assistant');
    } finally {
      _sending = false;
      btn.disabled = false;
      btn.innerHTML = '&#9775; Ask';
    }
  }

  // ─── Top rail ─────────────────────────────────────────────────
  // Top rail is managed by Playwright injection during execution.
  // These helpers let server-side code update it via postMessage.
  function _applyTopRailState(state, step, cost) {
    let topRail = document.getElementById('yyTopRail');
    if (!topRail) {
      topRail = document.createElement('div');
      topRail.id = 'yyTopRail';
      topRail.className = 'yy-top-rail';
      topRail.innerHTML = `
        <div class="yy-top-rail__state">
          <span class="yy-top-rail__dot" id="yyTopDot"></span>
          <span id="yyTopState"></span>
          <span id="yyTopStep" style="margin-left:12px;opacity:0.7"></span>
          <span id="yyTopCost" style="margin-left:auto;opacity:0.7"></span>
        </div>`;
      document.body.prepend(topRail);
      // Offset body so rail doesn't overlap content
      document.body.style.paddingTop = '32px';
    }

    const dot = topRail.querySelector('#yyTopDot');
    const stateEl = topRail.querySelector('#yyTopState');
    const stepEl = topRail.querySelector('#yyTopStep');
    const costEl = topRail.querySelector('#yyTopCost');

    // Map state → CSS class
    const dotClass = { idle: '--idle', processing: '--processing', error: '--error', blocked: '--blocked', done: '--idle' }[state] || '--idle';
    dot.className = `yy-top-rail__dot yy-top-rail__dot${dotClass}`;
    stateEl.textContent = state.toUpperCase();
    if (step) stepEl.textContent = step;
    if (cost) costEl.textContent = `$${cost}`;

    if (state === 'idle' || state === 'done') {
      setTimeout(() => {
        if (topRail && topRail.parentNode) topRail.parentNode.removeChild(topRail);
        document.body.style.paddingTop = '';
      }, 5000);
    }
  }

  // ─── Public API ───────────────────────────────────────────────
  function init() {
    if (document.getElementById('yyRail')) return; // already injected
    _rail = _buildRail();
    document.body.appendChild(_rail);

    // Adjust page bottom margin so content isn't hidden behind the rail
    document.body.style.paddingBottom = '44px';

    // Header toggle
    _rail.querySelector('#yyRailHeader').addEventListener('click', _toggle);
    _rail.querySelector('#yyRailHeader').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); _toggle(); }
    });

    // Send button
    _rail.querySelector('#yySend').addEventListener('click', _sendMessage);
    _rail.querySelector('#yyInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); _sendMessage(); }
    });

    // Keyboard shortcuts (Paper 04 §3)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'Y') {
        e.preventDefault();
        if (!_expanded) _toggle();
        _rail.querySelector('#yyInput').focus();
      } else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key === 'y') {
        e.preventDefault();
        _toggle();
      } else if (e.key === 'Escape' && _expanded) {
        _collapse();
      }
    });

    // Listen for FSM state messages from Playwright/server
    window.addEventListener('message', (e) => {
      if (e.data && e.data.type === 'yy_state') {
        _applyTopRailState(e.data.state, e.data.step, e.data.cost);
        // Auto-expand bottom rail on approval-requiring states
        if (['preview_ready', 'blocked', 'error'].includes(e.data.state) && !_expanded) {
          _toggle();
        }
      }
      if (e.data && e.data.type === 'yy_stats') {
        if (e.data.credits !== undefined) localStorage.setItem(STORAGE_KEY_CREDITS, e.data.credits);
        if (e.data.belt) localStorage.setItem(STORAGE_KEY_BELT, e.data.belt);
        if (e.data.actions !== undefined) localStorage.setItem(STORAGE_KEY_ACTIONS, e.data.actions);
        _refreshStats();
      }
    });

    // Greet on first ever page load
    const firstLoad = !localStorage.getItem('yy_greeted');
    if (firstLoad) {
      localStorage.setItem('yy_greeted', '1');
      setTimeout(() => {
        if (!_expanded) return; // only if user already opened
        _appendMsg("☯ Hi! I'm Yinyang. Ask me anything about your browser, apps, or settings.", 'assistant');
      }, 2000);
    }
  }

  /**
   * Push a notification message to the bottom rail.
   * Called by agent notification API or Playwright injection.
   */
  function notify(message, autoExpand) {
    if (!_rail) return;
    _appendMsg(message, 'assistant');
    if (autoExpand && !_expanded) _toggle();
  }

  /**
   * Update FSM state from external source.
   */
  function setState(state, step, cost) {
    _applyTopRailState(state, step, cost);
  }

  return { init, notify, setState };
})();

// Auto-init on DOM ready (all pages that include this script)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', YinyangRail.init);
} else {
  YinyangRail.init();
}

// Expose globally for Playwright injection and agent API
window.YinyangRail = YinyangRail;
