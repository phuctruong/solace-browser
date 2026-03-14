// Diagram: 02-dashboard-login
/**
 * recipes.js — Community Recipe Browser for Solace Hub
 * Laws:
 *   - No CDN dependencies. No jQuery. No Bootstrap. No Tailwind.
 *   - Port 8888 ONLY. Any other port reference is BANNED.
 *   - SILENT_INSTALL: BANNED — scope confirmation modal REQUIRED before install.
 *   - DIRECT_EXECUTE: BANNED — run always goes through /api/v1/actions/preview.
 *   - Solace Hub only. Legacy name BANNED.
 */

"use strict";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const API_BASE = "";  // same origin (port 8888)
const POLL_INTERVAL_MS = 30000;

// App ID → emoji mapping
const APP_ICONS = {
  gmail: "📧",
  linkedin: "💼",
  github: "🐙",
  slack: "💬",
  twitter: "🐦",
  notion: "📝",
  hubspot: "📊",
  trello: "📋",
  jira: "🔖",
  default: "⚙️",
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let _recipes = [];
let _activeTab = "community";
let _activeCategory = "";
let _searchQuery = "";
let _sortBy = "popular";
let _pendingInstallRecipe = null;
let _pollTimer = null;

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------
function $(id) {
  return document.getElementById(id);
}

function showToast(msg, type) {
  const el = $("toast");
  el.textContent = msg;
  el.className = "toast visible " + (type || "");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => { el.className = "toast"; }, 3500);
}

function getAppIcon(appId) {
  if (!appId) return APP_ICONS.default;
  const key = appId.toLowerCase().split("-")[0];
  return APP_ICONS[key] || APP_ICONS.default;
}

function hitRateClass(pct) {
  const n = parseInt(pct, 10) || 0;
  if (n >= 70) return "hit-rate--green";
  if (n >= 50) return "hit-rate--amber";
  return "hit-rate--red";
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Token helpers (read from port.lock cookie or localStorage — never from port)
// ---------------------------------------------------------------------------
function getToken() {
  // Hub injects token into localStorage under 'solace_token_sha256'
  return localStorage.getItem("solace_token_sha256") || "";
}

function authHeaders(extra) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;
  return Object.assign(headers, extra || {});
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
async function apiFetch(path, options) {
  const response = await fetch(API_BASE + path, options || {});
  const body = await response.json();
  return { status: response.status, data: body };
}

async function apiGet(path) {
  return apiFetch(path, {
    method: "GET",
    headers: authHeaders(),
  });
}

async function apiPost(path, payload) {
  return apiFetch(path, {
    method: "POST",
    headers: authHeaders(),
    body: payload !== undefined ? JSON.stringify(payload) : undefined,
  });
}

// ---------------------------------------------------------------------------
// Load recipes
// ---------------------------------------------------------------------------
async function loadRecipes() {
  let url = "/api/v1/recipes";
  const params = [];
  if (_activeCategory) params.push("category=" + encodeURIComponent(_activeCategory));
  if (_sortBy) params.push("sort=" + encodeURIComponent(_sortBy));
  params.push("limit=40");
  if (params.length) url += "?" + params.join("&");

  try {
    const { status, data } = await apiGet(url);
    if (status === 200 && Array.isArray(data.recipes)) {
      _recipes = data.recipes;
      renderGrid();
    } else {
      showToast("Failed to load recipes", "error");
    }
  } catch (_err) {
    showToast("Network error loading recipes", "error");
  }
}

async function loadMyLibrary() {
  try {
    const { status, data } = await apiGet("/api/v1/recipes/my-library");
    if (status === 200 && Array.isArray(data.recipes)) {
      _recipes = data.recipes;
      renderGrid();
    } else {
      showToast("Failed to load library", "error");
    }
  } catch (_err) {
    showToast("Network error loading library", "error");
  }
}

// ---------------------------------------------------------------------------
// Render grid
// ---------------------------------------------------------------------------
function renderGrid() {
  const grid = $("recipes-grid");
  const emptyState = $("empty-state");

  // Filter by search query client-side
  let visible = _recipes;
  if (_searchQuery) {
    const q = _searchQuery.toLowerCase();
    visible = _recipes.filter(r =>
      (r.name || "").toLowerCase().includes(q) ||
      (r.description || "").toLowerCase().includes(q) ||
      (r.creator || "").toLowerCase().includes(q) ||
      (r.tags || []).some(t => t.toLowerCase().includes(q))
    );
  }

  // Clear existing cards (keep empty-state element)
  Array.from(grid.children).forEach(child => {
    if (child.id !== "empty-state") child.remove();
  });

  if (visible.length === 0) {
    emptyState.hidden = false;
    return;
  }
  emptyState.hidden = true;

  visible.forEach(recipe => {
    const card = buildRecipeCard(recipe);
    grid.appendChild(card);
  });
}

function buildRecipeCard(recipe) {
  const card = document.createElement("div");
  card.className = "recipe-card";
  card.setAttribute("data-recipe-id", escHtml(recipe.recipe_id || ""));
  card.setAttribute("role", "listitem");

  const icon = getAppIcon(recipe.app_id);
  const hitClass = hitRateClass(recipe.hit_rate_pct || 0);
  const isInstalled = Boolean(recipe.is_installed);
  const tagsHtml = (recipe.tags || [])
    .map(t => `<span class="tag">${escHtml(t)}</span>`)
    .join("");

  card.innerHTML = `
    <div class="recipe-card__header">
      <span class="recipe-card__icon">${icon}</span>
      <span class="recipe-card__name" title="${escHtml(recipe.name || "")}">${escHtml(recipe.name || "Untitled")}</span>
      ${isInstalled ? '<span class="recipe-card__installed-badge">✓ installed</span>' : ""}
    </div>
    <div class="recipe-card__creator">by: ${escHtml(recipe.creator || "unknown")}</div>
    <div class="recipe-card__hit-rate ${hitClass}">${parseInt(recipe.hit_rate_pct || 0, 10)}% hit rate</div>
    <div class="recipe-card__stats">${parseInt(recipe.runs_count || 0, 10)} installs&nbsp;|&nbsp;$${escHtml(recipe.avg_cost_usd || "0.001")}/run</div>
    ${recipe.description ? `<div class="recipe-card__description">${escHtml(recipe.description)}</div>` : ""}
    <div class="recipe-card__tags">${tagsHtml}</div>
    <div class="recipe-card__actions">
      <button class="btn-install" data-recipe-id="${escHtml(recipe.recipe_id || "")}" ${isInstalled ? "disabled" : ""}>${isInstalled ? "Installed" : "Install"}</button>
      <button class="btn-preview" data-recipe-id="${escHtml(recipe.recipe_id || "")}">Preview</button>
      <button class="btn-fork" data-recipe-id="${escHtml(recipe.recipe_id || "")}">Fork</button>
    </div>
  `;

  // Attach listeners
  const btnInstall = card.querySelector(".btn-install");
  if (btnInstall && !isInstalled) {
    btnInstall.addEventListener("click", () => installRecipe(recipe));
  }

  card.querySelector(".btn-preview").addEventListener("click", () => openDetailModal(recipe));
  card.querySelector(".btn-fork").addEventListener("click", () => forkRecipe(recipe.recipe_id, recipe.name));

  return card;
}

// ---------------------------------------------------------------------------
// Install flow — SILENT_INSTALL is BANNED
// Step 1: show scope confirmation modal FIRST
// Step 2: user clicks Install → confirmInstall()
// ---------------------------------------------------------------------------
function installRecipe(recipe) {
  _pendingInstallRecipe = recipe;

  // Show scope confirmation modal BEFORE making any install request
  const scopeDetails = $("scope-details");
  scopeDetails.innerHTML = `
    <ul>
      <li>App: ${escHtml(recipe.app_id || "unknown")}</li>
      <li>Creator: ${escHtml(recipe.creator || "unknown")}</li>
      <li>Tags: ${escHtml((recipe.tags || []).join(", ") || "none")}</li>
      <li>Version: ${escHtml(recipe.version || "1.0.0")}</li>
    </ul>
  `;

  $("scope-modal").hidden = false;
}

async function confirmInstall() {
  $("scope-modal").hidden = true;
  const recipe = _pendingInstallRecipe;
  _pendingInstallRecipe = null;
  if (!recipe) return;

  try {
    const { status, data } = await apiPost(`/api/v1/recipes/${encodeURIComponent(recipe.recipe_id)}/install`, {});
    if (status === 200 && data.installed) {
      showToast(`Installed: ${recipe.name}`, "success");
      // Refresh the grid to update installed badge
      if (_activeTab === "community") {
        await loadRecipes();
      } else {
        await loadMyLibrary();
      }
    } else {
      showToast("Install failed: " + (data.error || "unknown error"), "error");
    }
  } catch (_err) {
    showToast("Network error during install", "error");
  }
}

// ---------------------------------------------------------------------------
// Run flow — DIRECT_EXECUTE is BANNED — always through /api/v1/actions/preview
// ---------------------------------------------------------------------------
async function runRecipe(recipeId) {
  try {
    const { status, data } = await apiPost(`/api/v1/recipes/${encodeURIComponent(recipeId)}/run`, {});
    if (status === 202 && data.requires_approval) {
      showApprovalFlow(data.preview_id, data.preview_text, data.action_class);
    } else {
      showToast("Run request failed: " + (data.error || "unknown"), "error");
    }
  } catch (_err) {
    showToast("Network error starting run", "error");
  }
}

function showApprovalFlow(previewId, previewText, actionClass) {
  // Display approval info in the detail modal if open, or as a toast + redirect
  showToast(`Preview created (${actionClass}): ${previewText.substring(0, 60)}...`, "success");
  // TODO: integrate with full approval panel in schedule viewer
}

// ---------------------------------------------------------------------------
// Fork flow
// ---------------------------------------------------------------------------
async function forkRecipe(recipeId, originalName) {
  const forkName = prompt(`Fork name for "${originalName}":`, `${originalName} (fork)`);
  if (!forkName || !forkName.trim()) return;

  try {
    const { status, data } = await apiPost(
      `/api/v1/recipes/${encodeURIComponent(recipeId)}/fork`,
      { name: forkName.trim() }
    );
    if (status === 201 && data.new_recipe_id) {
      showToast(`Forked as: ${forkName.trim()}`, "success");
      await loadMyLibrary();
      switchTab("my-library");
    } else {
      showToast("Fork failed: " + (data.error || "unknown"), "error");
    }
  } catch (_err) {
    showToast("Network error during fork", "error");
  }
}

// ---------------------------------------------------------------------------
// Detail modal
// ---------------------------------------------------------------------------
function openDetailModal(recipe) {
  const icon = getAppIcon(recipe.app_id);
  const hitClass = hitRateClass(recipe.hit_rate_pct || 0);
  const tagsHtml = (recipe.tags || [])
    .map(t => `<span class="tag">${escHtml(t)}</span>`)
    .join("");

  $("modal-body").innerHTML = `
    <div class="detail-header">
      <span class="detail-icon">${icon}</span>
      <div>
        <h2 class="detail-title" id="modal-recipe-name">${escHtml(recipe.name || "")}</h2>
        <div class="detail-creator">by ${escHtml(recipe.creator || "unknown")} &bull; v${escHtml(recipe.version || "1.0.0")}</div>
      </div>
    </div>

    <div class="detail-section">
      <h4>Description</h4>
      <p>${escHtml(recipe.description || "No description provided.")}</p>
    </div>

    <div class="detail-section">
      <h4>Stats</h4>
      <p>
        <span class="recipe-card__hit-rate ${hitClass}">${parseInt(recipe.hit_rate_pct || 0, 10)}% hit rate</span>
        &nbsp; ${parseInt(recipe.runs_count || 0, 10)} installs &nbsp; $${escHtml(recipe.avg_cost_usd || "0.001")}/run
      </p>
    </div>

    ${tagsHtml ? `<div class="detail-section"><h4>Tags</h4><div class="recipe-card__tags">${tagsHtml}</div></div>` : ""}

    <div class="detail-actions">
      ${!recipe.is_installed
        ? `<button class="btn btn--accent" id="detail-install-btn">Install</button>`
        : `<span class="recipe-card__installed-badge">✓ Installed</span>`
      }
      <button class="btn btn--ghost" id="detail-run-btn">Run (requires approval)</button>
      <button class="btn btn--muted" id="detail-fork-btn">Fork</button>
    </div>
  `;

  if (!recipe.is_installed) {
    $("detail-install-btn").addEventListener("click", () => {
      closeDetailModal();
      installRecipe(recipe);
    });
  }

  $("detail-run-btn").addEventListener("click", () => runRecipe(recipe.recipe_id));
  $("detail-fork-btn").addEventListener("click", () => {
    closeDetailModal();
    forkRecipe(recipe.recipe_id, recipe.name);
  });

  $("recipe-modal").hidden = false;
}

function closeDetailModal() {
  $("recipe-modal").hidden = true;
}

// ---------------------------------------------------------------------------
// Creator modal
// ---------------------------------------------------------------------------
function openCreatorModal() {
  $("creator-modal").hidden = false;
  $("creator-name").focus();
}

function closeCreatorModal() {
  $("creator-modal").hidden = true;
  $("creator-form").reset();
}

async function submitCreator(evt) {
  evt.preventDefault();
  const name = $("creator-name").value.trim();
  const appId = $("creator-app-id").value.trim();
  const description = $("creator-desc").value.trim();
  const tagsRaw = $("creator-tags").value.trim();
  const tags = tagsRaw ? tagsRaw.split(",").map(t => t.trim()).filter(Boolean) : [];

  if (!name) {
    showToast("Name is required", "error");
    return;
  }

  try {
    const { status, data } = await apiPost("/api/v1/recipes/create", {
      name,
      app_id: appId,
      description,
      tags,
      steps: [],
    });
    if (status === 201 && data.recipe_id) {
      showToast(`Created: ${name}`, "success");
      closeCreatorModal();
      await loadMyLibrary();
      switchTab("my-library");
    } else {
      showToast("Create failed: " + (data.error || "unknown"), "error");
    }
  } catch (_err) {
    showToast("Network error creating recipe", "error");
  }
}

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
function switchTab(tab) {
  _activeTab = tab;

  ["community", "my-library"].forEach(t => {
    const btn = document.querySelector(`[data-tab="${t}"]`);
    if (btn) btn.classList.toggle("active", t === tab);
  });

  if (tab === "community") {
    loadRecipes();
  } else {
    loadMyLibrary();
  }
}

// ---------------------------------------------------------------------------
// Event wiring
// ---------------------------------------------------------------------------
function wireEvents() {
  // Search input
  $("recipe-search").addEventListener("input", evt => {
    _searchQuery = evt.target.value;
    renderGrid();
  });

  // Sort select
  $("sort-select").addEventListener("change", evt => {
    _sortBy = evt.target.value;
    if (_activeTab === "community") loadRecipes();
  });

  // Category pills
  document.querySelectorAll(".pill").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      _activeCategory = btn.getAttribute("data-category") || "";
      if (_activeTab === "community") loadRecipes();
    });
  });

  // Tab buttons
  document.querySelectorAll(".tab-btn[data-tab]").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.getAttribute("data-tab")));
  });

  // Create recipe button
  $("btn-open-creator").addEventListener("click", openCreatorModal);

  // Explore community (empty state)
  $("btn-explore-community").addEventListener("click", () => switchTab("community"));

  // Detail modal close
  $("modal-close").addEventListener("click", closeDetailModal);
  $("modal-backdrop").addEventListener("click", closeDetailModal);

  // Scope confirmation modal
  $("scope-confirm-btn").addEventListener("click", confirmInstall);
  $("scope-cancel-btn").addEventListener("click", () => {
    $("scope-modal").hidden = true;
    _pendingInstallRecipe = null;
  });
  $("scope-backdrop").addEventListener("click", () => {
    $("scope-modal").hidden = true;
    _pendingInstallRecipe = null;
  });

  // Creator modal
  $("creator-close").addEventListener("click", closeCreatorModal);
  $("creator-backdrop").addEventListener("click", closeCreatorModal);
  $("creator-cancel-btn").addEventListener("click", closeCreatorModal);
  $("creator-form").addEventListener("submit", submitCreator);

  // Keyboard close
  document.addEventListener("keydown", evt => {
    if (evt.key === "Escape") {
      closeDetailModal();
      $("scope-modal").hidden = true;
      closeCreatorModal();
      _pendingInstallRecipe = null;
    }
  });
}

// ---------------------------------------------------------------------------
// Periodic refresh
// ---------------------------------------------------------------------------
function startPolling() {
  if (_pollTimer) clearInterval(_pollTimer);
  _pollTimer = setInterval(() => {
    if (_activeTab === "community") {
      loadRecipes();
    }
  }, POLL_INTERVAL_MS);
}

// ---------------------------------------------------------------------------
// Bootstrap
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  wireEvents();
  loadRecipes();
  startPolling();
});
