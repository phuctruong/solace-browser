(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var API_BASE = "/api/v1/reader-view";

  function showStatus(msg) {
    var el = document.getElementById("rvs-status");
    if (el) { el.textContent = msg; }
  }

  function loadOptions() {
    fetch(API_BASE + "/options")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        populateSelect("rvs-font", data.fonts || []);
        populateSelect("rvs-theme", data.themes || []);
        populateSelect("rvs-spacing", data.spacing || []);
      })
      .catch(function (err) { showStatus("Failed to load options: " + String(err)); });
  }

  function populateSelect(id, options) {
    var sel = document.getElementById(id);
    if (!sel) { return; }
    options.forEach(function (opt) {
      var o = document.createElement("option");
      o.value = opt;
      o.textContent = opt;
      sel.appendChild(o);
    });
  }

  function renderSetting(s) {
    var div = document.createElement("div");
    div.className = "rvs-card";
    div.setAttribute("data-id", s.setting_id);
    div.innerHTML =
      '<div>' +
        '<div class="rvs-card-meta">' +
          '<span class="rvs-badge">' + escHtml(s.font) + '</span>' +
          '<span class="rvs-badge">' + escHtml(s.theme) + '</span>' +
          '<span class="rvs-badge">' + escHtml(s.spacing) + '</span>' +
          '<span class="rvs-badge">' + escHtml(String(s.font_size_px)) + 'px</span>' +
          '<span class="rvs-badge">' + escHtml(String(s.line_width_chars)) + ' chars</span>' +
        '</div>' +
        '<div class="rvs-card-id">ID: ' + escHtml(s.setting_id) + '</div>' +
      '</div>' +
      '<button class="rvs-btn rvs-btn-danger rvs-del-btn" data-id="' + escHtml(s.setting_id) + '">Delete</button>';
    return div;
  }

  function loadSettings() {
    fetch(API_BASE + "/settings")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("rvs-list");
        if (!list) { return; }
        list.innerHTML = "";
        var settings = data.settings || [];
        if (settings.length === 0) {
          list.innerHTML = '<p class="rvs-empty">No settings saved yet.</p>';
          return;
        }
        settings.forEach(function (s) { list.appendChild(renderSetting(s)); });
        attachDeleteHandlers();
      })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function attachDeleteHandlers() {
    document.querySelectorAll(".rvs-del-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var sid = btn.getAttribute("data-id");
        fetch(API_BASE + "/settings/" + encodeURIComponent(sid), { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function () { showStatus("Deleted."); loadSettings(); })
          .catch(function (err) { showStatus("Delete error: " + String(err)); });
      });
    });
  }

  function handleSubmit(e) {
    e.preventDefault();
    var siteHash = document.getElementById("rvs-site-hash").value.trim();
    var font = document.getElementById("rvs-font").value;
    var theme = document.getElementById("rvs-theme").value;
    var spacing = document.getElementById("rvs-spacing").value;
    var fontSizePx = parseInt(document.getElementById("rvs-font-size").value, 10);
    var lineWidthChars = parseInt(document.getElementById("rvs-line-width").value, 10);

    fetch(API_BASE + "/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        site_hash: siteHash,
        font: font,
        theme: theme,
        spacing: spacing,
        font_size_px: fontSizePx,
        line_width_chars: lineWidthChars,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { showStatus("Error: " + data.error); return; }
        showStatus("Setting saved.");
        loadSettings();
      })
      .catch(function (err) { showStatus("Save error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadOptions();
    loadSettings();
    var form = document.getElementById("rvs-form");
    if (form) { form.addEventListener("submit", handleSubmit); }
  });
})();
