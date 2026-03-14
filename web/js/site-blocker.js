// Diagram: 02-dashboard-login
"use strict";
/* Site Blocker — Task 065 */
(function () {
  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  var SB = {
    async showRules() {
      var r = await fetch("/api/v1/blocker/rules");
      var data = await r.json();
      var el = document.getElementById("sb-content");
      if (!el) return;
      if (!data.rules || data.rules.length === 0) {
        el.textContent = "No blocking rules configured.";
        return;
      }
      el.innerHTML = data.rules.map(function (rule) {
        return '<div class="sb-rule">' +
          '<span class="sb-rule-pattern">' + escHtml(rule.pattern || "(no pattern)") + "</span>" +
          '<span class="sb-rule-type">' + escHtml(rule.rule_type) + "</span>" +
          '<span class="sb-rule-cat">' + escHtml(rule.category) + "</span>" +
          "</div>";
      }).join("");
      var statusEl = document.getElementById("sb-status");
      if (statusEl) statusEl.textContent = "Total rules: " + data.total;
    },
    async showLog() {
      var r = await fetch("/api/v1/blocker/log");
      var data = await r.json();
      var el = document.getElementById("sb-content");
      if (!el) return;
      if (!data.log || data.log.length === 0) {
        el.textContent = "No blocked requests logged.";
        return;
      }
      el.innerHTML = data.log.map(function (entry) {
        return '<div class="sb-rule">' +
          '<span class="sb-rule-pattern">' + escHtml(entry.url_hash.slice(0, 24)) + "...</span>" +
          '<span class="sb-rule-type">' + escHtml(entry.matched_rule_id) + "</span>" +
          "</div>";
      }).join("");
      var statusEl = document.getElementById("sb-status");
      if (statusEl) statusEl.textContent = "Blocked requests: " + data.total;
    },
    init() {
      var btnRules = document.getElementById("btn-sb-rules");
      if (btnRules) btnRules.addEventListener("click", function () { SB.showRules(); });
      var btnLog = document.getElementById("btn-sb-log");
      if (btnLog) btnLog.addEventListener("click", function () { SB.showLog(); });
      SB.showRules();
    },
  };

  document.addEventListener("DOMContentLoaded", function () { SB.init(); });
})();
