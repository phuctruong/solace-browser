// Diagram: 02-dashboard-login
(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var TOKEN = "";

  function authHeaders() {
    var h = { "Content-Type": "application/json" };
    if (TOKEN) { h["Authorization"] = "Bearer " + TOKEN; }
    return h;
  }

  function showMsg(id, msg) {
    var el = document.getElementById(id);
    if (!el) { return; }
    el.textContent = msg;
    el.hidden = false;
  }

  function loadHistory() {
    fetch("/api/v1/page-summarizer/history", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("aps-history");
        if (!el) { return; }
        el.innerHTML = "";
        var summaries = data.summaries || [];
        if (summaries.length === 0) {
          el.innerHTML = '<p class="aps-empty">No summaries yet.</p>';
          return;
        }
        summaries.forEach(function (s) {
          var div = document.createElement("div");
          div.className = "aps-card";
          div.innerHTML =
            '<div class="aps-card-header">' +
              '<span class="aps-card-id">' + escHtml(s.summary_id) + "</span>" +
              '<span class="aps-badge">' + escHtml(s.model) + "</span>" +
              '<span class="aps-badge">' + escHtml(s.length_type) + "</span>" +
              '<button class="aps-btn aps-btn-delete aps-del-btn" data-id="' + escHtml(s.summary_id) + '">Delete</button>' +
            "</div>" +
            '<div class="aps-card-meta">' +
              "url_hash: " + escHtml(s.url_hash.slice(0, 12)) + "… | words: " + escHtml(String(s.word_count)) + " | " + escHtml(s.created_at) +
            "</div>";
          el.appendChild(div);
        });
        el.addEventListener("click", function (e) {
          var btn = e.target.closest(".aps-del-btn");
          if (!btn) { return; }
          deleteSummary(btn.getAttribute("data-id"));
        });
      })
      .catch(function (err) { showMsg("aps-record-msg", "Load error: " + String(err)); });
  }

  function deleteSummary(id) {
    fetch("/api/v1/page-summarizer/history/" + encodeURIComponent(id), {
      method: "DELETE",
      headers: authHeaders(),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadHistory(); loadStats(); })
      .catch(function (err) { showMsg("aps-record-msg", "Error: " + String(err)); });
  }

  function loadStats() {
    fetch("/api/v1/page-summarizer/stats", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("aps-stats");
        if (!el) { return; }
        el.innerHTML =
          '<div class="aps-stat-item"><div class="aps-stat-label">Total</div><div class="aps-stat-value">' + escHtml(String(data.total || 0)) + "</div></div>";
        var byModel = data.by_model || {};
        Object.keys(byModel).forEach(function (model) {
          var item = document.createElement("div");
          item.className = "aps-stat-item";
          item.innerHTML = '<div class="aps-stat-label">' + escHtml(model) + "</div><div class=\"aps-stat-value\">" + escHtml(String(byModel[model])) + "</div>";
          el.appendChild(item);
        });
      })
      .catch(function (err) { showMsg("aps-record-msg", "Stats error: " + String(err)); });
  }

  function onRecord() {
    var model = (document.getElementById("aps-model") || {}).value || "sonnet";
    var lengthType = (document.getElementById("aps-length-type") || {}).value || "standard";
    var pageUrl = ((document.getElementById("aps-page-url") || {}).value || "").trim();
    var pageTitle = ((document.getElementById("aps-page-title") || {}).value || "").trim();
    var summaryText = ((document.getElementById("aps-summary") || {}).value || "").trim();
    var wordCount = parseInt(((document.getElementById("aps-word-count") || {}).value || "0"), 10);

    if (!pageUrl) { showMsg("aps-record-msg", "Page URL required."); return; }
    if (!summaryText) { showMsg("aps-record-msg", "Summary required."); return; }

    fetch("/api/v1/page-summarizer/summarize", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        model: model,
        length_type: lengthType,
        page_url: pageUrl,
        page_title: pageTitle,
        summary: summaryText,
        word_count: wordCount,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.summary_id) {
          showMsg("aps-record-msg", "Recorded: " + escHtml(data.summary_id));
          loadHistory();
          loadStats();
        } else {
          showMsg("aps-record-msg", data.error || "Error");
        }
      })
      .catch(function (err) { showMsg("aps-record-msg", "Error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var recordBtn = document.getElementById("aps-record-btn");
    if (recordBtn) { recordBtn.addEventListener("click", onRecord); }
    loadHistory();
    loadStats();
  });
}());
