// Diagram: 02-dashboard-login
/**
 * app-store.js — App Store Browser frontend for Solace Hub
 * Task 030 | Rung 641
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
 *   - 6 catalog apps hardcoded (cannot delete); install/uninstall toggle.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin
  var _currentTab = "catalog";
  var _currentCat = "";
  var _searchTerm  = "";
  var _allApps = [];

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

  // -------------------------------------------------------------------------
  // Banner
  // -------------------------------------------------------------------------
  function showBanner(msg, type) {
    var el = document.getElementById("status-banner");
    if (!el) { return; }
    el.textContent = msg;
    el.className = "status-banner " + type;
    setTimeout(function () { el.className = "status-banner hidden"; }, 3000);
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  function renderApps(apps) {
    var grid = document.getElementById("app-grid");
    var empty = document.getElementById("empty-msg");
    if (!grid) { return; }
    grid.innerHTML = "";

    var filtered = apps.filter(function (a) {
      var catOk = !_currentCat || a.category === _currentCat;
      var searchOk = !_searchTerm
        || a.name.toLowerCase().indexOf(_searchTerm) !== -1
        || (a.description || "").toLowerCase().indexOf(_searchTerm) !== -1;
      return catOk && searchOk;
    });

    if (filtered.length === 0) {
      if (empty) { empty.classList.remove("hidden"); }
      return;
    }
    if (empty) { empty.classList.add("hidden"); }

    filtered.forEach(function (app) {
      var card = document.createElement("div");
      card.className = "app-card";

      var nameEl = document.createElement("div");
      nameEl.className = "app-name";
      nameEl.textContent = app.name;

      var descEl = document.createElement("div");
      descEl.className = "app-desc";
      descEl.textContent = app.description || "";

      var catEl = document.createElement("span");
      catEl.className = "app-category";
      catEl.textContent = app.category;

      var ratingEl = document.createElement("span");
      ratingEl.className = "app-rating";
      ratingEl.textContent = "\u2605 " + escHtml(String(app.rating || ""));

      var metaEl = document.createElement("div");
      metaEl.className = "app-meta";
      metaEl.appendChild(catEl);
      metaEl.appendChild(ratingEl);

      var actionBtn = document.createElement("button");
      if (app.installed) {
        actionBtn.className = "btn-uninstall";
        actionBtn.textContent = app.builtin ? "Built-in" : "Uninstall";
        if (app.builtin) { actionBtn.disabled = true; }
        actionBtn.addEventListener("click", function () {
          if (app.builtin) { return; }
          apiPost("/api/v1/app-store/uninstall", { app_id: app.id }).then(function (res) {
            if (res.status === 200) {
              showBanner(escHtml(app.name) + " uninstalled", "success");
              loadCurrentTab();
            } else {
              var msg = (res.data && res.data.error) || "Failed";
              showBanner(msg, "error");
            }
          });
        });
      } else {
        actionBtn.className = "btn-install";
        actionBtn.textContent = "Install";
        actionBtn.addEventListener("click", function () {
          apiPost("/api/v1/app-store/install", { app_id: app.id }).then(function (res) {
            if (res.status === 200) {
              showBanner(escHtml(app.name) + " installed", "success");
              loadCurrentTab();
            } else {
              var msg = (res.data && res.data.error) || "Failed";
              showBanner(msg, "error");
            }
          });
        });
      }

      card.appendChild(nameEl);
      card.appendChild(descEl);
      card.appendChild(metaEl);
      card.appendChild(actionBtn);
      grid.appendChild(card);
    });
  }

  // -------------------------------------------------------------------------
  // Load
  // -------------------------------------------------------------------------
  function loadCurrentTab() {
    var endpoint = _currentTab === "installed"
      ? "/api/v1/app-store/installed"
      : "/api/v1/app-store/catalog";
    apiGet(endpoint).then(function (res) {
      _allApps = (res.data && res.data.apps) || [];
      renderApps(_allApps);
    });
  }

  function loadCategories() {
    apiGet("/api/v1/app-store/categories").then(function (res) {
      var cats = (res.data && res.data.categories) || [];
      var container = document.getElementById("cat-buttons");
      if (!container) { return; }
      container.innerHTML = "";
      cats.forEach(function (cat) {
        var btn = document.createElement("button");
        btn.className = "cat-btn";
        btn.setAttribute("data-cat", cat);
        btn.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
        btn.addEventListener("click", function () {
          _currentCat = cat;
          document.querySelectorAll(".cat-btn").forEach(function (b) {
            b.classList.toggle("active", b.getAttribute("data-cat") === cat);
          });
          renderApps(_allApps);
        });
        container.appendChild(btn);
      });
    });
  }

  // -------------------------------------------------------------------------
  // Init
  // -------------------------------------------------------------------------
  function init() {
    loadCategories();
    loadCurrentTab();

    // Tab switching
    document.querySelectorAll(".tab-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        _currentTab = btn.getAttribute("data-tab");
        document.querySelectorAll(".tab-btn").forEach(function (b) {
          b.classList.toggle("active", b.getAttribute("data-tab") === _currentTab);
        });
        loadCurrentTab();
      });
    });

    // "All" category button
    var allBtn = document.querySelector(".cat-btn[data-cat='']");
    if (allBtn) {
      allBtn.addEventListener("click", function () {
        _currentCat = "";
        document.querySelectorAll(".cat-btn").forEach(function (b) {
          b.classList.toggle("active", b.getAttribute("data-cat") === "");
        });
        renderApps(_allApps);
      });
    }

    // Search
    var searchInput = document.getElementById("search-input");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        _searchTerm = searchInput.value.toLowerCase().trim();
        renderApps(_allApps);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
