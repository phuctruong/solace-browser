/* reports.js — Scheduled Reports UI for Solace Hub
   Task 021 | Rung 641
   Laws:
     - IIFE pattern only. eval is banned. No CDN.
     - escHtml() required before any DOM interpolation.
     - Port 8888 ONLY. Debug port BANNED.
*/

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------
  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function tokenHash() {
    // Read Bearer token sha256 from meta tag injected by Solace Hub, or fallback.
    var meta = document.querySelector('meta[name="solace-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  function authHeaders() {
    var h = { "Content-Type": "application/json" };
    var t = tokenHash();
    if (t) {
      h["Authorization"] = "Bearer " + t;
    }
    return h;
  }

  function showError(elId, msg) {
    var el = document.getElementById(elId);
    if (!el) { return; }
    el.textContent = msg;
    el.hidden = false;
  }

  function hideError(elId) {
    var el = document.getElementById(elId);
    if (el) { el.hidden = true; }
  }

  // ---------------------------------------------------------------------------
  // Load templates
  // ---------------------------------------------------------------------------
  function loadTemplates() {
    fetch("/api/v1/reports/templates")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderTemplates(data.templates || []);
        populateTemplateSelects(data.templates || []);
      })
      .catch(function (err) {
        var el = document.getElementById("templates-list");
        if (el) {
          el.innerHTML = "<div class=\"empty-msg\">Failed to load templates: " + escHtml(String(err)) + "</div>";
        }
      });
  }

  function renderTemplates(templates) {
    var el = document.getElementById("templates-list");
    if (!el) { return; }
    if (!templates.length) {
      el.innerHTML = "<div class=\"empty-msg\">No templates available.</div>";
      return;
    }
    var html = "";
    for (var i = 0; i < templates.length; i++) {
      var t = templates[i];
      html += "<div class=\"template-card\">" +
        "<div>" +
        "<div class=\"template-name\">" + escHtml(t.name) + "</div>" +
        "<div class=\"template-desc\">" + escHtml(t.description) + "</div>" +
        "</div>" +
        "<div class=\"template-meta\">~" + escHtml(String(t.estimated_ms)) + "ms</div>" +
        "</div>";
    }
    el.innerHTML = html;
  }

  function populateTemplateSelects(templates) {
    var selects = [
      document.getElementById("template-select"),
      document.getElementById("generate-template-select"),
    ];
    for (var s = 0; s < selects.length; s++) {
      var sel = selects[s];
      if (!sel) { continue; }
      // Remove all options except the first placeholder
      while (sel.options.length > 1) {
        sel.remove(1);
      }
      for (var i = 0; i < templates.length; i++) {
        var opt = document.createElement("option");
        opt.value = templates[i].template_id;
        opt.textContent = templates[i].name;
        sel.appendChild(opt);
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Load scheduled reports
  // ---------------------------------------------------------------------------
  function loadScheduled() {
    fetch("/api/v1/reports/scheduled", { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderScheduled(data.scheduled || []);
      })
      .catch(function (err) {
        var el = document.getElementById("scheduled-list");
        if (el) {
          el.innerHTML = "<div class=\"empty-msg\">Failed to load scheduled reports: " + escHtml(String(err)) + "</div>";
        }
      });
  }

  function renderScheduled(items) {
    var el = document.getElementById("scheduled-list");
    if (!el) { return; }
    if (!items.length) {
      el.innerHTML = "<div class=\"empty-msg\">No scheduled reports yet.</div>";
      return;
    }
    var html = "";
    for (var i = 0; i < items.length; i++) {
      var item = items[i];
      html += "<div class=\"scheduled-item\" data-id=\"" + escHtml(item.id) + "\">" +
        "<div class=\"scheduled-item-info\">" +
        "<div class=\"scheduled-item-name\">" + escHtml(item.template_id) + "</div>" +
        "<div class=\"scheduled-item-meta\">" +
        "cron: <code>" + escHtml(item.cron) + "</code>" +
        " &nbsp;|&nbsp; delivery: " + escHtml(item.delivery) +
        " &nbsp;|&nbsp; created: " + escHtml(item.created_at) +
        "</div>" +
        "</div>" +
        "<button class=\"btn-danger-sm\" data-action=\"delete\" data-id=\"" + escHtml(item.id) + "\">Cancel</button>" +
        "</div>";
    }
    el.innerHTML = html;

    // Attach delete handlers
    var btns = el.querySelectorAll("[data-action=\"delete\"]");
    for (var b = 0; b < btns.length; b++) {
      btns[b].addEventListener("click", function (e) {
        var id = e.currentTarget.getAttribute("data-id");
        deleteScheduled(id);
      });
    }
  }

  function deleteScheduled(id) {
    fetch("/api/v1/reports/scheduled/" + encodeURIComponent(id), {
      method: "DELETE",
      headers: authHeaders(),
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        loadScheduled();
      })
      .catch(function (err) {
        showError("schedule-error", "Delete failed: " + String(err));
      });
  }

  // ---------------------------------------------------------------------------
  // Schedule form submit
  // ---------------------------------------------------------------------------
  function initScheduleForm() {
    var form = document.getElementById("schedule-form");
    if (!form) { return; }
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      hideError("schedule-error");
      var templateId = document.getElementById("template-select").value;
      var cron = document.getElementById("cron-input").value.trim();
      var delivery = document.getElementById("delivery-select").value;
      if (!templateId) {
        showError("schedule-error", "Please select a template.");
        return;
      }
      if (!cron) {
        showError("schedule-error", "Cron expression is required.");
        return;
      }
      fetch("/api/v1/reports/schedule", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ template_id: templateId, cron: cron, delivery: delivery }),
      })
        .then(function (r) {
          if (!r.ok) {
            return r.json().then(function (d) { throw new Error(d.error || r.statusText); });
          }
          return r.json();
        })
        .then(function () {
          form.reset();
          loadScheduled();
        })
        .catch(function (err) {
          showError("schedule-error", String(err));
        });
    });
  }

  // ---------------------------------------------------------------------------
  // Generate now
  // ---------------------------------------------------------------------------
  function initGenerateBtn() {
    var btn = document.getElementById("generate-btn");
    if (!btn) { return; }
    btn.addEventListener("click", function () {
      hideError("generate-error");
      var sel = document.getElementById("generate-template-select");
      var templateId = sel ? sel.value : "";
      if (!templateId) {
        showError("generate-error", "Please select a template.");
        return;
      }
      fetch("/api/v1/reports/generate", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ template_id: templateId }),
      })
        .then(function (r) {
          if (!r.ok) {
            return r.json().then(function (d) { throw new Error(d.error || r.statusText); });
          }
          return r.json();
        })
        .then(function (data) {
          var pre = document.getElementById("report-json");
          var preview = document.getElementById("report-preview");
          if (pre) {
            pre.textContent = JSON.stringify(data.report_data, null, 2);
          }
          if (preview) {
            preview.hidden = false;
          }
        })
        .catch(function (err) {
          showError("generate-error", String(err));
        });
    });
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    loadTemplates();
    loadScheduled();
    initScheduleForm();
    initGenerateBtn();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
}());
