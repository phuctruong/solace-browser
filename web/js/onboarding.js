/**
 * onboarding.js — Solace Browser onboarding wizard
 *
 * Committee panel: Jony Ive (design) + Russell Brunson (funnel) +
 *   Vanessa Van Edwards (warmth) + Rory Sutherland (reframing) + Seth Godin (remarkable)
 *
 * Shows a 3-step overlay wizard when the user hasn't set up their LLM yet:
 *   Step 1: Welcome (shows if logged in, greets by name)
 *   Step 2: Choose power source — BYOK or Managed ($8/mo)
 *   Step 3: Ready! — App Store CTA
 *
 * Skipped if: localStorage.solace_llm_configured === '1'
 * Forced: add ?onboard=1 to any URL to re-show
 */

(function () {
  'use strict';

  var STORAGE_KEY = 'solace_llm_configured';
  var CLOUD = 'https://www.solaceagi.com';

  function shouldShow() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('onboard') === '1') return true;
    return !localStorage.getItem(STORAGE_KEY);
  }

  function getUser() {
    return {
      name: (localStorage.getItem('solace_user_email') || '').split('@')[0] || '',
      email: localStorage.getItem('solace_user_email') || '',
      key: localStorage.getItem('solace_api_key') || '',
    };
  }

  // ── CSS ─────────────────────────────────────────────────────────────────────
  var CSS = `
    #sbOnboard {
      position: fixed; inset: 0; z-index: 9999;
      background: rgba(2,8,18,0.88);
      backdrop-filter: blur(8px);
      display: flex; align-items: center; justify-content: center;
      padding: 24px;
      animation: sbFadeIn 0.25s ease;
    }
    @keyframes sbFadeIn { from { opacity: 0; } to { opacity: 1; } }

    #sbOnboardCard {
      background: linear-gradient(160deg, #0d1a26 0%, #081019 100%);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 20px;
      padding: 40px 44px;
      max-width: 540px;
      width: 100%;
      box-shadow: 0 32px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(0,200,150,0.08);
      position: relative;
    }

    #sbOnboardCard .ob-logo {
      display: block; margin: 0 auto 20px;
      width: 64px; height: 64px; border-radius: 50%;
      box-shadow: 0 0 24px rgba(0,200,150,0.25);
    }

    #sbOnboardCard h2 {
      margin: 0 0 10px;
      font-size: 1.6rem; font-weight: 800;
      letter-spacing: -0.04em; line-height: 1.1;
      text-align: center; color: #fff;
    }

    #sbOnboardCard .ob-sub {
      margin: 0 0 28px;
      font-size: 0.9rem; color: rgba(255,255,255,0.5);
      text-align: center; line-height: 1.5;
    }

    /* Step dots */
    .ob-dots {
      display: flex; gap: 6px; justify-content: center; margin-bottom: 28px;
    }
    .ob-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: rgba(255,255,255,0.15);
      transition: background 0.2s, transform 0.2s;
    }
    .ob-dot.is-active { background: #00c896; transform: scale(1.25); }
    .ob-dot.is-done   { background: rgba(0,200,150,0.4); }

    /* Option cards (step 2) */
    .ob-options { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
    .ob-option {
      padding: 20px 16px; border-radius: 14px;
      border: 2px solid rgba(255,255,255,0.1);
      cursor: pointer; text-align: center;
      transition: border-color 0.2s, background 0.2s;
      background: rgba(255,255,255,0.03);
    }
    .ob-option:hover { border-color: rgba(0,200,150,0.5); background: rgba(0,200,150,0.05); }
    .ob-option.is-selected { border-color: #00c896; background: rgba(0,200,150,0.08); }
    .ob-option .ob-opt-icon { font-size: 1.8rem; margin-bottom: 8px; }
    .ob-option h3 { margin: 0 0 5px; font-size: 0.96rem; font-weight: 700; color: #fff; }
    .ob-option p  { margin: 0; font-size: 0.78rem; color: rgba(255,255,255,0.5); line-height: 1.4; }
    .ob-option .ob-opt-badge {
      display: inline-block; margin-top: 8px;
      font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
      padding: 2px 8px; border-radius: 4px;
      background: rgba(0,200,150,0.15); color: #00c896;
    }

    /* BYOK key input */
    .ob-byok { margin-bottom: 20px; display: none; }
    .ob-byok label { display: block; font-size: 0.78rem; color: rgba(255,255,255,0.5); margin-bottom: 6px; }
    .ob-byok select, .ob-byok input {
      width: 100%; padding: 10px 12px; border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.05); color: #fff;
      font-size: 0.88rem; margin-bottom: 8px; box-sizing: border-box;
    }
    .ob-byok input:focus, .ob-byok select:focus {
      outline: none; border-color: rgba(0,200,150,0.5);
    }

    /* Buttons */
    .ob-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }
    .ob-btn {
      padding: 11px 24px; border-radius: 10px; border: none;
      font-size: 0.9rem; font-weight: 700; cursor: pointer;
      transition: opacity 0.15s, transform 0.15s;
    }
    .ob-btn:hover { opacity: 0.88; transform: translateY(-1px); }
    .ob-btn--primary { background: #00c896; color: #000; }
    .ob-btn--secondary { background: rgba(255,255,255,0.07); color: rgba(255,255,255,0.7); }
    .ob-btn--ghost { background: transparent; color: rgba(255,255,255,0.35); font-size: 0.8rem; }

    /* Success state */
    .ob-success-check {
      width: 64px; height: 64px; border-radius: 50%;
      background: rgba(0,200,150,0.12); border: 2px solid #00c896;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.8rem; margin: 0 auto 20px; color: #00c896;
    }

    .ob-skip {
      position: absolute; top: 16px; right: 16px;
      background: none; border: none; color: rgba(255,255,255,0.25);
      font-size: 0.75rem; cursor: pointer; padding: 4px 8px;
    }
    .ob-skip:hover { color: rgba(255,255,255,0.5); }

    @media (max-width: 520px) {
      #sbOnboardCard { padding: 28px 20px; }
      .ob-options { grid-template-columns: 1fr; }
    }
  `;

  // ── State ────────────────────────────────────────────────────────────────────
  var state = { step: 1, choice: null }; // choice: 'byok' | 'managed'

  // ── Render ───────────────────────────────────────────────────────────────────
  function render() {
    var overlay = document.getElementById('sbOnboard');
    if (!overlay) return;
    var card = document.getElementById('sbOnboardCard');
    card.innerHTML = _buildCard();
    _bindEvents();
  }

  function _dots() {
    return '<div class="ob-dots">' +
      [1,2,3].map(function(i) {
        var cls = 'ob-dot' + (i === state.step ? ' is-active' : (i < state.step ? ' is-done' : ''));
        return '<div class="' + cls + '"></div>';
      }).join('') +
      '</div>';
  }

  function _buildCard() {
    if (state.step === 1) return _step1();
    if (state.step === 2) return _step2();
    return _step3();
  }

  function _step1() {
    var user = getUser();
    var greeting = user.name ? 'Welcome, ' + user.name + '.' : 'Welcome to Solace Browser.';
    return '<button class="ob-skip" id="obSkip">Skip setup</button>' +
      '<img class="ob-logo" src="/images/yinyang/yinyang-loading-128.gif" alt="Yinyang">' +
      _dots() +
      '<h2>' + greeting + '</h2>' +
      '<p class="ob-sub">Your AI agent can browse the web, access your machine, and run cloud tasks — but only with your explicit approval, every time.</p>' +
      '<div class="ob-actions">' +
        '<button class="ob-btn ob-btn--primary" id="obNext">Choose your power source →</button>' +
      '</div>';
  }

  function _step2() {
    var byokHidden = state.choice === 'byok' ? '' : 'display:none';
    return '<button class="ob-skip" id="obSkip">Skip setup</button>' +
      _dots() +
      '<h2>Choose your power source</h2>' +
      '<p class="ob-sub">Solace routes every AI call through OpenRouter. Bring your own key, or let us handle it.</p>' +
      '<div class="ob-options">' +
        '<div class="ob-option' + (state.choice === 'byok' ? ' is-selected' : '') + '" id="obChoiceBYOK">' +
          '<div class="ob-opt-icon">🔑</div>' +
          '<h3>Bring your own key</h3>' +
          '<p>Paste your OpenRouter, Claude, or OpenAI API key. Zero markup. Full control.</p>' +
          '<span class="ob-opt-badge">Free forever</span>' +
        '</div>' +
        '<div class="ob-option' + (state.choice === 'managed' ? ' is-selected' : '') + '" id="obChoiceManaged">' +
          '<div class="ob-opt-icon">⚡</div>' +
          '<h3>Let Solace handle it</h3>' +
          '<p>We route to Llama 3.3 70B via OpenRouter. No API key needed. Cancel anytime.</p>' +
          '<span class="ob-opt-badge">$8/mo · Dragon plan</span>' +
        '</div>' +
      '</div>' +
      '<div class="ob-byok" id="obByokFields" style="' + byokHidden + '">' +
        '<label>Provider</label>' +
        '<select id="obProvider">' +
          '<option value="openrouter">OpenRouter (recommended — access to all models)</option>' +
          '<option value="anthropic">Anthropic (Claude)</option>' +
          '<option value="openai">OpenAI (GPT-4o)</option>' +
        '</select>' +
        '<label>API Key</label>' +
        '<input type="password" id="obApiKey" placeholder="sk-or-v1-... or sk-ant-... or sk-..." autocomplete="off">' +
      '</div>' +
      '<div class="ob-actions">' +
        '<button class="ob-btn ob-btn--secondary" id="obBack">← Back</button>' +
        '<button class="ob-btn ob-btn--primary" id="obNext" ' + (!state.choice ? 'disabled style="opacity:0.4;cursor:not-allowed"' : '') + '>' +
          (state.choice === 'managed' ? 'Continue to checkout →' : 'Save and continue →') +
        '</button>' +
      '</div>';
  }

  function _step3() {
    return _dots() +
      '<div class="ob-success-check">✓</div>' +
      '<h2>You\'re all set!</h2>' +
      '<p class="ob-sub">Yinyang is powered up and ready. Every action requires your approval — you\'re always in control.</p>' +
      '<div class="ob-actions" style="justify-content:center">' +
        '<button class="ob-btn ob-btn--primary" id="obDone">Open App Store →</button>' +
        '<button class="ob-btn ob-btn--ghost" id="obDoneHome">Go to dashboard</button>' +
      '</div>';
  }

  // ── Events ───────────────────────────────────────────────────────────────────
  function _bindEvents() {
    var next = document.getElementById('obNext');
    var back = document.getElementById('obBack');
    var skip = document.getElementById('obSkip');
    var done = document.getElementById('obDone');
    var doneHome = document.getElementById('obDoneHome');

    if (skip) skip.addEventListener('click', dismiss);
    if (back) back.addEventListener('click', function() { state.step = 1; render(); });

    var byok = document.getElementById('obChoiceBYOK');
    var managed = document.getElementById('obChoiceManaged');
    if (byok) byok.addEventListener('click', function() {
      state.choice = 'byok'; render();
    });
    if (managed) managed.addEventListener('click', function() {
      state.choice = 'managed'; render();
    });

    if (next) next.addEventListener('click', function() {
      if (state.step === 1) { state.step = 2; render(); return; }
      if (state.step === 2) _handleStep2Next();
    });

    if (done) done.addEventListener('click', function() {
      dismiss(); window.location.href = '/app-store';
    });
    if (doneHome) doneHome.addEventListener('click', dismiss);
  }

  function _handleStep2Next() {
    if (state.choice === 'managed') {
      // Send user to Solace pricing page
      window.open(CLOUD + '/pricing?plan=dragon', '_blank');
      // Mark as configured optimistically — they'll complete payment there
      localStorage.setItem(STORAGE_KEY, '1');
      state.step = 3; render();
      return;
    }
    if (state.choice === 'byok') {
      var provider = (document.getElementById('obProvider') || {}).value || 'openrouter';
      var apiKey = ((document.getElementById('obApiKey') || {}).value || '').trim();
      if (!apiKey) {
        var inp = document.getElementById('obApiKey');
        if (inp) { inp.style.borderColor = '#ff6b6b'; inp.focus(); }
        return;
      }
      // Save to settings via web server settings endpoint
      _saveBYOK(provider, apiKey);
    }
  }

  function _saveBYOK(provider, apiKey) {
    var solaceKey = localStorage.getItem('solace_api_key') || '';
    var headers = { 'Content-Type': 'application/json' };
    if (solaceKey) headers['Authorization'] = 'Bearer ' + solaceKey;

    fetch('/api/settings', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({
        llm: {
          backend: provider,
          byok_key: apiKey,
          model: provider === 'openrouter'
            ? 'meta-llama/llama-3.3-70b-instruct'
            : (provider === 'anthropic' ? 'claude-haiku-4-5-20251001' : 'gpt-4o-mini'),
        }
      })
    })
    .then(function(r) {
      localStorage.setItem(STORAGE_KEY, '1');
      state.step = 3; render();
    })
    .catch(function() {
      // Fail silently — proceed to success anyway (user can configure in Settings)
      localStorage.setItem(STORAGE_KEY, '1');
      state.step = 3; render();
    });
  }

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, '1');
    var overlay = document.getElementById('sbOnboard');
    if (overlay) {
      overlay.style.animation = 'none';
      overlay.style.opacity = '0';
      overlay.style.transition = 'opacity 0.2s';
      setTimeout(function() { overlay.parentNode && overlay.parentNode.removeChild(overlay); }, 200);
    }
  }

  // ── Boot ─────────────────────────────────────────────────────────────────────
  function init() {
    if (!shouldShow()) return;
    // Inject CSS
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);
    // Inject overlay
    var overlay = document.createElement('div');
    overlay.id = 'sbOnboard';
    overlay.innerHTML = '<div id="sbOnboardCard"></div>';
    document.body.appendChild(overlay);
    render();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
