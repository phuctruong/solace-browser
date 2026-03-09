/* Focus Mode — Task 146 | IIFE, no eval */
(function () {
  "use strict";

  const API = "/api/v1/focus";
  const TOKEN = "";

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function headers() {
    return { "Content-Type": "application/json", Authorization: "Bearer " + TOKEN };
  }

  async function loadStats() {
    var r = await fetch(API + "/stats", { headers: headers() });
    var d = await r.json();
    var el = document.getElementById("fcs-stats");
    if (!el) return;
    el.innerHTML =
      '<div class="fcs-stats-grid">' +
      '<div class="fcs-stat"><div class="fcs-stat-val">' + escHtml(d.total_sessions || 0) + '</div><div class="fcs-stat-lbl">Sessions</div></div>' +
      '<div class="fcs-stat"><div class="fcs-stat-val">' + escHtml(d.completed_count || 0) + '</div><div class="fcs-stat-lbl">Completed</div></div>' +
      '<div class="fcs-stat"><div class="fcs-stat-val">' + escHtml(d.total_minutes || "0") + '</div><div class="fcs-stat-lbl">Total Min</div></div>' +
      '<div class="fcs-stat"><div class="fcs-stat-val">' + escHtml(d.avg_minutes || "0.00") + '</div><div class="fcs-stat-lbl">Avg Min</div></div>' +
      "</div>";
  }

  async function loadSessions() {
    var r = await fetch(API + "/sessions", { headers: headers() });
    var d = await r.json();
    var panel = document.getElementById("fcs-panel");
    if (!panel) return;
    if (!d.sessions || d.sessions.length === 0) {
      panel.innerHTML = '<p class="fcs-msg">No focus sessions yet.</p>';
      return;
    }
    panel.innerHTML = d.sessions.map(function (s) {
      var cls = s.status === "active" ? "fcs-status-active" : "fcs-status-completed";
      var endBtn = s.status === "active"
        ? '<button class="fcs-btn fcs-btn-end" onclick="window.fcsEnd(\'' + escHtml(s.session_id) + '\')">End</button>'
        : "";
      return (
        '<div class="fcs-item">' +
        '<div><div class="fcs-item-meta"><span class="' + cls + '">' + escHtml(s.status) + "</span> " +
        escHtml(s.session_type) + " | target: " + escHtml(s.target_minutes) + "min" +
        (s.actual_minutes !== null ? " | actual: " + escHtml(s.actual_minutes) + "min" : "") +
        "</div>" +
        '<div class="fcs-item-id">' + escHtml(s.session_id) + "</div></div>" +
        '<div class="fcs-actions">' + endBtn +
        '<button class="fcs-btn fcs-btn-del" onclick="window.fcsDel(\'' + escHtml(s.session_id) + '\')">Del</button>' +
        "</div></div>"
      );
    }).join("");
  }

  window.fcsEnd = async function (id) {
    var r = await fetch(API + "/sessions/" + encodeURIComponent(id) + "/end", { method: "POST", headers: headers() });
    var d = await r.json();
    var msg = document.getElementById("fcs-msg");
    if (r.ok) {
      if (msg) msg.textContent = "Session ended: " + d.session.actual_minutes + " minutes";
    } else {
      if (msg) msg.textContent = "Error: " + (d.error || "unknown");
    }
    loadSessions();
    loadStats();
  };

  window.fcsDel = async function (id) {
    await fetch(API + "/sessions/" + encodeURIComponent(id), { method: "DELETE", headers: headers() });
    loadSessions();
    loadStats();
  };

  async function startSession(e) {
    e.preventDefault();
    var sessionType = document.getElementById("fcs-session-type").value;
    var targetMin = parseInt(document.getElementById("fcs-target-minutes").value) || 0;
    var r = await fetch(API + "/sessions", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ session_type: sessionType, target_minutes: targetMin }),
    });
    var d = await r.json();
    var msg = document.getElementById("fcs-msg");
    if (r.ok) {
      if (msg) msg.textContent = "Session started: " + d.session.session_id;
      loadSessions();
      loadStats();
    } else {
      if (msg) msg.textContent = "Error: " + (d.error || "unknown");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("fcs-form");
    if (form) form.addEventListener("submit", startSession);
    loadSessions();
    loadStats();
  });
})();
