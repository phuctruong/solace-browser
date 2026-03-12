/* keyboard-shortcut-analytics.js — Task 180 */
/* NO eval(), NO CDN, NO port 9222 */
"use strict";

(function () {
  const API = "/api/v1/keyboard-shortcuts";

  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  async function loadEventTypes() {
    const r = await fetch(`${API}/event-types`);
    const data = await r.json();
    const sel = document.getElementById("kbd-type");
    (data.event_types || []).forEach(function (t) {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      sel.appendChild(opt);
    });
  }

  async function loadStats() {
    const r = await fetch(`${API}/stats`);
    const data = await r.json();
    const el = document.getElementById("kbd-stats");
    el.innerHTML =
      "<span>Total: " + escHtml(data.total) + "</span>" +
      "<span>Successful: " + escHtml(data.success_count) + "</span>" +
      "<span>Success rate: " + escHtml(data.success_rate) + "</span>" +
      "<span>Unique combos: " + escHtml(data.unique_combos) + "</span>";
  }

  async function loadList() {
    const r = await fetch(`${API}/events`);
    const data = await r.json();
    const ul = document.getElementById("kbd-list");
    ul.innerHTML = "";
    (data.events || []).forEach(function (ev) {
      const li = document.createElement("li");
      li.className = "kbd-item";
      li.textContent = "[" + ev.event_type + "] success=" + ev.was_successful;
      const btn = document.createElement("button");
      btn.textContent = "Delete";
      btn.className = "kbd-btn-sm";
      btn.addEventListener("click", function () { deleteEvent(ev.event_id); });
      li.appendChild(btn);
      ul.appendChild(li);
    });
  }

  async function deleteEvent(eventId) {
    await fetch(`${API}/events/${encodeURIComponent(eventId)}`, { method: "DELETE" });
    loadStats();
    loadList();
  }

  document.getElementById("kbd-form").addEventListener("submit", async function (e) {
    e.preventDefault();
    const body = {
      event_type: document.getElementById("kbd-type").value,
      url: document.getElementById("kbd-url").value,
      key_combo: document.getElementById("kbd-combo").value,
      ui_context: document.getElementById("kbd-context").value,
      was_successful: document.getElementById("kbd-success").checked,
    };
    const r = await fetch(`${API}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) { loadStats(); loadList(); }
  });

  loadEventTypes();
  loadStats();
  loadList();
}());
