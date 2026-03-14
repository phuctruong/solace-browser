// Diagram: 02-dashboard-login
/* Content Copy Tracker — Task 145 | IIFE, no eval */
(function () {
  "use strict";

  const API = "/api/v1/copy-tracker";
  const TOKEN = "";

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function headers() {
    return { "Content-Type": "application/json", Authorization: "Bearer " + TOKEN };
  }

  async function loadStats() {
    var r = await fetch(API + "/stats", { headers: headers() });
    var d = await r.json();
    var el = document.getElementById("cct-stats");
    if (!el) return;
    el.innerHTML =
      '<div class="cct-stats-grid">' +
      '<div class="cct-stat"><div class="cct-stat-val">' + escHtml(d.total_copies || 0) + '</div><div class="cct-stat-lbl">Total Copies</div></div>' +
      '<div class="cct-stat"><div class="cct-stat-val">' + escHtml(d.total_chars || 0) + '</div><div class="cct-stat-lbl">Total Chars</div></div>' +
      '<div class="cct-stat"><div class="cct-stat-val">' + escHtml(d.total_words || 0) + '</div><div class="cct-stat-lbl">Total Words</div></div>' +
      '<div class="cct-stat"><div class="cct-stat-val">' + escHtml(d.most_copied_type || "—") + '</div><div class="cct-stat-lbl">Top Type</div></div>' +
      "</div>";
  }

  async function loadCopies() {
    var r = await fetch(API + "/copies", { headers: headers() });
    var d = await r.json();
    var panel = document.getElementById("cct-panel");
    if (!panel) return;
    if (!d.copies || d.copies.length === 0) {
      panel.innerHTML = '<p class="cct-status">No copy events yet.</p>';
      return;
    }
    panel.innerHTML = d.copies.map(function (c) {
      return (
        '<div class="cct-item">' +
        '<div><div class="cct-item-meta"><span class="cct-type-badge">' + escHtml(c.content_type) + "</span> " +
        escHtml(c.char_count) + " chars, " + escHtml(c.word_count) + " words</div>" +
        '<div class="cct-item-id">' + escHtml(c.copy_id) + "</div></div>" +
        '<button class="cct-btn cct-btn-secondary" onclick="window.cctDelete(\'' + escHtml(c.copy_id) + '\')">Del</button>' +
        "</div>"
      );
    }).join("");
  }

  window.cctDelete = async function (id) {
    await fetch(API + "/copies/" + encodeURIComponent(id), { method: "DELETE", headers: headers() });
    loadCopies();
    loadStats();
  };

  async function submitCopy(e) {
    e.preventDefault();
    var contentType = document.getElementById("cct-content-type").value;
    var url = document.getElementById("cct-url").value;
    var content = document.getElementById("cct-content").value;
    var charCount = parseInt(document.getElementById("cct-chars").value) || 0;
    var wordCount = parseInt(document.getElementById("cct-words").value) || 0;
    var r = await fetch(API + "/copies", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ content_type: contentType, url: url, content: content, char_count: charCount, word_count: wordCount }),
    });
    var d = await r.json();
    var status = document.getElementById("cct-status");
    if (r.ok) {
      if (status) status.textContent = "Recorded: " + d.copy.copy_id;
      loadCopies();
      loadStats();
    } else {
      if (status) status.textContent = "Error: " + (d.error || "unknown");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("cct-form");
    if (form) form.addEventListener("submit", submitCopy);
    loadCopies();
    loadStats();
  });
})();
