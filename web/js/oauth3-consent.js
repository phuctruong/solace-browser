/**
 * oauth3-consent.js — OAuth3 Consent UI for Solace Hub
 * Task 024 | Rung 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
 *   - All scope values sanitized with escHtml before DOM insertion.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin

  // ---------------------------------------------------------------------------
  // escHtml — sanitize all dynamic content
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
  function apiFetch(method, path, body, cb) {
    var xhr = new XMLHttpRequest();
    xhr.open(method, BASE + path, true);
    xhr.setRequestHeader("Content-Type", "application/json");
    var token = window._SOLACE_TOKEN || "";
    if (token) {
      xhr.setRequestHeader("Authorization", "Bearer " + token);
    }
    xhr.onreadystatechange = function () {
      if (xhr.readyState !== 4) { return; }
      var data = null;
      try { data = JSON.parse(xhr.responseText); } catch (e) { data = {}; }
      cb(xhr.status, data);
    };
    xhr.send(body ? JSON.stringify(body) : null);
  }

  // ---------------------------------------------------------------------------
  // Status banner
  // ---------------------------------------------------------------------------
  function showStatus(msg, type) {
    var el = document.getElementById("status-banner");
    if (!el) { return; }
    el.textContent = msg;
    el.className = "status-banner visible " + (type || "success");
    clearTimeout(el._timer);
    el._timer = setTimeout(function () {
      el.className = "status-banner";
    }, 3000);
  }

  // ---------------------------------------------------------------------------
  // Render pending requests
  // ---------------------------------------------------------------------------
  function renderPending(requests) {
    var list = document.getElementById("pending-list");
    var empty = document.getElementById("pending-empty");
    if (!list || !empty) { return; }
    list.innerHTML = "";
    if (!requests || requests.length === 0) {
      empty.style.display = "";
      return;
    }
    empty.style.display = "none";
    requests.forEach(function (req) {
      var li = document.createElement("li");
      li.className = "consent-item";
      var scopeHtml = (req.requested_scopes || []).map(function (s) {
        return '<span class="scope-badge">' + escHtml(s) + "</span>";
      }).join("");
      li.innerHTML = (
        '<div class="consent-item-header">' +
          '<span class="consent-app-name">' + escHtml(req.app_name) + "</span>" +
          '<span class="consent-meta">expires: ' + escHtml(req.expires_at || "") + "</span>" +
        "</div>" +
        '<div class="scope-list">' + scopeHtml + "</div>" +
        '<div class="consent-actions">' +
          '<button class="btn btn-approve" data-id="' + escHtml(req.request_id) + '">Approve</button>' +
          '<button class="btn btn-reject" data-id="' + escHtml(req.request_id) + '">Reject</button>' +
        "</div>"
      );
      li.querySelector(".btn-approve").addEventListener("click", function () {
        doApprove(req.request_id, req.requested_scopes);
      });
      li.querySelector(".btn-reject").addEventListener("click", function () {
        doReject(req.request_id);
      });
      list.appendChild(li);
    });
  }

  // ---------------------------------------------------------------------------
  // Render grants
  // ---------------------------------------------------------------------------
  function renderGrants(grants) {
    var list = document.getElementById("grants-list");
    var empty = document.getElementById("grants-empty");
    if (!list || !empty) { return; }
    list.innerHTML = "";
    var active = (grants || []).filter(function (g) { return g.is_active; });
    if (active.length === 0) {
      empty.style.display = "";
      return;
    }
    empty.style.display = "none";
    active.forEach(function (grant) {
      var li = document.createElement("li");
      li.className = "consent-item";
      var scopeHtml = (grant.approved_scopes || []).map(function (s) {
        return '<span class="scope-badge">' + escHtml(s) + "</span>";
      }).join("");
      li.innerHTML = (
        '<div class="consent-item-header">' +
          '<span class="consent-app-name">' + escHtml(grant.app_name) + "</span>" +
          '<span class="grant-active-badge">active</span>' +
        "</div>" +
        '<div class="scope-list">' + scopeHtml + "</div>" +
        '<div class="consent-meta">granted: ' + escHtml(grant.granted_at || "") + "</div>" +
        '<div class="consent-actions">' +
          '<button class="btn btn-revoke" data-id="' + escHtml(grant.grant_id) + '">Revoke</button>' +
        "</div>"
      );
      li.querySelector(".btn-revoke").addEventListener("click", function () {
        doRevoke(grant.grant_id);
      });
      list.appendChild(li);
    });
  }

  // ---------------------------------------------------------------------------
  // Load data
  // ---------------------------------------------------------------------------
  function loadPending() {
    apiFetch("GET", "/api/v1/oauth3/pending", null, function (status, data) {
      if (status === 200) {
        renderPending(data.pending || []);
      } else {
        renderPending([]);
      }
    });
  }

  function loadGrants() {
    apiFetch("GET", "/api/v1/oauth3/consented", null, function (status, data) {
      if (status === 200) {
        renderGrants(data.grants || []);
      } else {
        renderGrants([]);
      }
    });
  }

  function refresh() {
    loadPending();
    loadGrants();
  }

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------
  function doApprove(requestId, scopes) {
    apiFetch(
      "POST",
      "/api/v1/oauth3/consent/" + encodeURIComponent(requestId) + "/approve",
      { approved_scopes: scopes },
      function (status, data) {
        if (status === 201) {
          showStatus("Consent approved.", "success");
          refresh();
        } else {
          showStatus("Approve failed: " + escHtml(data.error || "unknown"), "error");
        }
      }
    );
  }

  function doReject(requestId) {
    apiFetch(
      "POST",
      "/api/v1/oauth3/consent/" + encodeURIComponent(requestId) + "/reject",
      { reason: "user rejected via UI" },
      function (status, data) {
        if (status === 200) {
          showStatus("Consent rejected.", "success");
          refresh();
        } else {
          showStatus("Reject failed: " + escHtml(data.error || "unknown"), "error");
        }
      }
    );
  }

  function doRevoke(grantId) {
    apiFetch(
      "DELETE",
      "/api/v1/oauth3/consented/" + encodeURIComponent(grantId),
      null,
      function (status, data) {
        if (status === 200) {
          showStatus("Grant revoked.", "success");
          refresh();
        } else {
          showStatus("Revoke failed: " + escHtml(data.error || "unknown"), "error");
        }
      }
    );
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    refresh();
  });

}());
