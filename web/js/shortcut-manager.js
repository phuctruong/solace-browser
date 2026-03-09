"use strict";
/* Shortcut Manager — Task 066 */
(function () {
  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  var SC = {
    async showShortcuts() {
      var r = await fetch("/api/v1/shortcuts");
      var data = await r.json();
      var el = document.getElementById("sc-content");
      if (!el) return;
      if (!data.shortcuts || data.shortcuts.length === 0) {
        el.textContent = "No shortcuts found.";
        return;
      }
      el.innerHTML = data.shortcuts.map(function (s) {
        return '<div class="sc-item">' +
          '<span class="sc-item-keys">' + escHtml(s.keys) + "</span>" +
          '<span class="sc-item-desc">' + escHtml(s.description || s.action) + "</span>" +
          '<span class="sc-item-action">' + escHtml(s.action) + "</span>" +
          '<span class="sc-item-count">' + (s.trigger_count || 0) + " uses</span>" +
          "</div>";
      }).join("");
      var statusEl = document.getElementById("sc-status");
      if (statusEl) statusEl.textContent = "Total shortcuts: " + data.total;
    },
    async showStats() {
      var r = await fetch("/api/v1/shortcuts/stats");
      var data = await r.json();
      var el = document.getElementById("sc-status");
      if (el) {
        el.textContent = "Total: " + data.total_shortcuts +
          " | Triggers: " + data.total_triggers +
          " | Most used: " + (data.most_used_keys || "none");
      }
    },
    init() {
      var btnList = document.getElementById("btn-sc-list");
      if (btnList) btnList.addEventListener("click", function () { SC.showShortcuts(); });
      var btnStats = document.getElementById("btn-sc-stats");
      if (btnStats) btnStats.addEventListener("click", function () { SC.showStats(); });
      SC.showShortcuts();
    },
  };

  document.addEventListener("DOMContentLoaded", function () { SC.init(); });
})();
