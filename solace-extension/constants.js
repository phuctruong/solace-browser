/**
 * Solace Browser Extension -- Canonical Constants
 *
 * Single source of truth for ports, URLs, and configuration.
 * All extension code MUST import from here instead of hardcoding values.
 *
 * Paper: 47 Section 9 (Port Consolidation) | Auth: 65537
 */

// --- Ports ---
// Port 8888: Default API + WebSocket + Web UI (the "prosperity port")
// Dynamic discovery tries 8888-8899 and caches the active port.
const SOLACE_PORT_RANGE_START = 8888;
const SOLACE_PORT_RANGE_END = 8899;
let SOLACE_API_PORT = 8888;

// --- URLs (updated by discoverPort) ---
let SOLACE_API = `http://localhost:${SOLACE_API_PORT}`;
let SOLACE_WS = `ws://localhost:${SOLACE_API_PORT}`;

// --- API Endpoints ---
const ENDPOINTS = {
  health: '/api/health',
  apps: '/api/apps',
  models: '/api/models',
  wsYinyang: '/ws/yinyang',
};

/**
 * Discover the active Solace server port by probing 8888-8899.
 * Caches the resolved port in chrome.storage.local for fast startup.
 * Returns the port number, or null if no server found.
 */
async function discoverPort() {
  // Try cached port first
  try {
    const stored = await chrome.storage.local.get('solace_port');
    if (stored.solace_port) {
      const cached = stored.solace_port;
      try {
        const resp = await fetch(`http://localhost:${cached}${ENDPOINTS.health}`, { signal: AbortSignal.timeout(1000) });
        if (resp.ok) {
          _setPort(cached);
          return cached;
        }
      } catch { /* cached port stale, try discovery */ }
    }
  } catch { /* no storage access, proceed with scan */ }

  // Probe range
  for (let port = SOLACE_PORT_RANGE_START; port <= SOLACE_PORT_RANGE_END; port++) {
    try {
      const resp = await fetch(`http://localhost:${port}${ENDPOINTS.health}`, { signal: AbortSignal.timeout(1000) });
      if (resp.ok) {
        _setPort(port);
        try { await chrome.storage.local.set({ solace_port: port }); } catch { /* ok */ }
        return port;
      }
    } catch { continue; }
  }
  return null;
}

function _setPort(port) {
  SOLACE_API_PORT = port;
  SOLACE_API = `http://localhost:${port}`;
  SOLACE_WS = `ws://localhost:${port}`;
}

// --- Protocol ---
const WS_PROTOCOL_VERSION = '1.0';

// --- Timeouts ---
const HEALTH_CHECK_INTERVAL_MS = 30000;  // 30s per rethink doc
const HEALTH_CHECK_TIMEOUT_MS = 3000;
const APP_CACHE_TTL_MS = 60000;          // 1 minute
const WS_RECONNECT_BASE_MS = 2000;
const WS_RECONNECT_MAX_MS = 30000;
const TOAST_DURATION_MS = 3000;
