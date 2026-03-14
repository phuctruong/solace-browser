// Diagram: 02-dashboard-login
/* scroll-depth-tracker.js — Task 177 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

(function () {
  const API = "/api/v1/scroll-depth";

  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  async function loadContentTypes() {
    const r = await fetch(`${API}/content-types`);
    const data = await r.json();
    const sel = document.getElementById("sds-type");
    (data.content_types || []).forEach(function (t) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      sel.appendChild(opt);
    });
  }

  async function loadStats() {
    const r = await fetch(`${API}/stats`);
    const data = await r.json();
    const el = document.getElementById("sds-stats");
    el.innerHTML =
      "<span>Total: " + escHtml(data.total) + "</span>" +
      "<span>Reached bottom: " + escHtml(data.bottom_reach_count) + "</span>" +
      "<span>Bottom rate: " + escHtml(data.bottom_rate) + "</span>" +
      "<span>Avg depth: " + escHtml(data.avg_depth) + "%</span>";
  }

  async function loadList() {
    const r = await fetch(`${API}/sessions`);
    const data = await r.json();
    const ul = document.getElementById("sds-list");
    ul.innerHTML = "";
    (data.sessions || []).forEach(function (s) {
      const li = document.createElement("li");
      li.className = "sds-item";
      li.textContent = "[" + s.content_type + "] depth=" + s.max_depth_pct + "% bottom=" + s.reached_bottom;
      const btn = document.createElement("button");
      btn.textContent = "Delete";
      btn.className = "sds-btn-sm";
      btn.addEventListener("click", function () { deleteSession(s.session_id); });
      li.appendChild(btn);
      ul.appendChild(li);
    });
  }

  async function deleteSession(sessionId) {
    await fetch(`${API}/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
    loadStats();
    loadList();
  }

  document.getElementById("sds-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const body = {
      content_type: document.getElementById("sds-type").value,
      url: document.getElementById("sds-url").value,
      max_depth_pct: document.getElementById("sds-depth").value,
      time_on_page_seconds: document.getElementById("sds-time").value,
    };
    const r = await fetch(`${API}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) { loadStats(); loadList(); }
  });

  loadContentTypes();
  loadStats();
  loadList();
}());
