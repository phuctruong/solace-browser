// Diagram: 02-dashboard-login
/**
 * health-dashboard.js — System Health Dashboard for Solace Hub
 * Task 023 | Rung 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
 *   - cpu_pct is a number 0-100, never a string.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin
  var REFRESH_MS = 15000;
  var refreshTimer = null;

  // ---------------------------------------------------------------------------
  // escHtml — sanitize all dynamic content (REQUIRED by law)
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

  function apiPost(path) {
    return fetch(BASE + path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
    }).then(function (r) {
      return r.json().then(function (d) { return { status: r.status, data: d }; });
    });
  }

  // ---------------------------------------------------------------------------
  // Toast
  // ---------------------------------------------------------------------------
  function showToast(msg) {
    var el = document.getElementById("toast");
    if (!el) { return; }
    el.textContent = msg;
    el.classList.add("toast--visible");
    setTimeout(function () { el.classList.remove("toast--visible"); }, 3000);
  }

  // ---------------------------------------------------------------------------
  // Render overall status
  // ---------------------------------------------------------------------------
  function renderStatus(snapshot) {
    var statusText = document.getElementById("status-text");
    var statusDot = document.getElementById("status-dot");
    var statusMeta = document.getElementById("status-meta");
    if (!statusText) { return; }
    var s = snapshot.status || "unknown";
    statusText.textContent = s.toUpperCase();
    statusDot.className = "status-dot status-dot--" + escHtml(s);
    var ts = snapshot.timestamp || "";
    statusMeta.textContent = "Last checked: " + escHtml(ts);
  }

  // ---------------------------------------------------------------------------
  // Render metrics
  // ---------------------------------------------------------------------------
  function renderMetrics(snapshot) {
    var uptime = document.getElementById("uptime-val");
    var cpu = document.getElementById("cpu-val");
    var mem = document.getElementById("mem-val");
    var req = document.getElementById("req-val");
    if (uptime) { uptime.textContent = String(snapshot.uptime_s || 0) + "s"; }
    if (cpu) { cpu.textContent = (typeof snapshot.cpu_pct === "number" ? snapshot.cpu_pct.toFixed(1) : "0.0") + "%"; }
    if (mem) { mem.textContent = (typeof snapshot.mem_mb === "number" ? snapshot.mem_mb.toFixed(1) : "0.0"); }
    if (req) { req.textContent = String(snapshot.req_count || 0); }
  }

  // ---------------------------------------------------------------------------
  // Render checks table
  // ---------------------------------------------------------------------------
  function renderChecks(checks) {
    var tbody = document.getElementById("checks-tbody");
    if (!tbody) { return; }
    if (!checks || checks.length === 0) {
      tbody.innerHTML = "<tr><td colspan='5' class='empty-state'>No checks.</td></tr>";
      return;
    }
    var rows = checks.map(function (c) {
      var badge = c.passed
        ? "<span class='badge-pass'>PASS</span>"
        : "<span class='badge-fail'>FAIL</span>";
      return "<tr>"
        + "<td>" + escHtml(c.name || c.check_id) + "</td>"
        + "<td>" + escHtml(c.description || "") + "</td>"
        + "<td>" + badge + "</td>"
        + "<td>" + escHtml(c.detail || "") + "</td>"
        + "<td><button class='btn-run' data-check-id='" + escHtml(c.check_id) + "'>Run</button></td>"
        + "</tr>";
    });
    tbody.innerHTML = rows.join("");
    // Attach run buttons
    tbody.querySelectorAll(".btn-run").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var checkId = btn.getAttribute("data-check-id");
        runCheck(checkId);
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Render history table
  // ---------------------------------------------------------------------------
  function renderHistory(history) {
    var tbody = document.getElementById("history-tbody");
    if (!tbody) { return; }
    if (!history || history.length === 0) {
      tbody.innerHTML = "<tr><td colspan='5' class='empty-state'>No history yet.</td></tr>";
      return;
    }
    var reversed = history.slice().reverse();
    var rows = reversed.map(function (h) {
      var badge = h.status === "healthy"
        ? "<span class='badge-pass'>" + escHtml(h.status) + "</span>"
        : "<span class='badge-fail'>" + escHtml(h.status || "unknown") + "</span>";
      return "<tr>"
        + "<td>" + escHtml(h.timestamp || "") + "</td>"
        + "<td>" + badge + "</td>"
        + "<td>" + escHtml(String(h.uptime_s || 0)) + "</td>"
        + "<td>" + escHtml((typeof h.cpu_pct === "number" ? h.cpu_pct.toFixed(1) : "0.0") + "%") + "</td>"
        + "<td>" + escHtml(String(h.req_count || 0)) + "</td>"
        + "</tr>";
    });
    tbody.innerHTML = rows.join("");
  }

  // ---------------------------------------------------------------------------
  // Run a specific check
  // ---------------------------------------------------------------------------
  function runCheck(checkId) {
    apiPost("/api/v1/health/checks/" + encodeURIComponent(checkId) + "/run")
      .then(function (res) {
        if (res.status === 200) {
          showToast(escHtml(checkId) + ": " + (res.data.passed ? "PASS" : "FAIL") + " — " + escHtml(res.data.detail || ""));
          loadAll();
        } else {
          showToast("Error running check " + escHtml(checkId));
        }
      })
      .catch(function () { showToast("Network error"); });
  }

  // ---------------------------------------------------------------------------
  // Load all panels
  // ---------------------------------------------------------------------------
  function loadAll() {
    // Full health (public) — loads status, metrics, checks, and records history
    apiGet("/api/v1/health/full")
      .then(function (res) {
        if (res.status === 200) {
          renderStatus(res.data);
          renderMetrics(res.data);
          renderChecks(res.data.checks || []);
        }
      })
      .catch(function () {
        var el = document.getElementById("status-text");
        if (el) { el.textContent = "UNREACHABLE"; }
      });

    // History (auth-optional — same-origin cookie or no-auth)
    apiGet("/api/v1/health/history")
      .then(function (res) {
        if (res.status === 200) {
          renderHistory(res.data.history || []);
        }
      })
      .catch(function () {});
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  function init() {
    loadAll();
    refreshTimer = setInterval(loadAll, REFRESH_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
