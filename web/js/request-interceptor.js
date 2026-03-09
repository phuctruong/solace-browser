(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var TOKEN = "";

  function authHeaders() {
    var h = { "Content-Type": "application/json" };
    if (TOKEN) { h["Authorization"] = "Bearer " + TOKEN; }
    return h;
  }

  function showMsg(id, msg) {
    var el = document.getElementById(id);
    if (!el) { return; }
    el.textContent = msg;
    el.hidden = false;
  }

  function loadRules() {
    fetch("/api/v1/interceptor/rules", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("ri-rules-list");
        if (!el) { return; }
        el.innerHTML = "";
        var rules = data.rules || [];
        if (rules.length === 0) {
          el.innerHTML = '<p class="ri-empty">No rules defined.</p>';
          return;
        }
        rules.forEach(function (rule) {
          var div = document.createElement("div");
          div.className = "ri-entry";
          div.innerHTML =
            '<div class="ri-entry-header">' +
              '<span class="ri-entry-id">' + escHtml(rule.rule_id) + "</span>" +
              '<span class="ri-badge">' + escHtml(rule.rule_type) + "</span>" +
              '<span class="ri-badge">' + escHtml(rule.action) + "</span>" +
              '<button class="ri-btn ri-btn-delete ri-del-rule" data-id="' + escHtml(rule.rule_id) + '">Delete</button>' +
            "</div>" +
            '<div class="ri-entry-meta">method: ' + escHtml(rule.method) + " | pattern_hash: " + escHtml(rule.pattern_hash.slice(0, 12)) + "… | " + escHtml(rule.created_at) + "</div>";
          el.appendChild(div);
        });
        el.addEventListener("click", function (e) {
          var btn = e.target.closest(".ri-del-rule");
          if (!btn) { return; }
          deleteRule(btn.getAttribute("data-id"));
        });
      })
      .catch(function (err) { showMsg("ri-rule-msg", "Load error: " + String(err)); });
  }

  function deleteRule(id) {
    fetch("/api/v1/interceptor/rules/" + encodeURIComponent(id), {
      method: "DELETE",
      headers: authHeaders(),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadRules(); })
      .catch(function (err) { showMsg("ri-rule-msg", "Error: " + String(err)); });
  }

  function onAddRule() {
    var ruleType = (document.getElementById("ri-rule-type") || {}).value || "";
    var action = (document.getElementById("ri-action") || {}).value || "";
    var method = (document.getElementById("ri-method") || {}).value || "ALL";
    var pattern = ((document.getElementById("ri-pattern") || {}).value || "").trim();
    if (!pattern) { showMsg("ri-rule-msg", "Pattern required."); return; }
    fetch("/api/v1/interceptor/rules", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ rule_type: ruleType, action: action, method: method, pattern: pattern }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.rule) {
          showMsg("ri-rule-msg", "Created: " + escHtml(data.rule.rule_id));
          loadRules();
        } else {
          showMsg("ri-rule-msg", data.error || "Error");
        }
      })
      .catch(function (err) { showMsg("ri-rule-msg", "Error: " + String(err)); });
  }

  function loadLog() {
    fetch("/api/v1/interceptor/log", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("ri-log-list");
        if (!el) { return; }
        el.innerHTML = "";
        var log = data.log || [];
        if (log.length === 0) {
          el.innerHTML = '<p class="ri-empty">No intercepted requests.</p>';
          return;
        }
        log.forEach(function (entry) {
          var div = document.createElement("div");
          div.className = "ri-entry";
          div.innerHTML =
            '<div class="ri-entry-header">' +
              '<span class="ri-entry-id">' + escHtml(entry.log_id) + "</span>" +
              '<span class="ri-badge">' + escHtml(entry.action_taken || "") + "</span>" +
            "</div>" +
            '<div class="ri-entry-meta">url_hash: ' + escHtml(entry.url_hash.slice(0, 12)) + "… | " + escHtml(entry.logged_at) + "</div>";
          el.appendChild(div);
        });
      })
      .catch(function (err) { showMsg("ri-rule-msg", "Log error: " + String(err)); });
  }

  function loadRuleTypes() {
    fetch("/api/v1/interceptor/rule-types")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById("ri-types-list");
        if (!el) { return; }
        el.innerHTML = "";
        var types = data.rule_types || [];
        types.forEach(function (t) {
          var span = document.createElement("span");
          span.className = "ri-type-chip";
          span.textContent = t;
          el.appendChild(span);
        });
      })
      .catch(function (err) { showMsg("ri-rule-msg", "Types error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var addBtn = document.getElementById("ri-add-btn");
    if (addBtn) { addBtn.addEventListener("click", onAddRule); }
    loadRules();
    loadLog();
    loadRuleTypes();
  });
}());
