/* layout.js — Shared header/footer injection for all Solace Browser pages
 * Fetches _header.html and _footer.html, injects them, then wires up
 * hamburger menu, language switcher, nav highlighting, and current year.
 */
(function () {
  'use strict';

  // ── Early theme application (runs before DOMContentLoaded to prevent FOUC) ──
  (function applyThemeEarly() {
    const saved = localStorage.getItem('solace-theme');
    const theme = saved || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    // Inject theme CSS link if not already present
    if (!document.getElementById('theme-css')) {
      const builtIn = ['dark', 'light', 'midnight'];
      if (builtIn.indexOf(theme) !== -1) {
        const link = document.createElement('link');
        link.id = 'theme-css';
        link.rel = 'stylesheet';
        link.href = '/css/themes/' + theme + '.css';
        document.head.appendChild(link);
      }
    }
    // Update meta theme-color for mobile browsers
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      const colors = { dark: '#081019', light: '#faf8f5', midnight: '#000000' };
      meta.setAttribute('content', colors[theme] || '#081019');
    }
  })();

  // ── Early text size application (T8 Elder accessibility) ──
  (function applyTextSizeEarly() {
    const sizeMap = {
      'small': '14px',
      'medium': '16px',
      'large': '18px',
      'extra-large': '20px'
    };
    const saved = localStorage.getItem('solace_text_size');
    if (saved && sizeMap[saved]) {
      document.documentElement.style.setProperty('--sb-font-size-base', sizeMap[saved]);
      document.body.style.fontSize = sizeMap[saved];
    }
  })();

  const HEADER_URL = '/partials-header.html';
  const FOOTER_URL = '/partials-footer.html';

  async function injectLayout() {
    const headerSlot = document.getElementById('header-slot');
    const footerSlot = document.getElementById('footer-slot');

    const [headerResp, footerResp] = await Promise.all([
      headerSlot ? fetch(HEADER_URL).then(r => r.text()) : Promise.resolve(''),
      footerSlot ? fetch(FOOTER_URL).then(r => r.text()) : Promise.resolve('')
    ]);

    // Inject skip-nav link for accessibility (WCAG 2.4.1)
    if (!document.querySelector('.skip-nav')) {
      const skipLink = document.createElement('a');
      skipLink.href = '#main-content';
      skipLink.className = 'skip-nav';
      skipLink.textContent = 'Skip to main content';
      document.body.insertBefore(skipLink, document.body.firstChild);
    }

    // Add id="main-content" to the first <main> element for skip-nav target
    const mainEl = document.querySelector('main');
    if (mainEl && !mainEl.id) {
      mainEl.id = 'main-content';
    }

    if (headerSlot && headerResp) {
      headerSlot.innerHTML = headerResp;
    }
    if (footerSlot && footerResp) {
      footerSlot.innerHTML = footerResp;
    }

    wireNavHighlight();
    wireHamburger();
    wireLangSwitcher();
    wireCurrentYear();
    wireAuthStatus();
    wireThemeToggle();
  }

  function wireNavHighlight() {
    const path = window.location.pathname.replace(/\/$/, '') || '/';
    document.querySelectorAll('[data-nav-path]').forEach(function (el) {
      const navPath = el.getAttribute('data-nav-path');
      if (navPath === path) {
        el.classList.add('is-current');
      }
    });
  }

  function wireHamburger() {
    const btn = document.getElementById('hamburger-toggle');
    const menu = document.getElementById('mobile-menu');
    if (!btn || !menu) return;

    btn.addEventListener('click', function () {
      const open = menu.classList.toggle('is-open');
      btn.classList.toggle('is-open', open);
      btn.setAttribute('aria-expanded', String(open));
      document.body.classList.toggle('menu-open', open);
    });

    // Close on Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.classList.contains('is-open')) {
        menu.classList.remove('is-open');
        btn.classList.remove('is-open');
        btn.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('menu-open');
      }
    });

    // Close on link click
    menu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        menu.classList.remove('is-open');
        btn.classList.remove('is-open');
        btn.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('menu-open');
      });
    });
  }

  function wireLangSwitcher() {
    const langBtn = document.getElementById('sb-lang-btn');
    const langMenu = document.getElementById('sb-lang-menu');
    if (!langBtn || !langMenu) return;

    langBtn.addEventListener('click', function () {
      const open = langMenu.classList.toggle('is-open');
      langBtn.setAttribute('aria-expanded', String(open));
    });

    // Close on outside click
    document.addEventListener('click', function (e) {
      if (!langBtn.contains(e.target) && !langMenu.contains(e.target)) {
        langMenu.classList.remove('is-open');
        langBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Handle locale selection (delegate to solace.js i18n if available)
    langMenu.querySelectorAll('[data-locale]').forEach(function (el) {
      el.addEventListener('click', function () {
        const locale = el.getAttribute('data-locale');
        if (typeof window.setLocale === 'function') {
          window.setLocale(locale);
        } else {
          localStorage.setItem('sb_locale', locale);
          window.location.reload();
        }
        langMenu.classList.remove('is-open');
        langBtn.setAttribute('aria-expanded', 'false');
      });
    });

    // Also wire footer language links
    document.querySelectorAll('.footer-section [data-locale]').forEach(function (el) {
      el.addEventListener('click', function () {
        const locale = el.getAttribute('data-locale');
        if (typeof window.setLocale === 'function') {
          window.setLocale(locale);
        } else {
          localStorage.setItem('sb_locale', locale);
          window.location.reload();
        }
      });
    });
  }

  function wireCurrentYear() {
    document.querySelectorAll('[data-current-year]').forEach(function (el) {
      el.textContent = new Date().getFullYear();
    });
  }

  function wireAuthStatus() {
    const el = document.getElementById('sb-auth-status');
    if (!el) return;
    const key = typeof localStorage !== 'undefined' && localStorage.getItem('solace_api_key');
    if (key) {
      el.innerHTML = '<span class="sb-auth-pill sb-auth-pill--signed-in">Signed in</span>';
    }
  }

  function wireThemeToggle() {
    const btn = document.getElementById('sb-theme-toggle');
    const icon = document.getElementById('sb-theme-icon');
    if (!btn || !icon) return;

    const themes = ['dark', 'light', 'midnight'];
    const icons = { dark: '\uD83C\uDF19', light: '\u2600\uFE0F', midnight: '\u2728' };

    function updateIcon() {
      const current = (typeof SolaceTheme !== 'undefined') ? SolaceTheme.get() : (localStorage.getItem('solace-theme') || 'dark');
      icon.textContent = icons[current] || '\uD83C\uDFA8';
    }

    btn.addEventListener('click', function () {
      const current = (typeof SolaceTheme !== 'undefined') ? SolaceTheme.get() : (localStorage.getItem('solace-theme') || 'dark');
      const idx = themes.indexOf(current);
      const next = themes[(idx + 1) % themes.length];
      if (typeof SolaceTheme !== 'undefined') {
        SolaceTheme.set(next);
      } else {
        document.documentElement.setAttribute('data-theme', next);
        localStorage.setItem('solace-theme', next);
        const link = document.getElementById('theme-css');
        if (link) link.href = '/css/themes/' + next + '.css';
      }
      // Update meta theme-color
      const meta = document.querySelector('meta[name="theme-color"]');
      if (meta) {
        const colors = { dark: '#081019', light: '#faf8f5', midnight: '#000000' };
        meta.setAttribute('content', colors[next] || '#081019');
      }
      updateIcon();
    });

    updateIcon();
    if (typeof SolaceTheme !== 'undefined') {
      SolaceTheme.onchange(updateIcon);
    }
  }

  // Run on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectLayout);
  } else {
    injectLayout();
  }
})();
