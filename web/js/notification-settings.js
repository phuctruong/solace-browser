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

  var API_BASE = "/api/v1/notification-settings";

  function showStatus(msg) {
    var el = document.getElementById("ns-status");
    if (el) { el.textContent = msg; }
  }

  function renderChannels(settings) {
    var channels = settings.channels || {};
    var list = document.getElementById("channels-list");
    if (!list) { return; }
    list.innerHTML = "";
    Object.keys(channels).forEach(function (ch) {
      var row = document.createElement("div");
      row.className = "ns-channel-row";
      row.innerHTML =
        '<span class="ns-channel-name">' + escHtml(ch) + "</span>" +
        '<input type="checkbox" class="ns-toggle ns-ch" data-ch="' +
        escHtml(ch) + '" ' + (channels[ch] ? "checked" : "") + ">";
      list.appendChild(row);
    });
  }

  function applySettings(settings) {
    renderChannels(settings);
    var sev = document.getElementById("min-severity");
    if (sev) { sev.value = settings.min_severity || "info"; }
    var qe = document.getElementById("quiet-enabled");
    if (qe) { qe.checked = !!settings.quiet_hours_enabled; }
    var qs = document.getElementById("quiet-start");
    if (qs) { qs.value = settings.quiet_start || "22:00"; }
    var qend = document.getElementById("quiet-end");
    if (qend) { qend.value = settings.quiet_end || "08:00"; }
    var qtz = document.getElementById("quiet-tz");
    if (qtz) { qtz.value = settings.quiet_timezone || "UTC"; }
  }

  function loadSettings() {
    fetch(API_BASE)
      .then(function (r) { return r.json(); })
      .then(function (data) { applySettings(data); })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function saveSettings() {
    var channels = {};
    var checkboxes = document.querySelectorAll(".ns-ch");
    checkboxes.forEach(function (cb) {
      channels[cb.getAttribute("data-ch")] = cb.checked;
    });
    var payload = {
      channels: channels,
      min_severity: document.getElementById("min-severity").value,
      quiet_hours_enabled: document.getElementById("quiet-enabled").checked,
      quiet_start: document.getElementById("quiet-start").value,
      quiet_end: document.getElementById("quiet-end").value,
      quiet_timezone: document.getElementById("quiet-tz").value,
    };
    fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.status === "updated") {
          showStatus("Settings saved.");
        } else {
          showStatus("Error: " + escHtml(data.error || "unknown"));
        }
      })
      .catch(function (err) { showStatus("Save error: " + String(err)); });
  }

  function sendTest() {
    fetch(API_BASE + "/test", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.sent) {
          showStatus("Test notification sent to: " + (data.channels_notified || []).join(", "));
        } else {
          showStatus("Test failed.");
        }
      })
      .catch(function (err) { showStatus("Test error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadSettings();
    var btnSave = document.getElementById("btn-save");
    if (btnSave) { btnSave.addEventListener("click", saveSettings); }
    var btnTest = document.getElementById("btn-test");
    if (btnTest) { btnTest.addEventListener("click", sendTest); }
  });
})();
