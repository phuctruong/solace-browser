/**
 * dark-mode.js — Dark Mode Theme System frontend for Solace Hub
 * Task 029 | Rung 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
 *   - ACCENT_COLORS closed set — only values from server accepted.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin

  var ACCENT_HEX = {
    blue:   "#3b82f6",
    purple: "#8b5cf6",
    green:  "#22c55e",
    orange: "#f97316",
    red:    "#ef4444",
    pink:   "#ec4899",
    teal:   "#14b8a6",
    yellow: "#eab308",
  };

  // -------------------------------------------------------------------------
  // escHtml — sanitize all dynamic content
  // -------------------------------------------------------------------------
  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // -------------------------------------------------------------------------
  // API helpers
  // -------------------------------------------------------------------------
  function apiGet(path) {
    return fetch(BASE + path, { credentials: "same-origin" })
      .then(function (r) {
        return r.json().then(function (d) { return { status: r.status, data: d }; });
      });
  }

  function apiPost(path, body) {
    return fetch(BASE + path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (d) { return { status: r.status, data: d }; });
    });
  }

  // -------------------------------------------------------------------------
  // Banner helpers
  // -------------------------------------------------------------------------
  function showBanner(msg, type) {
    var el = document.getElementById("status-banner");
    if (!el) { return; }
    el.textContent = msg;
    el.className = "status-banner " + escHtml(type);
    setTimeout(function () { el.className = "status-banner hidden"; }, 3000);
  }

  // -------------------------------------------------------------------------
  // Render accent swatches
  // -------------------------------------------------------------------------
  function renderAccents(presets, currentAccent) {
    var grid = document.getElementById("accent-grid");
    if (!grid) { return; }
    grid.innerHTML = "";
    presets.forEach(function (p) {
      var btn = document.createElement("button");
      btn.className = "accent-swatch" + (p.id === currentAccent ? " active" : "");
      btn.title = escHtml(p.name);
      btn.setAttribute("data-accent", p.id);
      var hex = ACCENT_HEX[p.id] || "#888";
      btn.style.setProperty("--swatch-color", hex);
      btn.addEventListener("click", function () {
        apiPost("/api/v1/dark-mode", { accent: p.id }).then(function (res) {
          if (res.status === 200) {
            document.querySelectorAll(".accent-swatch").forEach(function (s) {
              s.classList.toggle("active", s.getAttribute("data-accent") === p.id);
            });
            showBanner("Accent updated to " + escHtml(p.name), "success");
          } else {
            showBanner("Failed to update accent", "error");
          }
        });
      });
      grid.appendChild(btn);
    });
  }

  // -------------------------------------------------------------------------
  // Apply current state to UI
  // -------------------------------------------------------------------------
  function applyState(state) {
    // Mode buttons
    document.querySelectorAll(".mode-btn").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-mode") === state.mode);
    });
    // Font size
    document.querySelectorAll(".size-btn").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-size") === state.font_size);
    });
    // Contrast
    document.querySelectorAll(".contrast-btn").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-contrast") === state.contrast);
    });
    // Accent swatches
    document.querySelectorAll(".accent-swatch").forEach(function (s) {
      s.classList.toggle("active", s.getAttribute("data-accent") === state.accent);
    });
  }

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  function init() {
    // Load current state + presets in parallel
    Promise.all([
      apiGet("/api/v1/dark-mode"),
      apiGet("/api/v1/dark-mode/presets"),
    ]).then(function (results) {
      var stateRes = results[0];
      var presetsRes = results[1];
      var state = stateRes.data;
      var presets = presetsRes.data.presets || [];
      renderAccents(presets, state.accent);
      applyState(state);
    });

    // Mode buttons
    document.querySelectorAll(".mode-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.getAttribute("data-mode");
        apiPost("/api/v1/dark-mode", { mode: mode }).then(function (res) {
          if (res.status === 200) {
            applyState(res.data);
            showBanner("Mode set to " + escHtml(mode), "success");
          } else {
            showBanner((res.data && res.data.error) || "Failed to set mode", "error");
          }
        });
      });
    });

    // Font size buttons
    document.querySelectorAll(".size-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var size = btn.getAttribute("data-size");
        apiPost("/api/v1/dark-mode", { font_size: size }).then(function (res) {
          if (res.status === 200) {
            applyState(res.data);
            showBanner("Font size set to " + escHtml(size), "success");
          } else {
            showBanner((res.data && res.data.error) || "Failed to set font size", "error");
          }
        });
      });
    });

    // Contrast buttons
    document.querySelectorAll(".contrast-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var contrast = btn.getAttribute("data-contrast");
        apiPost("/api/v1/dark-mode", { contrast: contrast }).then(function (res) {
          if (res.status === 200) {
            applyState(res.data);
            showBanner("Contrast set to " + escHtml(contrast), "success");
          } else {
            showBanner((res.data && res.data.error) || "Failed to set contrast", "error");
          }
        });
      });
    });

    // Reset
    var resetBtn = document.getElementById("btn-reset");
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        apiPost("/api/v1/dark-mode/reset", {}).then(function (res) {
          if (res.status === 200) {
            applyState(res.data);
            showBanner("Reset to defaults", "success");
          } else {
            showBanner("Reset failed", "error");
          }
        });
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
