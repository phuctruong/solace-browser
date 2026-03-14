// Diagram: 02-dashboard-login
/**
 * app-permissions.js — App Permissions Manager frontend for Solace Hub
 * Task 019 | Rung: 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - IIFE pattern. Dynamic code execution banned. escHtml() required for all user data.
 *   - Port 8888 ONLY. Debug port BANNED.
 *   - Auth required: Bearer token (same-origin credentials).
 */

"use strict";

(function AppPermissionsManager() {

  var BASE = "";  // same-origin
  var _pendingAction = null;  // { appId, scope, action }

  // ---------------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------------
  var appGrid       = document.getElementById("app-grid");
  var statusMsg     = document.getElementById("status-msg");
  var dialogOverlay = document.getElementById("dialog-overlay");
  var dialogTitle   = document.getElementById("dialog-title");
  var dialogBody    = document.getElementById("dialog-body");
  var btnConfirm    = document.getElementById("btn-confirm");
  var btnCancel     = document.getElementById("btn-cancel");
  var toast         = document.getElementById("toast");

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#x27;");
  }

  function apiGet(path) {
    return fetch(BASE + path, { credentials: "same-origin" })
      .then(function(r) {
        return r.json().then(function(d) { return { status: r.status, data: d }; });
      });
  }

  function apiPost(path, body) {
    return fetch(BASE + path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function(r) {
      return r.json().then(function(d) { return { status: r.status, data: d }; });
    });
  }

  function showToast(msg, type) {
    toast.textContent = msg;
    toast.className = "toast" + (type ? " toast--" + type : "");
    toast.hidden = false;
    setTimeout(function() { toast.hidden = true; }, 3000);
  }

  function setStatus(msg) {
    if (statusMsg) { statusMsg.textContent = msg; }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  function renderApps(data) {
    var permissions = data.permissions || {};
    var knownScopes = data.known_scopes || {};
    var appIds = Object.keys(permissions);

    if (appIds.length === 0) {
      appGrid.innerHTML = "<p class=\"card-hint\">No apps with explicit permissions yet. Grant a scope to an app to see it here.</p>";
      setStatus("No apps found.");
      return;
    }

    appGrid.innerHTML = "";

    appIds.forEach(function(appId) {
      var grantedSet = {};
      (permissions[appId] || []).forEach(function(s) { grantedSet[s] = true; });

      var row = document.createElement("div");
      row.className = "app-row";

      var grantedCount = (permissions[appId] || []).length;
      var scopeCount = Object.keys(knownScopes).length;

      row.innerHTML = (
        "<div class=\"app-row-header\">" +
          "<span class=\"app-name\">" + escHtml(appId) + "</span>" +
          "<span class=\"app-granted-count\">" + grantedCount + " / " + scopeCount + " scopes granted</span>" +
        "</div>" +
        "<div class=\"scope-list\" id=\"scopes-" + escHtml(appId) + "\"></div>"
      );

      appGrid.appendChild(row);

      var scopeList = document.getElementById("scopes-" + appId);
      if (!scopeList) { return; }

      Object.keys(knownScopes).forEach(function(scope) {
        var isGranted = Boolean(grantedSet[scope]);
        var badge = document.createElement("button");
        badge.className = "scope-badge " + (isGranted ? "granted" : "not-granted");
        badge.setAttribute("type", "button");
        badge.setAttribute("data-app-id", appId);
        badge.setAttribute("data-scope", scope);
        badge.setAttribute("data-granted", isGranted ? "1" : "0");
        badge.setAttribute("title", escHtml(knownScopes[scope]));
        badge.innerHTML = (
          "<span class=\"scope-icon\">" + (isGranted ? "+" : "-") + "</span>" +
          escHtml(scope)
        );
        badge.addEventListener("click", function() {
          handleBadgeClick(appId, scope, isGranted, knownScopes[scope] || scope);
        });
        scopeList.appendChild(badge);
      });
    });

    setStatus("Loaded " + appIds.length + " apps.");
  }

  // ---------------------------------------------------------------------------
  // Badge click → confirmation dialog
  // ---------------------------------------------------------------------------
  function handleBadgeClick(appId, scope, currentlyGranted, description) {
    var action = currentlyGranted ? "revoke" : "grant";
    _pendingAction = { appId: appId, scope: scope, action: action };

    dialogTitle.textContent = (action === "grant" ? "Grant Scope" : "Revoke Scope");
    dialogBody.innerHTML = (
      "Are you sure you want to <strong>" + escHtml(action) + "</strong> " +
      "<strong>" + escHtml(scope) + "</strong> " +
      "for app <strong>" + escHtml(appId) + "</strong>?" +
      "<br><br>" +
      "<em>" + escHtml(description) + "</em>"
    );
    btnConfirm.textContent = action === "grant" ? "Grant" : "Revoke";
    btnConfirm.className = "btn " + (action === "grant" ? "btn--success" : "btn--accent");
    dialogOverlay.hidden = false;
  }

  // ---------------------------------------------------------------------------
  // Confirm / cancel
  // ---------------------------------------------------------------------------
  btnConfirm.addEventListener("click", function() {
    if (!_pendingAction) { return; }
    var pa = _pendingAction;
    _pendingAction = null;
    dialogOverlay.hidden = true;

    var endpoint = BASE + "/api/v1/apps/" + encodeURIComponent(pa.appId) + "/permissions/" + pa.action;
    apiPost(endpoint.replace(BASE + "/api/v1/apps/", "/api/v1/apps/"), { scope: pa.scope })
      .then(function(res) {
        if (res.status === 200) {
          showToast(pa.action === "grant"
            ? ("Granted " + pa.scope + " to " + pa.appId)
            : ("Revoked " + pa.scope + " from " + pa.appId), "success");
          loadPermissions();
        } else {
          showToast((res.data && res.data.error) || "Operation failed.", "error");
        }
      })
      .catch(function() {
        showToast("Network error — is Yinyang server running on port 8888?", "error");
      });
  });

  btnCancel.addEventListener("click", function() {
    _pendingAction = null;
    dialogOverlay.hidden = true;
  });

  dialogOverlay.addEventListener("click", function(e) {
    if (e.target === dialogOverlay) {
      _pendingAction = null;
      dialogOverlay.hidden = true;
    }
  });

  // ---------------------------------------------------------------------------
  // Load permissions
  // ---------------------------------------------------------------------------
  function loadPermissions() {
    setStatus("Loading...");
    apiGet("/api/v1/apps/permissions")
      .then(function(res) {
        if (res.status === 200) {
          renderApps(res.data);
        } else {
          setStatus("Error loading permissions.");
          showToast((res.data && res.data.error) || "Failed to load permissions.", "error");
        }
      })
      .catch(function() {
        setStatus("Network error.");
        showToast("Network error — is Yinyang server running on port 8888?", "error");
      });
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", loadPermissions);

}());
