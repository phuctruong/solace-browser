/**
 * Solace Browser Extension -- Canonical Constants
 *
 * Single source of truth for ports, URLs, and configuration.
 * All extension code MUST import from here instead of hardcoding values.
 *
 * Paper: 47 Section 9 (Port Consolidation) | Auth: 65537
 */

// --- Ports ---
// Port 8888: Unified API + WebSocket + Web UI (the "prosperity port")
const SOLACE_API_PORT = 8888;

// --- URLs ---
const SOLACE_API = `http://localhost:${SOLACE_API_PORT}`;
const SOLACE_WS = `ws://localhost:${SOLACE_API_PORT}`;

// --- API Endpoints ---
const ENDPOINTS = {
  health: '/api/health',
  apps: '/api/apps',
  models: '/api/models',
  wsYinyang: '/ws/yinyang',
};

// --- Protocol ---
const WS_PROTOCOL_VERSION = '1.0';

// --- Timeouts ---
const HEALTH_CHECK_INTERVAL_MS = 30000;  // 30s per rethink doc
const HEALTH_CHECK_TIMEOUT_MS = 3000;
const APP_CACHE_TTL_MS = 60000;          // 1 minute
const WS_RECONNECT_BASE_MS = 2000;
const WS_RECONNECT_MAX_MS = 30000;
const TOAST_DURATION_MS = 3000;
