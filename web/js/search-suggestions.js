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

  function loadPopular() {
    fetch("/api/v1/search-suggestions/popular")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("ss-popular");
        if (!el) { return; }
        el.innerHTML = "";
        var popular = data.popular || [];
        if (popular.length === 0) {
          el.innerHTML = '<p class="ss-empty">No popular searches yet.</p>';
          return;
        }
        popular.forEach(function (item) {
          var div = document.createElement("div");
          div.className = "ss-entry";
          div.innerHTML = escHtml(item.query_hash.slice(0, 12) + "…") + " <strong>" + escHtml(String(item.count)) + "</strong>";
          el.appendChild(div);
        });
      })
      .catch(function (err) { showMsg("ss-record-msg", "Error: " + String(err)); });
  }

  function loadStats() {
    fetch("/api/v1/search-suggestions/stats", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("ss-stats");
        if (!el) { return; }
        el.innerHTML =
          '<div class="ss-stat-row"><span class="ss-stat-label">Total Searches</span><span class="ss-stat-value">' + escHtml(String(data.total_searches || 0)) + "</span></div>" +
          '<div class="ss-stat-row"><span class="ss-stat-label">Unique Hashes</span><span class="ss-stat-value">' + escHtml(String(data.unique_hashes || 0)) + "</span></div>" +
          '<div class="ss-stat-row"><span class="ss-stat-label">Last Searched</span><span class="ss-stat-value">' + escHtml(data.last_searched_at || "—") + "</span></div>";
      })
      .catch(function (err) { showMsg("ss-record-msg", "Stats error: " + String(err)); });
  }

  function onRecord() {
    var query = (document.getElementById("ss-query") || {}).value || "";
    var engine = (document.getElementById("ss-engine") || {}).value || "";
    var cnt = parseInt((document.getElementById("ss-result-count") || {}).value || "0", 10);
    if (!query.trim()) { showMsg("ss-record-msg", "Query required."); return; }
    fetch("/api/v1/search-suggestions/record", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ query: query, engine_url: engine, result_count: cnt }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.search_id) {
          showMsg("ss-record-msg", "Recorded: " + escHtml(data.search_id));
          loadPopular();
          loadStats();
        } else {
          showMsg("ss-record-msg", data.error || "Error");
        }
      })
      .catch(function (err) { showMsg("ss-record-msg", "Error: " + String(err)); });
  }

  function onSuggest() {
    var prefix = (document.getElementById("ss-prefix") || {}).value || "";
    fetch("/api/v1/search-suggestions/suggest?q=" + encodeURIComponent(prefix))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("ss-suggestions");
        if (!el) { return; }
        el.innerHTML = "";
        var suggestions = data.suggestions || [];
        if (suggestions.length === 0) {
          el.innerHTML = '<p class="ss-empty">No suggestions.</p>';
          return;
        }
        suggestions.forEach(function (s) {
          var div = document.createElement("div");
          div.className = "ss-entry";
          div.textContent = s.query_hash;
          el.appendChild(div);
        });
      })
      .catch(function (err) { showMsg("ss-record-msg", "Error: " + String(err)); });
  }

  function onClear() {
    if (!confirm("Clear all search history?")) { return; }
    fetch("/api/v1/search-suggestions/history", {
      method: "DELETE",
      headers: authHeaders(),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showMsg("ss-record-msg", "Cleared " + escHtml(String(data.removed || 0)) + " entries.");
        loadPopular();
        loadStats();
      })
      .catch(function (err) { showMsg("ss-record-msg", "Error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var recordBtn = document.getElementById("ss-record-btn");
    var suggestBtn = document.getElementById("ss-suggest-btn");
    var popularBtn = document.getElementById("ss-popular-btn");
    var clearBtn = document.getElementById("ss-clear-btn");
    if (recordBtn) { recordBtn.addEventListener("click", onRecord); }
    if (suggestBtn) { suggestBtn.addEventListener("click", onSuggest); }
    if (popularBtn) { popularBtn.addEventListener("click", loadPopular); }
    if (clearBtn) { clearBtn.addEventListener("click", onClear); }
    loadPopular();
    loadStats();
  });
}());
