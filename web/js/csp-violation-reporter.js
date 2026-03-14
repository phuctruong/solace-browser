// Diagram: 02-dashboard-login
/* csp-violation-reporter.js — Task 174 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

const API = "/api/v1/csp-violations";

async function loadDirectives() {
  const r = await fetch(`${API}/directive-types`);
  const data = await r.json();
  const sel = document.getElementById("csp-directive");
  (data.directive_types || []).forEach(d => {
    const opt = document.createElement("option");
    opt.value = d;
    opt.textContent = d;
    sel.appendChild(opt);
  });
}

async function loadStats() {
  const r = await fetch(`${API}/stats`);
  const data = await r.json();
  const el = document.getElementById("csp-stats");
  el.innerHTML = `
    <span>Total: ${data.total}</span>
    <span>Report-only: ${data.report_only_count}</span>
    <span>Report-only rate: ${data.report_only_rate}</span>
  `;
}

async function loadList() {
  const r = await fetch(`${API}/reports`);
  const data = await r.json();
  const ul = document.getElementById("csp-list");
  ul.innerHTML = "";
  (data.reports || []).forEach(v => {
    const li = document.createElement("li");
    li.className = "csp-item";
    li.textContent = `[${v.directive}] report_only=${v.is_report_only}`;
    const btn = document.createElement("button");
    btn.textContent = "Delete";
    btn.className = "csp-btn-sm";
    btn.addEventListener("click", () => deleteViolation(v.violation_id));
    li.appendChild(btn);
    ul.appendChild(li);
  });
}

async function deleteViolation(violationId) {
  await fetch(`${API}/reports/${encodeURIComponent(violationId)}`, { method: "DELETE" });
  loadStats();
  loadList();
}

document.getElementById("csp-form").addEventListener("submit", async e => {
  e.preventDefault();
  const body = {
    directive: document.getElementById("csp-directive").value,
    page_url: document.getElementById("csp-page-url").value,
    blocked_url: document.getElementById("csp-blocked-url").value,
    is_report_only: document.getElementById("csp-report-only").checked,
  };
  const r = await fetch(`${API}/reports`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (r.ok) { loadStats(); loadList(); }
});

loadDirectives();
loadStats();
loadList();
