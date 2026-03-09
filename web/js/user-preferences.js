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

  function showMsg(msg) {
    var el = document.getElementById("up-msg");
    if (!el) { return; }
    el.textContent = msg;
    el.hidden = false;
  }

  function loadPrefs() {
    fetch("/api/v1/preferences", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var prefs = data.preferences || {};
        var theme = document.getElementById("up-theme");
        if (theme) { theme.value = prefs.theme || "auto"; }
        var lang = document.getElementById("up-language");
        if (lang) { lang.value = prefs.language || "en"; }
        var tz = document.getElementById("up-timezone");
        if (tz) { tz.value = prefs.timezone || "UTC"; }
        var notif = document.getElementById("up-notifications");
        if (notif) { notif.checked = prefs.notifications_enabled !== false; }
        var autosave = document.getElementById("up-auto-save");
        if (autosave) { autosave.checked = prefs.auto_save !== false; }
        var compact = document.getElementById("up-compact");
        if (compact) { compact.checked = !!prefs.compact_view; }
        var timeout = document.getElementById("up-session-timeout");
        if (timeout) { timeout.value = prefs.session_timeout_minutes || 60; }
        var pageSize = document.getElementById("up-page-size");
        if (pageSize) { pageSize.value = prefs.result_page_size || 20; }
      })
      .catch(function (err) { showMsg("Load error: " + String(err)); });
  }

  function savePref(key, value) {
    return fetch("/api/v1/preferences", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ key: key, value: value }),
    }).then(function (r) { return r.json(); });
  }

  function onSave() {
    var theme = (document.getElementById("up-theme") || {}).value;
    var lang = (document.getElementById("up-language") || {}).value;
    var tz = ((document.getElementById("up-timezone") || {}).value || "").trim();
    var notif = !!(document.getElementById("up-notifications") || {}).checked;
    var autosave = !!(document.getElementById("up-auto-save") || {}).checked;
    var compact = !!(document.getElementById("up-compact") || {}).checked;
    var timeout = parseInt(((document.getElementById("up-session-timeout") || {}).value || "60"), 10);
    var pageSize = parseInt(((document.getElementById("up-page-size") || {}).value || "20"), 10);

    var saves = [
      savePref("theme", theme),
      savePref("language", lang),
      savePref("timezone", tz),
      savePref("notifications_enabled", notif),
      savePref("auto_save", autosave),
      savePref("compact_view", compact),
      savePref("session_timeout_minutes", timeout),
      savePref("result_page_size", pageSize),
    ];

    Promise.all(saves)
      .then(function () { showMsg("Preferences saved."); })
      .catch(function (err) { showMsg("Save error: " + String(err)); });
  }

  function onResetAll() {
    if (!confirm("Reset all preferences to defaults?")) { return; }
    fetch("/api/v1/preferences/reset-all", {
      method: "POST",
      headers: authHeaders(),
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        showMsg("All preferences reset to defaults.");
        loadPrefs();
      })
      .catch(function (err) { showMsg("Error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var saveBtn = document.getElementById("up-save-btn");
    var resetBtn = document.getElementById("up-reset-btn");
    if (saveBtn) { saveBtn.addEventListener("click", onSave); }
    if (resetBtn) { resetBtn.addEventListener("click", onResetAll); }
    loadPrefs();
  });
}());
