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

  function loadSnippets() {
    fetch("/api/v1/devtools/snippets", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("dt-snip-list");
        if (!el) { return; }
        el.innerHTML = "";
        var snippets = data.snippets || [];
        if (snippets.length === 0) {
          el.innerHTML = '<p class="dt-empty">No snippets saved.</p>';
          return;
        }
        snippets.forEach(function (s) {
          var div = document.createElement("div");
          div.className = "dt-entry";
          div.innerHTML =
            '<div class="dt-entry-header">' +
              '<span class="dt-entry-title">' + escHtml(s.title) + "</span>" +
              '<span class="dt-badge">' + escHtml(s.language) + "</span>" +
              '<button class="dt-btn dt-btn-delete dt-del-snip" data-id="' + escHtml(s.snippet_id) + '">Delete</button>' +
            "</div>" +
            '<div class="dt-entry-meta">hash: ' + escHtml(s.content_hash.slice(0, 16)) + "… | " + escHtml(s.created_at) + "</div>";
          el.appendChild(div);
        });
        el.addEventListener("click", function (e) {
          var btn = e.target.closest(".dt-del-snip");
          if (!btn) { return; }
          deleteSnippet(btn.getAttribute("data-id"));
        });
      })
      .catch(function (err) { showMsg("dt-snip-msg", "Load error: " + String(err)); });
  }

  function deleteSnippet(id) {
    fetch("/api/v1/devtools/snippets/" + encodeURIComponent(id), {
      method: "DELETE",
      headers: authHeaders(),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadSnippets(); })
      .catch(function (err) { showMsg("dt-snip-msg", "Error: " + String(err)); });
  }

  function onSaveSnippet() {
    var title = ((document.getElementById("dt-snip-title") || {}).value || "").trim();
    var lang = (document.getElementById("dt-snip-lang") || {}).value || "";
    var content = ((document.getElementById("dt-snip-content") || {}).value || "").trim();
    if (!title) { showMsg("dt-snip-msg", "Title required."); return; }
    if (!content) { showMsg("dt-snip-msg", "Content required."); return; }
    fetch("/api/v1/devtools/snippets", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ title: title, language: lang, content: content }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.snippet) {
          showMsg("dt-snip-msg", "Saved: " + escHtml(data.snippet.snippet_id));
          loadSnippets();
        } else {
          showMsg("dt-snip-msg", data.error || "Error");
        }
      })
      .catch(function (err) { showMsg("dt-snip-msg", "Error: " + String(err)); });
  }

  function loadConsoleLogs() {
    fetch("/api/v1/devtools/console-logs", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("dt-log-list");
        if (!el) { return; }
        el.innerHTML = "";
        var logs = data.logs || [];
        if (logs.length === 0) {
          el.innerHTML = '<p class="dt-empty">No console logs.</p>';
          return;
        }
        logs.forEach(function (l) {
          var lvl = l.log_level || "log";
          var badgeClass = lvl === "error" ? "dt-badge-error" : lvl === "warn" ? "dt-badge-warn" : lvl === "info" ? "dt-badge-info" : "";
          var div = document.createElement("div");
          div.className = "dt-entry";
          div.innerHTML =
            '<div class="dt-entry-header">' +
              '<span class="dt-badge ' + escHtml(badgeClass) + '">' + escHtml(lvl) + "</span>" +
              '<span class="dt-entry-title">' + escHtml(l.log_id) + "</span>" +
            "</div>" +
            '<div class="dt-entry-meta">msg_hash: ' + escHtml(l.message_hash.slice(0, 16)) + "… | " + escHtml(l.logged_at) + "</div>";
          el.appendChild(div);
        });
      })
      .catch(function (err) { showMsg("dt-log-msg-out", "Load error: " + String(err)); });
  }

  function onRecordLog() {
    var level = (document.getElementById("dt-log-level") || {}).value || "log";
    var msg = ((document.getElementById("dt-log-msg") || {}).value || "").trim();
    var page = ((document.getElementById("dt-log-page") || {}).value || "").trim();
    if (!msg) { showMsg("dt-log-msg-out", "Message required."); return; }
    fetch("/api/v1/devtools/console-logs", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ log_level: level, message: msg, page_url: page }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.log_id) {
          showMsg("dt-log-msg-out", "Recorded: " + escHtml(data.log_id));
          loadConsoleLogs();
        } else {
          showMsg("dt-log-msg-out", data.error || "Error");
        }
      })
      .catch(function (err) { showMsg("dt-log-msg-out", "Error: " + String(err)); });
  }

  function onClearLogs() {
    if (!confirm("Clear all console logs?")) { return; }
    fetch("/api/v1/devtools/console-logs", {
      method: "DELETE",
      headers: authHeaders(),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showMsg("dt-log-msg-out", "Cleared " + escHtml(String(data.removed || 0)) + " logs.");
        loadConsoleLogs();
      })
      .catch(function (err) { showMsg("dt-log-msg-out", "Error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var saveSnipBtn = document.getElementById("dt-snip-save-btn");
    var logRecordBtn = document.getElementById("dt-log-record-btn");
    var logClearBtn = document.getElementById("dt-log-clear-btn");
    if (saveSnipBtn) { saveSnipBtn.addEventListener("click", onSaveSnippet); }
    if (logRecordBtn) { logRecordBtn.addEventListener("click", onRecordLog); }
    if (logClearBtn) { logClearBtn.addEventListener("click", onClearLogs); }
    loadSnippets();
    loadConsoleLogs();
  });
}());
