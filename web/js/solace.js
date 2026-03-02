(function () {
  const state = {
    tunnel: {
      status: "disconnected",
      publicUrl: "Not connected",
      approval: "OAuth3 scope required before opening the tunnel.",
    },
    apps: [],
    settings: null,
  };

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    markActiveNav();
    initHamburger();
    initLangSwitcher();
    initFooterYear();
    initRevealObserver();
    initParticles();
    initDelight();

    const page = document.body.dataset.page || "";
    if (page === "home") {
      initHomePage();
    } else if (page === "download") {
      initDownloadPage();
    } else if (page === "machine-dashboard") {
      initMachineDashboard();
    } else if (page === "tunnel-connect") {
      initTunnelPage();
    } else if (page === "app-store") {
      initAppStorePage();
    } else if (page === "app-detail") {
      initAppDetailPage();
    } else if (page === "settings") {
      initSettingsPage();
    }
  }

  function initDelight() {
    if (typeof YinyangDelight === "undefined") {
      return;
    }

    YinyangDelight.init();
    document.addEventListener("solace:warm-token", (event) => {
      const warmToken = event.detail || {};
      YinyangDelight.respond(warmToken);
    });
    document.addEventListener("solace:celebrate", (event) => {
      const detail = event.detail || {};
      const trigger = detail.trigger || "first_run_complete";
      YinyangDelight.celebrate(trigger, detail.data || {});
    });
  }

  function markActiveNav() {
    const current = window.location.pathname === "/" ? "/" : window.location.pathname.replace(/\.html$/, "");
    document.querySelectorAll("[data-nav-path]").forEach((link) => {
      if (link.getAttribute("data-nav-path") === current) {
        link.classList.add("is-active");
      }
    });
  }

  function initHamburger() {
    const toggle = document.querySelector("#hamburger-toggle");
    const menu = document.querySelector("#mobile-menu");
    if (!toggle || !menu) {
      return;
    }

    function closeMenu() {
      menu.classList.remove("is-active");
      toggle.classList.remove("is-active");
      toggle.setAttribute("aria-expanded", "false");
    }

    toggle.addEventListener("click", function () {
      const willOpen = !menu.classList.contains("is-active");
      menu.classList.toggle("is-active", willOpen);
      toggle.classList.toggle("is-active", willOpen);
      toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
    });

    document.addEventListener("click", function (event) {
      if (!(event.target instanceof Node)) {
        return;
      }
      if (!toggle.contains(event.target) && !menu.contains(event.target)) {
        closeMenu();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeMenu();
      }
    });
  }

  function initLangSwitcher() {
    const btn = document.querySelector("#sb-lang-btn");
    const menu = document.querySelector("#sb-lang-menu");
    if (!btn || !menu) return;

    const current = localStorage.getItem("sb_locale") || "en";
    menu.querySelectorAll("[data-locale]").forEach((a) => {
      a.setAttribute("aria-current", a.dataset.locale === current ? "true" : "false");
    });

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = menu.classList.toggle("is-active");
      btn.setAttribute("aria-expanded", open);
    });

    menu.addEventListener("click", (e) => {
      e.preventDefault();
      const link = e.target.closest("[data-locale]");
      if (!link) return;
      const code = link.dataset.locale;
      localStorage.setItem("sb_locale", code);
      menu.classList.remove("is-active");
      btn.setAttribute("aria-expanded", "false");
      menu.querySelectorAll("[data-locale]").forEach((a) => {
        a.setAttribute("aria-current", a.dataset.locale === code ? "true" : "false");
      });
    });

    document.addEventListener("click", (e) => {
      if (menu.classList.contains("is-active") && !btn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.remove("is-active");
        btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  function initFooterYear() {
    document.querySelectorAll("[data-current-year]").forEach((node) => {
      node.textContent = String(new Date().getFullYear());
    });
  }

  function initRevealObserver() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
        }
      });
    }, { threshold: 0.15 });

    document.querySelectorAll(".reveal").forEach((node) => observer.observe(node));
  }

  function initParticles() {
    const canvas = document.querySelector("[data-particles-canvas]");
    if (!canvas) {
      return;
    }

    const context = canvas.getContext("2d");
    const particles = [];
    let width = 0;
    let height = 0;

    function resize() {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      particles.length = 0;
      for (let index = 0; index < 36; index += 1) {
        particles.push({
          x: Math.random() * width,
          y: Math.random() * height,
          radius: 1 + Math.random() * 2.5,
          speedX: -0.35 + Math.random() * 0.7,
          speedY: -0.3 + Math.random() * 0.6,
        });
      }
    }

    function draw() {
      context.clearRect(0, 0, width, height);
      particles.forEach((particle) => {
        particle.x += particle.speedX;
        particle.y += particle.speedY;
        if (particle.x < 0) particle.x = width;
        if (particle.x > width) particle.x = 0;
        if (particle.y < 0) particle.y = height;
        if (particle.y > height) particle.y = 0;
        context.beginPath();
        context.fillStyle = "rgba(100, 196, 255, 0.5)";
        context.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
        context.fill();
      });
      requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener("resize", resize);
    requestAnimationFrame(draw);
  }

  async function fetchJson(url, options) {
    let response;
    try {
      response = await fetch(url, options);
    } catch (networkError) {
      return { ok: false, status: 0, error: "Network error: " + (networkError.message || String(networkError)) };
    }
    if (!response.ok) {
      return { ok: false, status: response.status, error: response.statusText };
    }
    try {
      const data = await response.json();
      return { ok: true, data: data };
    } catch (_parseError) {
      return { ok: false, status: response.status, error: "JSON parse error" };
    }
  }

  function showError(message) {
    const banner = document.createElement("div");
    banner.setAttribute("role", "alert");
    banner.setAttribute("aria-live", "assertive");
    banner.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:10000;padding:12px 20px;background:#d32f2f;color:#fff;font-family:inherit;font-size:14px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.3);transition:opacity 0.3s ease;";
    banner.textContent = message;
    document.body.appendChild(banner);
    setTimeout(function () {
      banner.style.opacity = "0";
      setTimeout(function () {
        if (banner.parentNode) {
          banner.parentNode.removeChild(banner);
        }
      }, 300);
    }, 5000);
  }

  function setText(selector, value) {
    const node = document.querySelector(selector);
    if (node) {
      node.textContent = value;
    }
  }

  function initHomePage() {
    bindRecipeSearch();
    loadTokenTable();
    loadActivityFeed();
    loadScopeSummary();
  }

  function bindRecipeSearch() {
    const input = document.querySelector("#recipe-search");
    if (!input) {
      return;
    }
    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      document.querySelectorAll("[data-recipe-name]").forEach((item) => {
        const match = item.getAttribute("data-recipe-name").toLowerCase().includes(query);
        item.hidden = !match;
      });
    });
  }

  async function loadTokenTable() {
    const tbody = document.querySelector("#token-table-body");
    if (!tbody) {
      return;
    }
    const result = await fetchJson("/api/tokens/active", { headers: { Accept: "application/json" } });
    if (!result.ok) {
      showError("Failed to load token table: " + result.error);
    }
    const tokens = Array.isArray(result.ok && result.data && result.data.tokens) ? result.data.tokens : [
      { app: "GitHub", scope: "repo:read,user:email", status: "Ready", expires_at: "Rotates on connect" },
      { app: "Slack", scope: "channels:read,chat:write", status: "Approval needed", expires_at: "Pending grant" },
    ];

    tbody.innerHTML = tokens.map((token) => `
      <tr>
        <td>${escapeHtml(token.app || token.provider || "Unknown")}</td>
        <td>${escapeHtml(token.scope || token.scopes || "No scopes")}</td>
        <td>${escapeHtml(token.status || "Ready")}</td>
        <td>${escapeHtml(token.expires_at || token.expiresAt || "Managed by vault")}</td>
      </tr>
    `).join("");
  }

  async function loadActivityFeed() {
    const list = document.querySelector("#activity-list");
    if (!list) {
      return;
    }
    const result = await fetchJson("/api/activity/recent", { headers: { Accept: "application/json" } });
    if (!result.ok) {
      showError("Failed to load activity feed: " + result.error);
    }
    const items = Array.isArray(result.ok && result.data && result.data.items) ? result.data.items : [
      { title: "Recipe draft updated", detail: "Added OAuth3 approval step for GitHub publishing." },
      { title: "Machine scope narrowed", detail: "Downloads folder remains readable, shell stays blocked." },
      { title: "Tunnel request pending", detail: "Waiting on explicit cloud-connect approval." },
    ];
    list.innerHTML = items.map((item) => `<li><strong>${escapeHtml(item.title)}</strong><br>${escapeHtml(item.detail)}</li>`).join("");
  }

  async function loadScopeSummary() {
    const list = document.querySelector("#scope-list");
    if (!list) {
      return;
    }
    const result = await fetchJson("/api/tokens/scopes", { headers: { Accept: "application/json" } });
    if (!result.ok) {
      showError("Failed to load scope summary: " + result.error);
    }
    const scopes = Array.isArray(result.ok && result.data && result.data.scopes) ? result.data.scopes : [
      "browser.read DOM snapshots",
      "machine.read Downloads only",
      "tunnel.connect one-time approval",
      "recipes.write draft only",
    ];
    list.innerHTML = scopes.map((scope) => `<li><span class="scope-tag">OAuth3</span> ${escapeHtml(scope)}</li>`).join("");
  }

  function initDownloadPage() {
    const platform = detectPlatform();
    setText("#detected-platform", platform.label);
    const button = document.querySelector("#primary-download");
    const command = document.querySelector("#install-command");
    if (!button || !command) {
      return;
    }
    button.href = platform.href;
    button.querySelector("span:last-child").textContent = platform.button;
    command.textContent = platform.command;
  }

  async function initAppStorePage() {
    const result = await fetchJson("/api/apps", { headers: { Accept: "application/json" } });
    if (!result.ok) {
      showError("Failed to load app store: " + result.error);
    }
    state.apps = Array.isArray(result.ok && result.data && result.data.apps) ? result.data.apps : [];
    renderAppStoreCategories(state.apps);
    bindAppStoreSearch();
    loadFunPacks();
    emitWarmToken({ mode: "warm_friendly", trigger: "app_store_loaded" });
  }

  async function loadFunPacks() {
    const grid = document.querySelector("#fun-pack-grid");
    if (!grid) {
      return;
    }
    const result = await fetchJson("/api/fun-packs", { headers: { Accept: "application/json" } });
    const packs = Array.isArray(result.ok && result.data && result.data.packs) ? result.data.packs : null;

    if (!packs || packs.length === 0) {
      grid.innerHTML = `
        <div class="kpi-card">
          <strong>Default English Pack</strong>
          <span>100 jokes + 100 facts. Installed automatically.</span>
          <span class="status-tag status-tag--success" style="margin-top:8px">installed</span>
        </div>
        <div class="kpi-card">
          <strong>More packs coming</strong>
          <span>Community packs in 13 languages downloadable from packs.solaceagi.com.</span>
          <span class="status-tag status-tag--neutral" style="margin-top:8px">soon</span>
        </div>
      `;
      return;
    }

    grid.innerHTML = packs.map((pack) => `
      <div class="kpi-card">
        <strong>${escapeHtml(pack.name || pack.id)}</strong>
        <span>${escapeHtml(pack.description || `${pack.jokes_count || "?"} jokes · ${pack.facts_count || "?"} facts`)}</span>
        <span class="recipe-tag" style="margin-top:8px">${escapeHtml(pack.locale || "en")}</span>
        <span class="status-tag status-tag--success" style="margin-top:4px">installed</span>
      </div>
    `).join("");
  }

  function bindAppStoreSearch() {
    const input = document.querySelector("#app-search");
    if (!input) {
      return;
    }
    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      const filtered = state.apps.filter((app) => {
        const haystack = [app.name, app.category, app.site, app.description].join(" ").toLowerCase();
        return haystack.includes(query);
      });
      renderAppStoreCategories(filtered);
    });
  }

  function renderAppStoreCategories(apps) {
    const mount = document.querySelector("#app-store-categories");
    if (!mount) {
      return;
    }
    if (!Array.isArray(apps) || apps.length === 0) {
      mount.innerHTML = `
        <article class="data-panel">
          <p class="section-copy">No apps matched the current filter.</p>
        </article>
      `;
      return;
    }

    const categories = {};
    apps.forEach((app) => {
      const category = app.category || "uncategorized";
      if (!categories[category]) {
        categories[category] = [];
      }
      categories[category].push(app);
    });

    mount.innerHTML = Object.keys(categories).sort().map((category) => `
      <section class="page-section reveal">
        <div class="section-heading">
          <div>
            <h3 class="section-title">${escapeHtml(titleCase(category))}</h3>
            <p class="section-copy">${escapeHtml(categoryCopy(category))}</p>
          </div>
        </div>
        <div class="surface-grid">
          ${categories[category].map((app) => renderAppCard(app)).join("")}
        </div>
      </section>
    `).join("");
  }

  function renderAppCard(app) {
    return `
      <a class="surface-card" href="/app-detail?app=${encodeURIComponent(app.id)}" data-app-name="${escapeHtml(app.name || app.id)}">
        <div class="surface-card__icon">${escapeHtml((app.name || app.id).slice(0, 2).toUpperCase())}</div>
        <h3>${escapeHtml(app.name || app.id)}</h3>
        <p>${escapeHtml(app.description || "Live app manifest loaded from the filesystem.")}</p>
        <div class="status-strip">
          <span class="status-pill ${statusPillClass(app.status)}"><span class="status-pill__dot"></span>${escapeHtml(readableStatus(app.status))}</span>
          <span class="recipe-tag">Safety ${escapeHtml(app.safety || "A")}</span>
          <span class="recipe-tag">${escapeHtml(app.site || "web")}</span>
        </div>
      </a>
    `;
  }

  async function initAppDetailPage() {
    const params = new URLSearchParams(window.location.search);
    const appId = params.get("app");
    if (!appId) {
      renderAppDetailError("Missing ?app= query parameter.");
      return;
    }
    const result = await fetchJson(`/api/apps/${encodeURIComponent(appId)}`, { headers: { Accept: "application/json" } });
    if (!result.ok) {
      showError("Failed to load app details: " + result.error);
      renderAppDetailError(`App not found: ${appId}`);
      return;
    }
    renderAppDetail(result.data);
    emitWarmToken({ mode: "warm_friendly", trigger: "app_detail_loaded" });
  }

  function renderAppDetail(app) {
    setText("#app-name", app.name || app.id);
    setText("#app-desc", app.description || "No description available.");
    setText("#app-safety", `Safety ${app.safety || "A"}`);
    setText("#app-site", app.site || "web");
    setText("#app-inbox-path", `Drop files into ~/.solace/apps/${app.id}/inbox/ to teach the AI your preferences.`);

    const iconEl = document.querySelector("#app-icon");
    if (iconEl) {
      iconEl.src = `/images/apps/${app.id}.png`;
      iconEl.onerror = function () { this.src = "/images/apps/default.png"; };
    }

    const status = document.querySelector("#app-status");
    if (status) {
      status.className = `status-pill ${statusPillClass(app.status)}`;
      status.innerHTML = `<span class="status-pill__dot"></span>${escapeHtml(readableStatus(app.status || "available"))}`;
    }

    renderFileSections("#app-inbox-sections", app.inbox || {}, ["prompts", "templates", "assets", "policies", "datasets", "requests"]);
    renderFileSections("#app-outbox-sections", app.outbox || {}, ["previews", "drafts", "reports", "suggestions", "runs"]);
    renderBudgetTable(app.budgets || {});
    renderScopes(app.scopes || []);
    renderRuns(app.recent_runs || []);
  }

  function renderAppDetailError(message) {
    setText("#app-name", "App unavailable");
    setText("#app-desc", message);
    renderFileSections("#app-inbox-sections", {}, ["prompts", "templates", "assets", "policies", "datasets", "requests"]);
    renderFileSections("#app-outbox-sections", {}, ["previews", "drafts", "reports", "suggestions", "runs"]);
  }

  function renderFileSections(selector, listing, order) {
    const mount = document.querySelector(selector);
    if (!mount) {
      return;
    }
    mount.innerHTML = order.map((sectionName, index) => `
      <h3>${escapeHtml(sectionName)}/</h3>
      <ul class="file-list">
        ${renderFileList(listing[sectionName] || [], fileFallbackLabel(sectionName))}
      </ul>
    `).join("");
  }

  function renderFileList(items, fallbackText) {
    if (!Array.isArray(items) || items.length === 0) {
      return `<li><span class="file-list__name">${escapeHtml(fallbackText)}</span> <span class="status-tag status-tag--neutral">empty</span></li>`;
    }
    return items.map((item) => `
      <li>
        <span class="file-list__name">${escapeHtml(item.name || "unknown")}</span>
        <span class="status-tag ${statusTagClass(item.status)}">${escapeHtml(readableStatus(item.status || "loaded"))}</span>
      </li>
    `).join("");
  }

  function renderBudgetTable(budgets) {
    const tbody = document.querySelector("#app-budget-table-body");
    const thead = tbody ? tbody.closest("table").querySelector("thead") : null;
    if (!tbody) {
      return;
    }
    const entries = Object.keys(budgets);
    if (entries.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3">No budget data available.</td></tr>`;
      return;
    }

    const hasStructured = entries.some((key) => budgets[key] && typeof budgets[key] === "object" && ("limit" in budgets[key] || "used" in budgets[key]));

    if (hasStructured) {
      if (thead) {
        thead.innerHTML = `<tr><th>Action</th><th>Limit</th><th>Used</th><th>Status</th></tr>`;
      }
      tbody.innerHTML = entries.map((key) => {
        const entry = budgets[key];
        const limit = entry && typeof entry === "object" ? (entry.limit != null ? entry.limit : "n/a") : entry;
        const used = entry && typeof entry === "object" ? (entry.used != null ? entry.used : 0) : "n/a";
        const overBudget = typeof limit === "number" && typeof used === "number" && used > limit;
        const statusClass = overBudget ? "status-tag--warning" : "status-tag--success";
        const statusLabel = overBudget ? "over" : "ok";
        return `
          <tr>
            <td>${escapeHtml(readableBudgetKey(key))}</td>
            <td>${escapeHtml(String(limit))}</td>
            <td>${escapeHtml(String(used))}</td>
            <td><span class="status-tag ${statusClass}">${statusLabel}</span></td>
          </tr>
        `;
      }).join("");
    } else {
      if (thead) {
        thead.innerHTML = `<tr><th>Action</th><th>Value</th><th>Status</th></tr>`;
      }
      tbody.innerHTML = entries.map((key) => {
        const value = budgets[key];
        return `
          <tr>
            <td>${escapeHtml(readableBudgetKey(key))}</td>
            <td>${escapeHtml(String(value))}</td>
            <td><span class="status-tag status-tag--success">ok</span></td>
          </tr>
        `;
      }).join("");
    }
  }

  function renderScopes(scopes) {
    const list = document.querySelector("#app-scopes-list");
    if (!list) {
      return;
    }
    if (!Array.isArray(scopes) || scopes.length === 0) {
      list.innerHTML = `<li><span class="scope-tag">none</span> No scopes declared</li>`;
      return;
    }
    list.innerHTML = scopes.map((scope) => `<li><span class="scope-tag">${escapeHtml(scope)}</span> Live scope from manifest</li>`).join("");
  }

  function renderRuns(runs) {
    const tbody = document.querySelector("#app-runs-table-body");
    if (!tbody) {
      return;
    }
    if (!Array.isArray(runs) || runs.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5">No recent runs yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = runs.map((run) => `
      <tr>
        <td>${escapeHtml(formatDateTime(run.created_at || ""))}</td>
        <td>${escapeHtml(readableStatus(run.trigger || "manual"))}</td>
        <td>${escapeHtml(run.actions_summary || "")}</td>
        <td>$${escapeHtml(String(run.cost_usd || 0))}</td>
        <td><span class="status-tag ${statusTagClass(String(run.state || "").toLowerCase())}">${escapeHtml(String(run.state || "done").toLowerCase())}</span></td>
      </tr>
    `).join("");
  }

  async function initSettingsPage() {
    const settingsResult = await fetchJson("/api/settings", { headers: { Accept: "application/json" } });
    if (!settingsResult.ok) {
      showError("Failed to load settings: " + settingsResult.error);
      state.settings = {};
    } else {
      state.settings = settingsResult.data || {};
    }
    renderAllSettingsSections();
    bindSettingsSaveButtons();
    initYinyangChat();
    emitWarmToken({ mode: "warm_friendly", trigger: "settings_loaded" });
  }

  function initYinyangChat() {
    const input = document.querySelector("#yinyang-chat-input");
    const sendBtn = document.querySelector("#yinyang-chat-send");
    const history = document.querySelector("#yinyang-chat-history");
    if (!input || !sendBtn || !history) {
      return;
    }

    // Pre-fill buttons
    document.querySelectorAll("[data-yy-prefill]").forEach((btn) => {
      btn.addEventListener("click", () => {
        input.value = btn.getAttribute("data-yy-prefill");
        input.focus();
      });
    });

    // Send on button click
    sendBtn.addEventListener("click", sendYinyangMessage);

    // Send on Ctrl+Enter / Cmd+Enter
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        sendYinyangMessage();
      }
    });

    async function sendYinyangMessage() {
      const message = input.value.trim();
      if (!message) {
        return;
      }
      input.value = "";
      sendBtn.disabled = true;

      // Append user message
      const userItem = document.createElement("li");
      userItem.innerHTML = `<strong>You:</strong> ${escapeHtml(message)}`;
      history.appendChild(userItem);

      // Append thinking indicator
      const thinkItem = document.createElement("li");
      thinkItem.innerHTML = `<em>YinYang is thinking…</em>`;
      history.appendChild(thinkItem);
      history.scrollTop = history.scrollHeight;

      const result = await fetchJson("/api/yinyang/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ message }),
      });

      history.removeChild(thinkItem);
      const replyItem = document.createElement("li");

      if (!result.ok) {
        replyItem.innerHTML = `<strong>YinYang:</strong> <em>Could not reach the chat API — is the server running?</em>`;
      } else {
        const reply = (result.data && (result.data.reply || result.data.message)) || JSON.stringify(result.data);
        replyItem.innerHTML = `<strong>YinYang ☯:</strong> ${escapeHtml(String(reply))}`;
      }
      history.appendChild(replyItem);
      history.scrollTop = history.scrollHeight;
      sendBtn.disabled = false;
    }
  }

  function renderAllSettingsSections() {
    const sections = ["account", "history", "llm", "tunnel", "part11", "privacy", "yinyang", "about"];
    sections.forEach((section) => renderSettingsSection(section, state.settings[section] || {}));
  }

  function renderSettingsSection(sectionName, payload) {
    const mount = document.querySelector(`[data-settings-section="${sectionName}"]`);
    if (!mount) {
      return;
    }
    const fields = flattenSettingsSection(sectionName, payload);
    mount.innerHTML = `
      <div class="data-grid">
        ${fields.map((field) => `
          <label>
            <strong>${escapeHtml(field.label)}</strong><br>
            ${renderSettingsInput(field)}
          </label>
        `).join("")}
      </div>
    `;
  }

  function flattenSettingsSection(sectionName, payload) {
    const fields = [];

    function walk(prefix, value) {
      Object.keys(value).forEach((key) => {
        const nextPath = prefix ? `${prefix}.${key}` : key;
        const current = value[key];
        if (Array.isArray(current)) {
          fields.push({ name: nextPath, label: key, type: "array", value: current.join(", ") });
        } else if (typeof current === "boolean") {
          fields.push({ name: nextPath, label: key, type: "boolean", value: current });
        } else if (typeof current === "number") {
          fields.push({ name: nextPath, label: key, type: "number", value: current });
        } else if (current && typeof current === "object") {
          walk(nextPath, current);
        } else {
          fields.push({ name: nextPath, label: key, type: "string", value: current == null ? "" : current });
        }
      });
    }

    walk(sectionName, payload);
    return fields;
  }

  function renderSettingsInput(field) {
    if (field.type === "boolean") {
      return `<input type="checkbox" name="${escapeHtml(field.name)}" data-type="boolean" ${field.value ? "checked" : ""}>`;
    }
    return `<input class="search-input" type="${field.type === "number" ? "number" : "text"}" name="${escapeHtml(field.name)}" data-type="${escapeHtml(field.type)}" value="${escapeHtml(field.value)}">`;
  }

  function bindSettingsSaveButtons() {
    document.querySelectorAll("[data-settings-save]").forEach((button) => {
      button.addEventListener("click", async () => {
        const sectionName = button.getAttribute("data-settings-save");
        if (!sectionName) {
          return;
        }
        const sectionValue = readSettingsSection(sectionName);
        state.settings[sectionName] = sectionValue;
        const saveResult = await fetchJson("/api/settings", {
          method: "PUT",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify(state.settings),
        });
        if (!saveResult.ok) {
          showError("Failed to save settings: " + saveResult.error);
        } else {
          state.settings = saveResult.data;
          renderAllSettingsSections();
          emitCelebration("budget_saved");
        }
      });
    });
  }

  function readSettingsSection(sectionName) {
    const mount = document.querySelector(`[data-settings-section="${sectionName}"]`);
    const result = {};
    if (!mount) {
      return result;
    }
    mount.querySelectorAll("input[name]").forEach((input) => {
      const path = input.getAttribute("name");
      const type = input.getAttribute("data-type");
      if (!path) {
        return;
      }
      let value;
      if (type === "boolean") {
        value = input.checked;
      } else if (type === "number") {
        value = Number(input.value);
      } else if (type === "array") {
        value = input.value.split(",").map((item) => item.trim()).filter(Boolean);
      } else {
        value = input.value;
      }
      setNestedValue(result, path.split(".").slice(1), value);
    });
    return result;
  }

  function setNestedValue(target, path, value) {
    let cursor = target;
    path.forEach((segment, index) => {
      if (index === path.length - 1) {
        cursor[segment] = value;
        return;
      }
      if (!cursor[segment] || typeof cursor[segment] !== "object") {
        cursor[segment] = {};
      }
      cursor = cursor[segment];
    });
  }

  function detectPlatform() {
    const agent = navigator.userAgent.toLowerCase();
    if (agent.includes("mac")) {
      return {
        label: "macOS detected",
        button: "Download for macOS",
        href: "https://storage.googleapis.com/solace-downloads/v1.0.0/SolaceBrowser-1.0.0-mac-arm64.dmg",
        command: "curl -fsSL https://downloads.solaceagi.com/install.sh | bash -s -- --channel stable",
      };
    }
    if (agent.includes("win")) {
      return {
        label: "Windows detected",
        button: "Download MSI",
        href: "https://storage.googleapis.com/solace-downloads/v1.0.0/SolaceBrowser-1.0.0-windows-x64.msi",
        command: "powershell -ExecutionPolicy Bypass -File .\\install-solace-browser.ps1",
      };
    }
    return {
      label: "Linux detected",
      button: "Download AppImage",
      href: "https://storage.googleapis.com/solace-downloads/v1.0.0/SolaceBrowser-1.0.0-linux-amd64.AppImage",
      command: "curl -fsSL https://downloads.solaceagi.com/install.sh | bash",
    };
  }

  function initMachineDashboard() {
    bindFileSearch();
    bindTerminal();
    loadMachineFiles();
    loadSystemSnapshot();
  }

  function bindFileSearch() {
    const input = document.querySelector("#file-search");
    if (!input) {
      return;
    }
    input.addEventListener("input", () => {
      const query = input.value.trim().toLowerCase();
      document.querySelectorAll("[data-file-name]").forEach((item) => {
        item.hidden = !item.getAttribute("data-file-name").toLowerCase().includes(query);
      });
    });
  }

  function bindTerminal() {
    const form = document.querySelector("#terminal-form");
    const input = document.querySelector("#terminal-command");
    const output = document.querySelector("#terminal-output");
    if (!form || !input || !output) {
      return;
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const command = input.value.trim();
      if (!command) {
        return;
      }
      const termResult = await fetchJson("/machine/terminal/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ command }),
      });
      if (!termResult.ok) {
        showError("Terminal command failed: " + termResult.error);
      }
      const response = termResult.ok && termResult.data && termResult.data.output ? termResult.data.output : `preview only > ${command}\ncommand blocked until machine scope is approved`;
      output.textContent = `$ ${command}\n${response}`;
      input.value = "";
    });
  }

  async function loadMachineFiles() {
    const list = document.querySelector("#file-list");
    if (!list) {
      return;
    }
    const filesResult = await fetchJson("/machine/files?path=/", { headers: { Accept: "application/json" } });
    if (!filesResult.ok) {
      showError("Failed to load machine files: " + filesResult.error);
    }
    const items = Array.isArray(filesResult.ok && filesResult.data && filesResult.data.items) ? filesResult.data.items : [
      { name: "Downloads", type: "folder", detail: "scoped" },
      { name: "Recipes", type: "folder", detail: "editable" },
      { name: "session.log", type: "file", detail: "audit only" },
      { name: "Desktop", type: "folder", detail: "blocked" },
    ];
    list.innerHTML = items.map((item) => `
      <li data-file-name="${escapeHtml(item.name)}">
        <span>${escapeHtml(item.name)}</span>
        <span class="machine-tag">${escapeHtml(item.type)} · ${escapeHtml(item.detail || "")}</span>
      </li>
    `).join("");
  }

  async function loadSystemSnapshot() {
    const table = document.querySelector("#system-table-body");
    if (!table) {
      return;
    }
    const sysResult = await fetchJson("/machine/system", { headers: { Accept: "application/json" } });
    if (!sysResult.ok) {
      showError("Failed to load system snapshot: " + sysResult.error);
    }
    const metrics = sysResult.ok && sysResult.data && sysResult.data.metrics ? sysResult.data.metrics : [
      { label: "OS", value: navigator.platform || "Unknown" },
      { label: "Tunnel", value: "Disconnected" },
      { label: "Shell", value: "Preview-only until approval" },
      { label: "Vault", value: "OAuth3 sealed" },
    ];
    table.innerHTML = metrics.map((row) => `<tr><td>${escapeHtml(row.label)}</td><td>${escapeHtml(row.value)}</td></tr>`).join("");
  }

  function initTunnelPage() {
    const connectButton = document.querySelector("#connect-button");
    const disconnectButton = document.querySelector("#disconnect-button");
    const copyButton = document.querySelector("#copy-endpoint");
    const openButton = document.querySelector("#open-endpoint");

    if (connectButton) {
      connectButton.addEventListener("click", handleConnect);
    }
    if (disconnectButton) {
      disconnectButton.addEventListener("click", handleDisconnect);
    }
    if (copyButton) {
      copyButton.addEventListener("click", copyEndpoint);
    }
    if (openButton) {
      openButton.addEventListener("click", openEndpoint);
    }
    refreshTunnelStatus();
  }

  async function handleConnect() {
    const connectResult = await fetchJson("/tunnel/start", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ requested_scope: "tunnel.connect" }),
    });
    if (!connectResult.ok) {
      showError("Tunnel connect failed: " + connectResult.error);
    }
    const connectData = connectResult.ok ? connectResult.data : null;
    state.tunnel.status = connectData && connectData.status ? connectData.status : "approval-required";
    state.tunnel.publicUrl = connectData && connectData.public_url ? connectData.public_url : "Waiting for approval";
    state.tunnel.approval = connectData && connectData.message ? connectData.message : "Grant tunnel.connect before the browser exposes a public URL.";
    applyTunnelState();
  }

  async function handleDisconnect() {
    const disconnectResult = await fetchJson("/tunnel/stop", { method: "POST", headers: { Accept: "application/json" } });
    if (!disconnectResult.ok) {
      showError("Tunnel disconnect failed: " + disconnectResult.error);
    }
    state.tunnel.status = "disconnected";
    state.tunnel.publicUrl = "Not connected";
    state.tunnel.approval = "Tunnel has been closed. Nothing is exposed.";
    applyTunnelState();
  }

  async function refreshTunnelStatus() {
    const statusResult = await fetchJson("/tunnel/status", { headers: { Accept: "application/json" } });
    if (!statusResult.ok) {
      showError("Failed to refresh tunnel status: " + statusResult.error);
    } else {
      state.tunnel.status = statusResult.data.status || state.tunnel.status;
      state.tunnel.publicUrl = statusResult.data.public_url || state.tunnel.publicUrl;
      state.tunnel.approval = statusResult.data.message || state.tunnel.approval;
    }
    applyTunnelState();
  }

  function applyTunnelState() {
    const ring = document.querySelector("#status-ring");
    const label = document.querySelector("#status-label");
    const description = document.querySelector("#status-description");
    const endpoint = document.querySelector("#endpoint-value");
    const badge = document.querySelector("#approval-badge");
    const isConnected = state.tunnel.status === "connected";
    const isBlocked = state.tunnel.status === "blocked" || state.tunnel.status === "approval-required";

    if (ring) {
      ring.dataset.state = isConnected ? "connected" : isBlocked ? "blocked" : "connecting";
    }
    if (label) {
      label.textContent = isConnected ? "Connected" : isBlocked ? "Approval required" : "Disconnected";
    }
    if (description) {
      description.textContent = state.tunnel.approval;
    }
    if (endpoint) {
      endpoint.textContent = state.tunnel.publicUrl;
    }
    if (badge) {
      badge.textContent = isConnected ? "Live endpoint" : "Fail-closed";
      badge.className = `status-tag ${isConnected ? "status-tag--success" : "status-tag--warning"}`;
    }
  }

  async function copyEndpoint() {
    const value = document.querySelector("#endpoint-value");
    if (!value) {
      return;
    }
    await navigator.clipboard.writeText(value.textContent || "");
  }

  function openEndpoint() {
    const value = document.querySelector("#endpoint-value");
    if (!value || !value.textContent.startsWith("http")) {
      return;
    }
    window.open(value.textContent, "_blank", "noopener");
  }

  function emitWarmToken(warmToken) {
    document.dispatchEvent(new CustomEvent("solace:warm-token", { detail: warmToken }));
  }

  function emitCelebration(trigger, data) {
    document.dispatchEvent(new CustomEvent("solace:celebrate", { detail: { trigger, data } }));
  }

  function titleCase(value) {
    return String(value || "").split("-").map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(" ");
  }

  function categoryCopy(category) {
    const copy = {
      communications: "Email, messaging, and networking automation loaded from local manifests.",
      productivity: "Read-only briefs, scheduling, and orchestration across installed apps.",
      sales: "Lead and outreach flows that stay inside the browser.",
      engineering: "GitHub and community workflows with evidence-first replay.",
      social: "No-API social workflows through the native web UI.",
      shopping: "Consumer web automation without vendor APIs.",
    };
    return copy[category] || "Live apps discovered from the local app registry.";
  }

  function statusPillClass(status) {
    if (status === "installed" || status === "available") {
      return "status-pill--success";
    }
    if (status === "beta" || status === "approval-required") {
      return "status-pill--warning";
    }
    return "status-pill--warning";
  }

  function statusTagClass(status) {
    if (status === "loaded" || status === "delivered" || status === "sealed" || status === "done") {
      return "status-tag--success";
    }
    if (status === "pending_approval" || status === "suggested" || status === "blocked") {
      return "status-tag--warning";
    }
    return "status-tag--neutral";
  }

  function readableStatus(status) {
    return String(status || "").replaceAll("_", " ");
  }

  function readableBudgetKey(key) {
    return titleCase(String(key || "").replaceAll("_", "-"));
  }

  function fileFallbackLabel(sectionName) {
    return `No ${sectionName} files`;
  }

  function formatDateTime(value) {
    if (!value) {
      return "n/a";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value);
    }
    return date.toISOString().replace("T", " ").slice(0, 16);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
})();
