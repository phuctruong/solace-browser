// Diagram: 02-dashboard-login
(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var RULES_URL = "/api/v1/ext-firewall/rules";
  var BLOCKED_URL = "/api/v1/ext-firewall/blocked";
  var CHECK_URL = "/api/v1/ext-firewall/check";

  function showStatus(msg) {
    var el = document.getElementById("ef-status");
    if (el) { el.textContent = msg; }
  }

  function renderRule(rule) {
    var div = document.createElement("div");
    div.className = "ef-rule-entry";
    var actionBadge = "ef-badge" + (rule.action === "block" ? " ef-badge-block" : rule.action === "allow" ? " ef-badge-allow" : "");
    var builtinBadge = rule.is_builtin ? '<span class="ef-badge ef-badge-builtin">builtin</span>' : "";
    var delBtn = rule.is_builtin ? "" :
      '<button class="ef-btn ef-btn-danger ef-del-rule-btn" data-id="' + escHtml(rule.rule_id) + '">Delete</button>';
    div.innerHTML =
      '<span class="ef-rule-pattern">' + escHtml(rule.pattern) + "</span>" +
      '<span class="' + escHtml(actionBadge) + '">' + escHtml(rule.action) + "</span>" +
      builtinBadge +
      delBtn;
    return div;
  }

  function renderBlockedEntry(entry) {
    var div = document.createElement("div");
    div.className = "ef-blocked-entry";
    div.innerHTML =
      "<span>Hash: " + escHtml(entry.ext_id_hash.substring(0, 16)) + "...</span>" +
      "<span>Blocked: " + escHtml(entry.blocked_at) + " — " + escHtml(entry.reason) + "</span>";
    return div;
  }

  function loadRules() {
    fetch(RULES_URL)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("ef-rules-list");
        if (!list) { return; }
        list.innerHTML = "";
        var rules = data.rules || [];
        if (rules.length === 0) {
          list.innerHTML = '<p style="color:var(--hub-text-secondary)">No rules.</p>';
        } else {
          rules.forEach(function (rule) { list.appendChild(renderRule(rule)); });
          attachDeleteHandlers();
        }
      })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function loadBlocked() {
    fetch(BLOCKED_URL)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("ef-blocked-list");
        if (!list) { return; }
        list.innerHTML = "";
        var entries = data.blocked || [];
        if (entries.length === 0) {
          list.innerHTML = '<p style="color:var(--hub-text-secondary)">No blocked attempts.</p>';
        } else {
          entries.forEach(function (e) { list.appendChild(renderBlockedEntry(e)); });
        }
      })
      .catch(function (err) { showStatus("Blocked load error: " + String(err)); });
  }

  function attachDeleteHandlers() {
    document.querySelectorAll(".ef-del-rule-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        fetch(RULES_URL + "/" + encodeURIComponent(id), { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.status === "deleted") {
              showStatus("Rule deleted.");
              loadRules();
            } else {
              showStatus("Error: " + escHtml(data.error || "unknown"));
            }
          })
          .catch(function (err) { showStatus("Delete error: " + String(err)); });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadRules();
    loadBlocked();

    var btnAdd = document.getElementById("btn-add-rule");
    if (btnAdd) {
      btnAdd.addEventListener("click", function () {
        var pattern = document.getElementById("ef-pattern").value.trim();
        var action = document.getElementById("ef-action").value;
        if (!pattern) { showStatus("Pattern is required."); return; }
        fetch(RULES_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pattern: pattern, action: action }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.rule_id) {
              showStatus("Rule added: " + escHtml(data.rule_id));
              document.getElementById("ef-pattern").value = "";
              loadRules();
            } else {
              showStatus("Error: " + escHtml(data.error || "unknown"));
            }
          })
          .catch(function (err) { showStatus("Add error: " + String(err)); });
      });
    }

    var btnCheck = document.getElementById("btn-check");
    if (btnCheck) {
      btnCheck.addEventListener("click", function () {
        var extId = document.getElementById("ef-check-id").value.trim();
        if (!extId) { showStatus("Extension ID is required."); return; }
        fetch(CHECK_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ext_id: extId }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            var result = document.getElementById("ef-check-result");
            if (result) {
              if (data.allowed) {
                result.innerHTML = '<span class="ef-check-allowed">ALLOWED</span> — rule: ' + escHtml(data.rule_matched || "none") +
                  ' — hash: ' + escHtml((data.ext_id_hash || "").substring(0, 16)) + "...";
              } else {
                result.innerHTML = '<span class="ef-check-blocked">BLOCKED</span> — rule: ' + escHtml(data.rule_matched || "none") +
                  ' — hash: ' + escHtml((data.ext_id_hash || "").substring(0, 16)) + "...";
                loadBlocked();
              }
            }
          })
          .catch(function (err) { showStatus("Check error: " + String(err)); });
      });
    }
  });
})();
