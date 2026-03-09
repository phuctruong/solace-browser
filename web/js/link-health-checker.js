(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderStats(stats) {
    var el = document.getElementById("lhc-stats");
    if (!el) return;
    el.innerHTML = [
      ["Total Checks", escHtml(stats.total_checks)],
      ["Broken", escHtml(stats.broken_count)],
      ["Healthy", escHtml(stats.healthy_count)],
      ["Broken Rate", escHtml(stats.broken_rate) + "%"],
      ["Avg Response", escHtml(stats.avg_response_ms) + "ms"],
    ].map(function (pair) {
      return (
        '<div class="lhc-stat-card">' +
        '<div class="lhc-stat-value">' + pair[1] + "</div>" +
        '<div class="lhc-stat-label">' + pair[0] + "</div>" +
        "</div>"
      );
    }).join("");
  }

  function renderList(checks) {
    var el = document.getElementById("lhc-list");
    if (!el) return;
    if (!checks || checks.length === 0) {
      el.innerHTML = '<p style="color:var(--hub-text-muted)">No checks recorded yet.</p>';
      return;
    }
    el.innerHTML = checks.slice(-50).reverse().map(function (c) {
      var cls = c.is_broken ? "broken" : "healthy";
      return (
        '<div class="lhc-item ' + escHtml(cls) + '">' +
        "<strong>Status " + escHtml(c.status_code) + "</strong> — " +
        escHtml(c.response_ms) + "ms — " +
        escHtml(c.checked_at) +
        "</div>"
      );
    }).join("");
  }

  function renderCodes(codes) {
    var el = document.getElementById("lhc-codes");
    if (!el || !codes) return;
    el.innerHTML = codes.map(function (code) {
      return '<span class="lhc-badge">' + escHtml(code) + "</span>";
    }).join("");
  }

  function loadData() {
    fetch("/api/v1/link-health/status-codes")
      .then(function (r) { return r.json(); })
      .then(function (d) { renderCodes(d.status_codes); })
      .catch(function () {});

    fetch("/api/v1/link-health/stats")
      .then(function (r) { return r.json(); })
      .then(function (d) { renderStats(d); })
      .catch(function () {});

    fetch("/api/v1/link-health/checks")
      .then(function (r) { return r.json(); })
      .then(function (d) { renderList(d.checks); })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadData();
  });
}());
