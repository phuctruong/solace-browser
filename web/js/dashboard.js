// Diagram: 02-dashboard-login
'use strict';

const DEFAULT_TOKEN = localStorage.getItem('solace_token') || '';
const DEFAULT_METRICS_URL = '/api/v1/session/stats';
const DEFAULT_RESET_URL = '/api/v1/session/stats/reset';
const ACTIVE_STATES = ['EXECUTING', 'PREVIEW_READY', 'BUDGET_CHECK'];

const FACTS = [
  "Recipe replay costs $0.001 — 10x cheaper than LLM",
  "PZip compresses 66:1 — your evidence fits in 2% of the space",
  "Sealed store: 0% of apps are plugins (auditable by design)",
  "Evidence chain: tamper-evident, hash-chained, Part 11 ready",
  "Local-first: your data never leaves your machine without consent",
  "Recipe flywheel: cost → $0 as replay_count → ∞",
  "65537 is a Fermat prime and our verification ceiling"
];

const TIPS = [
  "Press Ctrl+K to search across all your apps",
  "Recipes get cheaper every time you replay them",
  "E-sign your approvals for FDA Part 11 compliance",
  "Enable cloud twin for 24/7 background automation"
];

const QUOTES = [
  { q: "Absorb what is useful, discard what is useless.", by: "Bruce Lee" },
  { q: "Simplicity is the key to brilliance.", by: "Bruce Lee" },
  { q: "It's not the daily increase but daily decrease.", by: "Bruce Lee" }
];

class ValueDashboard {
  constructor(apiToken, metricsUrl, resetUrl = DEFAULT_RESET_URL) {
    this.token = apiToken || DEFAULT_TOKEN;
    this.metricsUrl = metricsUrl || DEFAULT_METRICS_URL;
    this.resetUrl = resetUrl;
    this.rotateInterval = null;
    this.statsInterval = null;
    this.centerModes = ['stats', 'delight'];
    this.modeIndex = 0;
    this.lastStats = null;
    this.delightItems = [...FACTS, ...TIPS, ...QUOTES.map((quote) => `"${quote.q}" — ${quote.by}`)];
    this.delightIndex = 0;
  }

  start() {
    this._fetchStats();
    this.statsInterval = setInterval(() => this._fetchStats(), 5000);
    this.rotateInterval = setInterval(() => this._rotateCenterZone(), 8000);

    const resetButton = document.getElementById('reset-btn');
    if (resetButton) {
      resetButton.addEventListener('click', () => this._resetStats());
    }
  }

  stop() {
    clearInterval(this.statsInterval);
    clearInterval(this.rotateInterval);
    this.statsInterval = null;
    this.rotateInterval = null;
  }

  _authHeaders() {
    if (!this.token) {
      return {};
    }
    return { Authorization: `Bearer ${this.token}` };
  }

  async _fetchStats() {
    try {
      const response = await fetch(this.metricsUrl, {
        headers: this._authHeaders()
      });
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      this.lastStats = data;
      this._updateLeftZone(data);
      this._updateStatCards(data);
      this._renderCenterZone(data);
      this._updateRightZone(data);
    } catch (error) {
      // fail silently — dashboard is decorative when API unavailable
    }
  }

  _updateLeftZone(data) {
    const state = data.state || 'IDLE';
    const dot = document.getElementById('state-dot');
    const stateText = document.getElementById('state-text');
    const appLabel = document.getElementById('app-label');

    dot.dataset.state = state;
    stateText.textContent = state;
    appLabel.textContent = data.app_name || '';
  }

  _updateStatCards(data) {
    document.getElementById('pages-count').textContent = data.pages_visited || 0;
    document.getElementById('llm-count').textContent = data.llm_calls || 0;
    document.getElementById('cost-display').textContent = `$${data.cost_usd || '0.00'}`;
    document.getElementById('saved-pct').textContent = `${data.cost_saved_pct || 0}%`;
  }

  _updateRightZone(data) {
    const state = data.state || 'IDLE';
    const rightZone = document.getElementById('rail-right');
    if (state === 'FAILED') {
      rightZone.textContent = 'ERR';
      return;
    }
    const hostname = window.location.hostname;
    rightZone.textContent = hostname || 'OK';
  }

  _rotateCenterZone() {
    this.modeIndex = (this.modeIndex + 1) % this.centerModes.length;
    if (!this.lastStats) {
      this._showDelightMode();
      return;
    }
    this._renderCenterZone(this.lastStats);
  }

  _shouldShowStats(data) {
    return ACTIVE_STATES.includes(data.state || 'IDLE');
  }

  _renderCenterZone(data) {
    if (this._shouldShowStats(data)) {
      this._showStatsMode(data);
      return;
    }
    const mode = this.centerModes[this.modeIndex];
    if (mode === 'stats') {
      this._showStatsMode(data);
      return;
    }
    this._showDelightMode();
  }

  _formatDuration(durationSeconds) {
    const totalSeconds = durationSeconds || 0;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    if (minutes > 0) {
      return `${minutes}m ${seconds}s`;
    }
    return `${seconds}s`;
  }

  _showStatsMode(data) {
    const center = document.getElementById('rail-center');
    center.textContent = `📄 ${data.pages_visited || 0} pages  🧠 ${data.llm_calls || 0} LLM calls  💰 $${data.cost_usd || '0.00'}  💵 ${data.cost_saved_pct || 0}% saved  ⏱️ ${this._formatDuration(data.duration_seconds || 0)} elapsed  🔁 ${data.recipes_replayed || 0} replays  📝 ${data.evidence_captured || 0} evidence`;
  }

  _showDelightMode() {
    const center = document.getElementById('rail-center');
    const item = this.delightItems[this.delightIndex % this.delightItems.length];
    this.delightIndex += 1;
    center.textContent = item;
  }

  async _resetStats() {
    try {
      const response = await fetch(this.resetUrl, {
        method: 'POST',
        headers: this._authHeaders()
      });
      if (!response.ok) {
        return;
      }
      await this._fetchStats();
    } catch (error) {
      // fail silently — dashboard is decorative when API unavailable
    }
  }
}

const dashboard = new ValueDashboard(DEFAULT_TOKEN, DEFAULT_METRICS_URL);
dashboard.start();
