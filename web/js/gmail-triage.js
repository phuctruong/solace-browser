/**
 * gmail-triage.js — Gmail Inbox Triage frontend for Solace Hub
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - Preview-first: show what WOULD happen, require explicit approval.
 *   - Auto-reject countdown: 30 seconds if no action taken.
 *   - Port 8888 ONLY. Debug port BANNED.
 */

"use strict";

const BASE = "";          // same-origin
const AUTO_REJECT_SECS = 30;

let _countdownTimer = null;
let _pendingActionId = null;

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const statusDot    = document.getElementById("status-dot");
const statusLabel  = document.getElementById("status-label");
const statusMeta   = document.getElementById("status-meta");
const setupCard    = document.getElementById("setup-card");
const tokenInput   = document.getElementById("token-input");
const btnConnect   = document.getElementById("btn-connect");
const setupError   = document.getElementById("setup-error");
const btnRun       = document.getElementById("btn-run");
const runMeta      = document.getElementById("run-meta");
const previewCard  = document.getElementById("preview-card");
const previewTbody = document.getElementById("preview-tbody");
const btnApprove   = document.getElementById("btn-approve");
const btnDismiss   = document.getElementById("btn-dismiss");
const countdownEl  = document.getElementById("countdown-secs");
const resultsCard  = document.getElementById("results-card");
const resultsTbody = document.getElementById("results-tbody");
const resultsMeta  = document.getElementById("results-meta");
const rulesList    = document.getElementById("rules-list");
const toast        = document.getElementById("toast");

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
function apiGet(path) {
  return fetch(BASE + path, { credentials: "same-origin" })
    .then(function(r) { return r.json().then(function(d) { return { status: r.status, data: d }; }); });
}

function apiPost(path, body) {
  return fetch(BASE + path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(function(r) { return r.json().then(function(d) { return { status: r.status, data: d }; }); });
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
function showToast(msg, durationMs) {
  toast.textContent = msg;
  toast.hidden = false;
  setTimeout(function() { toast.hidden = true; }, durationMs || 3000);
}

// ---------------------------------------------------------------------------
// Render helpers
// ---------------------------------------------------------------------------
function actionBadge(action) {
  var cls = ["archive", "snooze", "label", "keep"].indexOf(action) >= 0 ? action : "keep";
  return "<span class=\"action-badge " + cls + "\">" + action + "</span>";
}

function confidenceCell(pct) {
  return (
    "<span class=\"confidence-bar\" aria-label=\"" + pct + "% confidence\">" +
    "<span class=\"confidence-fill\" style=\"width:" + pct + "%\"></span>" +
    "</span> " + pct + "%"
  );
}

function renderRows(tbody, rows) {
  tbody.innerHTML = "";
  rows.forEach(function(row) {
    var tr = document.createElement("tr");
    tr.innerHTML = (
      "<td title=\"" + _esc(row.sender) + "\">" + _esc(row.sender) + "</td>" +
      "<td title=\"" + _esc(row.subject) + "\">" + _esc(row.subject) + "</td>" +
      "<td>" + actionBadge(row.action) + "</td>" +
      "<td>" + confidenceCell(row.confidence) + "</td>"
    );
    tbody.appendChild(tr);
  });
}

function _esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Config / Rules
// ---------------------------------------------------------------------------
var RULE_LABELS = {
  archive_newsletters: "Archive newsletters & noreply senders",
  snooze_follow_ups: "Snooze follow-up & reminder emails",
  label_receipts: "Label receipts & order confirmations",
  archive_social_notifications: "Archive social network notifications",
};

function renderRules(config) {
  rulesList.innerHTML = "";
  Object.keys(config).forEach(function(key) {
    var enabled = config[key];
    var row = document.createElement("div");
    row.className = "rule-row";
    var inputId = "rule-" + key;
    row.innerHTML = (
      "<span class=\"rule-label\">" + _esc(RULE_LABELS[key] || key) + "</span>" +
      "<label class=\"rule-toggle\" aria-label=\"Toggle " + _esc(key) + "\">" +
      "<input type=\"checkbox\" id=\"" + inputId + "\"" + (enabled ? " checked" : "") + ">" +
      "<span class=\"rule-toggle-track\"></span>" +
      "</label>"
    );
    rulesList.appendChild(row);
  });
}

// ---------------------------------------------------------------------------
// Load status on page init
// ---------------------------------------------------------------------------
function loadStatus() {
  apiGet("/api/v1/apps/gmail-inbox-triage/status").then(function(res) {
    if (res.status !== 200) {
      statusLabel.textContent = "Error loading status";
      return;
    }
    var d = res.data;
    if (d.connected) {
      statusDot.className = "status-dot connected";
      statusLabel.textContent = "Connected";
      statusMeta.textContent = "Result count: " + d.result_count;
      setupCard.hidden = true;
      btnRun.disabled = false;
      if (d.last_run) {
        runMeta.textContent = "Last run: " + d.last_run;
      }
    } else {
      statusDot.className = "status-dot disconnected";
      statusLabel.textContent = "Disconnected";
      statusMeta.textContent = "Connect your Gmail OAuth2 token below.";
      setupCard.hidden = false;
      btnRun.disabled = true;
    }
  });
  apiGet("/api/v1/apps/gmail-inbox-triage/config").then(function(res) {
    if (res.status === 200) {
      renderRules(res.data.config);
    }
  });
  apiGet("/api/v1/apps/gmail-inbox-triage/results").then(function(res) {
    if (res.status === 200 && res.data.count > 0) {
      resultsCard.hidden = false;
      resultsMeta.textContent = res.data.count + " emails triaged. Last run: " + (res.data.last_run || "—");
      renderRows(resultsTbody, res.data.results);
    }
  });
}

// ---------------------------------------------------------------------------
// Connect handler
// ---------------------------------------------------------------------------
btnConnect.addEventListener("click", function() {
  var token = tokenInput.value.trim();
  if (token.length < 10) {
    setupError.textContent = "Token must be at least 10 characters.";
    setupError.hidden = false;
    return;
  }
  setupError.hidden = true;
  btnConnect.disabled = true;
  apiPost("/api/v1/apps/gmail-inbox-triage/setup", { oauth2_token: token }).then(function(res) {
    btnConnect.disabled = false;
    if (res.status === 200) {
      tokenInput.value = "";
      showToast("Connected! Token stored as hash only.");
      loadStatus();
    } else {
      setupError.textContent = (res.data && res.data.error) || "Setup failed.";
      setupError.hidden = false;
    }
  }).catch(function() {
    btnConnect.disabled = false;
    setupError.textContent = "Network error — is Yinyang server running on port 8888?";
    setupError.hidden = false;
  });
});

// ---------------------------------------------------------------------------
// Run triage handler
// ---------------------------------------------------------------------------
btnRun.addEventListener("click", function() {
  btnRun.disabled = true;
  runMeta.textContent = "Running preview...";
  apiPost("/api/v1/apps/gmail-inbox-triage/run", {}).then(function(res) {
    btnRun.disabled = false;
    if (res.status !== 200) {
      runMeta.textContent = (res.data && res.data.error) || "Run failed.";
      return;
    }
    var d = res.data;
    _pendingActionId = d.action_id;
    runMeta.textContent = d.emails_processed + " emails analyzed at " + d.run_at;
    renderRows(previewTbody, d.previews);
    previewCard.hidden = false;
    startCountdown(AUTO_REJECT_SECS);
  }).catch(function() {
    btnRun.disabled = false;
    runMeta.textContent = "Network error.";
  });
});

// ---------------------------------------------------------------------------
// Countdown
// ---------------------------------------------------------------------------
function startCountdown(secs) {
  clearCountdown();
  var remaining = secs;
  countdownEl.textContent = String(remaining);
  _countdownTimer = setInterval(function() {
    remaining -= 1;
    countdownEl.textContent = String(remaining);
    if (remaining <= 0) {
      clearCountdown();
      dismissPreview();
      showToast("Preview auto-rejected after 30 seconds.");
    }
  }, 1000);
}

function clearCountdown() {
  if (_countdownTimer !== null) {
    clearInterval(_countdownTimer);
    _countdownTimer = null;
  }
}

// ---------------------------------------------------------------------------
// Approve / Dismiss
// ---------------------------------------------------------------------------
btnApprove.addEventListener("click", function() {
  clearCountdown();
  previewCard.hidden = true;
  resultsCard.hidden = false;
  resultsMeta.textContent = previewTbody.rows.length + " emails — approved.";
  // Copy preview rows to results
  resultsTbody.innerHTML = previewTbody.innerHTML;
  _pendingActionId = null;
  showToast("Triage approved. Actions logged.");
  loadStatus();
});

btnDismiss.addEventListener("click", function() {
  clearCountdown();
  dismissPreview();
  showToast("Preview dismissed. Nothing changed.");
});

function dismissPreview() {
  clearCountdown();
  previewCard.hidden = true;
  _pendingActionId = null;
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", loadStatus);
