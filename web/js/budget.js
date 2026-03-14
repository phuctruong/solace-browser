// Diagram: 02-dashboard-login
/**
 * budget.js — Budget Controls frontend for Solace Hub
 * Task 020 | Rung 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
 *   - All monetary values displayed as strings (from API). Never format as float.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin

  // ---------------------------------------------------------------------------
  // escHtml — sanitize all dynamic content
  // ---------------------------------------------------------------------------
  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ---------------------------------------------------------------------------
  // API helpers
  // ---------------------------------------------------------------------------
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

  // ---------------------------------------------------------------------------
  // Toast
  // ---------------------------------------------------------------------------
  var toastEl = document.getElementById("toast");
  var toastTimer = null;

  function showToast(msg, type) {
    if (!toastEl) { return; }
    toastEl.textContent = escHtml(msg);
    toastEl.className = "toast show toast--" + escHtml(type || "success");
    if (toastTimer) { clearTimeout(toastTimer); }
    toastTimer = setTimeout(function () {
      toastEl.className = "toast";
    }, 3000);
  }

  // ---------------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------------
  var todaySpendEl = document.getElementById("today-spend");
  var monthSpendEl = document.getElementById("month-spend");
  var dailyLimitDisplayEl = document.getElementById("daily-limit-display");
  var monthlyLimitDisplayEl = document.getElementById("monthly-limit-display");
  var dailyBadgeEl = document.getElementById("daily-badge");
  var monthlyBadgeEl = document.getElementById("monthly-badge");
  var dailyBarEl = document.getElementById("daily-bar");
  var monthlyBarEl = document.getElementById("monthly-bar");
  var warningBannerEl = document.getElementById("warning-banner");
  var dangerBannerEl = document.getElementById("danger-banner");

  var inputDailyEl = document.getElementById("input-daily");
  var inputMonthlyEl = document.getElementById("input-monthly");
  var inputPauseEl = document.getElementById("input-pause");

  var btnSaveEl = document.getElementById("btn-save");
  var btnResetEl = document.getElementById("btn-reset");

  var confirmDialogEl = document.getElementById("confirm-dialog");
  var btnCancelEl = document.getElementById("btn-cancel");
  var btnConfirmResetEl = document.getElementById("btn-confirm-reset");

  // ---------------------------------------------------------------------------
  // Progress bar helpers — pct is a string from API (e.g. "0.2345")
  // ---------------------------------------------------------------------------
  function pctToWidth(pctStr) {
    var n = parseFloat(pctStr);
    if (isNaN(n)) { return 0; }
    return Math.min(Math.round(n * 100), 100);
  }

  function barClass(pctStr, exceeded) {
    if (exceeded) { return "progress-fill exceeded"; }
    var n = parseFloat(pctStr);
    if (!isNaN(n) && n >= 0.8) { return "progress-fill warn"; }
    return "progress-fill";
  }

  function badgeText(exceeded, alert) {
    if (exceeded) { return "exceeded"; }
    if (alert) { return "warning"; }
    return "ok";
  }

  function badgeClass(exceeded, alert) {
    if (exceeded) { return "status-badge status-badge--exceeded"; }
    if (alert) { return "status-badge status-badge--warn"; }
    return "status-badge status-badge--ok";
  }

  // ---------------------------------------------------------------------------
  // Render usage
  // ---------------------------------------------------------------------------
  function renderUsage(data) {
    // All amounts come from API as strings — display exactly as-is (never as float)
    if (todaySpendEl) { todaySpendEl.textContent = escHtml(data.today_spend_usd || "0.000000"); }
    if (monthSpendEl) { monthSpendEl.textContent = escHtml(data.month_spend_usd || "0.000000"); }
    if (dailyLimitDisplayEl) { dailyLimitDisplayEl.textContent = escHtml(data.daily_limit_usd || "—"); }
    if (monthlyLimitDisplayEl) { monthlyLimitDisplayEl.textContent = escHtml(data.monthly_limit_usd || "—"); }

    var dailyExceeded = !!data.daily_exceeded;
    var monthlyExceeded = !!data.monthly_exceeded;
    var dailyAlert = !!data.daily_alert;
    var monthlyAlert = !!data.monthly_alert;

    if (dailyBadgeEl) {
      dailyBadgeEl.textContent = badgeText(dailyExceeded, dailyAlert);
      dailyBadgeEl.className = badgeClass(dailyExceeded, dailyAlert);
    }
    if (monthlyBadgeEl) {
      monthlyBadgeEl.textContent = badgeText(monthlyExceeded, monthlyAlert);
      monthlyBadgeEl.className = badgeClass(monthlyExceeded, monthlyAlert);
    }

    if (dailyBarEl) {
      dailyBarEl.style.width = pctToWidth(data.daily_pct) + "%";
      dailyBarEl.className = barClass(data.daily_pct, dailyExceeded);
    }
    if (monthlyBarEl) {
      monthlyBarEl.style.width = pctToWidth(data.monthly_pct) + "%";
      monthlyBarEl.className = barClass(data.monthly_pct, monthlyExceeded);
    }

    // Warning banner: >80% but not exceeded
    var showWarning = (dailyAlert || monthlyAlert) && !(dailyExceeded || monthlyExceeded);
    var showDanger = dailyExceeded || monthlyExceeded;

    if (warningBannerEl) {
      warningBannerEl.className = "warning-banner" + (showWarning ? " show" : "");
    }
    if (dangerBannerEl) {
      dangerBannerEl.className = "danger-banner" + (showDanger ? " show" : "");
    }
  }

  // ---------------------------------------------------------------------------
  // Render settings into form
  // ---------------------------------------------------------------------------
  function renderSettings(data) {
    // Display string values directly — never parse as float
    if (inputDailyEl) { inputDailyEl.value = data.daily_limit_usd || ""; }
    if (inputMonthlyEl) { inputMonthlyEl.value = data.monthly_limit_usd || ""; }
    if (inputPauseEl) { inputPauseEl.checked = !!data.pause_on_exceeded; }
  }

  // ---------------------------------------------------------------------------
  // Load usage + settings
  // ---------------------------------------------------------------------------
  function loadAll() {
    apiGet("/api/v1/budget/usage").then(function (res) {
      if (res.status === 200) {
        renderUsage(res.data);
      } else {
        showToast("Failed to load usage data", "error");
      }
    }).catch(function () {
      showToast("Network error loading usage", "error");
    });

    apiGet("/api/v1/budget").then(function (res) {
      if (res.status === 200) {
        renderSettings(res.data);
      }
    }).catch(function () {
      // settings load failure is non-fatal
    });
  }

  // ---------------------------------------------------------------------------
  // Save settings
  // ---------------------------------------------------------------------------
  if (btnSaveEl) {
    btnSaveEl.addEventListener("click", function () {
      var daily = inputDailyEl ? inputDailyEl.value.trim() : "";
      var monthly = inputMonthlyEl ? inputMonthlyEl.value.trim() : "";
      var pause = inputPauseEl ? inputPauseEl.checked : true;

      // Basic client-side validation — only digits + optional decimal
      var numPattern = /^\d+(\.\d+)?$/;
      if (daily && !numPattern.test(daily)) {
        showToast("Daily limit must be a non-negative number (e.g. 10.00)", "error");
        return;
      }
      if (monthly && !numPattern.test(monthly)) {
        showToast("Monthly limit must be a non-negative number (e.g. 100.00)", "error");
        return;
      }

      var payload = { pause_on_exceeded: pause };
      // Send values as strings — server accepts string Decimals (Task 020 law)
      if (daily) { payload.daily_limit_usd = daily; }
      if (monthly) { payload.monthly_limit_usd = monthly; }

      btnSaveEl.disabled = true;
      apiPost("/api/v1/budget", payload).then(function (res) {
        btnSaveEl.disabled = false;
        if (res.status === 200) {
          showToast("Budget settings saved", "success");
          loadAll();
        } else {
          var msg = (res.data && res.data.error) ? res.data.error : "Failed to save settings";
          showToast(escHtml(msg), "error");
        }
      }).catch(function () {
        btnSaveEl.disabled = false;
        showToast("Network error saving settings", "error");
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Reset (with confirmation dialog)
  // ---------------------------------------------------------------------------
  if (btnResetEl) {
    btnResetEl.addEventListener("click", function () {
      if (confirmDialogEl) { confirmDialogEl.className = "dialog-overlay active"; }
    });
  }

  if (btnCancelEl) {
    btnCancelEl.addEventListener("click", function () {
      if (confirmDialogEl) { confirmDialogEl.className = "dialog-overlay"; }
    });
  }

  if (confirmDialogEl) {
    confirmDialogEl.addEventListener("click", function (e) {
      if (e.target === confirmDialogEl) {
        confirmDialogEl.className = "dialog-overlay";
      }
    });
  }

  if (btnConfirmResetEl) {
    btnConfirmResetEl.addEventListener("click", function () {
      if (confirmDialogEl) { confirmDialogEl.className = "dialog-overlay"; }
      btnConfirmResetEl.disabled = true;
      apiPost("/api/v1/budget/reset", {}).then(function (res) {
        btnConfirmResetEl.disabled = false;
        if (res.status === 200) {
          showToast("Budget reset to defaults", "success");
          loadAll();
        } else {
          showToast("Failed to reset budget", "error");
        }
      }).catch(function () {
        btnConfirmResetEl.disabled = false;
        showToast("Network error resetting budget", "error");
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Keyboard: Escape closes dialog
  // ---------------------------------------------------------------------------
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && confirmDialogEl) {
      confirmDialogEl.className = "dialog-overlay";
    }
  });

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  loadAll();

}());
