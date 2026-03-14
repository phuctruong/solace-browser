// Diagram: 02-dashboard-login
/* lazy-load-tracker.js — Task 178 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

(function () {
  const API = "/api/v1/lazy-load";

  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  async function loadElementTypes() {
    const r = await fetch(`${API}/element-types`);
    const data = await r.json();
    const sel = document.getElementById("lzl-type");
    (data.element_types || []).forEach(function (t) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      sel.appendChild(opt);
    });
  }

  async function loadTriggers() {
    const sel = document.getElementById("lzl-trigger");
    const triggers = ["intersection", "scroll", "click", "timeout", "manual", "import", "preload", "unknown"];
    triggers.forEach(function (t) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      sel.appendChild(opt);
    });
  }

  async function loadStats() {
    const r = await fetch(`${API}/stats`);
    const data = await r.json();
    const el = document.getElementById("lzl-stats");
    el.innerHTML =
      "<span>Total: " + escHtml(data.total) + "</span>" +
      "<span>Visible on load: " + escHtml(data.visible_on_load_count) + "</span>" +
      "<span>Visible rate: " + escHtml(data.visible_rate) + "</span>" +
      "<span>Avg load time: " + escHtml(data.avg_load_ms) + "ms</span>";
  }

  async function loadList() {
    const r = await fetch(`${API}/records`);
    const data = await r.json();
    const ul = document.getElementById("lzl-list");
    ul.innerHTML = "";
    (data.records || []).forEach(function (rec) {
      const li = document.createElement("li");
      li.className = "lzl-item";
      li.textContent = "[" + rec.element_type + "] trigger=" + rec.load_trigger + " " + rec.load_time_ms + "ms";
      const btn = document.createElement("button");
      btn.textContent = "Delete";
      btn.className = "lzl-btn-sm";
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

  document.getElementById("lzl-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const body = {
      element_type: document.getElementById("lzl-type").value,
      url: document.getElementById("lzl-url").value,
      element_url: document.getElementById("lzl-el-url").value,
      load_trigger: document.getElementById("lzl-trigger").value,
      load_time_ms: document.getElementById("lzl-ms").value,
      was_visible_on_load: document.getElementById("lzl-visible").checked,
    };
    const r = await fetch(`${API}/records`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) { loadStats(); loadList(); }
  });

  loadElementTypes();
  loadTriggers();
  loadStats();
  loadList();
}());
