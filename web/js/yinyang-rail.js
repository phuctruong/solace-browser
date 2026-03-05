/**
 * YinYang Dual Rail — Solace Browser
 * v2.0.0 | Auth: 65537
 *
 * Implements Paper 04: Yinyang Dual Rail — Browser Integration
 * v2.0: Top suggestion bar + enhanced chat + quick actions + history
 *
 * TOP SUGGEST BAR: always-visible context-aware suggestion chips
 *   Shows smart prompts based on current page/app
 *   Dismissible, remembers state per session
 *
 * Bottom rail: always-visible 36px companion bar
 *   Collapsed: ☯ Yinyang | $X.XX | Belt | N actions ── [▲]
 *   Expanded:  chat history + quick actions + input field (340px)
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
  const STORAGE_KEY_PALETTE = 'yy_palette';
  const STORAGE_KEY_HISTORY = 'yy_chat_history';
  const STORAGE_KEY_SUGGEST_HIDDEN = 'yy_suggest_hidden';
  const YY_PALETTE_COUNT = 6;
  const YY_PALETTE_NAMES = ['Cyan', 'Ocean', 'Sunset', 'Aurora', 'Fire', 'Lunar'];
  const MAX_HISTORY = 50;

  let _rail = null;
  let _suggestBar = null;
  let _expanded = localStorage.getItem(STORAGE_KEY_EXPANDED) === 'true';
  let _sending = false;

  // ─── Context-aware suggestions per page ────────────────────
  const PAGE_SUGGESTIONS = {
    '/': [
      { icon: '📬', text: 'Run Gmail Triage', action: 'Run my Gmail Inbox Triage app' },
      { icon: '📊', text: 'Check schedule', action: 'What tasks are scheduled for today?' },
      { icon: '🔍', text: 'Search apps', action: 'What apps are available for email management?' },
      { icon: '💡', text: 'Getting started', action: 'How do I get started with Solace Browser?' },
    ],
    '/home': [
      { icon: '📬', text: 'Run Gmail Triage', action: 'Run my Gmail Inbox Triage app' },
      { icon: '📊', text: 'Check schedule', action: 'What tasks are scheduled for today?' },
      { icon: '🧹', text: 'Clean spam', action: 'Run Gmail Spam Cleaner to delete spam' },
      { icon: '💡', text: 'Quick tips', action: 'Give me a productivity tip' },
    ],
    '/start': [
      { icon: '🚀', text: 'Quick setup', action: 'Help me set up my first app' },
      { icon: '🔗', text: 'Link Gmail', action: 'How do I connect my Google account?' },
      { icon: '📱', text: 'Link LinkedIn', action: 'How do I link my LinkedIn account?' },
      { icon: '❓', text: 'What can you do?', action: 'What can Solace Browser do for me?' },
    ],
    '/app-store': [
      { icon: '📧', text: 'Best for email', action: 'Which apps help with email management?' },
      { icon: '📈', text: 'Marketing apps', action: 'Show me apps for marketing and social media' },
      { icon: '🔒', text: 'Privacy & safety', action: 'How does Solace keep my data safe?' },
      { icon: '💰', text: 'Cost per app', action: 'How much does it cost to run each app?' },
    ],
    '/apps': [
      { icon: '📧', text: 'Best for email', action: 'Which apps help with email management?' },
      { icon: '📈', text: 'Marketing apps', action: 'Show me apps for marketing and social media' },
      { icon: '🔒', text: 'Privacy & safety', action: 'How does Solace keep my data safe?' },
      { icon: '💰', text: 'Cost per app', action: 'How much does it cost to run each app?' },
    ],
    '/app-detail': [
      { icon: '▶️', text: 'Run this app', action: 'Run the currently selected app' },
      { icon: '📋', text: 'View recipe', action: 'Show me the recipe steps for this app' },
      { icon: '💰', text: 'Cost estimate', action: 'How much will it cost to run this app?' },
      { icon: '📊', text: 'Past runs', action: 'Show my recent run history for this app' },
    ],
    '/schedule': [
      { icon: '➕', text: 'Add schedule', action: 'How do I schedule an app to run automatically?' },
      { icon: '📅', text: 'Today\'s tasks', action: 'What is scheduled for today?' },
      { icon: '⏸️', text: 'Pause all', action: 'How do I pause all scheduled tasks?' },
    ],
    '/settings': [
      { icon: '🔑', text: 'API keys', action: 'How do I configure my API key?' },
      { icon: '🌍', text: 'Change language', action: 'How do I change the language?' },
      { icon: '🔒', text: 'Privacy settings', action: 'What privacy settings are available?' },
      { icon: '💾', text: 'Export data', action: 'How do I export my data and evidence?' },
    ],
    '/guide': [
      { icon: '1️⃣', text: 'First steps', action: 'Walk me through setting up Solace step by step' },
      { icon: '📧', text: 'Gmail setup', action: 'How do I connect Gmail and run my first triage?' },
      { icon: '🔗', text: 'LinkedIn setup', action: 'How do I connect LinkedIn?' },
    ],
  };

  const QUICK_ACTIONS = [
    { icon: '📬', label: 'Gmail Triage', msg: 'Run my Gmail Inbox Triage app now' },
    { icon: '🧹', label: 'Clean Spam', msg: 'Run Gmail Spam Cleaner' },
    { icon: '📊', label: 'My Schedule', msg: 'Show my scheduled tasks' },
    { icon: '💡', label: 'Tip', msg: 'Give me a productivity tip for today' },
    { icon: '😄', label: 'Joke', msg: 'Tell me a tech joke' },
  ];

  // ─── Bottom rail ──────────────────────────────────────────────
  function _getStats() {
    return {
      credits: parseFloat(localStorage.getItem(STORAGE_KEY_CREDITS) || '0').toFixed(2),
      belt: localStorage.getItem(STORAGE_KEY_BELT) || 'White Belt',
      actions: parseInt(localStorage.getItem(STORAGE_KEY_ACTIONS) || '0', 10),
    };
  }

  // ─── Chat history persistence ────────────────────────────
  function _saveHistory() {
    if (!_rail) return;
    const msgs = _rail.querySelectorAll('.yy-msg');
    const history = [];
    msgs.forEach(m => {
      if (m.classList.contains('yy-msg--typing')) return;
      history.push({
        role: m.classList.contains('yy-msg--user') ? 'user' : 'assistant',
        text: m.textContent,
        time: m.querySelector('.yy-msg__time') ? m.querySelector('.yy-msg__time').textContent : '',
      });
    });
    // Keep last MAX_HISTORY messages
    const trimmed = history.slice(-MAX_HISTORY);
    try { localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(trimmed)); } catch(e) { /* quota */ }
  }

  function _loadHistory(body) {
    try {
      const raw = localStorage.getItem(STORAGE_KEY_HISTORY);
      if (!raw) return;
      const history = JSON.parse(raw);
      history.forEach(h => {
        const msg = document.createElement('div');
        msg.className = `yy-msg yy-msg--${h.role}`;
        msg.innerHTML = _formatMessage(h.text);
        if (h.time && h.role === 'assistant') {
          const timeEl = document.createElement('span');
          timeEl.className = 'yy-msg__time';
          timeEl.textContent = h.time;
          msg.appendChild(timeEl);
        }
        body.appendChild(msg);
      });
      body.scrollTop = body.scrollHeight;
    } catch(e) { /* corrupt */ }
  }

  // ─── Simple markdown rendering ─────────────────────────────
  function _formatMessage(text) {
    return text
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  // ─── Top suggestion bar ────────────────────────────────────
  function _buildSuggestBar() {
    if (sessionStorage.getItem(STORAGE_KEY_SUGGEST_HIDDEN) === '1') return null;

    const path = window.location.pathname.replace(/\/$/, '') || '/';
    const suggestions = PAGE_SUGGESTIONS[path] || PAGE_SUGGESTIONS['/'];

    const bar = document.createElement('div');
    bar.id = 'yySuggestBar';
    bar.className = 'yy-suggest-bar';
    bar.innerHTML = `
      <img class="yy-suggest-bar__logo" src="/images/yinyang/yinyang-logo-32.png" alt="" width="22" height="22">
      <span class="yy-suggest-bar__label">YinYang</span>
      <div class="yy-suggest-bar__chips" id="yySuggestChips"></div>
      <button class="yy-suggest-bar__dismiss" id="yySuggestDismiss" title="Hide suggestions" aria-label="Hide suggestions">&times;</button>
    `;

    const chips = bar.querySelector('#yySuggestChips');
    suggestions.forEach(s => {
      const chip = document.createElement('button');
      chip.className = 'yy-chip';
      chip.innerHTML = `<span class="yy-chip__icon">${s.icon}</span> ${s.text}`;
      chip.addEventListener('click', () => {
        // Open chat and send the suggestion
        if (!_expanded) _toggle();
        setTimeout(() => {
          const input = _rail.querySelector('#yyInput');
          if (input) { input.value = s.action; _sendMessage(); }
        }, 100);
      });
      chips.appendChild(chip);
    });

    bar.querySelector('#yySuggestDismiss').addEventListener('click', () => {
      bar.classList.add('is-hidden');
      document.body.classList.remove('yy-suggest-active');
      sessionStorage.setItem(STORAGE_KEY_SUGGEST_HIDDEN, '1');
    });

    return bar;
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
      <div class="yy-quick-actions" id="yyQuickActions"></div>
      <div class="yy-bottom-rail__input" id="yyRailInput">
        <img class="yy-input-logo" src="/images/yinyang/yinyang-logo-32.png" alt="" width="22" height="22" aria-hidden="true">
        <input type="text" id="yyInput" placeholder="Ask Yinyang anything&#8230;" autocomplete="off" spellcheck="false"
               aria-label="Message Yinyang">
        <button id="yySend" aria-label="Send message">Ask</button>
      </div>
    `;

    // Build quick action buttons
    const qContainer = el.querySelector('#yyQuickActions');
    QUICK_ACTIONS.forEach(qa => {
      const btn = document.createElement('button');
      btn.className = 'yy-quick-btn';
      btn.innerHTML = `${qa.icon} ${qa.label}`;
      btn.addEventListener('click', () => {
        const input = el.querySelector('#yyInput');
        if (input) { input.value = qa.msg; _sendMessage(); }
      });
      qContainer.appendChild(btn);
    });

    // Load chat history into body
    const body = el.querySelector('#yyRailBody');
    _loadHistory(body);

    // Show/hide body + input based on initial state
    _applyExpandState(el);

    return el;
  }

  function _applyExpandState(el) {
    const body = el.querySelector('#yyRailBody');
    const input = el.querySelector('#yyRailInput');
    const quick = el.querySelector('#yyQuickActions');
    const icon = el.querySelector('#yyToggleIcon');
    const header = el.querySelector('#yyRailHeader');
    if (_expanded) {
      el.classList.add('is-expanded');
      body.style.display = '';
      input.style.display = '';
      if (quick) quick.style.display = '';
      if (icon) icon.innerHTML = '&#9660;';
      if (header) header.setAttribute('aria-expanded', 'true');
    } else {
      el.classList.remove('is-expanded');
      body.style.display = 'none';
      input.style.display = 'none';
      if (quick) quick.style.display = 'none';
      if (icon) icon.innerHTML = '&#9650;';
      if (header) header.setAttribute('aria-expanded', 'false');
    }
  }

  // ─── Palette ──────────────────────────────────────────────────
  function _applyPalette(idx) {
    if (!_rail) return;
    _rail.querySelectorAll('.yy-logo-img, .yy-input-logo').forEach(img => {
      img.setAttribute('data-palette', String(idx));
    });
  }

  function _spinLogos() {
    if (!_rail) return;
    _rail.querySelectorAll('.yy-logo-img, .yy-input-logo').forEach(img => {
      img.classList.remove('is-spinning');
      void img.offsetWidth; // force reflow so animation restarts
      img.classList.add('is-spinning');
      img.addEventListener('animationend', () => img.classList.remove('is-spinning'), { once: true });
    });
  }

  function _cyclePalette() {
    const cur = parseInt(localStorage.getItem(STORAGE_KEY_PALETTE) || '0', 10);
    const next = (cur + 1) % YY_PALETTE_COUNT;
    localStorage.setItem(STORAGE_KEY_PALETTE, next);
    _applyPalette(next);
    return next;
  }

  function _toggle() {
    _expanded = !_expanded;
    localStorage.setItem(STORAGE_KEY_EXPANDED, _expanded);
    _applyExpandState(_rail);
    if (_expanded) {
      _cyclePalette();
      _spinLogos();
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
    if (role === 'assistant') {
      msg.innerHTML = _formatMessage(text);
      const ts = document.createElement('span');
      ts.className = 'yy-msg__time';
      ts.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      msg.appendChild(ts);
    } else {
      msg.textContent = text;
    }
    body.appendChild(msg);
    body.scrollTop = body.scrollHeight;
    _saveHistory();
  }

  function _showTyping() {
    const body = _rail.querySelector('#yyRailBody');
    if (!body) return;
    const dot = document.createElement('div');
    dot.className = 'yy-msg yy-msg--assistant yy-msg--typing';
    dot.innerHTML = '<div class="yy-typing-dots"><span></span><span></span><span></span></div>';
    body.appendChild(dot);
    body.scrollTop = body.scrollHeight;
  }

  function _removeTyping() {
    const body = _rail.querySelector('#yyRailBody');
    if (!body) return;
    const dot = body.querySelector('.yy-msg--typing');
    if (dot) dot.remove();
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
    _showTyping();

    try {
      const res = await fetch('/api/yinyang/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          context: {
            page: window.location.pathname,
            page_title: document.title,
            current_app: document.querySelector('[data-app-id]')?.dataset?.appId || '',
            url: window.location.href,
            credits: localStorage.getItem(STORAGE_KEY_CREDITS) || '0',
            belt: localStorage.getItem(STORAGE_KEY_BELT) || 'White',
            locale: localStorage.getItem('sb_locale') || 'en',
            installed_apps: parseInt(localStorage.getItem('sb_installed_count') || '0', 10),
          },
        }),
      });

      _removeTyping();

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
      _removeTyping();
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

    // Build and inject top suggestion bar
    _suggestBar = _buildSuggestBar();
    if (_suggestBar) {
      document.body.prepend(_suggestBar);
      document.body.classList.add('yy-suggest-active');
    }

    _rail = _buildRail();
    document.body.appendChild(_rail);

    // Restore saved palette
    const savedPalette = parseInt(localStorage.getItem(STORAGE_KEY_PALETTE) || '0', 10);
    _applyPalette(savedPalette);

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
