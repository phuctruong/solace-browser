// Diagram: 02-dashboard-login
/* history-cleaner.js — Task 173 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

const API = "/api/v1/history-cleaner";

async function loadReasons() {
  const r = await fetch(`${API}/clean-reasons`);
  const data = await r.json();
  const sel = document.getElementById("hcl-reason");
  (data.clean_reasons || []).forEach(reason => {
    const opt = document.createElement("option");
    opt.value = reason;
    opt.textContent = reason;
    sel.appendChild(opt);
  });
}

async function loadStats() {
  const r = await fetch(`${API}/stats`);
  const data = await r.json();
  const el = document.getElementById("hcl-stats");
  el.innerHTML = `
    <span>Total cleanups: ${data.total_cleanups}</span>
    <span>Total entries removed: ${data.total_entries_removed}</span>
    <span>Avg entries per cleanup: ${data.avg_entries}</span>
  `;
}

async function loadList() {
  const r = await fetch(`${API}/records`);
  const data = await r.json();
  const ul = document.getElementById("hcl-list");
  ul.innerHTML = "";
  (data.records || []).forEach(rec => {
    const li = document.createElement("li");
    li.className = "hcl-item";
    li.textContent = `[${rec.reason}] removed=${rec.entries_removed} range=${rec.time_range_hours}h`;
    const btn = document.createElement("button");
    btn.textContent = "Delete";
    btn.className = "hcl-btn-sm";
    btn.addEventListener("click", () => deleteRecord(rec.clean_id));
    li.appendChild(btn);
    ul.appendChild(li);
  });
}

async function deleteRecord(cleanId) {
  await fetch(`${API}/records/${encodeURIComponent(cleanId)}`, { method: "DELETE" });
  loadStats();
  loadList();
}

document.getElementById("hcl-form").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {
    reason: document.getElementById("hcl-reason").value,
    url_pattern: document.getElementById("hcl-url-pattern").value,
    entries_removed: parseInt(document.getElementById("hcl-entries").value, 10),
    time_range_hours: parseInt(document.getElementById("hcl-time-range").value, 10),
  };
  const r = await fetch(`${API}/records`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.ok) { loadStats(); loadList(); }
});

loadReasons();
loadStats();
loadList();
