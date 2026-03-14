// Diagram: 02-dashboard-login
/* Form Autofill Tracker — Task 143 | IIFE, no eval */
(function () {
  "use strict";

  const API = "/api/v1/autofill";
  const TOKEN = "";

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function headers() {
    return { "Content-Type": "application/json", Authorization: "Bearer " + TOKEN };
  }

  async function loadStats() {
    const r = await fetch(API + "/stats", { headers: headers() });
    const d = await r.json();
    const el = document.getElementById("aft-stats");
    if (!el) return;
    el.innerHTML =
      '<div class="aft-stats-grid">' +
      '<div class="aft-stat"><div class="aft-stat-val">' + escHtml(d.total_fills || 0) + '</div><div class="aft-stat-lbl">Total Fills</div></div>' +
      '<div class="aft-stat"><div class="aft-stat-val">' + escHtml(d.success_count || 0) + '</div><div class="aft-stat-lbl">Success</div></div>' +
      '<div class="aft-stat"><div class="aft-stat-val">' + escHtml(d.success_rate || "0.0000") + '</div><div class="aft-stat-lbl">Rate</div></div>' +
      "</div>";
  }

  async function loadEntries() {
    const r = await fetch(API + "/entries", { headers: headers() });
    const d = await r.json();
    const panel = document.getElementById("aft-panel");
    if (!panel) return;
    if (!d.entries || d.entries.length === 0) {
      panel.innerHTML = '<p class="aft-status">No autofill entries yet.</p>';
      return;
    }
    panel.innerHTML = d.entries.map(function (e) {
      var cls = e.success ? "aft-success" : "aft-fail";
      return (
        '<div class="aft-item">' +
        '<div><div class="aft-item-meta">' + escHtml(e.field_type) + " — " + escHtml(e.field_name) + ' <span class="' + cls + '">' + (e.success ? "OK" : "FAIL") + "</span></div>" +
        '<div class="aft-item-id">' + escHtml(e.entry_id) + "</div></div>" +
        '<button class="aft-btn aft-btn-secondary" onclick="window.aftDelete(\'' + escHtml(e.entry_id) + '\')">Del</button>' +
        "</div>"
      );
    }).join("");
  }

  window.aftDelete = async function (id) {
    await fetch(API + "/entries/" + encodeURIComponent(id), { method: "DELETE", headers: headers() });
    loadEntries();
    loadStats();
  };

  async function submitEntry(e) {
    e.preventDefault();
    var fieldType = document.getElementById("aft-field-type").value;
    var fieldName = document.getElementById("aft-field-name").value;
    var url = document.getElementById("aft-url").value;
    var value = document.getElementById("aft-value").value;
    var success = document.getElementById("aft-success").checked;
    var r = await fetch(API + "/entries", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ field_type: fieldType, field_name: fieldName, url: url, value: value, success: success }),
    });
    var d = await r.json();
    var status = document.getElementById("aft-status");
    if (r.ok) {
      if (status) status.textContent = "Recorded: " + d.entry.entry_id;
      loadEntries();
      loadStats();
    } else {
      if (status) status.textContent = "Error: " + (d.error || "unknown");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("aft-form");
    if (form) form.addEventListener("submit", submitEntry);
    loadEntries();
    loadStats();
  });
})();
