(function () {
  const state = {
    tunnel: {
      status: "disconnected",
      publicUrl: "Not connected",
      approval: "OAuth3 scope required before opening the tunnel.",
    },
  };

  document.addEventListener("DOMContentLoaded", init);

  function init() {
    markActiveNav();
    initFooterYear();
    initRevealObserver();
    initParticles();

    const page = document.body.dataset.page || "";
    if (page === "home") {
      initHomePage();
    } else if (page === "download") {
      initDownloadPage();
    } else if (page === "machine-dashboard") {
      initMachineDashboard();
    } else if (page === "tunnel-connect") {
      initTunnelPage();
    }
  }

  function markActiveNav() {
    const current = window.location.pathname === "/" ? "/" : window.location.pathname.replace(/\.html$/, "");
    document.querySelectorAll("[data-nav-path]").forEach((link) => {
      if (link.getAttribute("data-nav-path") === current) {
        link.classList.add("is-active");
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
    try {
      const response = await fetch(url, options);
      if (!response.ok) {
        return null;
      }
      return await response.json();
    } catch (_error) {
      return null;
    }
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
    const payload = await fetchJson("/api/tokens/active", { headers: { Accept: "application/json" } });
    const tokens = Array.isArray(payload && payload.tokens) ? payload.tokens : [
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
    const payload = await fetchJson("/api/activity/recent", { headers: { Accept: "application/json" } });
    const items = Array.isArray(payload && payload.items) ? payload.items : [
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
    const payload = await fetchJson("/api/tokens/scopes", { headers: { Accept: "application/json" } });
    const scopes = Array.isArray(payload && payload.scopes) ? payload.scopes : [
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
      const payload = await fetchJson("/machine/terminal/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ command }),
      });
      const response = payload && payload.output ? payload.output : `preview only > ${command}\ncommand blocked until machine scope is approved`;
      output.textContent = `$ ${command}\n${response}`;
      input.value = "";
    });
  }

  async function loadMachineFiles() {
    const list = document.querySelector("#file-list");
    if (!list) {
      return;
    }
    const payload = await fetchJson("/machine/files?path=/", { headers: { Accept: "application/json" } });
    const items = Array.isArray(payload && payload.items) ? payload.items : [
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
    const payload = await fetchJson("/machine/system", { headers: { Accept: "application/json" } });
    const metrics = payload && payload.metrics ? payload.metrics : [
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
    const payload = await fetchJson("/tunnel/start", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ requested_scope: "tunnel.connect" }),
    });
    state.tunnel.status = payload && payload.status ? payload.status : "approval-required";
    state.tunnel.publicUrl = payload && payload.public_url ? payload.public_url : "Waiting for approval";
    state.tunnel.approval = payload && payload.message ? payload.message : "Grant tunnel.connect before the browser exposes a public URL.";
    applyTunnelState();
  }

  async function handleDisconnect() {
    await fetchJson("/tunnel/stop", { method: "POST", headers: { Accept: "application/json" } });
    state.tunnel.status = "disconnected";
    state.tunnel.publicUrl = "Not connected";
    state.tunnel.approval = "Tunnel has been closed. Nothing is exposed.";
    applyTunnelState();
  }

  async function refreshTunnelStatus() {
    const payload = await fetchJson("/tunnel/status", { headers: { Accept: "application/json" } });
    if (payload) {
      state.tunnel.status = payload.status || state.tunnel.status;
      state.tunnel.publicUrl = payload.public_url || state.tunnel.publicUrl;
      state.tunnel.approval = payload.message || state.tunnel.approval;
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

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
})();
