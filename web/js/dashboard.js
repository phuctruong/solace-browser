'use strict';

const TOKEN = localStorage.getItem('solace_token') || '';
const FACTS = [
  "Recipe replay costs $0.001 — 10x cheaper than LLM",
  "PZip compresses 66:1 — your evidence fits in 2% of the space",
  "Sealed store: 0% of apps are plugins (auditable by design)",
  "Evidence chain: tamper-evident, hash-chained, Part 11 ready",
  "Local-first: your data never leaves your machine without consent",
  "Recipe flywheel: cost \u2192 $0 as replay_count \u2192 \u221e",
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
  constructor() {
    this._rotateInterval = null;
    this._statsInterval = null;
    this._centerModes = ['stats', 'delight'];
    this._modeIndex = 0;
    this._lastStats = null;
    this._delightItems = [...FACTS, ...TIPS, ...QUOTES.map(q => `"${q.q}" \u2014 ${q.by}`)];
    this._delightIdx = 0;
  }

  start() {
    this._fetchStats();
    this._statsInterval = setInterval(() => this._fetchStats(), 5000);
    this._rotateInterval = setInterval(() => this._rotateCenterZone(), 8000);
    document.getElementById('reset-btn').addEventListener('click', () => this._resetStats());
  }

  stop() {
    clearInterval(this._statsInterval);
    clearInterval(this._rotateInterval);
  }

  async _fetchStats() {
    try {
      const r = await fetch('/api/v1/session/stats', { headers: { Authorization: 'Bearer ' + TOKEN } });
      if (!r.ok) return;
      const data = await r.json();
      this._lastStats = data;
      this._updateLeftZone(data);
      this._updateStatCards(data);
      if (this._centerModes[this._modeIndex] === 'stats') {
        this._showStatsMode(data);
      }
      // Update right zone
      const state = data.state || 'IDLE';
      document.getElementById('rail-right').textContent = state === 'FAILED' ? 'ERR' : 'OK';
    } catch (_) {
      // fail silently — dashboard is decorative when API unavailable
    }
  }

  _updateLeftZone(data) {
    const dot = document.getElementById('state-dot');
    const stateText = document.getElementById('state-text');
    const appLabel = document.getElementById('app-label');
    const state = data.state || 'IDLE';
    dot.dataset.state = state;
    stateText.textContent = state;
    appLabel.textContent = data.app_name || '';
  }

  _updateStatCards(data) {
    document.getElementById('pages-count').textContent = data.pages_visited || 0;
    document.getElementById('llm-count').textContent = data.llm_calls || 0;
    document.getElementById('cost-display').textContent = '$' + (data.cost_usd || '0.00');
    document.getElementById('saved-pct').textContent = (data.cost_saved_pct || 0) + '%';
    document.getElementById('replays-count').textContent = data.recipes_replayed || 0;
    document.getElementById('evidence-count').textContent = data.evidence_captured || 0;
  }

  _rotateCenterZone() {
    this._modeIndex = (this._modeIndex + 1) % this._centerModes.length;
    const mode = this._centerModes[this._modeIndex];
    if (mode === 'stats' && this._lastStats) {
      this._showStatsMode(this._lastStats);
    } else {
      this._showDelightMode();
    }
  }

  _showStatsMode(data) {
    const center = document.getElementById('rail-center');
    const duration = data.duration_seconds || 0;
    const mins = Math.floor(duration / 60), secs = duration % 60;
    const dStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
    center.textContent = `\uD83D\uDCC4 ${data.pages_visited||0} pages  \uD83E\uDDE0 ${data.llm_calls||0} LLM  \uD83D\uDCB0 $${data.cost_usd||'0.00'}  \uD83D\uDCB5 ${data.cost_saved_pct||0}% saved  \u23F1\uFE0F ${dStr}  \uD83D\uDD01 ${data.recipes_replayed||0} replays`;
  }

  _showDelightMode() {
    const center = document.getElementById('rail-center');
    const item = this._delightItems[this._delightIdx % this._delightItems.length];
    this._delightIdx++;
    center.textContent = item;
  }

  async _resetStats() {
    try {
      await fetch('/api/v1/session/stats/reset', { method: 'POST', headers: { Authorization: 'Bearer ' + TOKEN } });
      this._fetchStats();
    } catch (_) {}
  }
}

const dashboard = new ValueDashboard();
dashboard.start();
