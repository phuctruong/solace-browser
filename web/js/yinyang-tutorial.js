/**
 * YinYang Tutorial — Solace Browser
 * v1.0.0 | Auth: 65537
 *
 * 5-step guided first-time tutorial popup.
 * Supports 13 locales, Anti-Clippy compliant, delight-integrated.
 *
 * Storage key: localStorage['sb_tutorial_v1'] = "done" | "skipped"
 * Trigger: first visit to home.html or start.html
 * Locale: loaded from /api/locale?key=tutorial (fallback: embedded English)
 */

/* global YinyangDelight */

const YinyangTutorial = (() => {
  'use strict';

  const STORAGE_KEY = 'sb_tutorial_v1';
  const YY_GIF = '/images/yinyang/yinyang-rotating_70pct_128px.gif';

  // ---------------------------------------------------------------------------
  // Embedded English fallback (used if /api/locale unreachable)
  // ---------------------------------------------------------------------------
  const STRINGS_EN = {
    step1_title: 'Meet Yinyang ☯',
    step1_body: "I'm Yinyang — your AI browser navigator. I navigate the web, click buttons, fill forms, take screenshots, and capture evidence. All on your behalf, always with your approval.",
    step2_title: 'Browser Control',
    step2_body: 'Point me at any URL and I\'ll navigate it. Ask me to click, fill, or screenshot — I\'ll do it and seal the evidence. Every action produces a SHA-256 audit trail.',
    step2_code: 'curl http://localhost:9222/api/navigate -d \'{"url":"https://example.com"}\'',
    step3_title: 'OAuth3 Safety &#128274;',
    step3_body: 'I never act without your explicit approval. Sensitive actions go through a scoped OAuth3 gate — time-bounded, revocable, and audited. You stay in control. Always.',
    step4_title: '18 Apps Ready &#127981;',
    step4_body: 'Browse the App Store. 18 automations ready to run — Gmail triage, LinkedIn outreach, Slack summaries, and more. One click to start. Recipe replay costs $0.001.',
    step5_title: "Let's Begin! &#127881;",
    step5_body: "You're all set. I'll be here in the bottom rail whenever you need me. Just ask — or point me at a task.",
    step5_joke: '',
    btn_next: 'Next \u2192',
    btn_prev: '\u2190 Back',
    btn_skip: 'Skip Tutorial',
    btn_done: "Let's Go! \u262F",
    progress: 'Step {current} of {total}',
    welcome_title: 'Welcome to Solace Browser',
    welcome_body: 'Your AI-powered browser with OAuth3 approvals and evidence trails.',
    welcome_tour: 'Take the 2-minute tour',
    welcome_skip: 'Skip, I know what I\'m doing',
  };

  const STEP_ICONS = ['☯', '&#128248;', '&#128274;', '&#127981;', '&#127881;'];

  let _strings = STRINGS_EN;
  let _currentStep = 0;
  let _overlay = null;
  const TOTAL_STEPS = 5;

  // ---------------------------------------------------------------------------
  // Locale loading
  // ---------------------------------------------------------------------------
  async function _loadLocale() {
    try {
      const resp = await fetch('/api/locale?key=tutorial', { signal: AbortSignal.timeout(3000) });
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.tutorial) {
          _strings = Object.assign({}, STRINGS_EN, data.tutorial);
        }
      }
    } catch (_) {
      // fallback to English — already loaded
    }
  }

  // ---------------------------------------------------------------------------
  // Build step HTML
  // ---------------------------------------------------------------------------
  function _stepHTML(step) {
    const stepKey = `step${step + 1}`;
    const title = _strings[`${stepKey}_title`] || '';
    const body = _strings[`${stepKey}_body`] || '';
    const code = _strings[`${stepKey}_code`] || '';
    const joke = step === 4 ? (_strings.step5_joke || '') : '';

    let extra = '';
    if (code) {
      extra = `<pre class="yyT-code">${code}</pre>`;
    }
    if (joke) {
      extra += `<p class="yyT-joke">&#128172; "${joke}"</p>`;
    }

    return `
      <div class="yyT-step-icon">${STEP_ICONS[step]}</div>
      <h2 class="yyT-step-title">${title}</h2>
      <p class="yyT-step-body">${body}</p>
      ${extra}
    `;
  }

  // ---------------------------------------------------------------------------
  // Dots HTML
  // ---------------------------------------------------------------------------
  function _dotsHTML(current) {
    return Array.from({ length: TOTAL_STEPS }, (_, i) =>
      `<span class="yyT-dot${i === current ? ' yyT-dot--active' : ''}" data-dot="${i}"></span>`
    ).join('');
  }

  // ---------------------------------------------------------------------------
  // Progress label
  // ---------------------------------------------------------------------------
  function _progressLabel(step) {
    return (_strings.progress || 'Step {current} of {total}')
      .replace('{current}', step + 1)
      .replace('{total}', TOTAL_STEPS);
  }

  // ---------------------------------------------------------------------------
  // Render overlay
  // ---------------------------------------------------------------------------
  function _render() {
    if (!_overlay) return;
    const isFirst = _currentStep === 0;
    const isLast = _currentStep === TOTAL_STEPS - 1;

    _overlay.querySelector('.yyT-step-content').innerHTML = _stepHTML(_currentStep);
    _overlay.querySelector('.yyT-dots').innerHTML = _dotsHTML(_currentStep);
    _overlay.querySelector('.yyT-progress').textContent = _progressLabel(_currentStep);

    const btnPrev = _overlay.querySelector('.yyT-btn-prev');
    const btnNext = _overlay.querySelector('.yyT-btn-next');
    const btnSkip = _overlay.querySelector('.yyT-btn-skip');
    const btnDone = _overlay.querySelector('.yyT-btn-done');

    btnPrev.style.visibility = isFirst ? 'hidden' : 'visible';
    btnNext.style.display = isLast ? 'none' : 'inline-flex';
    btnDone.style.display = isLast ? 'inline-flex' : 'none';
    btnSkip.style.display = isLast ? 'none' : 'inline-block';
  }

  // ---------------------------------------------------------------------------
  // Build DOM
  // ---------------------------------------------------------------------------
  function _buildOverlay() {
    const div = document.createElement('div');
    div.id = 'yyTutorial';
    div.className = 'yyT-overlay';
    div.setAttribute('role', 'dialog');
    div.setAttribute('aria-modal', 'true');
    div.setAttribute('aria-label', 'Yinyang Tutorial');

    div.innerHTML = `
      <div class="yyT-card">
        <div class="yyT-header">
          <img class="yyT-gif" src="${YY_GIF}" alt="Yinyang" width="64" height="64">
          <span class="yyT-progress"></span>
        </div>
        <div class="yyT-step-content"></div>
        <div class="yyT-dots"></div>
        <div class="yyT-btns">
          <button class="yyT-btn yyT-btn-prev" aria-label="Previous step">${_strings.btn_prev}</button>
          <button class="yyT-btn yyT-btn-skip">${_strings.btn_skip}</button>
          <button class="yyT-btn yyT-btn-next yyT-btn--primary">${_strings.btn_next}</button>
          <button class="yyT-btn yyT-btn-done yyT-btn--primary" style="display:none">${_strings.btn_done}</button>
        </div>
      </div>
    `;

    // Event handlers
    div.querySelector('.yyT-btn-next').addEventListener('click', () => {
      if (_currentStep < TOTAL_STEPS - 1) {
        _currentStep++;
        _render();
      }
    });

    div.querySelector('.yyT-btn-prev').addEventListener('click', () => {
      if (_currentStep > 0) {
        _currentStep--;
        _render();
      }
    });

    div.querySelector('.yyT-btn-skip').addEventListener('click', _skip);
    div.querySelector('.yyT-btn-done').addEventListener('click', _done);

    // Dot navigation
    div.querySelector('.yyT-dots').addEventListener('click', (e) => {
      const dot = e.target.closest('[data-dot]');
      if (dot) {
        _currentStep = parseInt(dot.dataset.dot, 10);
        _render();
      }
    });

    // Keyboard navigation
    document.addEventListener('keydown', _handleKey, { once: false });

    return div;
  }

  function _handleKey(e) {
    if (!document.getElementById('yyTutorial')) return;
    if (e.key === 'ArrowRight' || e.key === 'Enter') {
      if (_currentStep < TOTAL_STEPS - 1) { _currentStep++; _render(); }
      else { _done(); }
    } else if (e.key === 'ArrowLeft') {
      if (_currentStep > 0) { _currentStep--; _render(); }
    } else if (e.key === 'Escape') {
      _skip();
    }
  }

  function _skip() {
    localStorage.setItem(STORAGE_KEY, 'skipped');
    _close();
  }

  function _done() {
    localStorage.setItem(STORAGE_KEY, 'done');
    _close();
    // Fire delight on completion
    if (typeof YinyangDelight !== 'undefined') {
      YinyangDelight.celebrate('first_run_complete');
    }
  }

  function _close() {
    document.removeEventListener('keydown', _handleKey);
    if (_overlay) {
      _overlay.classList.add('yyT-overlay--exit');
      setTimeout(() => {
        if (_overlay && _overlay.parentNode) {
          _overlay.parentNode.removeChild(_overlay);
        }
        _overlay = null;
      }, 300);
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Show the tutorial. Respects localStorage flag — use force=true to always show.
   */
  async function show(force = false) {
    const status = localStorage.getItem(STORAGE_KEY);
    if (!force && (status === 'done' || status === 'skipped')) {
      return;
    }

    // Respect reduced-motion — skip animations, not the tutorial itself
    await _loadLocale();

    _currentStep = 0;
    _overlay = _buildOverlay();
    document.body.appendChild(_overlay);
    _render();

    // Fade in
    requestAnimationFrame(() => _overlay.classList.add('yyT-overlay--visible'));
  }

  /**
   * Programmatically reset and re-show (for testing or manual re-launch).
   */
  function reset() {
    localStorage.removeItem(STORAGE_KEY);
    show(true);
  }

  /**
   * Auto-init: show on first visit if not already seen.
   */
  function autoInit() {
    const status = localStorage.getItem(STORAGE_KEY);
    if (!status) {
      // Small delay to let the page paint first
      setTimeout(() => show(), 800);
    }
  }

  return { show, reset, autoInit };
})();

// Auto-init when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', YinyangTutorial.autoInit);
} else {
  setTimeout(YinyangTutorial.autoInit, 800);
}
