/* layout.js — Shared header/footer injection for all Solace Browser pages
 * Fetches _header.html and _footer.html, injects them, then wires up
 * hamburger menu, language switcher, nav highlighting, and current year.
 */
(function () {
  'use strict';

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
      var skipLink = document.createElement('a');
      skipLink.href = '#main-content';
      skipLink.className = 'skip-nav';
      skipLink.textContent = 'Skip to main content';
      document.body.insertBefore(skipLink, document.body.firstChild);
    }

    // Add id="main-content" to the first <main> element for skip-nav target
    var mainEl = document.querySelector('main');
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
    var langBtn = document.getElementById('sb-lang-btn');
    var langMenu = document.getElementById('sb-lang-menu');
    if (!langBtn || !langMenu) return;

    langBtn.addEventListener('click', function () {
      var open = langMenu.classList.toggle('is-open');
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
        var locale = el.getAttribute('data-locale');
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
        var locale = el.getAttribute('data-locale');
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
    var el = document.getElementById('sb-auth-status');
    if (!el) return;
    var key = typeof localStorage !== 'undefined' && localStorage.getItem('solace_api_key');
    if (key) {
      el.innerHTML = '<span class="sb-auth-pill sb-auth-pill--signed-in">Signed in</span>';
    }
  }

  // Run on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectLayout);
  } else {
    injectLayout();
  }
})();
