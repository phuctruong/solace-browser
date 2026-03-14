// Diagram: 02-dashboard-login
/**
 * quick-actions.js — Quick Actions Menu frontend for Solace Hub
 * Task 032 | Rung 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
 *   - DEFAULT_ACTIONS (8, cannot delete → 409); custom actions add-only.
 *   - Recent actions FIFO last 20.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin

  // -------------------------------------------------------------------------
  // escHtml — sanitize all dynamic content
  // -------------------------------------------------------------------------
  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // -------------------------------------------------------------------------
  // Icon map — map icon names to simple Unicode symbols
  // -------------------------------------------------------------------------
  var ICON_MAP = {
    grid: "▦", wallet: "💳", shield: "🛡", clock: "🕐",
    book: "📖", store: "🏪", chart: "📊", key: "🔑",
    link: "🔗", star: "⭐",
  };

  function iconFor(name) {
    return ICON_MAP[name] || ICON_MAP["link"];
  }

  // -------------------------------------------------------------------------
  // API helpers
  // -------------------------------------------------------------------------
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

  // -------------------------------------------------------------------------
  // Banner
  // -------------------------------------------------------------------------
  function showBanner(msg, type) {
    var el = document.getElementById("status-banner");
    if (!el) { return; }
    el.textContent = msg;
    el.className = "status-banner " + type;
    setTimeout(function () { el.className = "status-banner hidden"; }, 3500);
  }

  // -------------------------------------------------------------------------
  // Record recent action use
  // -------------------------------------------------------------------------
  function recordRecent(actionId, callback) {
    apiPost("/api/v1/quick-actions/recent", { action_id: actionId }).then(function () {
      if (callback) { callback(); }
    });
  }

  // -------------------------------------------------------------------------
  // Render all actions
  // -------------------------------------------------------------------------
  function renderActions(actions) {
    var grid = document.getElementById("actions-grid");
    if (!grid) { return; }
    grid.innerHTML = "";
    actions.forEach(function (action) {
      var tile = document.createElement("a");
      tile.className = "action-tile";
      tile.href = escHtml(action.url);

      var iconEl = document.createElement("span");
      iconEl.className = "action-icon";
      iconEl.textContent = iconFor(action.icon);

      var labelEl = document.createElement("span");
      labelEl.className = "action-label";
      labelEl.textContent = action.label;

      tile.appendChild(iconEl);
      tile.appendChild(labelEl);

      if (action.builtin) {
        var badge = document.createElement("span");
        badge.className = "action-badge-builtin";
        badge.textContent = "built-in";
        tile.appendChild(badge);
      } else {
        // Custom action: show delete button on hover
        var delBtn = document.createElement("button");
        delBtn.className = "btn-delete-action";
        delBtn.textContent = "\u00d7";
        delBtn.title = "Remove action";
        delBtn.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          apiDelete("/api/v1/quick-actions/" + encodeURIComponent(action.id)).then(function (res) {
            if (res.status === 200) {
              showBanner("Action removed", "success");
              loadActions();
            } else if (res.status === 409) {
              showBanner("Built-in actions cannot be deleted", "error");
            } else {
              showBanner((res.data && res.data.error) || "Delete failed", "error");
            }
          });
        });
        tile.appendChild(delBtn);
      }

      tile.addEventListener("click", function (e) {
        // Record usage; navigation continues via href
        recordRecent(action.id, function () { loadRecent(); });
      });

      grid.appendChild(tile);
    });
  }

  // -------------------------------------------------------------------------
  // Render recent list
  // -------------------------------------------------------------------------
  function renderRecent(recent) {
    var list = document.getElementById("recent-list");
    if (!list) { return; }
    list.innerHTML = "";
    if (!recent || recent.length === 0) {
      var empty = document.createElement("div");
      empty.className = "empty-recent";
      empty.textContent = "No recent actions yet.";
      list.appendChild(empty);
      return;
    }
    recent.forEach(function (action) {
      var item = document.createElement("a");
      item.className = "recent-item";
      item.href = escHtml(action.url);

      var iconEl = document.createElement("span");
      iconEl.textContent = iconFor(action.icon);

      var labelEl = document.createElement("span");
      labelEl.textContent = escHtml(action.label);

      var timeEl = document.createElement("span");
      timeEl.className = "recent-time";
      if (action.used_at) {
        try {
          timeEl.textContent = new Date(action.used_at).toLocaleTimeString();
        } catch (e) {
          timeEl.textContent = action.used_at;
        }
      }

      item.appendChild(iconEl);
      item.appendChild(labelEl);
      item.appendChild(timeEl);
      list.appendChild(item);
    });
  }

  // -------------------------------------------------------------------------
  // Load
  // -------------------------------------------------------------------------
  function loadActions() {
    apiGet("/api/v1/quick-actions").then(function (res) {
      renderActions((res.data && res.data.actions) || []);
    });
  }

  function loadRecent() {
    apiGet("/api/v1/quick-actions/recent").then(function (res) {
      renderRecent((res.data && res.data.recent) || []);
    });
  }

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  function init() {
    loadActions();
    loadRecent();

    // Add form
    var form = document.getElementById("add-form");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var label = (document.getElementById("input-label") || {}).value || "";
        var url   = (document.getElementById("input-url")   || {}).value || "";
        var icon  = (document.getElementById("input-icon")  || {}).value || "link";
        if (!label.trim() || !url.trim()) {
          showBanner("Label and URL are required", "error");
          return;
        }
        apiPost("/api/v1/quick-actions", { label: label.trim(), url: url.trim(), icon: icon.trim() || "link" })
          .then(function (res) {
            if (res.status === 200) {
              showBanner("Action added", "success");
              form.reset();
              loadActions();
            } else {
              showBanner((res.data && res.data.error) || "Failed to add action", "error");
            }
          });
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
