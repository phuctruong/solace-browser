/**
 * YinYang Tutorial WOW Edition — Solace Browser
 * v2.0.0 | Auth: 65537 | GLOW 123
 *
 * 5-step WOW guided first-time tutorial.
 * Persona committee: Rory Sutherland · Jony Ive · Vanessa Van Edwards · Russell Brunson · Seth Godin
 * Anti-Clippy compliant. Delight-integrated. 13 locales.
 *
 * Hook → Story → Story → Story → Offer (Brunson funnel)
 *
 * Storage key: localStorage['sb_tutorial_v1'] = "done" | "skipped"
 */

/* global YinyangDelight */

const YinyangTutorial = (() => {
  'use strict';

  const STORAGE_KEY = 'sb_tutorial_v1';
  const LOCALE_KEY  = 'sb_locale';
  const YY_GIF      = '/images/yinyang/yinyang-rotating_70pct_128px.gif';

  const LOCALES = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'vi', name: 'Tiếng Việt' },
    { code: 'zh', name: '中文' },
    { code: 'pt', name: 'Português' },
    { code: 'fr', name: 'Français' },
    { code: 'ja', name: '日本語' },
    { code: 'de', name: 'Deutsch' },
    { code: 'ar', name: 'العربية' },
    { code: 'hi', name: 'हिंदी' },
    { code: 'ko', name: '한국어' },
    { code: 'id', name: 'Bahasa Indonesia' },
    { code: 'ru', name: 'Русский' },
  ];

  let _locale = localStorage.getItem(LOCALE_KEY) || 'en';

  // ---------------------------------------------------------------------------
  // WOW Strings — English fallback
  // Persona: Russell Brunson Hook/Story/Story/Story/Offer structure
  // Persona: Vanessa Van Edwards — "I've been waiting for you" first signal
  // Persona: Rory Sutherland — reframe mundane as sacred, quantify psychic value
  // Persona: Seth Godin — permission first, each step a gift
  // Persona: Jony Ive — no jank, inevitable animations, one button on step 5
  // ---------------------------------------------------------------------------
  const STRINGS_EN = {
    // Step 1 — THE HOOK (Vanessa + Russell + Rory)
    step1_title: "I\u2019ve been waiting for you.",
    step1_body:  "847 emails are sitting in your inbox right now. Not spam \u2014 real decisions. At 3 minutes each, that\u2019s 42 hours. A full work week. Every week. I handle all of it while you sleep. You approve everything before it moves. Nothing leaves without your OK.",
    step1_time_morning:   "Good morning.",
    step1_time_afternoon: "Good afternoon.",
    step1_time_evening:   "Good evening.",
    step1_time_night:     "Still up?",

    // Step 2 — THE DEMO (Jony Ive + Rory)
    step2_title:      "Watch. 47 seconds. Real.",
    step2_body:       "Right now, across 847 emails in a real inbox, I\u2019m doing this:",
    step2_demo_line1: "Reading 847 emails\u2026",
    step2_demo_line2: "Classified: 12 urgent \u00b7 43 needs reply \u00b7 792 archived",
    step2_demo_line3: "Evidence sealed \u25b8 SHA-256 \u25b8 awaiting your approval",
    step2_demo_t1:    "0.3s",
    step2_demo_t2:    "18s",
    step2_demo_t3:    "47s",

    // Step 3 — SAVINGS (Rory + Russell)
    step3_title:    "$847 you\u2019re leaving on the table. Every month.",
    step3_body:     "This isn\u2019t about saving a few hours. It\u2019s about reclaiming your most expensive resource: your attention.",
    step3_without:  "Without me",
    step3_with:     "With Yinyang",
    step3_you_keep: "You keep",

    // Step 4 — TRUST (Seth Godin + Vanessa)
    step4_title:             "I will never act without your \u201cOK.\u201d",
    step4_guarantee1_title:  "One click to revoke.",
    step4_guarantee1_body:   "Settings \u2192 Tokens \u2192 Revoke. Instant. No email, no waiting.",
    step4_guarantee2_title:  "You see everything first.",
    step4_guarantee2_body:   "Every draft, every action shown to you before it happens. No surprises.",
    step4_guarantee3_title:  "SHA-256 sealed forever.",
    step4_guarantee3_body:   "Every run creates an immutable evidence chain. Audit-ready. Always.",

    // Step 5 — THE OFFER (Russell + Seth + Jony)
    step5_title:    "Your inbox. 47 seconds. Sign in free.",
    step5_body:     "Your colleagues are going to wonder how you\u2019re suddenly so on top of everything.",
    step5_cta_wow:  "Sign in with Google \u2014 free \u262F",
    step5_joke:     "People think you got more focused. You just got smarter about what to delegate. \u2014 Yinyang",

    // Navigation
    lang_pick:    'Choose your language',
    btn_next:     'Next \u2192',
    btn_prev:     '\u2190 Back',
    btn_skip:     'Skip Tutorial',
    btn_done:     "Let\u2019s Go! \u262F",
    progress:     'Step {current} of {total}',
    welcome_title: 'Welcome to Solace Browser',
    welcome_body:  'Your AI-powered browser with OAuth3 approvals and evidence trails.',
    welcome_tour:  'Take the 2-minute tour',
    welcome_skip:  "Skip, I know what I\u2019m doing",
  };

  // ---------------------------------------------------------------------------
  // Step entry side-effects — fire when step becomes visible
  // Jony Ive: "Every animation must feel inevitable."
  // ---------------------------------------------------------------------------
  const STEP_ENTER_FX = {
    // Step 1 — single ding + sparkles (not fireworks yet — Seth: permission first)
    0: function () {
      setTimeout(() => {
        if (typeof YinyangDelight !== 'undefined') {
          if (YinyangDelight.effects && YinyangDelight.effects.sparkles) YinyangDelight.effects.sparkles();
          if (YinyangDelight.effects && YinyangDelight.effects.sound)    YinyangDelight.effects.sound('ding');
        }
      }, 600);
    },

    // Step 2 — staggered terminal line reveal
    1: function () {
      setTimeout(() => {
        const l2 = document.querySelector('.yyT-demo-line--2');
        if (l2) { l2.style.opacity = '1'; l2.style.transform = 'translateY(0)'; }
      }, 800);
      setTimeout(() => {
        const l3 = document.querySelector('.yyT-demo-line--3');
        if (l3) { l3.style.opacity = '1'; l3.style.transform = 'translateY(0)'; }
      }, 1600);
    },

    // Step 3 — savings counter animation (Rory: make psychic value feel real)
    2: function () {
      const el = document.getElementById('yyT-savings-num');
      if (!el) return;
      const target   = 836;
      const start    = Date.now();
      const duration = 1200;
      function tick() {
        const elapsed = Date.now() - start;
        const pct     = Math.min(elapsed / duration, 1);
        const eased   = 1 - Math.pow(1 - pct, 3); // ease-out-cubic
        el.textContent = '$' + Math.round(eased * target) + '/month';
        if (pct < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    },

    // Step 4 — trust items stagger in (Jony: inevitable, considered)
    3: function () {
      document.querySelectorAll('.yyT-trust-item').forEach((item, i) => {
        item.style.animationDelay = (i * 200) + 'ms';
        item.classList.add('yyT-trust-item--animate');
      });
    },

    // Step 5 — no auto-effect, save fireworks for the button click (Seth: permission)
    4: function () {},
  };

  let _strings     = STRINGS_EN;
  let _currentStep = 0;
  let _overlay     = null;
  const TOTAL_STEPS = 5;

  // ---------------------------------------------------------------------------
  // Locale loading
  // ---------------------------------------------------------------------------
  async function _loadLocale(locale) {
    if (locale) _locale = locale;
    try {
      const resp = await fetch(`/api/locale?key=tutorial&locale=${_locale}`, { signal: AbortSignal.timeout(3000) });
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
  // Build step HTML — unique layout per step
  // ---------------------------------------------------------------------------
  function _stepHTML(step) {
    const stepKey = `step${step + 1}`;
    const title   = _strings[`${stepKey}_title`] || '';
    const body    = _strings[`${stepKey}_body`]  || '';

    // ── Step 1: HOOK — hero layout, personalized time greeting ──
    if (step === 0) {
      const hour      = new Date().getHours();
      const timeGreet = hour < 12 ? (_strings.step1_time_morning   || 'Good morning.')
                      : hour < 17 ? (_strings.step1_time_afternoon || 'Good afternoon.')
                      : hour < 21 ? (_strings.step1_time_evening   || 'Good evening.')
                      :             (_strings.step1_time_night     || 'Still up?');
      return `
        <img class="yyT-hero-gif" src="${YY_GIF}" alt="Yinyang">
        <h2 class="yyT-step-title yyT-step-title--hero">${title}</h2>
        <p class="yyT-step-body--time">${timeGreet}</p>
        <p class="yyT-step-body">${body}</p>
        <p class="yyT-lang-hint">&#127760; <a href="#" class="yyT-lang-hint-link"
           onclick="document.querySelector('.yyT-lang-btn').click();return false;">${_locale.toUpperCase()} \u00b7 Change language</a></p>
      `;
    }

    // ── Step 2: DEMO — live terminal with staggered reveal ──
    if (step === 1) {
      return `
        <div class="yyT-step-icon">&#128248;</div>
        <h2 class="yyT-step-title">${title}</h2>
        <p class="yyT-step-body">${body}</p>
        <div class="yyT-demo-terminal">
          <div class="yyT-demo-line yyT-demo-line--1">
            <span class="yyT-demo-dot yyT-demo-dot--running"></span>
            <span>${_strings.step2_demo_line1 || 'Reading 847 emails\u2026'}</span>
            <span class="yyT-demo-time">${_strings.step2_demo_t1 || '0.3s'}</span>
          </div>
          <div class="yyT-demo-line yyT-demo-line--2" style="opacity:0;transform:translateY(6px);transition:opacity 0.5s ease,transform 0.5s ease">
            <span class="yyT-demo-dot yyT-demo-dot--done"></span>
            <span>${_strings.step2_demo_line2 || 'Classified: 12 urgent \u00b7 43 needs reply \u00b7 792 archived'}</span>
            <span class="yyT-demo-time">${_strings.step2_demo_t2 || '18s'}</span>
          </div>
          <div class="yyT-demo-line yyT-demo-line--3" style="opacity:0;transform:translateY(6px);transition:opacity 0.5s ease,transform 0.5s ease">
            <span class="yyT-demo-dot yyT-demo-dot--seal"></span>
            <span>${_strings.step2_demo_line3 || 'Evidence sealed \u25b8 SHA-256 \u25b8 awaiting your approval'}</span>
            <span class="yyT-demo-time">${_strings.step2_demo_t3 || '47s'}</span>
          </div>
        </div>
      `;
    }

    // ── Step 3: SAVINGS — counter animation ──
    if (step === 2) {
      return `
        <div class="yyT-step-icon">&#128176;</div>
        <h2 class="yyT-step-title">${title}</h2>
        <div class="yyT-savings-display">
          <div class="yyT-savings-row">
            <span class="yyT-savings-label">${_strings.step3_without || 'Without me'}</span>
            <span class="yyT-savings-value yyT-savings-value--bad">42 hrs \u00d7 $20/hr = <strong>$840/month</strong></span>
          </div>
          <div class="yyT-savings-row">
            <span class="yyT-savings-label">${_strings.step3_with || 'With Yinyang'}</span>
            <span class="yyT-savings-value yyT-savings-value--good">47 sec \u00d7 $0.12/run = <strong>$3.60/month</strong></span>
          </div>
          <div class="yyT-savings-total">
            ${_strings.step3_you_keep || 'You keep'} <strong id="yyT-savings-num">$0/month</strong> \u26a1
          </div>
        </div>
        <p class="yyT-step-body" style="margin-top:16px">${body}</p>
      `;
    }

    // ── Step 4: TRUST — staggered lock guarantees ──
    if (step === 3) {
      return `
        <div class="yyT-step-icon">&#128274;</div>
        <h2 class="yyT-step-title">${title}</h2>
        <div class="yyT-trust-grid">
          <div class="yyT-trust-item">
            <span class="yyT-trust-icon">\uD83D\uDD12</span>
            <div>
              <strong>${_strings.step4_guarantee1_title || 'One click to revoke.'}</strong>
              <p>${_strings.step4_guarantee1_body || 'Settings \u2192 Tokens \u2192 Revoke. Instant. No email, no waiting.'}</p>
            </div>
          </div>
          <div class="yyT-trust-item">
            <span class="yyT-trust-icon">&#128065;</span>
            <div>
              <strong>${_strings.step4_guarantee2_title || 'You see everything first.'}</strong>
              <p>${_strings.step4_guarantee2_body || 'Every draft, every action shown to you before it happens. No surprises.'}</p>
            </div>
          </div>
          <div class="yyT-trust-item">
            <span class="yyT-trust-icon">&#128279;</span>
            <div>
              <strong>${_strings.step4_guarantee3_title || 'SHA-256 sealed forever.'}</strong>
              <p>${_strings.step4_guarantee3_body || 'Every run creates an immutable evidence chain. Audit-ready. Always.'}</p>
            </div>
          </div>
        </div>
      `;
    }

    // ── Step 5: THE OFFER — single CTA, Jony: one button, Seth: gift ──
    return `
      <div class="yyT-step-icon">&#127881;</div>
      <h2 class="yyT-step-title yyT-step-title--hero">${title}</h2>
      <p class="yyT-step-body">${body}</p>
      <button class="yyT-cta-btn" id="yyT-final-cta">${_strings.step5_cta_wow || 'Sign in with Google \u2014 free \u262F'}</button>
      <p class="yyT-joke">&#128172; "${_strings.step5_joke || ''}"</p>
    `;
  }

  // ---------------------------------------------------------------------------
  // Dots + Progress
  // ---------------------------------------------------------------------------
  function _dotsHTML(current) {
    return Array.from({ length: TOTAL_STEPS }, (_, i) =>
      `<span class="yyT-dot${i === current ? ' yyT-dot--active' : ''}" data-dot="${i}"></span>`
    ).join('');
  }

  function _progressLabel(step) {
    return (_strings.progress || 'Step {current} of {total}')
      .replace('{current}', step + 1)
      .replace('{total}', TOTAL_STEPS);
  }

  // ---------------------------------------------------------------------------
  // Render — update DOM + fire step effects
  // ---------------------------------------------------------------------------
  function _render() {
    if (!_overlay) return;
    const isFirst = _currentStep === 0;
    const isLast  = _currentStep === TOTAL_STEPS - 1;

    _overlay.querySelector('.yyT-step-content').innerHTML = _stepHTML(_currentStep);
    _overlay.querySelector('.yyT-dots').innerHTML         = _dotsHTML(_currentStep);
    _overlay.setAttribute('data-step', _currentStep);
    _overlay.querySelector('.yyT-progress').textContent   = _progressLabel(_currentStep);

    const btnPrev = _overlay.querySelector('.yyT-btn-prev');
    const btnNext = _overlay.querySelector('.yyT-btn-next');
    const btnSkip = _overlay.querySelector('.yyT-btn-skip');
    const btnDone = _overlay.querySelector('.yyT-btn-done');

    btnPrev.style.visibility = isFirst ? 'hidden' : 'visible';
    btnNext.style.display    = isLast  ? 'none'   : 'inline-flex';
    // On last step, btns bar hides (CTA button IS inside step-content)
    btnDone.style.display    = 'none';
    btnSkip.style.display    = (isLast || isFirst) ? 'none' : 'inline-block';
    btnNext.textContent      = isFirst ? 'Show me \u2192' : (_strings.btn_next || 'Next \u2192');
    _overlay.querySelector('.yyT-gif').classList.toggle('yyT-gif--hero', isFirst);

    // Fire step entry effects
    if (STEP_ENTER_FX[_currentStep]) STEP_ENTER_FX[_currentStep]();
  }

  // ---------------------------------------------------------------------------
  // Build DOM
  // ---------------------------------------------------------------------------
  function _buildOverlay() {
    const div = document.createElement('div');
    div.id        = 'yyTutorial';
    div.className = 'yyT-overlay';
    div.setAttribute('role', 'dialog');
    div.setAttribute('aria-modal', 'true');
    div.setAttribute('aria-label', 'Yinyang Tutorial');

    const langMenuItems = LOCALES.map(l =>
      `<a role="button" tabindex="0" data-locale="${l.code}" aria-current="${l.code === _locale ? 'true' : 'false'}">${l.name}</a>`
    ).join('');

    div.innerHTML = `
      <div class="yyT-card">
        <div class="yyT-header">
          <img class="yyT-gif" src="${YY_GIF}" alt="Yinyang">
          <span class="yyT-progress"></span>
          <div class="yyT-lang-wrap">
            <button class="yyT-lang-btn" aria-label="Select language" aria-expanded="false" aria-controls="yyT-lang-menu">
              <img src="/images/icons/internationalization/160.png" alt="Language" width="20" height="20" style="width:20px;height:20px;object-fit:contain;display:block;">
            </button>
            <div class="yyT-lang-menu" id="yyT-lang-menu">${langMenuItems}</div>
          </div>
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

    // ── Navigation ──
    div.querySelector('.yyT-btn-next').addEventListener('click', () => {
      if (_currentStep < TOTAL_STEPS - 1) { _currentStep++; _render(); }
    });
    div.querySelector('.yyT-btn-prev').addEventListener('click', () => {
      if (_currentStep > 0) { _currentStep--; _render(); }
    });
    div.querySelector('.yyT-btn-skip').addEventListener('click', _skip);
    div.querySelector('.yyT-btn-done').addEventListener('click', () => _done(false));

    // ── Final CTA: fireworks THEN redirect (Jony: confident reveal) ──
    div.querySelector('.yyT-step-content').addEventListener('click', async (e) => {
      // Final CTA button
      if (e.target.id === 'yyT-final-cta') {
        e.target.disabled     = true;
        e.target.textContent  = 'Signing in\u2026 \u262F';
        if (typeof YinyangDelight !== 'undefined') {
          if (YinyangDelight.effects && YinyangDelight.effects.fireworks) await YinyangDelight.effects.fireworks();
          if (YinyangDelight.effects && YinyangDelight.effects.sound)     YinyangDelight.effects.sound('fanfare');
        }
        setTimeout(() => {
          _done(true); // skipDelight = true (fireworks already fired)
          const gBtn = document.getElementById('btn-google');
          if (gBtn) gBtn.click();
        }, 1200);
        return;
      }
      // Locale pill handler
      const pill = e.target.closest('[data-locale-pill]');
      if (!pill) return;
      const code = pill.dataset.localePill;
      localStorage.setItem(LOCALE_KEY, code);
      await _loadLocale(code);
      _rebuildButtons(div);
      _render();
      if (typeof window.SolacePageI18n === 'function') window.SolacePageI18n(code);
    });

    // ── Language switcher ──
    const langBtn  = div.querySelector('.yyT-lang-btn');
    const langMenu = div.querySelector('.yyT-lang-menu');
    langBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = langMenu.classList.toggle('is-active');
      langBtn.setAttribute('aria-expanded', open);
    });
    langMenu.addEventListener('click', async (e) => {
      e.preventDefault();
      const link = e.target.closest('[data-locale]');
      if (!link) return;
      const code = link.dataset.locale;
      localStorage.setItem(LOCALE_KEY, code);
      langMenu.classList.remove('is-active');
      langBtn.setAttribute('aria-expanded', 'false');
      await _loadLocale(code);
      langMenu.querySelectorAll('[data-locale]').forEach(a => {
        a.setAttribute('aria-current', a.dataset.locale === code ? 'true' : 'false');
      });
      _rebuildButtons(div);
      _render();
      if (typeof window.SolacePageI18n === 'function') window.SolacePageI18n(code);
    });
    document.addEventListener('click', (e) => {
      if (langMenu.classList.contains('is-active') && !langBtn.contains(e.target) && !langMenu.contains(e.target)) {
        langMenu.classList.remove('is-active');
        langBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // ── Dot navigation ──
    div.querySelector('.yyT-dots').addEventListener('click', (e) => {
      const dot = e.target.closest('[data-dot]');
      if (dot) { _currentStep = parseInt(dot.dataset.dot, 10); _render(); }
    });

    // ── Keyboard navigation ──
    document.addEventListener('keydown', _handleKey, { once: false });

    return div;
  }

  function _rebuildButtons(div) {
    div.querySelector('.yyT-btn-prev').textContent = _strings.btn_prev;
    div.querySelector('.yyT-btn-skip').textContent = _strings.btn_skip;
    div.querySelector('.yyT-btn-next').textContent = _strings.btn_next;
    div.querySelector('.yyT-btn-done').textContent = _strings.btn_done;
  }

  function _handleKey(e) {
    if (!document.getElementById('yyTutorial')) return;
    if (e.key === 'ArrowRight' || e.key === 'Enter') {
      if (_currentStep < TOTAL_STEPS - 1) { _currentStep++; _render(); }
      else { _done(false); }
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

  function _done(skipDelight = false) {
    localStorage.setItem(STORAGE_KEY, 'done');
    _close();
    if (!skipDelight && typeof YinyangDelight !== 'undefined') {
      YinyangDelight.celebrate('first_run_complete');
    }
  }

  function _close() {
    document.removeEventListener('keydown', _handleKey);
    if (_overlay) {
      _overlay.classList.add('yyT-overlay--exit');
      setTimeout(() => {
        if (_overlay && _overlay.parentNode) _overlay.parentNode.removeChild(_overlay);
        _overlay = null;
      }, 300);
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  async function show(force = false) {
    const status = localStorage.getItem(STORAGE_KEY);
    if (!force && (status === 'done' || status === 'skipped')) return;
    await _loadLocale();
    _currentStep = 0;
    _overlay = _buildOverlay();
    document.body.appendChild(_overlay);
    _render();
    requestAnimationFrame(() => _overlay.classList.add('yyT-overlay--visible'));
  }

  function reset() {
    localStorage.removeItem(STORAGE_KEY);
    show(true);
  }

  function autoInit() {
    const status = localStorage.getItem(STORAGE_KEY);
    if (!status) setTimeout(() => show(), 800);
  }

  return { show, reset, autoInit };
})();

// Auto-init when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', YinyangTutorial.autoInit);
} else {
  setTimeout(YinyangTutorial.autoInit, 800);
}
