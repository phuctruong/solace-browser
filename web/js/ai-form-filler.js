(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var API_BASE = "/api/v1/form-filler";
  var _fieldTypes = [];

  function showStatus(msg) {
    var el = document.getElementById("aff-status");
    if (el) { el.textContent = msg; }
  }

  function loadFieldTypes() {
    fetch(API_BASE + "/field-types")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _fieldTypes = data.field_types || [];
        renderFieldTypeCheckboxes();
      })
      .catch(function (err) { showStatus("Failed to load field types: " + String(err)); });
  }

  function renderFieldTypeCheckboxes() {
    var container = document.getElementById("aff-field-types");
    if (!container) { return; }
    container.innerHTML = "";
    _fieldTypes.forEach(function (ft) {
      var lbl = document.createElement("label");
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = ft;
      cb.className = "aff-ft-cb";
      lbl.appendChild(cb);
      lbl.appendChild(document.createTextNode(ft));
      container.appendChild(lbl);
    });
  }

  function getCheckedFieldTypes() {
    var cbs = document.querySelectorAll(".aff-ft-cb:checked");
    var result = [];
    cbs.forEach(function (cb) { result.push(cb.value); });
    return result;
  }

  function renderProfile(p) {
    var div = document.createElement("div");
    div.className = "aff-card";
    div.setAttribute("data-id", p.profile_id);
    var types = (p.field_types || []).map(function (t) {
      return '<span class="aff-badge">' + escHtml(t) + '</span>';
    }).join(" ");
    div.innerHTML =
      '<div>' +
        '<div class="aff-card-meta">' +
          '<span class="aff-badge">fields: ' + escHtml(String(p.field_count)) + '</span>' +
          '<span class="aff-badge">fills: ' + escHtml(String(p.fill_count || 0)) + '</span>' +
          types +
        '</div>' +
        '<div class="aff-card-id">ID: ' + escHtml(p.profile_id) + '</div>' +
      '</div>' +
      '<button class="aff-btn aff-btn-danger aff-del-btn" data-id="' + escHtml(p.profile_id) + '">Delete</button>';
    return div;
  }

  function renderFill(f) {
    var div = document.createElement("div");
    div.className = "aff-card";
    div.innerHTML =
      '<div>' +
        '<div class="aff-card-meta">' +
          '<span class="aff-badge">profile: ' + escHtml(f.profile_id) + '</span>' +
        '</div>' +
        '<div class="aff-card-id">ID: ' + escHtml(f.fill_id) + ' &mdash; ' + escHtml(f.filled_at || "") + '</div>' +
      '</div>';
    return div;
  }

  function loadProfiles() {
    fetch(API_BASE + "/profiles")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("aff-profiles");
        if (!list) { return; }
        list.innerHTML = "";
        var profiles = data.profiles || [];
        if (profiles.length === 0) {
          list.innerHTML = '<p class="aff-empty">No profiles yet.</p>';
          return;
        }
        profiles.forEach(function (p) { list.appendChild(renderProfile(p)); });
        attachDeleteHandlers();
      })
      .catch(function (err) { showStatus("Load error: " + String(err)); });
  }

  function loadFillLog() {
    fetch(API_BASE + "/fill-log")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("aff-fill-log");
        if (!list) { return; }
        list.innerHTML = "";
        var fills = data.fills || [];
        if (fills.length === 0) {
          list.innerHTML = '<p class="aff-empty">No fill events logged.</p>';
          return;
        }
        fills.slice(-20).reverse().forEach(function (f) { list.appendChild(renderFill(f)); });
      })
      .catch(function (err) { showStatus("Fill log error: " + String(err)); });
  }

  function attachDeleteHandlers() {
    document.querySelectorAll(".aff-del-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var pid = btn.getAttribute("data-id");
        fetch(API_BASE + "/profiles/" + encodeURIComponent(pid), { method: "DELETE" })
          .then(function (r) { return r.json(); })
          .then(function () { showStatus("Profile deleted."); loadProfiles(); })
          .catch(function (err) { showStatus("Delete error: " + String(err)); });
      });
    });
  }

  function handleSubmit(e) {
    e.preventDefault();
    var profileName = document.getElementById("aff-profile-name").value.trim();
    var fieldCount = parseInt(document.getElementById("aff-field-count").value, 10);
    var fieldTypes = getCheckedFieldTypes();

    fetch(API_BASE + "/profiles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        profile_name: profileName,
        field_count: fieldCount,
        field_types: fieldTypes,
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) { showStatus("Error: " + data.error); return; }
        showStatus("Profile created.");
        loadProfiles();
      })
      .catch(function (err) { showStatus("Create error: " + String(err)); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadFieldTypes();
    loadProfiles();
    loadFillLog();
    var form = document.getElementById("aff-profile-form");
    if (form) { form.addEventListener("submit", handleSubmit); }
  });
})();
