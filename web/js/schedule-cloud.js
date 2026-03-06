/**
 * schedule-cloud.js — Cloud Twin API bridge for solaceagi.com
 * Merges cloud schedules/history into local state without breaking local functionality.
 *
 * Cloud API (solaceagi.com):
 *   GET    /api/v1/browser/schedules       — list cloud schedules
 *   POST   /api/v1/browser/schedules       — create schedule
 *   PATCH  /api/v1/browser/schedules/{id}  — update schedule
 *   DELETE /api/v1/browser/schedules/{id}  — delete schedule
 *   GET    /api/v1/browser/sessions        — list cloud runs (history)
 *   GET    /api/v1/browser/runs/{id}/evidence — get evidence chain
 *
 * Depends on: schedule-core.js (window.SolaceSchedule)
 */

(function () {
  'use strict';

  const S = window.SolaceSchedule;
  const state     = S.state;
  const utils     = S.utils;
  const constants = S.constants;
  const fn        = S.fn;

  // ── Cloud State ─────────────────────────────────────────────────────────────
  state.cloudConnected    = false;
  state.cloudSchedules    = [];
  state.cloudHistory      = [];
  state.cloudError        = null;
  state.cloudLastSync     = null;

  // ── Cloud Config ────────────────────────────────────────────────────────────
  function getCloudApiUrl() {
    return state.cloudApiUrl
      || localStorage.getItem('sb_cloud_api_url')
      || 'https://www.solaceagi.com';
  }

  function getAuthToken() {
    return localStorage.getItem('solace_token') || '';
  }

  function isCloudEnabled() {
    const token = getAuthToken();
    return token.length > 0;
  }

  // ── Cloud Fetch Wrapper ─────────────────────────────────────────────────────
  function cloudFetch(path, options) {
    const baseUrl = getCloudApiUrl();
    const url = baseUrl.replace(/\/+$/, '') + path;
    const token = getAuthToken();

    const headers = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }

    const fetchOptions = Object.assign({}, options || {}, {
      headers: Object.assign(headers, (options && options.headers) || {}),
    });

    return fetch(url, fetchOptions).then(function (res) {
      if (!res.ok) {
        const err = new Error('Cloud API error: HTTP ' + res.status);
        err.status = res.status;
        throw err;
      }
      return res.json();
    });
  }

  // ── Cloud Schedule Operations ───────────────────────────────────────────────

  function loadCloudSchedules() {
    if (!isCloudEnabled()) {
      state.cloudSchedules = [];
      return Promise.resolve([]);
    }

    return cloudFetch('/api/v1/browser/schedules').then(function (data) {
      const schedules = data.schedules || data || [];
      state.cloudSchedules = schedules;
      state.cloudConnected = true;
      state.cloudError = null;
      state.cloudLastSync = new Date().toISOString();
      mergeCloudData();
      renderCloudIndicator();
      return schedules;
    }).catch(function (e) {
      state.cloudConnected = false;
      state.cloudError = e.message || 'Cloud unreachable';
      state.cloudSchedules = [];
      console.debug('loadCloudSchedules failed:', e.message || e);
      renderCloudIndicator();
      return [];
    });
  }

  function createCloudSchedule(data) {
    if (!isCloudEnabled()) {
      return Promise.reject(new Error('Cloud not configured — set auth token'));
    }

    return cloudFetch('/api/v1/browser/schedules', {
      method: 'POST',
      body: JSON.stringify(data),
    }).then(function (result) {
      return loadCloudSchedules().then(function () {
        return result;
      });
    });
  }

  function updateCloudSchedule(id, data) {
    if (!isCloudEnabled()) {
      return Promise.reject(new Error('Cloud not configured — set auth token'));
    }

    return cloudFetch('/api/v1/browser/schedules/' + encodeURIComponent(id), {
      method: 'PATCH',
      body: JSON.stringify(data),
    }).then(function (result) {
      return loadCloudSchedules().then(function () {
        return result;
      });
    });
  }

  function deleteCloudSchedule(id) {
    if (!isCloudEnabled()) {
      return Promise.reject(new Error('Cloud not configured — set auth token'));
    }

    return cloudFetch('/api/v1/browser/schedules/' + encodeURIComponent(id), {
      method: 'DELETE',
    }).then(function (result) {
      return loadCloudSchedules().then(function () {
        return result;
      });
    });
  }

  // ── Cloud History & Evidence ────────────────────────────────────────────────

  function loadCloudHistory() {
    if (!isCloudEnabled()) {
      state.cloudHistory = [];
      return Promise.resolve([]);
    }

    return cloudFetch('/api/v1/browser/sessions').then(function (data) {
      const sessions = data.sessions || data || [];
      state.cloudHistory = sessions;
      state.cloudConnected = true;
      state.cloudError = null;
      mergeCloudData();
      renderCloudIndicator();
      return sessions;
    }).catch(function (e) {
      state.cloudConnected = false;
      state.cloudError = e.message || 'Cloud unreachable';
      state.cloudHistory = [];
      console.debug('loadCloudHistory failed:', e.message || e);
      renderCloudIndicator();
      return [];
    });
  }

  function loadCloudEvidence(runId) {
    if (!isCloudEnabled()) {
      return Promise.reject(new Error('Cloud not configured — set auth token'));
    }

    return cloudFetch('/api/v1/browser/runs/' + encodeURIComponent(runId) + '/evidence');
  }

  // ── Data Merging ────────────────────────────────────────────────────────────
  // Merge cloud schedules into state.upcoming and cloud history into
  // state.activities without duplicating local entries.

  function mergeCloudData() {
    // Merge cloud schedules into state.upcoming
    const localUpcomingIds = new Set(state.upcoming.map(function (u) { return u.id || u.app_id; }));
    state.cloudSchedules.forEach(function (cs) {
      const key = cs.id || cs.app_id;
      if (!localUpcomingIds.has(key)) {
        state.upcoming.push({
          id:            cs.id,
          app_id:        cs.app_id || cs.id,
          app_name:      cs.app_name || cs.name || cs.app_id,
          type:          cs.type || 'app_schedule',
          pattern:       cs.schedule_pattern || cs.pattern || 'manual',
          pattern_label: cs.pattern_label || cs.schedule_pattern || '',
          _cloud:        true,
        });
      }
    });

    // Merge cloud history into state.activities
    const localActivityIds = new Set(state.activities.map(function (a) { return a.id; }));
    state.cloudHistory.forEach(function (ch) {
      if (ch.id && !localActivityIds.has(ch.id)) {
        state.activities.push({
          id:              ch.id,
          app_id:          ch.app_id || ch.name || '',
          app_name:        ch.app_name || ch.name || '',
          status:          ch.status || 'success',
          started_at:      ch.started_at || ch.created_at || '',
          duration_ms:     ch.duration_ms || 0,
          cost_usd:        ch.cost_usd || 0,
          tokens_used:     ch.tokens_used || 0,
          evidence_hash:   ch.evidence_hash || '',
          output_summary:  ch.output_summary || '',
          safety_tier:     ch.safety_tier || '',
          recipe_hit:      ch.recipe_hit || false,
          _cloud:          true,
        });
      }
    });
  }

  // ── Cloud Twin Indicator ────────────────────────────────────────────────────

  function renderCloudIndicator() {
    let indicator = document.getElementById('cloudTwinIndicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'cloudTwinIndicator';
      indicator.className = 'cloud-twin-indicator';
      const toolbar = document.querySelector('.schedule-toolbar');
      if (toolbar) {
        toolbar.insertBefore(indicator, toolbar.firstChild);
      }
    }

    // Clear and rebuild (no innerHTML with untrusted data)
    indicator.textContent = '';

    const dot = document.createElement('span');
    dot.className = 'cloud-twin-indicator__dot';

    const label = document.createElement('span');
    label.className = 'cloud-twin-indicator__label';

    if (!isCloudEnabled()) {
      indicator.className = 'cloud-twin-indicator cloud-twin-indicator--disabled';
      dot.className += ' cloud-twin-indicator__dot--disabled';
      label.textContent = 'Cloud Twin: Not configured';
    } else if (state.cloudConnected) {
      indicator.className = 'cloud-twin-indicator cloud-twin-indicator--connected';
      dot.className += ' cloud-twin-indicator__dot--connected';
      label.textContent = 'Cloud Twin: Connected';
      if (state.cloudLastSync) {
        const syncTime = document.createElement('span');
        syncTime.className = 'cloud-twin-indicator__sync';
        syncTime.textContent = 'Synced ' + utils.formatTime(state.cloudLastSync);
        indicator.appendChild(dot);
        indicator.appendChild(label);
        indicator.appendChild(syncTime);
        return;
      }
    } else {
      indicator.className = 'cloud-twin-indicator cloud-twin-indicator--error';
      dot.className += ' cloud-twin-indicator__dot--error';
      label.textContent = 'Cloud Twin: Disconnected';
    }

    indicator.appendChild(dot);
    indicator.appendChild(label);
  }

  // ── Boot Integration ────────────────────────────────────────────────────────
  // Hook into the existing loadActivities cycle: after local data loads,
  // also pull cloud data if a token is present.

  const originalLoadActivities = fn.loadActivities;

  fn.loadActivities = function () {
    return originalLoadActivities().then(function () {
      if (isCloudEnabled()) {
        return Promise.all([
          loadCloudSchedules(),
          loadCloudHistory(),
        ]).then(function () {
          // Re-render after cloud data merges
          if (fn.renderCurrentView) fn.renderCurrentView();
          if (fn.updateROIPanel) fn.updateROIPanel();
        }).catch(function (e) {
          // Cloud failure must not break local UI
          console.debug('Cloud sync failed (non-blocking):', e.message || e);
        });
      }
      renderCloudIndicator();
      return Promise.resolve();
    });
  };

  // ── Export to namespace ──────────────────────────────────────────────────────
  fn.loadCloudSchedules  = loadCloudSchedules;
  fn.createCloudSchedule = createCloudSchedule;
  fn.updateCloudSchedule = updateCloudSchedule;
  fn.deleteCloudSchedule = deleteCloudSchedule;
  fn.loadCloudHistory    = loadCloudHistory;
  fn.loadCloudEvidence   = loadCloudEvidence;
  fn.renderCloudIndicator = renderCloudIndicator;

})();
