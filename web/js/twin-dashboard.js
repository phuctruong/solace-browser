/**
 * twin-dashboard.js — Twin Browser Dashboard for Solace Hub
 * Task 022 | Rung 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
 *   - All monetary values displayed as strings (from API). Never format as float.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin
  var REFRESH_MS = 10000;
  var refreshTimer = null;

  // ---------------------------------------------------------------------------
  // escHtml — sanitize all dynamic content (REQUIRED by law)
  // ---------------------------------------------------------------------------
  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // ---------------------------------------------------------------------------
  // API helpers
  // ---------------------------------------------------------------------------
  function apiGet(path) {
    return fetch(BASE + path, { credentials: "same-origin" })
      .then(function (r) {
        return r.json().then(function (d) { return { status: r.status, data: d }; });
      });
  }

  function apiPost(path, body) {
    return fetch(BASE + path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (d) { return { status: r.status, data: d }; });
    });
  }

  function apiDelete(path) {
    return fetch(BASE + path, {
      method: "DELETE",
      credentials: "same-origin",
    }).then(function (r) {
      return r.json().then(function (d) { return { status: r.status, data: d }; });
    });
  }

  // ---------------------------------------------------------------------------
  // Toast
  // ---------------------------------------------------------------------------
  var toastEl = document.getElementById("toast");
  var toastTimer = null;

  function showToast(msg, type) {
    if (!toastEl) { return; }
    toastEl.textContent = msg;
    toastEl.className = "toast show toast--" + escHtml(type || "success");
    if (toastTimer) { clearTimeout(toastTimer); }
    toastTimer = setTimeout(function () {
      toastEl.className = "toast";
    }, 3000);
  }

  // ---------------------------------------------------------------------------
  // Status indicator
  // ---------------------------------------------------------------------------
  function renderStatus(data) {
    var el = document.getElementById("twin-status");
    if (!el) { return; }
    var status = data.status || "idle";
    var dotClass = "status-dot status-dot--" + escHtml(status);
    var lastActive = data.last_active
      ? "Last active: " + escHtml(data.last_active)
      : "Never active";
    el.innerHTML =
      '<span class="status-dot ' + escHtml("status-dot--" + status) + '"></span>' +
      '<span class="status-text">' + escHtml(status.toUpperCase()) + "</span>";
    var metaEl = document.getElementById("twin-status-meta");
    if (metaEl) { metaEl.textContent = lastActive; }
  }

  // ---------------------------------------------------------------------------
  // Queue panel
  // ---------------------------------------------------------------------------
  function renderQueue(data) {
    var tbody = document.getElementById("queue-tbody");
    if (!tbody) { return; }
    var tasks = data.queue || [];
    if (tasks.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No pending tasks</td></tr>';
      return;
    }
    var html = "";
    for (var i = 0; i < tasks.length; i++) {
      var t = tasks[i];
      html +=
        "<tr>" +
        "<td>" + escHtml(t.task_id || "") + "</td>" +
        "<td>" + escHtml(t.action || "") + "</td>" +
        "<td>" + escHtml(t.created_at || "") + "</td>" +
        '<td><button class="btn btn--danger" data-task-id="' +
        escHtml(t.task_id || "") +
        '" onclick="cancelTask(this)">Cancel</button></td>' +
        "</tr>";
    }
    tbody.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // History panel
  // ---------------------------------------------------------------------------
  function renderHistory(data) {
    var tbody = document.getElementById("history-tbody");
    if (!tbody) { return; }
    var entries = data.history || [];
    if (entries.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No completed tasks</td></tr>';
      return;
    }
    var html = "";
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      var statusClass =
        e.status === "ok" ? "ok" :
        e.status === "error" ? "error" : "pending";
      // cost_usd is always a string from API — display as-is, never format as float
      var costDisplay = "$" + escHtml(String(e.cost_usd || "0.000"));
      html +=
        "<tr>" +
        "<td>" + escHtml(e.task_id || "") + "</td>" +
        "<td>" + escHtml(e.action || "") + "</td>" +
        '<td><span class="status-chip status-chip--' + escHtml(statusClass) + '">' +
        escHtml(e.status || "") + "</span></td>" +
        "<td>" + escHtml(String(e.duration_ms || "0")) + " ms</td>" +
        "<td>" + costDisplay + "</td>" +
        "</tr>";
    }
    tbody.innerHTML = html;
  }

  // ---------------------------------------------------------------------------
  // Refresh all data
  // ---------------------------------------------------------------------------
  function refresh() {
    apiGet("/api/v1/twin/status").then(function (r) {
      if (r.status === 200) { renderStatus(r.data); }
    });
    apiGet("/api/v1/twin/queue").then(function (r) {
      if (r.status === 200) { renderQueue(r.data); }
    });
    apiGet("/api/v1/twin/history").then(function (r) {
      if (r.status === 200) { renderHistory(r.data); }
    });
  }

  // ---------------------------------------------------------------------------
  // Cancel task (called from onclick attribute — exposed to window scope)
  // ---------------------------------------------------------------------------
  window.cancelTask = function (btn) {
    var taskId = btn.getAttribute("data-task-id");
    if (!taskId) { return; }
    apiDelete("/api/v1/twin/queue/" + encodeURIComponent(taskId))
      .then(function (r) {
        if (r.status === 200) {
          showToast("Task cancelled", "success");
          refresh();
        } else {
          showToast(r.data.error || "Cancel failed", "error");
        }
      });
  };

  // ---------------------------------------------------------------------------
  // Add task form submission
  // ---------------------------------------------------------------------------
  var addForm = document.getElementById("add-task-form");
  if (addForm) {
    addForm.addEventListener("submit", function (evt) {
      evt.preventDefault();
      var actionEl = document.getElementById("task-action");
      var payloadEl = document.getElementById("task-payload");
      var action = actionEl ? actionEl.value : "";
      var payloadRaw = payloadEl ? payloadEl.value.trim() : "";
      var payload = null;
      if (payloadRaw) {
        try {
          payload = JSON.parse(payloadRaw);
        } catch (_) {
          showToast("Payload must be valid JSON", "error");
          return;
        }
      }
      apiPost("/api/v1/twin/queue", { action: action, payload: payload })
        .then(function (r) {
          if (r.status === 201) {
            showToast("Task queued: " + r.data.task_id, "success");
            if (payloadEl) { payloadEl.value = ""; }
            refresh();
          } else {
            showToast(r.data.error || "Failed to queue task", "error");
          }
        });
    });
  }

  // ---------------------------------------------------------------------------
  // Auto-refresh
  // ---------------------------------------------------------------------------
  function startAutoRefresh() {
    refresh();
    refreshTimer = setInterval(refresh, REFRESH_MS);
  }

  document.addEventListener("DOMContentLoaded", startAutoRefresh);
})();
