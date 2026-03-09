(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var API_BASE = "/api/v1/user-scripts";

  function showStatus(msg) {
    var el = document.getElementById("us-status");
    if (el) { el.textContent = msg; }
  }

  function renderScript(script) {
    var div = document.createElement("div");
    div.className = "us-entry";
    div.setAttribute("data-id", script.script_id);
    var enabledClass = script.enabled ? "us-badge-enabled" : "us-badge-disabled";
    var enabledLabel = script.enabled ? "enabled" : "disabled";
    var toggleLabel = script.enabled ? "Disable" : "Enable";
    div.innerHTML =
      '<div class="us-entry-header">' +
        '<span class="us-entry-name">' + escHtml(script.name) + "</span>" +
        '<span class="us-badge ' + escHtml(enabledClass) + '">' + escHtml(enabledLabel) + "</span>" +
      "</div>" +
      '<div class="us-meta">' +
        "Pattern: " + escHtml(script.url_pattern) + " | run_at: " + escHtml(script.run_at) +
      "</div>" +
      '<div class="us-entry-actions">' +
        '<button class="us-btn us-btn-toggle us-toggle-btn" data-id="' + escHtml(script.script_id) + '">' + escHtml(toggleLabel) + "</button>" +
        '<button class="us-btn us-btn-validate us-validate-btn" data-id="' + escHtml(script.script_id) + '">Validate</button>' +
        '<button class="us-btn us-btn-delete us-del-btn" data-id="' + escHtml(script.script_id) + '">Delete</button>' +
      "</div>" +
      '<div class="us-validate-result" id="val-' + escHtml(script.script_id) + '"></div>';
    return div;
  }

  function loadScripts() {
    fetch(API_BASE)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("us-list");
        if (!list) { return; }
        list.innerHTML = "";
        var scripts = data.scripts || [];
        if (scripts.length === 0) {
          list.innerHTML = '<p style="color:var(--hub-text-secondary)">No user scripts.</p>';
        } else {
          scripts.forEach(function (s) { list.appendChild(renderScript(s)); });
          attachHandlers();
        }
      })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function attachHandlers() {
    document.querySelectorAll(".us-toggle-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        fetch(API_BASE + "/" + encodeURIComponent(id) + "/toggle", { method: "POST" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.status === "toggled") {
              showStatus("Toggled: " + escHtml(id) + " → " + (data.enabled ? "enabled" : "disabled"));
              loadScripts();
            } else {
              showStatus("Error: " + escHtml(data.error || "unknown"));
            }
          })
          .catch(function (err) { showStatus("Toggle error: " + String(err)); });
      });
    });

    document.querySelectorAll(".us-validate-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        fetch(API_BASE + "/" + encodeURIComponent(id) + "/validate")
          .then(function (r) { return r.json(); })
          .then(function (data) {
            var el = document.getElementById("val-" + id);
            if (!el) { return; }
            if (data.safe) {
              el.className = "us-validate-result us-validate-safe";
              el.textContent = "Safe — no forbidden patterns found.";
            } else {
              el.className = "us-validate-result us-validate-unsafe";
              el.textContent = "Unsafe: " + (data.warnings || []).join("; ");
            }
          })
          .catch(function (err) { showStatus("Validate error: " + String(err)); });
      });
    });

    document.querySelectorAll(".us-del-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var id = btn.getAttribute("data-id");
        if (!confirm("Delete script?")) { return; }
        fetch(API_BASE + "/" + encodeURIComponent(id), { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.status === "deleted") {
              showStatus("Deleted.");
              loadScripts();
            } else {
              showStatus("Error: " + escHtml(data.error || "unknown"));
            }
          })
          .catch(function (err) { showStatus("Delete error: " + String(err)); });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadScripts();

    var btnAdd = document.getElementById("btn-add-script");
    if (btnAdd) {
      btnAdd.addEventListener("click", function () {
        var name = document.getElementById("us-name").value.trim();
        var urlPattern = document.getElementById("us-url-pattern").value.trim();
        var runAt = document.getElementById("us-run-at").value;
        var code = document.getElementById("us-code").value;
        if (!name || !urlPattern) { showStatus("Name and URL pattern are required."); return; }
        fetch(API_BASE, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: name, url_pattern: urlPattern, run_at: runAt, code: code }),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.script_id) {
              showStatus("Script added: " + escHtml(data.script_id));
              document.getElementById("us-name").value = "";
              document.getElementById("us-url-pattern").value = "";
              document.getElementById("us-code").value = "";
              loadScripts();
            } else {
              showStatus("Error: " + escHtml(data.error || "unknown"));
            }
          })
          .catch(function (err) { showStatus("Add error: " + String(err)); });
      });
    }
  });
})();
