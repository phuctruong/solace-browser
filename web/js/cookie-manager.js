// Diagram: 02-dashboard-login
"use strict";
/* Cookie Manager — Task 062 */
const CM = {
  async showSummary() {
    const r = await fetch("/api/v1/cookies/summary");
    const data = await r.json();
    const el = document.getElementById("cm-summary");
    if (!el) return;
    const cats = Object.entries(data.by_category || {}).map(([c, n]) =>
      `<div class="cm-cat"><span class="cm-cat-name">${c}</span><span class="cm-cat-count">${n}</span></div>`
    ).join("");
    el.innerHTML = `<div class="cm-total">Total: ${data.total}</div>${cats}`;
  },
  async showCategories() {
    const r = await fetch("/api/v1/cookies/categories");
    const data = await r.json();
    const el = document.getElementById("cm-status");
    if (el) el.textContent = `Categories: ${(data.categories || []).join(", ")}`;
  },
  async showByDomain() {
    const r = await fetch("/api/v1/cookies/by-domain");
    const data = await r.json();
    const el = document.getElementById("cm-status");
    if (el) el.textContent = `${data.total_domains} domains tracked`;
  },
  init() {
    const btnSummary = document.getElementById("btn-cm-summary");
    if (btnSummary) btnSummary.addEventListener("click", () => CM.showSummary());
    const btnCats = document.getElementById("btn-cm-categories");
    if (btnCats) btnCats.addEventListener("click", () => CM.showCategories());
    const btnDomain = document.getElementById("btn-cm-by-domain");
    if (btnDomain) btnDomain.addEventListener("click", () => CM.showByDomain());
    CM.showSummary();
  },
};
document.addEventListener("DOMContentLoaded", () => CM.init());
