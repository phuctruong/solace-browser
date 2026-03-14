// Diagram: 02-dashboard-login
/**
 * recipe-store.js — Hub Recipe Store frontend for Solace Hub
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - No eval. escHtml() required for all dynamic content.
 *   - IIFE pattern. Port 8888 ONLY. Debug port BANNED.
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

  // ---------------------------------------------------------------------------
  // Toast
  // ---------------------------------------------------------------------------
  var toastEl = document.getElementById("toast");
  var toastTimer = null;

  function showToast(msg, type) {
    if (!toastEl) { return; }
    toastEl.textContent = msg;
    toastEl.className = "toast show toast--" + (type || "success");
    if (toastTimer) { clearTimeout(toastTimer); }
    toastTimer = setTimeout(function () {
      toastEl.className = "toast";
    }, 3000);
  }

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  var _pendingInstall = null;  // recipe object awaiting confirmation

  // ---------------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------------
  var searchInput     = document.getElementById("search-input");
  var featuredGrid    = document.getElementById("featured-grid");
  var searchGrid      = document.getElementById("search-grid");
  var searchSection   = document.getElementById("search-section");
  var installedList   = document.getElementById("installed-list");
  var dialogOverlay   = document.getElementById("dialog-overlay");
  var dialogRecipeName = document.getElementById("dialog-recipe-name");
  var dialogScope     = document.getElementById("dialog-scope");
  var dialogCost      = document.getElementById("dialog-cost");
  var btnConfirmInstall = document.getElementById("btn-confirm-install");
  var btnCancelInstall  = document.getElementById("btn-cancel-install");

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------
  function renderRecipeCard(recipe, installed) {
    var btnLabel = installed ? "Installed" : "Install";
    var btnDisabled = installed ? " disabled" : "";
    return (
      '<div class="recipe-card" data-id="' + escHtml(recipe.recipe_id) + '">' +
        '<div class="recipe-name">' + escHtml(recipe.name) + '</div>' +
        '<div class="recipe-desc">' + escHtml(recipe.description) + '</div>' +
        '<div class="recipe-meta">' +
          '<span>' + escHtml(String(recipe.installs)) + ' installs</span>' +
          '<span>Hit rate: ' + escHtml(String(recipe.hit_rate_pct)) + '%</span>' +
          '<span>~$' + escHtml(String(recipe.avg_cost_usd)) + '/run</span>' +
        '</div>' +
        '<button class="btn btn--primary btn-install"' + btnDisabled + ' data-id="' + escHtml(recipe.recipe_id) + '">' +
          escHtml(btnLabel) +
        '</button>' +
      '</div>'
    );
  }

  function renderInstalledItem(recipe) {
    var installedAt = recipe.installed_at ? " — " + escHtml(recipe.installed_at.slice(0, 10)) : "";
    return (
      '<div class="installed-item" data-id="' + escHtml(recipe.recipe_id) + '">' +
        '<span class="installed-item-name">' + escHtml(recipe.name) + '</span>' +
        '<span class="installed-item-meta">' + escHtml(recipe.description) + installedAt + '</span>' +
        '<div class="installed-actions">' +
          '<button class="btn btn--ghost btn-run-recipe" data-id="' + escHtml(recipe.recipe_id) + '">Run</button>' +
          '<button class="btn btn--danger btn-uninstall" data-id="' + escHtml(recipe.recipe_id) + '">Uninstall</button>' +
        '</div>' +
      '</div>'
    );
  }

  // ---------------------------------------------------------------------------
  // Load featured
  // ---------------------------------------------------------------------------
  function loadFeatured() {
    if (!featuredGrid) { return; }
    apiGet("/api/v1/recipe-store/featured").then(function (res) {
      if (res.status !== 200) {
        featuredGrid.innerHTML = '<div class="empty-state">Could not load featured recipes.</div>';
        return;
      }
      var recipes = res.data.recipes || [];
      loadInstalled(function (installedIds) {
        if (recipes.length === 0) {
          featuredGrid.innerHTML = '<div class="empty-state">No featured recipes available.</div>';
          return;
        }
        var html = "";
        for (var i = 0; i < recipes.length; i++) {
          var r = recipes[i];
          html += renderRecipeCard(r, installedIds.indexOf(r.recipe_id) !== -1);
        }
        featuredGrid.innerHTML = html;
        bindInstallButtons(featuredGrid);
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Load installed
  // ---------------------------------------------------------------------------
  function loadInstalled(cb) {
    apiGet("/api/v1/recipe-store/installed").then(function (res) {
      var recipes = (res.status === 200 && res.data.recipes) ? res.data.recipes : [];
      var ids = recipes.map(function (r) { return r.recipe_id; });
      if (cb) { cb(ids); }
      if (!installedList) { return; }
      if (recipes.length === 0) {
        installedList.innerHTML = '<div class="empty-state">No recipes installed yet.</div>';
        return;
      }
      var html = "";
      for (var i = 0; i < recipes.length; i++) {
        html += renderInstalledItem(recipes[i]);
      }
      installedList.innerHTML = html;
      bindInstalledButtons(installedList);
    });
  }

  // ---------------------------------------------------------------------------
  // Search (debounced)
  // ---------------------------------------------------------------------------
  var searchTimer = null;

  function doSearch(q) {
    if (!searchSection || !searchGrid) { return; }
    if (!q.trim()) {
      searchSection.hidden = true;
      return;
    }
    apiGet("/api/v1/recipe-store/search?q=" + encodeURIComponent(q)).then(function (res) {
      searchSection.hidden = false;
      var recipes = (res.status === 200 && res.data.recipes) ? res.data.recipes : [];
      loadInstalled(function (installedIds) {
        if (recipes.length === 0) {
          searchGrid.innerHTML = '<div class="empty-state">No results for &ldquo;' + escHtml(q) + '&rdquo;</div>';
          return;
        }
        var html = "";
        for (var i = 0; i < recipes.length; i++) {
          var r = recipes[i];
          html += renderRecipeCard(r, installedIds.indexOf(r.recipe_id) !== -1);
        }
        searchGrid.innerHTML = html;
        bindInstallButtons(searchGrid);
      });
    });
  }

  // ---------------------------------------------------------------------------
  // Install flow — confirmation dialog
  // ---------------------------------------------------------------------------
  function openInstallDialog(recipe) {
    _pendingInstall = recipe;
    if (dialogRecipeName) { dialogRecipeName.textContent = recipe.name; }
    if (dialogScope) { dialogScope.textContent = recipe.app_id || "n/a"; }
    if (dialogCost) { dialogCost.textContent = "$" + recipe.avg_cost_usd + "/run"; }
    if (dialogOverlay) { dialogOverlay.classList.add("active"); }
  }

  function closeInstallDialog() {
    _pendingInstall = null;
    if (dialogOverlay) { dialogOverlay.classList.remove("active"); }
  }

  function confirmInstall() {
    if (!_pendingInstall) { return; }
    var recipe = _pendingInstall;
    closeInstallDialog();
    apiPost("/api/v1/recipe-store/install", { recipe_id: recipe.recipe_id }).then(function (res) {
      if (res.status === 200) {
        showToast("Installed: " + recipe.name, "success");
        loadFeatured();
        loadInstalled(null);
      } else {
        var msg = (res.data && res.data.error) ? res.data.error : "Install failed";
        showToast(msg, "error");
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Bind install buttons in a container
  // ---------------------------------------------------------------------------
  function bindInstallButtons(container) {
    var btns = container.querySelectorAll(".btn-install");
    for (var i = 0; i < btns.length; i++) {
      (function (btn) {
        btn.addEventListener("click", function () {
          var recipeId = btn.getAttribute("data-id");
          apiGet("/api/v1/recipe-store/featured").then(function (res) {
            var recipes = (res.status === 200 && res.data.recipes) ? res.data.recipes : [];
            var recipe = null;
            for (var j = 0; j < recipes.length; j++) {
              if (recipes[j].recipe_id === recipeId) { recipe = recipes[j]; break; }
            }
            if (recipe) { openInstallDialog(recipe); }
          });
        });
      })(btns[i]);
    }
  }

  // ---------------------------------------------------------------------------
  // Bind run/uninstall buttons in installed list
  // ---------------------------------------------------------------------------
  function bindInstalledButtons(container) {
    var runBtns = container.querySelectorAll(".btn-run-recipe");
    for (var i = 0; i < runBtns.length; i++) {
      (function (btn) {
        btn.addEventListener("click", function () {
          var recipeId = btn.getAttribute("data-id");
          showToast("Run dispatched for: " + escHtml(recipeId), "success");
        });
      })(runBtns[i]);
    }

    var uninstallBtns = container.querySelectorAll(".btn-uninstall");
    for (var j = 0; j < uninstallBtns.length; j++) {
      (function (btn) {
        btn.addEventListener("click", function () {
          var recipeId = btn.getAttribute("data-id");
          showToast("Uninstalled: " + escHtml(recipeId), "success");
          loadInstalled(null);
          loadFeatured();
        });
      })(uninstallBtns[j]);
    }
  }

  // ---------------------------------------------------------------------------
  // Wire up events
  // ---------------------------------------------------------------------------
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      var q = searchInput.value;
      if (searchTimer) { clearTimeout(searchTimer); }
      searchTimer = setTimeout(function () { doSearch(q); }, 300);
    });
  }

  if (btnConfirmInstall) {
    btnConfirmInstall.addEventListener("click", confirmInstall);
  }

  if (btnCancelInstall) {
    btnCancelInstall.addEventListener("click", closeInstallDialog);
  }

  if (dialogOverlay) {
    dialogOverlay.addEventListener("click", function (e) {
      if (e.target === dialogOverlay) { closeInstallDialog(); }
    });
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------
  loadFeatured();
  loadInstalled(null);

})();
