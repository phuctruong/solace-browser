"use strict";
/* Tab Group Manager — Task 058 */
const TGM = {
  async refresh() {
    const r = await fetch("/api/v1/tab-groups");
    const data = await r.json();
    const el = document.getElementById("tgm-groups");
    if (!el) return;
    if (!data.groups || data.groups.length === 0) {
      el.textContent = "No groups yet.";
      return;
    }
    el.innerHTML = data.groups.map(g =>
      `<div class="tgm-group tgm-color-${g.color}">
        <strong>${g.name}</strong> <span class="tgm-badge">${g.tab_count} tabs</span>
        <span class="tgm-id">${g.group_id}</span>
       </div>`
    ).join("");
  },
  init() {
    const btnRefresh = document.getElementById("btn-tgm-refresh");
    if (btnRefresh) btnRefresh.addEventListener("click", () => TGM.refresh());
    TGM.refresh();
  },
};
document.addEventListener("DOMContentLoaded", () => TGM.init());
