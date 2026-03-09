"use strict";
/* History Search — Task 063 */
const HS = {
  async listEntries() {
    const r = await fetch("/api/v1/history/entries");
    const data = await r.json();
    const el = document.getElementById("hs-entries");
    if (!el) return;
    if (!data.entries || data.entries.length === 0) {
      el.textContent = "No history entries.";
      return;
    }
    el.innerHTML = data.entries.slice(0, 50).map(e =>
      `<div class="hs-entry">
        <span class="hs-entry-title">${e.title || e.url_hash.slice(0, 20)}</span>
        <span class="hs-entry-visits">${e.visit_count} visits</span>
        <span class="hs-entry-type">${e.content_type}</span>
       </div>`
    ).join("");
  },
  async showStats() {
    const r = await fetch("/api/v1/history/stats");
    const data = await r.json();
    const el = document.getElementById("hs-status");
    if (el) el.textContent = `Entries: ${data.total_entries} | Total visits: ${data.total_visits}`;
  },
  async showTopDomains() {
    const r = await fetch("/api/v1/history/top-domains");
    const data = await r.json();
    const el = document.getElementById("hs-status");
    if (el) el.textContent = `Top ${data.total} domains tracked`;
  },
  init() {
    const btnList = document.getElementById("btn-hs-list");
    if (btnList) btnList.addEventListener("click", () => HS.listEntries());
    const btnStats = document.getElementById("btn-hs-stats");
    if (btnStats) btnStats.addEventListener("click", () => HS.showStats());
    const btnTop = document.getElementById("btn-hs-top");
    if (btnTop) btnTop.addEventListener("click", () => HS.showTopDomains());
    HS.listEntries();
  },
};
document.addEventListener("DOMContentLoaded", () => HS.init());
