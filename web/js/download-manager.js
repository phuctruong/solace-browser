(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var API_BASE = "/api/v1/downloads";

  function showStatus(msg) {
    var el = document.getElementById("dm-status");
    if (el) { el.textContent = msg; }
  }

  function badgeClass(status) {
    var map = {
      completed: "dm-badge-completed",
      failed: "dm-badge-failed",
      cancelled: "dm-badge-cancelled",
      downloading: "dm-badge-downloading",
    };
    return map[status] || "";
  }

  function renderEntry(entry) {
    var div = document.createElement("div");
    div.className = "dm-entry";
    div.setAttribute("data-id", entry.download_id);
    var pct = parseFloat(entry.progress_pct) || 0;
    var retryBtn = (entry.status === "failed" || entry.status === "cancelled")
      ? '<button class="dm-btn dm-btn-retry dm-retry-btn" data-id="' + escHtml(entry.download_id) + '">Retry</button>'
      : "";
    div.innerHTML =
      '<div class="dm-entry-header">' +
        '<span class="dm-filename">' + escHtml(entry.filename) + "</span>" +
        '<span class="dm-badge ' + escHtml(badgeClass(entry.status)) + '">' + escHtml(entry.status) + "</span>" +
      "</div>" +
      '<div class="dm-meta">' +
        "Hash: " + escHtml(entry.url_hash.substring(0, 16)) + "... | " +
        "Size: " + escHtml(String(entry.size_bytes)) + " bytes | " +
        "Progress: " + escHtml(entry.progress_pct) + "%" +
      "</div>" +
      '<div class="dm-progress"><div class="dm-progress-bar" style="width:' + pct + '%"></div></div>' +
      '<div class="dm-entry-actions">' +
        retryBtn +
        '<button class="dm-btn dm-btn-delete dm-del-btn" data-id="' + escHtml(entry.download_id) + '">Remove</button>' +
      "</div>";
    return div;
  }

  function loadDownloads() {
    fetch(API_BASE)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var filterVal = document.getElementById("dm-filter").value;
        var items = data.downloads || [];
        if (filterVal) {
          items = items.filter(function (d) { return d.status === filterVal; });
        }
        var list = document.getElementById("dm-list");
        if (!list) { return; }
        list.innerHTML = "";
        if (items.length === 0) {
          list.innerHTML = '<p style="color:var(--hub-text-secondary)">No downloads.</p>';
        } else {
          items.forEach(function (d) { list.appendChild(renderEntry(d)); });
          attachRowHandlers();
        }
      })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function loadStats() {
    fetch(API_BASE + "/stats")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("dm-stats");
        if (!el) { return; }
        el.innerHTML =
          '<div class="dm-stat"><div class="dm-stat-value">' + escHtml(String(data.total)) + '</div><div class="dm-stat-label">Total</div></div>' +
          '<div class="dm-stat"><div class="dm-stat-value">' + escHtml(String(data.completed)) + '</div><div class="dm-stat-label">Completed</div></div>' +
          '<div class="dm-stat"><div class="dm-stat-value">' + escHtml(String(data.failed)) + '</div><div class="dm-stat-label">Failed</div></div>' +
          '<div class="dm-stat"><div class="dm-stat-value">' + escHtml(String(data.total_size_bytes)) + '</div><div class="dm-stat-label">Total Bytes</div></div>';
      })
      .catch(function (err) { showStatus("Stats error: " + String(err)); });
  }

  function attachRowHandlers() {
    document.querySelectorAll(".dm-retry-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        fetch(API_BASE + "/" + encodeURIComponent(id) + "/retry", { method: "POST" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.status === "queued") {
              showStatus("Retry queued.");
              loadDownloads();
              loadStats();
            } else {
              showStatus("Retry error: " + escHtml(data.error || "unknown"));
            }
          })
          .catch(function (err) { showStatus("Retry error: " + String(err)); });
      });
    });
    document.querySelectorAll(".dm-del-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        fetch(API_BASE + "/" + encodeURIComponent(id), { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.status === "deleted") {
              showStatus("Removed.");
              loadDownloads();
              loadStats();
            } else {
              showStatus("Error: " + escHtml(data.error || "unknown"));
            }
          })
          .catch(function (err) { showStatus("Delete error: " + String(err)); });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadDownloads();
    loadStats();
    var filter = document.getElementById("dm-filter");
    if (filter) {
      filter.addEventListener("change", function () { loadDownloads(); });
    }
  });
})();
