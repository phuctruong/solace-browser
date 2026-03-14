// Diagram: 02-dashboard-login
/* Password Strength Checker — Task 144 | IIFE, no eval */
(function () {
  "use strict";

  const API = "/api/v1/password-checker";
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

  async function analyzePassword(e) {
    e.preventDefault();
    var password = document.getElementById("psc-password").value;
    var url = document.getElementById("psc-url").value;
    var r = await fetch(API + "/analyze", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ password: password, url: url }),
    });
    var d = await r.json();
    var result = document.getElementById("psc-result");
    var status = document.getElementById("psc-status");
    if (r.ok) {
      var c = d.check;
      var cls = "psc-strength-" + c.strength;
      result.innerHTML =
        '<h3>Analysis Result</h3>' +
        '<div>Strength: <span class="' + cls + '">' + escHtml(c.strength) + "</span></div>" +
        "<div>Score: " + escHtml(c.score) + " / 100</div>" +
        "<div>Length: " + escHtml(c.length) + "</div>" +
        "<div>Has Upper: " + escHtml(c.has_upper) + " | Lower: " + escHtml(c.has_lower) + " | Digit: " + escHtml(c.has_digit) + " | Special: " + escHtml(c.has_special) + "</div>";
      if (status) status.textContent = "";
      loadHistory();
    } else {
      result.innerHTML = "";
      if (status) status.textContent = "Error: " + (d.error || "unknown");
    }
  }

  async function loadHistory() {
    var r = await fetch(API + "/history", { headers: headers() });
    var d = await r.json();
    var panel = document.getElementById("psc-panel");
    if (!panel) return;
    if (!d.history || d.history.length === 0) {
      panel.innerHTML = '<p class="psc-status">No history yet.</p>';
      return;
    }
    panel.innerHTML = d.history.map(function (c) {
      var cls = "psc-strength-" + c.strength;
      return (
        '<div class="psc-item">' +
        '<div><div class="psc-item-meta">Strength: <span class="' + cls + '">' + escHtml(c.strength) + "</span> | Score: " + escHtml(c.score) + " | Len: " + escHtml(c.length) + "</div>" +
        '<div class="psc-item-id">' + escHtml(c.check_id) + "</div></div>" +
        '<button class="psc-btn" style="background:var(--hub-secondary);color:var(--hub-text)" onclick="window.pscDelete(\'' + escHtml(c.check_id) + '\')">Del</button>' +
        "</div>"
      );
    }).join("");
  }

  window.pscDelete = async function (id) {
    await fetch(API + "/history/" + encodeURIComponent(id), { method: "DELETE", headers: headers() });
    loadHistory();
  };

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("psc-form");
    if (form) form.addEventListener("submit", analyzePassword);
    loadHistory();
  });
})();
