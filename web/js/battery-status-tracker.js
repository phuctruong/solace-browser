// Diagram: 02-dashboard-login
/* battery-status-tracker.js — Task 176 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

(function () {
  const API = "/api/v1/battery-status";

  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  async function loadChargingStates() {
    const r = await fetch(`${API}/charging-states`);
    const data = await r.json();
    const sel = document.getElementById("bst-state");
    (data.charging_states || []).forEach(function (s) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      sel.appendChild(opt);
    });
  }

  async function loadStats() {
    const r = await fetch(`${API}/stats`);
    const data = await r.json();
    const el = document.getElementById("bst-stats");
    el.innerHTML =
      "<span>Total: " + escHtml(data.total) + "</span>" +
      "<span>Charging: " + escHtml(data.charging_count) + "</span>" +
      "<span>Avg level: " + escHtml(data.avg_level) + "%</span>" +
      "<span>Low battery: " + escHtml(data.low_battery_count) + "</span>";
  }

  async function loadList() {
    const r = await fetch(`${API}/records`);
    const data = await r.json();
    const ul = document.getElementById("bst-list");
    ul.innerHTML = "";
    (data.records || []).forEach(function (rec) {
      const li = document.createElement("li");
      li.className = "bst-item";
      li.textContent = "[" + rec.charging_state + "] " + rec.level_pct + "%";
      const btn = document.createElement("button");
      btn.textContent = "Delete";
      btn.className = "bst-btn-sm";
      btn.addEventListener("click", function () { deleteRecord(rec.record_id); });
      li.appendChild(btn);
      ul.appendChild(li);
    });
  }

  async function deleteRecord(recordId) {
    await fetch(`${API}/records/${encodeURIComponent(recordId)}`, { method: "DELETE" });
    loadStats();
    loadList();
  }

  document.getElementById("bst-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const ctVal = document.getElementById("bst-ct").value.trim();
    const dtVal = document.getElementById("bst-dt").value.trim();
    const body = {
      charging_state: document.getElementById("bst-state").value,
      url: document.getElementById("bst-url").value,
      level_pct: document.getElementById("bst-level").value,
      charging_time_seconds: ctVal !== "" ? parseInt(ctVal, 10) : null,
      discharging_time_seconds: dtVal !== "" ? parseInt(dtVal, 10) : null,
    };
    const r = await fetch(`${API}/records`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) { loadStats(); loadList(); }
  });

  loadChargingStates();
  loadStats();
  loadList();
}());
