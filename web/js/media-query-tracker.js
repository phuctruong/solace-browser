/* media-query-tracker.js — Task 175 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

(function () {
  const API = "/api/v1/media-query";

  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  async function loadBreakpoints() {
    const r = await fetch(`${API}/breakpoints`);
    const data = await r.json();
    const sel = document.getElementById("mqt-breakpoint");
    (data.breakpoints || []).forEach(function (b) {
      const opt = document.createElement("option");
      opt.value = b;
      opt.textContent = b;
      sel.appendChild(opt);
    });
  }

  async function loadStats() {
    const r = await fetch(`${API}/stats`);
    const data = await r.json();
    const el = document.getElementById("mqt-stats");
    el.innerHTML =
      "<span>Total: " + escHtml(data.total) + "</span>" +
      "<span>Landscape: " + escHtml(data.landscape_count) + "</span>" +
      "<span>Landscape rate: " + escHtml(data.landscape_rate) + "</span>" +
      "<span>Avg width: " + escHtml(data.avg_width) + "px</span>";
  }

  async function loadList() {
    const r = await fetch(`${API}/records`);
    const data = await r.json();
    const ul = document.getElementById("mqt-list");
    ul.innerHTML = "";
    (data.records || []).forEach(function (rec) {
      const li = document.createElement("li");
      li.className = "mqt-item";
      li.textContent = "[" + rec.breakpoint + "] " + rec.orientation + " " + rec.width_px + "x" + rec.height_px;
      const btn = document.createElement("button");
      btn.textContent = "Delete";
      btn.className = "mqt-btn-sm";
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

  document.getElementById("mqt-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const body = {
      breakpoint: document.getElementById("mqt-breakpoint").value,
      url: document.getElementById("mqt-url").value,
      orientation: document.getElementById("mqt-orientation").value,
      width_px: parseInt(document.getElementById("mqt-width").value, 10),
      height_px: parseInt(document.getElementById("mqt-height").value, 10),
      device_pixel_ratio: document.getElementById("mqt-dpr").value,
    };
    const r = await fetch(`${API}/records`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) { loadStats(); loadList(); }
  });

  loadBreakpoints();
  loadStats();
  loadList();
}());
