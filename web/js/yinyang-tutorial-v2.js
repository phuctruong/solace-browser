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
  const LOCALE_KEY = 'sb_locale';
  const YY_GIF = '/images/yinyang/yinyang-rotating_70pct_128px.gif';

  // 13 supported locales with native names
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
  // Embedded English fallback (used if /api/locale unreachable)
  // ---------------------------------------------------------------------------
  const STRINGS_EN = {
    step1_title: '847 emails. 3 hours of your life. Or 47 seconds.',
    step1_body: "That\u2019s your Monday morning, every Monday. I handle it while you sleep \u2014 classify, draft, seal the evidence. You approve everything before anything moves. Then you go about your day.",
    step2_title: 'That \u2018inbox zero\u2019 feeling. Every morning.',
    step2_body: 'I read every email and sort it: Urgent, Respond, Archive. I draft the replies. You see exactly what I found and what I wrote \u2014 <strong style="color:var(--sb-signal)">before anything is sent</strong>. You click Approve. That\u2019s it.',
    step2_code: '',
    step3_title: 'I show you everything. You decide. Then I act.',
    step3_body: 'Every action requires your explicit approval before it happens. Revoke my access in one click from Settings \u2014 any time, instantly. I have never surprised anyone. I won\u2019t start with you.',
    step4_title: '18 Apps. It learns once, then costs almost nothing.',
    step4_body: 'Gmail triage, LinkedIn outreach, Slack summaries, Calendar \u2014 and 14 more. The first run uses AI to figure out what works. After that, replaying what worked costs <strong style="color:var(--sb-signal)">$0.001</strong>. Less than a search.',
    step5_title: "Sign in free \u2014 your inbox runs in 47 seconds &#9889;",
    step5_body: "Your colleagues are going to wonder how you\u2019re suddenly so on top of everything. Sign in with Google \u2014 10 seconds. Inbox triage starts immediately after.",
    step5_joke: 'People think you got more focused. You just got smarter about what to delegate. \u2014 YinYang',
    lang_pick: 'Choose your language',
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
  // Build step HTML
  // ---------------------------------------------------------------------------
  function _langPickerHTML() {
    const label = _strings.lang_pick || 'Choose your language:';
    const items = LOCALES.map(l =>
      `<button class="yyT-lang-pill${l.code === _locale ? ' yyT-lang-pill--active' : ''}" data-locale-pill="${l.code}">${l.name}</button>`
    ).join('');
    return `
      <div class="yyT-lang-picker">
        <p class="yyT-lang-picker__label">&#127760; ${label}</p>
        <div class="yyT-lang-pills">${items}</div>
      </div>
    `;
  }

  function _stepHTML(step) {
    const stepKey = `step${step + 1}`;
    const title = _strings[`${stepKey}_title`] || '';
    const body = _strings[`${stepKey}_body`] || '';
    const code = _strings[`${stepKey}_code`] || '';
    const joke = step === 4 ? (_strings.step5_joke || '') : '';

    // Step 1 — hero layout: big YinYang first, no small icon, no lang pills
    if (step === 0) {
      const langLink = `<p class="yyT-lang-hint">&#127760; <a href="#" class="yyT-lang-hint-link" onclick="document.querySelector('.yyT-lang-btn').click();return false;">${_locale.toUpperCase()} · Change language</a></p>`;
      return `
        <img class="yyT-hero-gif" src="${YY_GIF}" alt="Yinyang">
        <h2 class="yyT-step-title yyT-step-title--hero">${title}</h2>
        <p class="yyT-step-body">${body}</p>
        ${langLink}
      `;
    }

    let extra = '';
    if (code) {
      extra += `<pre class="yyT-code">${code}</pre>`;
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
    _overlay.setAttribute('data-step', _currentStep);
    _overlay.querySelector('.yyT-progress').textContent = _progressLabel(_currentStep);

    const btnPrev = _overlay.querySelector('.yyT-btn-prev');
    const btnNext = _overlay.querySelector('.yyT-btn-next');
    const btnSkip = _overlay.querySelector('.yyT-btn-skip');
    const btnDone = _overlay.querySelector('.yyT-btn-done');

    btnPrev.style.visibility = isFirst ? 'hidden' : 'visible';
    btnNext.style.display = isLast ? 'none' : 'inline-flex';
    btnDone.style.display = isLast ? 'inline-flex' : 'none';
    // Hide Skip on step 1 — make them see the hook first
    btnSkip.style.display = (isLast || isFirst) ? 'none' : 'inline-block';
    // Step 1 CTA is punchier
    btnNext.textContent = isFirst ? 'Show me →' : (_strings.btn_next || 'Next →');
    // Step 1: hero mode — bigger YinYang
    _overlay.querySelector('.yyT-gif').classList.toggle('yyT-gif--hero', isFirst);
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

    // Language switcher
    const langBtn = div.querySelector('.yyT-lang-btn');
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
      // Rebuild buttons with new strings
      div.querySelector('.yyT-btn-prev').textContent = _strings.btn_prev;
      div.querySelector('.yyT-btn-skip').textContent = _strings.btn_skip;
      div.querySelector('.yyT-btn-next').textContent = _strings.btn_next;
      div.querySelector('.yyT-btn-done').textContent = _strings.btn_done;
      // Update aria-current on menu items
      langMenu.querySelectorAll('[data-locale]').forEach(a => {
        a.setAttribute('aria-current', a.dataset.locale === code ? 'true' : 'false');
      });
      _render();
      // Also update page nav/UI strings via solace.js global
      if (typeof window.SolacePageI18n === 'function') window.SolacePageI18n(code);
    });
    // Close lang menu on outside click
    document.addEventListener('click', (e) => {
      if (langMenu.classList.contains('is-active') && !langBtn.contains(e.target) && !langMenu.contains(e.target)) {
        langMenu.classList.remove('is-active');
        langBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Language pills (step 1 inline picker) — delegated on step-content
    div.querySelector('.yyT-step-content').addEventListener('click', async (e) => {
      const pill = e.target.closest('[data-locale-pill]');
      if (!pill) return;
      const code = pill.dataset.localePill;
      localStorage.setItem(LOCALE_KEY, code);
      await _loadLocale(code);
      div.querySelector('.yyT-btn-prev').textContent = _strings.btn_prev;
      div.querySelector('.yyT-btn-skip').textContent = _strings.btn_skip;
      div.querySelector('.yyT-btn-next').textContent = _strings.btn_next;
      div.querySelector('.yyT-btn-done').textContent = _strings.btn_done;
      langMenu.querySelectorAll('[data-locale]').forEach(a => {
        a.setAttribute('aria-current', a.dataset.locale === code ? 'true' : 'false');
      });
      _render();
      if (typeof window.SolacePageI18n === 'function') window.SolacePageI18n(code);
    });

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
