"use strict";
/* Web Vitals Monitor — Task 061 */
const WV = {
  async showSummary() {
    const r = await fetch("/api/v1/vitals/summary");
    const data = await r.json();
    const el = document.getElementById("wv-summary");
    if (!el) return;
    const metrics = Object.entries(data.summary || {}).map(([m, s]) =>
      `<div class="wv-metric"><strong>${m}</strong>: avg=${s.avg} count=${s.count}</div>`
    ).join("");
    el.innerHTML = metrics || "No vitals recorded.";
  },
  async showThresholds() {
    const r = await fetch("/api/v1/vitals/thresholds");
    const data = await r.json();
    const el = document.getElementById("wv-status");
    if (el) el.textContent = JSON.stringify(data.thresholds);
  },
  async showByPage() {
    const r = await fetch("/api/v1/vitals/by-page");
    const data = await r.json();
    const el = document.getElementById("wv-status");
    if (el) el.textContent = `${data.total_pages} pages tracked`;
  },
  init() {
    const btnSummary = document.getElementById("btn-wv-summary");
    if (btnSummary) btnSummary.addEventListener("click", () => WV.showSummary());
    const btnThresholds = document.getElementById("btn-wv-thresholds");
    if (btnThresholds) btnThresholds.addEventListener("click", () => WV.showThresholds());
    const btnByPage = document.getElementById("btn-wv-by-page");
    if (btnByPage) btnByPage.addEventListener("click", () => WV.showByPage());
    WV.showSummary();
  },
};
document.addEventListener("DOMContentLoaded", () => WV.init());
