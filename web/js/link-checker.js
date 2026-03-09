(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var API_BASE = "/api/v1/link-checker";

  function showStatus(msg) {
    var el = document.getElementById("lck-status-msg");
    if (el) { el.textContent = msg; }
  }

  function loadStatuses() {
    fetch(API_BASE + "/statuses")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById("lck-status");
        if (!sel) { return; }
        (data.statuses || []).forEach(function (s) {
          var o = document.createElement("option");
          o.value = s;
          o.textContent = s;
          sel.appendChild(o);
        });
      })
      .catch(function (err) { showStatus("Failed to load statuses: " + String(err)); });
  }

  function badgeClass(status) {
    if (status === "ok") { return "lck-badge lck-badge-ok"; }
    if (status === "broken") { return "lck-badge lck-badge-broken"; }
    if (status === "redirect") { return "lck-badge lck-badge-redirect"; }
    return "lck-badge lck-badge-default";
  }

  function renderCheck(c) {
    var div = document.createElement("div");
    div.className = "lck-card";
    div.setAttribute("data-id", c.check_id);
    var httpCode = c.http_code != null ? String(c.http_code) : "—";
    div.innerHTML =
      '<div>' +
        '<div class="lck-card-meta">' +
          '<span class="' + badgeClass(c.status) + '">' + escHtml(c.status) + '</span>' +
          '<span class="lck-badge lck-badge-default">HTTP ' + escHtml(httpCode) + '</span>' +
          '<span class="lck-badge lck-badge-default">' + escHtml(String(c.response_ms)) + 'ms</span>' +
        '</div>' +
        '<div class="lck-card-id">ID: ' + escHtml(c.check_id) + '</div>' +
      '</div>' +
      '<button class="lck-btn lck-btn-danger lck-del-btn" data-id="' + escHtml(c.check_id) + '">Delete</button>';
    return div;
  }

  function loadStats() {
    fetch(API_BASE + "/stats")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var bar = document.getElementById("lck-stats-bar");
        if (!bar) { return; }
        bar.innerHTML =
          '<div class="lck-stat-item"><span class="lck-stat-value">' + escHtml(String(data.total_checks || 0)) + '</span><span class="lck-stat-label">Total</span></div>' +
          '<div class="lck-stat-item"><span class="lck-stat-value">' + escHtml(String(data.broken_count || 0)) + '</span><span class="lck-stat-label">Broken</span></div>' +
          '<div class="lck-stat-item"><span class="lck-stat-value">' + escHtml(String(data.avg_response_ms || "0")) + '</span><span class="lck-stat-label">Avg ms</span></div>';
      })
      .catch(function () { /* stats optional */ });
  }

  function loadChecks() {
    fetch(API_BASE + "/checks")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("lck-list");
        if (!list) { return; }
        list.innerHTML = "";
        var checks = data.checks || [];
        if (checks.length === 0) {
          list.innerHTML = '<p class="lck-empty">No checks recorded.</p>';
          return;
        }
        checks.slice(-50).reverse().forEach(function (c) { list.appendChild(renderCheck(c)); });
        attachDeleteHandlers();
      })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function attachDeleteHandlers() {
    document.querySelectorAll(".lck-del-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var cid = btn.getAttribute("data-id");
        fetch(API_BASE + "/checks/" + encodeURIComponent(cid), { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function () { showStatus("Deleted."); loadChecks(); loadStats(); })
          .catch(function (err) { showStatus("Delete error: " + String(err)); });
      });
    });
  }

  function handleSubmit(e) {
    e.preventDefault();
    var urlHash = document.getElementById("lck-url-hash").value.trim();
    var pageHash = document.getElementById("lck-page-hash").value.trim();
    var status = document.getElementById("lck-status").value;
    var httpCodeRaw = document.getElementById("lck-http-code").value.trim();
    var httpCode = httpCodeRaw ? parseInt(httpCodeRaw, 10) : null;
    var responseMs = parseInt(document.getElementById("lck-response-ms").value, 10) || 0;

    fetch(API_BASE + "/checks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url_hash: urlHash,
        page_hash: pageHash,
        status: status,
        http_code: httpCode,
        response_ms: responseMs,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { showStatus("Error: " + data.error); return; }
        showStatus("Check recorded.");
        loadChecks();
        loadStats();
      })
      .catch(function (err) { showStatus("Record error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadStatuses();
    loadStats();
    loadChecks();
    var form = document.getElementById("lck-form");
    if (form) { form.addEventListener("submit", handleSubmit); }
  });
})();
