"use strict";
/* Focus Mode — Task 060 */
const FM = {
  async showStatus() {
    const r = await fetch("/api/v1/focus/status");
    const data = await r.json();
    const el = document.getElementById("fm-session");
    if (!el) return;
    if (data.active && data.session) {
      el.innerHTML = `<div class="fm-active">Focus active: <strong>${data.session.focus_type}</strong> — ${data.session.duration_minutes} min</div>`;
    } else {
      el.textContent = "No active focus session.";
    }
  },
  async showBlocklist() {
    const r = await fetch("/api/v1/focus/blocklist");
    const data = await r.json();
    const el = document.getElementById("fm-status");
    if (el) el.textContent = `Blocklist: ${data.total} entries`;
  },
  async showHistory() {
    const r = await fetch("/api/v1/focus/history");
    const data = await r.json();
    const el = document.getElementById("fm-status");
    if (el) el.textContent = `History: ${data.total} past sessions`;
  },
  init() {
    const btnStatus = document.getElementById("btn-fm-status");
    if (btnStatus) btnStatus.addEventListener("click", () => FM.showStatus());
    const btnBlocklist = document.getElementById("btn-fm-blocklist");
    if (btnBlocklist) btnBlocklist.addEventListener("click", () => FM.showBlocklist());
    const btnHistory = document.getElementById("btn-fm-history");
    if (btnHistory) btnHistory.addEventListener("click", () => FM.showHistory());
    FM.showStatus();
  },
};
document.addEventListener("DOMContentLoaded", () => FM.init());
