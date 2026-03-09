(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var API_BASE = "/api/v1/clipboard";
  var _searchTimer = null;

  function showStatus(msg) {
    var el = document.getElementById("cb-status");
    if (el) { el.textContent = msg; }
  }

  function renderEntry(entry) {
    var div = document.createElement("div");
    div.className = "cb-entry";
    div.setAttribute("data-id", entry.entry_id);
    div.innerHTML =
      '<div class="cb-entry-header">' +
        '<span class="cb-badge">' + escHtml(entry.content_type) + "</span>" +
        '<span class="cb-preview">' + escHtml(entry.preview) + "</span>" +
        '<span class="cb-ts">' + escHtml(entry.created_at || "") + "</span>" +
      "</div>" +
      '<div class="cb-entry-actions">' +
        '<button class="cb-btn cb-btn-icon cb-copy-btn" data-id="' + escHtml(entry.entry_id) + '">Copy</button>' +
        '<button class="cb-btn cb-btn-icon cb-del-btn" data-id="' + escHtml(entry.entry_id) + '">Delete</button>' +
      "</div>";
    return div;
  }

  function loadEntries(q) {
    var url = q ? (API_BASE + "/search?q=" + encodeURIComponent(q)) : API_BASE;
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("cb-list");
        if (!list) { return; }
        list.innerHTML = "";
        var entries = data.entries || [];
        if (entries.length === 0) {
          list.innerHTML = '<p style="color:var(--hub-text-secondary)">No clipboard entries.</p>';
          return;
        }
        entries.forEach(function (e) {
          list.appendChild(renderEntry(e));
        });
        attachRowHandlers();
      })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function attachRowHandlers() {
    document.querySelectorAll(".cb-copy-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        showStatus("Copied entry " + id);
      });
    });
    document.querySelectorAll(".cb-del-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        deleteEntry(id);
      });
    });
  }

  function deleteEntry(id) {
    fetch(API_BASE + "/" + encodeURIComponent(id), { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.status === "deleted") {
          showStatus("Entry deleted.");
          loadEntries(document.getElementById("cb-search").value.trim());
        } else {
          showStatus("Error: " + escHtml(data.error || "unknown"));
        }
      })
      .catch(function (err) { showStatus("Delete error: " + String(err)); });
  }

  function clearAll() {
    if (!confirm("Clear all clipboard entries?")) { return; }
    fetch(API_BASE, { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showStatus("Cleared " + (data.removed || 0) + " entries.");
        loadEntries("");
      })
      .catch(function (err) { showStatus("Clear error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadEntries("");

    var searchInput = document.getElementById("cb-search");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        clearTimeout(_searchTimer);
        var q = searchInput.value.trim();
        _searchTimer = setTimeout(function () { loadEntries(q); }, 250);
      });
    }

    var btnClear = document.getElementById("btn-clear-all");
    if (btnClear) { btnClear.addEventListener("click", clearAll); }
  });
})();
