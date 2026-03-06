#!/usr/bin/env node
/**
 * Solace Browser CLI Bridge - HTTP API Server
 * Phase 6: Bridges solace_cli with Chrome extension via HTTP on localhost:9999
 *
 * Endpoints:
 *   POST /record-episode    - Start recording browser interactions
 *   POST /stop-recording    - Stop recording and save episode
 *   POST /play-recipe       - Replay a recorded episode
 *   GET  /list-episodes     - List all recorded episodes
 *   GET  /episode/:id       - Get episode details
 *   POST /export-episode    - Export episode as JSON
 *   POST /get-snapshot      - Get current page snapshot
 *   POST /verify-interaction - Verify an element exists on page
 *
 * Architecture:
 *   HTTP (localhost:9999) -> WebSocket (localhost:9222) -> Chrome Extension
 */

const http = require("http");
const WebSocket = require("ws");
const fs = require("fs");
const path = require("path");
const { URL } = require("url");

// Configuration
const HTTP_PORT = parseInt(process.env.SOLACE_HTTP_PORT || "9999", 10);
const WS_URL = process.env.SOLACE_WS_URL || "ws://localhost:9222";

// CORS — allowed origins (no wildcard)
const ALLOWED_ORIGINS = [
  "http://127.0.0.1:8791",
  "http://localhost:8791",
  "https://www.solaceagi.com",
];

/**
 * Return the origin for CORS headers if the request origin is allowed,
 * otherwise return null (no CORS header will be set).
 */
function getAllowedOrigin(req) {
  const origin = req.headers.origin;
  if (origin && ALLOWED_ORIGINS.includes(origin)) {
    return origin;
  }
  return null;
}
const EPISODE_DIR = process.env.SOLACE_EPISODE_DIR ||
  path.join(require("os").homedir(), ".solace", "browser");
const REQUEST_TIMEOUT_MS = 30000;

// Ensure episode directory exists
if (!fs.existsSync(EPISODE_DIR)) {
  fs.mkdirSync(EPISODE_DIR, { recursive: true });
}

// WebSocket connection state
let ws = null;
let wsConnected = false;
const pendingRequests = new Map(); // request_id -> { resolve, reject, timer }
let requestCounter = 0;

// Active recording state
let activeRecording = null; // { session_id, domain, start_time, actions }

/**
 * Connect to the WebSocket server (solace browser websocket_server.py)
 */
function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  log("Connecting to WebSocket:", WS_URL);
  ws = new WebSocket(WS_URL);

  ws.on("open", () => {
    wsConnected = true;
    log("Connected to WebSocket server");
  });

  ws.on("message", (data) => {
    try {
      const msg = JSON.parse(data.toString());
      handleWsMessage(msg);
    } catch (e) {
      log("WebSocket parse error:", e.message);
    }
  });

  ws.on("close", () => {
    wsConnected = false;
    log("WebSocket disconnected, reconnecting in 3s...");
    setTimeout(connectWebSocket, 3000);
  });

  ws.on("error", (err) => {
    log("WebSocket error:", err.message);
  });
}

/**
 * Handle incoming WebSocket messages (responses from extension)
 */
function handleWsMessage(msg) {
  const requestId = msg.request_id;

  // Track recording actions
  if (activeRecording) {
    if (msg.type === "RECORDING_STARTED") {
      activeRecording.session_id = msg.session_id;
    } else if (msg.type === "RECORDING_STOPPED") {
      activeRecording = null;
    }
  }

  // Resolve pending HTTP request if matched
  if (requestId && pendingRequests.has(requestId)) {
    const pending = pendingRequests.get(requestId);
    clearTimeout(pending.timer);
    pendingRequests.delete(requestId);
    pending.resolve(msg);
  }
}

/**
 * Send a command via WebSocket and wait for response
 */
function sendCommand(command) {
  return new Promise((resolve, reject) => {
    if (!wsConnected || !ws || ws.readyState !== WebSocket.OPEN) {
      reject(new Error("Not connected to browser extension WebSocket server"));
      return;
    }

    const requestId = `http_${++requestCounter}_${Date.now()}`;
    command.request_id = requestId;

    const timer = setTimeout(() => {
      pendingRequests.delete(requestId);
      reject(new Error("Request timeout after " + REQUEST_TIMEOUT_MS + "ms"));
    }, REQUEST_TIMEOUT_MS);

    pendingRequests.set(requestId, { resolve, reject, timer });
    ws.send(JSON.stringify(command));
  });
}

/**
 * List episode files from disk
 */
function listEpisodes() {
  const episodes = [];
  if (!fs.existsSync(EPISODE_DIR)) return episodes;

  const files = fs.readdirSync(EPISODE_DIR)
    .filter(f => f.startsWith("episode_") && f.endsWith(".json"))
    .sort();

  for (const file of files) {
    try {
      const filepath = path.join(EPISODE_DIR, file);
      const data = JSON.parse(fs.readFileSync(filepath, "utf-8"));
      episodes.push({
        id: data.session_id || file.replace("episode_", "").replace(".json", ""),
        file: file,
        domain: data.domain || "unknown",
        action_count: (data.actions || []).length,
        start_time: data.start_time || null,
        end_time: data.end_time || null,
      });
    } catch (e) {
      // Skip malformed files
    }
  }
  return episodes;
}

/**
 * Get episode by ID
 */
function getEpisode(episodeId) {
  if (!fs.existsSync(EPISODE_DIR)) return null;

  const files = fs.readdirSync(EPISODE_DIR)
    .filter(f => f.startsWith("episode_") && f.endsWith(".json"));

  for (const file of files) {
    try {
      const filepath = path.join(EPISODE_DIR, file);
      const data = JSON.parse(fs.readFileSync(filepath, "utf-8"));
      const id = data.session_id || file.replace("episode_", "").replace(".json", "");
      if (id === episodeId || file === `episode_${episodeId}.json`) {
        return { ...data, _file: file, _path: filepath };
      }
    } catch (e) {
      // Skip malformed files
    }
  }
  return null;
}

/**
 * Parse JSON body from request
 */
function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", chunk => { body += chunk; });
    req.on("end", () => {
      if (!body) {
        resolve({});
        return;
      }
      try {
        resolve(JSON.parse(body));
      } catch (e) {
        reject(new Error("Invalid JSON body"));
      }
    });
    req.on("error", reject);
  });
}

/**
 * Send JSON response.
 * CORS headers are set via res._corsOrigin (populated in handleRequest).
 */
function sendJson(res, statusCode, data) {
  const json = JSON.stringify(data, null, 2);
  const headers = { "Content-Type": "application/json", "Vary": "Origin" };
  if (res._corsOrigin) {
    headers["Access-Control-Allow-Origin"] = res._corsOrigin;
    headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS";
    headers["Access-Control-Allow-Headers"] = "Content-Type";
  }
  res.writeHead(statusCode, headers);
  res.end(json);
}

/**
 * Send error response
 */
function sendError(res, statusCode, message) {
  sendJson(res, statusCode, { error: message, status: "error" });
}

/**
 * Route: POST /record-episode
 * Start recording browser interactions
 * Body: { url: string, domain?: string }
 */
async function handleRecordEpisode(req, res) {
  const body = await parseBody(req);
  const url = body.url;
  const domain = body.domain || (url ? new URL(url).hostname : "unknown");

  if (!url) {
    sendError(res, 400, "Missing required field: url");
    return;
  }

  try {
    // Navigate to URL first
    const navResult = await sendCommand({
      type: "NAVIGATE",
      payload: { url },
    });

    // Start recording
    const recResult = await sendCommand({
      type: "START_RECORDING",
      payload: { domain },
    });

    activeRecording = {
      session_id: recResult.session_id || `session_${Date.now()}`,
      domain,
      start_time: new Date().toISOString(),
      actions: [],
    };

    sendJson(res, 200, {
      status: "recording",
      session_id: activeRecording.session_id,
      domain,
      url,
      message: "Recording started",
    });
  } catch (e) {
    sendError(res, 502, "Failed to start recording: " + e.message);
  }
}

/**
 * Route: POST /stop-recording
 * Stop recording and save episode
 */
async function handleStopRecording(req, res) {
  if (!activeRecording) {
    sendError(res, 400, "No active recording session");
    return;
  }

  try {
    const result = await sendCommand({ type: "STOP_RECORDING" });

    const episode = result.episode || {
      session_id: activeRecording.session_id,
      domain: activeRecording.domain,
      start_time: activeRecording.start_time,
      end_time: new Date().toISOString(),
      actions: activeRecording.actions,
    };

    const sessionId = activeRecording.session_id;
    activeRecording = null;

    sendJson(res, 200, {
      status: "stopped",
      session_id: sessionId,
      episode,
      message: "Recording stopped and episode saved",
    });
  } catch (e) {
    sendError(res, 502, "Failed to stop recording: " + e.message);
  }
}

/**
 * Route: POST /play-recipe
 * Replay a recorded episode
 * Body: { episode_id: string, speed?: number }
 */
async function handlePlayRecipe(req, res) {
  const body = await parseBody(req);
  const episodeId = body.episode_id;
  const speed = body.speed || 1.0;

  if (!episodeId) {
    sendError(res, 400, "Missing required field: episode_id");
    return;
  }

  const episode = getEpisode(episodeId);
  if (!episode) {
    sendError(res, 404, "Episode not found: " + episodeId);
    return;
  }

  const actions = episode.actions || [];
  const results = [];
  let errors = 0;

  for (const action of actions) {
    try {
      let command = null;

      switch (action.type) {
        case "navigate":
          command = { type: "NAVIGATE", payload: { url: action.data.url } };
          break;
        case "click":
          command = { type: "CLICK", payload: action.data };
          break;
        case "type":
          command = { type: "TYPE", payload: action.data };
          break;
        case "snapshot":
          command = { type: "SNAPSHOT", payload: {} };
          break;
        default:
          results.push({ action: action.type, status: "skipped", reason: "unknown action type" });
          continue;
      }

      if (command) {
        const result = await sendCommand(command);
        results.push({ action: action.type, status: "success", result });

        // Apply speed delay
        const delay = Math.max(100, 500 / speed);
        await new Promise(r => setTimeout(r, delay));
      }
    } catch (e) {
      errors++;
      results.push({ action: action.type, status: "error", error: e.message });
    }
  }

  sendJson(res, 200, {
    status: "completed",
    episode_id: episodeId,
    total_actions: actions.length,
    executed: results.length,
    errors,
    results,
    message: `Replay complete: ${results.length - errors}/${actions.length} actions succeeded`,
  });
}

/**
 * Route: GET /list-episodes
 * List all recorded episodes
 */
function handleListEpisodes(req, res) {
  const episodes = listEpisodes();
  sendJson(res, 200, {
    status: "ok",
    count: episodes.length,
    episodes,
    episode_dir: EPISODE_DIR,
  });
}

/**
 * Route: GET /episode/:id
 * Get episode details
 */
function handleGetEpisode(req, res, episodeId) {
  if (!episodeId) {
    sendError(res, 400, "Missing episode ID");
    return;
  }

  const episode = getEpisode(episodeId);
  if (!episode) {
    sendError(res, 404, "Episode not found: " + episodeId);
    return;
  }

  // Remove internal fields
  const { _file, _path, ...data } = episode;
  sendJson(res, 200, {
    status: "ok",
    episode: data,
    file: _file,
  });
}

/**
 * Route: POST /export-episode
 * Export episode as downloadable JSON
 * Body: { episode_id: string, output_path?: string }
 */
async function handleExportEpisode(req, res) {
  const body = await parseBody(req);
  const episodeId = body.episode_id;
  const outputPath = body.output_path;

  if (!episodeId) {
    sendError(res, 400, "Missing required field: episode_id");
    return;
  }

  const episode = getEpisode(episodeId);
  if (!episode) {
    sendError(res, 404, "Episode not found: " + episodeId);
    return;
  }

  const { _file, _path, ...data } = episode;

  if (outputPath) {
    try {
      const dir = path.dirname(outputPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
      fs.writeFileSync(outputPath, JSON.stringify(data, null, 2));
      sendJson(res, 200, {
        status: "exported",
        episode_id: episodeId,
        output_path: outputPath,
        size_bytes: fs.statSync(outputPath).size,
        message: "Episode exported to " + outputPath,
      });
    } catch (e) {
      sendError(res, 500, "Failed to write export file: " + e.message);
    }
  } else {
    sendJson(res, 200, {
      status: "exported",
      episode_id: episodeId,
      episode: data,
      message: "Episode data returned inline",
    });
  }
}

/**
 * Route: POST /get-snapshot
 * Get current page snapshot
 * Body: { step?: string }
 */
async function handleGetSnapshot(req, res) {
  const body = await parseBody(req);

  try {
    const result = await sendCommand({
      type: "SNAPSHOT",
      payload: { step: body.step || "api_snapshot" },
    });

    sendJson(res, 200, {
      status: "ok",
      snapshot: result.snapshot || result,
      timestamp: new Date().toISOString(),
    });
  } catch (e) {
    sendError(res, 502, "Failed to get snapshot: " + e.message);
  }
}

/**
 * Route: POST /verify-interaction
 * Verify an element exists and is interactable on the current page
 * Body: { selector?: string, reference?: object }
 */
async function handleVerifyInteraction(req, res) {
  const body = await parseBody(req);
  const selector = body.selector;
  const reference = body.reference;

  if (!selector && !reference) {
    sendError(res, 400, "Missing required field: selector or reference");
    return;
  }

  try {
    // Use EXECUTE_SCRIPT to verify element existence and visibility
    const script = selector
      ? `(function() {
          const el = document.querySelector(${JSON.stringify(selector)});
          if (!el) return { found: false, selector: ${JSON.stringify(selector)} };
          const rect = el.getBoundingClientRect();
          const visible = rect.width > 0 && rect.height > 0 && el.offsetParent !== null;
          const enabled = !el.disabled;
          return {
            found: true,
            visible: visible,
            enabled: enabled,
            tag: el.tagName,
            id: el.id,
            text: (el.innerText || '').substring(0, 100),
            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
            selector: ${JSON.stringify(selector)}
          };
        })()`
      : `(function() {
          const ref = ${JSON.stringify(reference)};
          const elements = document.querySelectorAll('[role]');
          for (const el of elements) {
            const role = el.getAttribute('role');
            const label = el.getAttribute('aria-label') || el.innerText;
            if (role === ref.role && (!ref.name || label === ref.name || (label && label.includes(ref.name)))) {
              const rect = el.getBoundingClientRect();
              return {
                found: true,
                visible: rect.width > 0 && rect.height > 0,
                enabled: !el.disabled,
                tag: el.tagName,
                role: role,
                label: label ? label.substring(0, 100) : null,
                rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
              };
            }
          }
          return { found: false, reference: ref };
        })()`;

    const result = await sendCommand({
      type: "EXECUTE_SCRIPT",
      payload: { script },
    });

    const verification = result.result || result;
    sendJson(res, 200, {
      status: "ok",
      verified: verification.found === true,
      interactable: verification.found && verification.visible && verification.enabled,
      details: verification,
      timestamp: new Date().toISOString(),
    });
  } catch (e) {
    sendError(res, 502, "Failed to verify interaction: " + e.message);
  }
}

/**
 * Route: GET /health
 * Health check endpoint
 */
function handleHealth(req, res) {
  sendJson(res, 200, {
    status: "ok",
    service: "solace-browser-cli-bridge",
    version: "0.6.0",
    ws_connected: wsConnected,
    ws_url: WS_URL,
    http_port: HTTP_PORT,
    episode_dir: EPISODE_DIR,
    active_recording: activeRecording ? activeRecording.session_id : null,
    pending_requests: pendingRequests.size,
    uptime_seconds: Math.floor(process.uptime()),
    timestamp: new Date().toISOString(),
  });
}

/**
 * Route: GET /status
 * Detailed system status
 */
function handleStatus(req, res) {
  const episodes = listEpisodes();
  sendJson(res, 200, {
    status: "ok",
    ws_connected: wsConnected,
    active_recording: activeRecording,
    episode_count: episodes.length,
    pending_requests: pendingRequests.size,
    uptime_seconds: Math.floor(process.uptime()),
  });
}

/**
 * Parse URL path and extract episode ID if present
 */
function parseRoute(reqUrl) {
  const parsed = new URL(reqUrl, `http://localhost:${HTTP_PORT}`);
  const pathname = parsed.pathname;

  // Match /episode/:id
  const episodeMatch = pathname.match(/^\/episode\/(.+)$/);
  if (episodeMatch) {
    return { route: "episode_detail", episodeId: decodeURIComponent(episodeMatch[1]) };
  }

  return { route: pathname, episodeId: null };
}

/**
 * Main HTTP request handler
 */
async function handleRequest(req, res) {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    const origin = getAllowedOrigin(req);
    const headers = {
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Vary": "Origin",
    };
    if (origin) {
      headers["Access-Control-Allow-Origin"] = origin;
    }
    res.writeHead(204, headers);
    res.end();
    return;
  }

  // Set CORS origin for all non-preflight responses
  res._corsOrigin = getAllowedOrigin(req);

  const { route, episodeId } = parseRoute(req.url);
  const method = req.method;

  log(`${method} ${req.url}`);

  try {
    // GET routes
    if (method === "GET") {
      switch (route) {
        case "/health":
          return handleHealth(req, res);
        case "/status":
          return handleStatus(req, res);
        case "/list-episodes":
          return handleListEpisodes(req, res);
        case "episode_detail":
          return handleGetEpisode(req, res, episodeId);
        default:
          return sendError(res, 404, "Not found: " + route);
      }
    }

    // POST routes
    if (method === "POST") {
      switch (route) {
        case "/record-episode":
          return await handleRecordEpisode(req, res);
        case "/stop-recording":
          return await handleStopRecording(req, res);
        case "/play-recipe":
          return await handlePlayRecipe(req, res);
        case "/export-episode":
          return await handleExportEpisode(req, res);
        case "/get-snapshot":
          return await handleGetSnapshot(req, res);
        case "/verify-interaction":
          return await handleVerifyInteraction(req, res);
        default:
          return sendError(res, 404, "Not found: " + route);
      }
    }

    sendError(res, 405, "Method not allowed: " + method);
  } catch (e) {
    log("Request error:", e.message);
    sendError(res, 500, "Internal server error: " + e.message);
  }
}

/**
 * Logging utility
 */
function log(...args) {
  const ts = new Date().toISOString().substring(11, 23);
  console.log(`[${ts}] [solace-http]`, ...args);
}

/**
 * Start HTTP server
 */
function startServer() {
  const server = http.createServer(handleRequest);

  server.listen(HTTP_PORT, "127.0.0.1", () => {
    log("Solace Browser CLI Bridge started");
    log(`  HTTP API:    http://127.0.0.1:${HTTP_PORT}`);
    log(`  WebSocket:   ${WS_URL}`);
    log(`  Episodes:    ${EPISODE_DIR}`);
    log("");
    log("Endpoints:");
    log("  GET  /health            - Health check");
    log("  GET  /status            - System status");
    log("  GET  /list-episodes     - List recorded episodes");
    log("  GET  /episode/:id       - Get episode details");
    log("  POST /record-episode    - Start recording { url }");
    log("  POST /stop-recording    - Stop recording");
    log("  POST /play-recipe       - Replay episode { episode_id }");
    log("  POST /export-episode    - Export episode { episode_id }");
    log("  POST /get-snapshot      - Page snapshot");
    log("  POST /verify-interaction - Verify element { selector }");
  });

  // Connect to WebSocket server
  connectWebSocket();

  // Graceful shutdown
  process.on("SIGINT", () => {
    log("Shutting down...");
    if (ws) ws.close();
    server.close(() => process.exit(0));
  });

  process.on("SIGTERM", () => {
    log("Shutting down...");
    if (ws) ws.close();
    server.close(() => process.exit(0));
  });

  return server;
}

// Export for testing
module.exports = {
  startServer,
  listEpisodes,
  getEpisode,
  parseRoute,
  sendJson,
  sendError,
  HTTP_PORT,
  WS_URL,
  EPISODE_DIR,
};

// Start if run directly
if (require.main === module) {
  startServer();
}
