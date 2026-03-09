/**
 * live-metrics.js — Live Metrics Dashboard frontend for Solace Hub
 * Task 031 | Rung 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
 *   - SVG sparklines INLINE — no canvas, no Chart.js, no D3.
 *   - cpu_pct clamped 0–100, uptime_s >= 0.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin
  var POLL_INTERVAL_MS = 5000;
  var _pollTimer = null;

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
  // Utility: format uptime seconds → "2h 15m 3s"
  // -------------------------------------------------------------------------
  function formatUptime(s) {
    var secs = Math.max(0, Math.floor(Number(s) || 0));
    var h = Math.floor(secs / 3600);
    var m = Math.floor((secs % 3600) / 60);
    var sec = secs % 60;
    var parts = [];
    if (h > 0) { parts.push(h + "h"); }
    if (m > 0 || h > 0) { parts.push(m + "m"); }
    parts.push(sec + "s");
    return parts.join(" ");
  }

  // -------------------------------------------------------------------------
  // Sparkline: compute SVG polyline points from a data series
  //   viewBox is 600 x 80
  // -------------------------------------------------------------------------
  function computeSparklinePoints(series, clampMax) {
    if (!series || series.length === 0) { return ""; }
    var n = series.length;
    var maxVal = clampMax != null ? clampMax : Math.max.apply(null, series);
    if (maxVal <= 0) { maxVal = 1; }
    var pts = [];
    for (var i = 0; i < n; i++) {
      var x = (i / Math.max(1, n - 1)) * 600;
      var raw = Math.max(0, Math.min(maxVal, Number(series[i]) || 0));
      var y = 80 - (raw / maxVal) * 76;   // 2px top padding, 2px bottom padding
      pts.push(x.toFixed(1) + "," + y.toFixed(1));
    }
    return pts.join(" ");
  }

  // -------------------------------------------------------------------------
  // setText — update a DOM element's text safely
  // -------------------------------------------------------------------------
  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) { el.textContent = String(value); }
  }

  // -------------------------------------------------------------------------
  // updateSparkline
  // -------------------------------------------------------------------------
  function updateSparkline(lineId, series, clampMax) {
    var line = document.getElementById(lineId);
    if (!line) { return; }
    line.setAttribute("points", computeSparklinePoints(series, clampMax));
  }

  // -------------------------------------------------------------------------
  // Fetch + render
  // -------------------------------------------------------------------------
  function fetchAndRender() {
    fetch(BASE + "/api/v1/live-metrics", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var uptimeS = Math.max(0, Math.floor(Number(d.uptime_s) || 0));
        var cpuPct  = Math.max(0, Math.min(100, Number(d.cpu_pct) || 0));
        var memMb   = Math.max(0, Number(d.mem_mb) || 0);
        var rps     = Math.max(0, Number(d.rps) || 0);
        var totalReq = d.req_total || 0;
        var totalErr = d.error_total || 0;

        setText("kpi-uptime",    formatUptime(uptimeS));
        setText("kpi-cpu",       cpuPct.toFixed(1) + "%");
        setText("kpi-mem",       memMb.toFixed(1) + " MB");
        setText("kpi-rps",       rps.toFixed(2));
        setText("kpi-total-req", totalReq);
        setText("kpi-total-err", totalErr);

        var ts = document.getElementById("last-updated");
        if (ts) { ts.textContent = "Updated " + new Date().toLocaleTimeString(); }

        updateSparkline("line-cpu", d.cpu_sparkline || [], 100);
        updateSparkline("line-mem", d.mem_sparkline || [], null);
        updateSparkline("line-rps", d.rps_sparkline || [], null);
      });
  }

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  function init() {
    fetchAndRender();
    _pollTimer = setInterval(fetchAndRender, POLL_INTERVAL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
