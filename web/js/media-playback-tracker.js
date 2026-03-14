// Diagram: 02-dashboard-login
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
    var el = document.getElementById("mpt-stats");
    if (!el) return;
    el.innerHTML = [
      ["Total Sessions", escHtml(stats.total_sessions)],
      ["Avg Watched", escHtml(stats.avg_watched_pct) + "%"],
      ["Total Hours", escHtml(stats.total_watched_hours) + "h"],
    ].map(function (pair) {
      return (
        '<div class="mpt-stat-card">' +
        '<div class="mpt-stat-value">' + pair[1] + "</div>" +
        '<div class="mpt-stat-label">' + pair[0] + "</div>" +
        "</div>"
      );
    }).join("");
  }

  function renderList(sessions) {
    var el = document.getElementById("mpt-list");
    if (!el) return;
    if (!sessions || sessions.length === 0) {
      el.innerHTML = '<p style="color:var(--hub-text-muted)">No sessions recorded yet.</p>';
      return;
    }
    el.innerHTML = sessions.slice(-50).reverse().map(function (s) {
      return (
        '<div class="mpt-item">' +
        "<strong>" + escHtml(s.media_type) + "</strong> — " +
        escHtml(s.event_type) + " — " +
        escHtml(s.watched_pct) + "% watched — " +
        escHtml(s.recorded_at) +
        "</div>"
      );
    }).join("");
  }

  function renderTypes(types) {
    var el = document.getElementById("mpt-types");
    if (!el || !types) return;
    el.innerHTML = types.map(function (t) {
      return '<span class="mpt-badge">' + escHtml(t) + "</span>";
    }).join("");
  }

  function loadData() {
    fetch("/api/v1/media-tracker/media-types")
      .then(function (r) { return r.json(); })
      .then(function (d) { renderTypes(d.media_types); })
      .catch(function () {});

    fetch("/api/v1/media-tracker/stats")
      .then(function (r) { return r.json(); })
      .then(function (d) { renderStats(d); })
      .catch(function () {});

    fetch("/api/v1/media-tracker/sessions")
      .then(function (r) { return r.json(); })
      .then(function (d) { renderList(d.sessions); })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadData();
  });
}());
