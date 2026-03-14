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

  var API_SETTINGS = "/api/v1/settings";
  var API_EXPORT = "/api/v1/settings/export-bundle";
  var API_IMPORT = "/api/v1/settings/import-bundle";
  var API_RESET = "/api/v1/settings/reset-bundle";
  var API_DIFF = "/api/v1/settings/diff-bundle";

  function showStatus(msg) {
    var el = document.getElementById("se-status");
    if (el) { el.textContent = msg; }
  }

  function renderTable(settings) {
    var wrap = document.getElementById("se-table");
    if (!wrap) { return; }
    var rows = Object.keys(settings).map(function (k) {
      return "<tr><td>" + escHtml(k) + "</td><td>" + escHtml(String(settings[k])) + "</td></tr>";
    });
    wrap.innerHTML =
      "<table><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>" +
      rows.join("") +
      "</tbody></table>";
  }

  function renderDiff(diff) {
    var wrap = document.getElementById("se-diff");
    if (!wrap) { return; }
    var keys = Object.keys(diff || {});
    if (keys.length === 0) {
      wrap.textContent = "No changes from defaults.";
      return;
    }
    var rows = keys.map(function (k) {
      var d = diff[k];
      return '<tr class="se-diff-row"><td>' + escHtml(k) + "</td><td>" +
        escHtml(String(d.current)) + "</td><td>" +
        escHtml(String(d.default)) + "</td></tr>";
    });
    wrap.innerHTML =
      "<table><thead><tr><th>Key</th><th>Current</th><th>Default</th></tr></thead><tbody>" +
      rows.join("") + "</tbody></table>";
  }

  function loadSettings() {
    fetch(API_SETTINGS)
      .then(function (r) { return r.json(); })
      .then(function (data) { renderTable(data); })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function loadDiff() {
    fetch(API_DIFF)
      .then(function (r) { return r.json(); })
      .then(function (data) { renderDiff(data.diff); })
      .catch(function () {});
  }

  function exportSettings() {
    fetch(API_EXPORT)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        var url = URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "settings.json";
        a.click();
        URL.revokeObjectURL(url);
        showStatus("Settings exported.");
      })
      .catch(function (err) { showStatus("Export error: " + String(err)); });
  }

  function importSettings() {
    var textarea = document.getElementById("se-import-json");
    if (!textarea) { return; }
    var raw = textarea.value.trim();
    if (!raw) { showStatus("Nothing to import."); return; }
    var parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (e) {
      if (e instanceof SyntaxError) {
        showStatus("Invalid JSON: " + String(e.message));
      } else {
        showStatus("Parse error.");
      }
      return;
    }
    fetch(API_IMPORT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsed),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.status === "imported") {
          showStatus("Settings imported.");
          renderTable(data.settings || {});
          loadDiff();
        } else {
          showStatus("Error: " + escHtml(data.error || "unknown"));
        }
      })
      .catch(function (err) { showStatus("Import error: " + String(err)); });
  }

  function resetSettings() {
    if (!confirm("Reset all settings to defaults?")) { return; }
    fetch(API_RESET, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showStatus("Settings reset.");
        renderTable(data.settings || {});
        loadDiff();
      })
      .catch(function (err) { showStatus("Reset error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadSettings();
    loadDiff();

    var btnExport = document.getElementById("btn-export");
    if (btnExport) { btnExport.addEventListener("click", exportSettings); }

    var btnImport = document.getElementById("btn-import");
    if (btnImport) { btnImport.addEventListener("click", importSettings); }

    var btnReset = document.getElementById("btn-reset");
    if (btnReset) { btnReset.addEventListener("click", resetSettings); }
  });
})();
