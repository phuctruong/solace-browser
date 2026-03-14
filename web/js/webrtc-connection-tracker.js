// Diagram: 02-dashboard-login
/* webrtc-connection-tracker.js — Task 172 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

const API = "/api/v1/webrtc";

async function loadTypes() {
  const r = await fetch(`${API}/connection-types`);
  const data = await r.json();
  const sel = document.getElementById("wrc-type");
  (data.connection_types || []).forEach(t => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    sel.appendChild(opt);
  });
}

async function loadStats() {
  const r = await fetch(`${API}/stats`);
  const data = await r.json();
  const el = document.getElementById("wrc-stats");
  el.innerHTML = `
    <span>Total: ${data.total}</span>
    <span>ICE connected: ${data.ice_connected_count}</span>
    <span>Avg duration: ${data.avg_duration_ms} ms</span>
    <span>Total bytes: ${data.total_bytes}</span>
  `;
}

async function loadList() {
  const r = await fetch(`${API}/connections`);
  const data = await r.json();
  const ul = document.getElementById("wrc-list");
  ul.innerHTML = "";
  (data.connections || []).forEach(c => {
    const li = document.createElement("li");
    li.className = "wrc-item";
    li.textContent = `[${c.connection_type}] duration=${c.duration_ms}ms ice=${c.is_ice_connected}`;
    const btn = document.createElement("button");
    btn.textContent = "Delete";
    btn.className = "wrc-btn-sm";
    btn.addEventListener("click", () => deleteConn(c.conn_id));
    li.appendChild(btn);
    ul.appendChild(li);
  });
}

async function deleteConn(connId) {
  await fetch(`${API}/connections/${encodeURIComponent(connId)}`, { method: "DELETE" });
  loadStats();
  loadList();
}

document.getElementById("wrc-form").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {
    connection_type: document.getElementById("wrc-type").value,
    page_url: document.getElementById("wrc-page-url").value,
    remote_ip: document.getElementById("wrc-remote-ip").value,
    duration_ms: document.getElementById("wrc-duration").value,
    bytes_sent: parseInt(document.getElementById("wrc-bytes-sent").value, 10),
    bytes_received: parseInt(document.getElementById("wrc-bytes-received").value, 10),
    is_ice_connected: document.getElementById("wrc-ice").checked,
  };
  const r = await fetch(`${API}/connections`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.ok) { loadStats(); loadList(); }
});

loadTypes();
loadStats();
loadList();
