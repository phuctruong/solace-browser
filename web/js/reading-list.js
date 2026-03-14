// Diagram: 02-dashboard-login
"use strict";
/* Reading List — Task 059 */
const RL = {
  async refresh() {
    const r = await fetch("/api/v1/reading-list");
    const data = await r.json();
    const el = document.getElementById("rl-items");
    if (!el) return;
    if (!data.items || data.items.length === 0) {
      el.textContent = "No items in reading list.";
      return;
    }
    el.innerHTML = data.items.map(i =>
      `<div class="rl-item rl-status-${i.status}">
        <span class="rl-title-text">${i.title || i.url_hash.slice(0, 16)}</span>
        <span class="rl-progress">${i.progress_pct}%</span>
        <span class="rl-badge">${i.status}</span>
       </div>`
    ).join("");
  },
  async showStats() {
    const r = await fetch("/api/v1/reading-list/stats");
    const data = await r.json();
    const el = document.getElementById("rl-status");
    if (el) el.textContent = `Total: ${data.total} | ${JSON.stringify(data.by_status)}`;
  },
  init() {
    const btnRefresh = document.getElementById("btn-rl-refresh");
    if (btnRefresh) btnRefresh.addEventListener("click", () => RL.refresh());
    const btnStats = document.getElementById("btn-rl-stats");
    if (btnStats) btnStats.addEventListener("click", () => RL.showStats());
    RL.refresh();
  },
};
document.addEventListener("DOMContentLoaded", () => RL.init());
