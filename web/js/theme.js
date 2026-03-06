/**
 * theme.js — Solace Browser Theme Engine
 * DNA: theme(choice) = css_vars(tokens) x user_pref(stored) x system_pref(fallback) x a11y(contrast)
 * Rung: 65537 | Belt: Orange
 *
 * Three built-in themes: dark (default), light, midnight
 * Custom themes: paid users can create and submit to app store
 *
 * Public API:
 *   SolaceTheme.init()              — load saved theme or detect system preference
 *   SolaceTheme.set(name)           — switch to named theme
 *   SolaceTheme.get()               — current theme name
 *   SolaceTheme.list()              — available theme names
 *   SolaceTheme.loadCustom(css)     — load custom theme CSS string
 *   SolaceTheme.onchange(callback)  — register theme change listener
 */

const SolaceTheme = (() => {
  "use strict";

  const STORAGE_KEY = "solace-theme";
  const BUILT_IN = ["dark", "light", "midnight"];
  const DEFAULT_THEME = "dark";

  let _current = DEFAULT_THEME;
  let _listeners = [];
  let _customStyleEl = null;

  /**
   * Load theme CSS files. Built-in themes use [data-theme] attribute.
   * Custom themes inject a <style> element.
   */
  function _applyTheme(name) {
    const root = document.documentElement;

    // Remove custom theme style if switching to built-in
    if (BUILT_IN.includes(name)) {
      root.setAttribute("data-theme", name);
      if (_customStyleEl) {
        _customStyleEl.textContent = "";
      }
    }

    // Ensure theme CSS is loaded
    const themeLink = document.getElementById("theme-css");
    if (themeLink && BUILT_IN.includes(name)) {
      themeLink.href = `/css/themes/${name}.css`;
    }

    _current = name;
    localStorage.setItem(STORAGE_KEY, name);

    // Notify listeners
    for (const fn of _listeners) {
      try { fn(name); } catch (e) { console.warn("[Theme] listener error:", e); }
    }
  }

  /**
   * Detect system color scheme preference.
   */
  function _detectSystemTheme() {
    if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
      return "light";
    }
    return "dark";
  }

  return {
    /**
     * Initialize theme system. Call once on page load.
     * Priority: saved preference > system preference > default (dark)
     */
    init() {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved && (BUILT_IN.includes(saved) || saved.startsWith("custom-"))) {
        _applyTheme(saved);
      } else {
        _applyTheme(_detectSystemTheme());
      }

      // Listen for system theme changes
      if (window.matchMedia) {
        window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", (e) => {
          // Only auto-switch if user hasn't set a manual preference
          if (!localStorage.getItem(STORAGE_KEY)) {
            _applyTheme(e.matches ? "light" : "dark");
          }
        });
      }
    },

    /**
     * Switch to a named theme.
     * @param {string} name - "dark", "light", "midnight", or "custom-{id}"
     */
    set(name) {
      if (!BUILT_IN.includes(name) && !name.startsWith("custom-")) {
        console.warn(`[Theme] Unknown theme: ${name}. Available: ${BUILT_IN.join(", ")}`);
        return;
      }
      _applyTheme(name);
    },

    /** Get current theme name. */
    get() { return _current; },

    /** List available built-in themes. */
    list() { return [...BUILT_IN]; },

    /**
     * Load a custom theme CSS string (paid users only).
     * @param {string} css - CSS custom property overrides
     * @param {string} id - unique theme identifier
     */
    loadCustom(css, id) {
      if (!_customStyleEl) {
        _customStyleEl = document.createElement("style");
        _customStyleEl.id = "custom-theme-css";
        document.head.appendChild(_customStyleEl);
      }
      // Wrap in [data-theme="custom-{id}"] selector
      const safeName = `custom-${id}`;
      _customStyleEl.textContent = `[data-theme="${safeName}"] { ${css} }`;
      _applyTheme(safeName);
    },

    /**
     * Register a callback for theme changes.
     * @param {function} fn - receives theme name as argument
     */
    onchange(fn) {
      if (typeof fn === "function") {
        _listeners.push(fn);
      }
    },

    /**
     * Get theme metadata for display.
     */
    meta(name) {
      const themes = {
        dark: { label: "Dark", description: "Deep navy with warm orange accents", icon: "moon" },
        light: { label: "Light", description: "Clean white with warm tones", icon: "sun" },
        midnight: { label: "Midnight", description: "True black with electric blue", icon: "stars" },
      };
      return themes[name] || { label: name, description: "Custom theme", icon: "palette" };
    },
  };
})();

// Auto-initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => SolaceTheme.init());
} else {
  SolaceTheme.init();
}
