// Diagram: 02-dashboard-login
/* mouse-heatmap-tracker.js — Task 179 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

(function () {
  const API = "/api/v1/mouse-heatmap";

  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  async function loadInteractionTypes() {
    const r = await fetch(`${API}/interaction-types`);
    const data = await r.json();
    const sel = document.getElementById("mhe-type");
    (data.interaction_types || []).forEach(function (t) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      sel.appendChild(opt);
    });
  }

  async function loadStats() {
    const r = await fetch(`${API}/stats`);
    const data = await r.json();
    const el = document.getElementById("mhe-stats");
    el.innerHTML =
      "<span>Total: " + escHtml(data.total) + "</span>" +
      "<span>Avg X: " + escHtml(data.avg_x) + "%</span>" +
      "<span>Avg Y: " + escHtml(data.avg_y) + "%</span>" +
      "<span>Unique sessions: " + escHtml(data.unique_sessions) + "</span>";
  }

  async function loadList() {
    const r = await fetch(`${API}/records`);
    const data = await r.json();
    const ul = document.getElementById("mhe-list");
    ul.innerHTML = "";
    (data.records || []).forEach(function (rec) {
      const li = document.createElement("li");
      li.className = "mhe-item";
      li.textContent = "[" + rec.interaction_type + "] x=" + rec.x_pct + "% y=" + rec.y_pct + "%";
      const btn = document.createElement("button");
      btn.textContent = "Delete";
      btn.className = "mhe-btn-sm";
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

  document.getElementById("mhe-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const body = {
      interaction_type: document.getElementById("mhe-type").value,
      url: document.getElementById("mhe-url").value,
      x_pct: document.getElementById("mhe-x").value,
      y_pct: document.getElementById("mhe-y").value,
      session_id: document.getElementById("mhe-session").value,
    };
    const r = await fetch(`${API}/records`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) { loadStats(); loadList(); }
  });

  loadInteractionTypes();
  loadStats();
  loadList();
}());
