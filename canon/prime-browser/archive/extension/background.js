/**
 * Solace Browser Control - Background Service Worker
 * Connects to local Solace CLI via WebSocket
 * Handles CDP commands, snapshots, and recording
 *
 * Phase A Integration (A1-A2):
 *   A1: Per-tab state machine
 *   A2: Badge config + per-tab title updates
 */

const DEFAULT_WS_URL = "ws://localhost:9222";
const EXTENSION_ID = "solace-browser-v0.1.0";

let ws = null;

// A1: Per-tab state machine
const VALID_TRANSITIONS = {
  IDLE:       ["CONNECTED"],
  CONNECTED:  ["NAVIGATING", "CLICKING", "TYPING", "RECORDING", "ERROR"],
  NAVIGATING: ["CONNECTED", "ERROR"],
  CLICKING:   ["CONNECTED", "ERROR"],
  TYPING:     ["CONNECTED", "ERROR"],
  RECORDING:  ["RECORDING", "CONNECTED", "ERROR"],
  ERROR:      ["IDLE"],
};

const tabStates = new Map();      // Map<tabId, TabStateObj>
const auditLog = new Map();       // Map<tabId, AuditEntry[]>
const tabActionLogs = new Map();  // Map<tabId, action[]>

// A2: Badge configuration
const BADGE_CONFIG = {
    IDLE:       { text: '',   color: '#000000' },
    CONNECTED:  { text: 'ON', color: '#FF5A36' },
    NAVIGATING: { text: '..', color: '#F59E0B' },
    CLICKING:   { text: '..', color: '#F59E0B' },
    TYPING:     { text: '..', color: '#F59E0B' },
    RECORDING:  { text: 'REC', color: '#DC2626' },
    ERROR:      { text: '!',  color: '#B91C1C' },
};

const STATE_TITLES = {
    IDLE: 'Solace: Disconnected',
    CONNECTED: 'Solace: Connected',
    NAVIGATING: 'Solace: Navigating...',
    CLICKING: 'Solace: Clicking...',
    TYPING: 'Solace: Typing...',
    RECORDING: 'Solace: Recording',
    ERROR: 'Solace: Error',
};

// Initialize extension
console.log("[Solace] Background worker starting...");

// ===== A1: Per-Tab State Machine Functions =====

function createTabState(tabId) {
  if (tabStates.has(tabId)) {
    throw new Error(`Tab ${tabId} already has state`);
  }
  const now = new Date().toISOString();
  const state = {
    tabId,
    state: "CONNECTED",
    currentAction: null,
    recordingSession: null,
    lastError: null,
    timestamp: now,
    metadata: {},
  };
  tabStates.set(tabId, state);
  appendAudit(tabId, "IDLE", "CONNECTED", "extension attached");
  return state;
}

function transitionTabState(tabId, newState, reason = "") {
  const tab = tabStates.get(tabId);
  if (!tab) {
    throw new Error(`No state for tab ${tabId}`);
  }
  const allowed = VALID_TRANSITIONS[tab.state] || [];
  if (!allowed.includes(newState)) {
    throw new Error(`Invalid transition: ${tab.state} -> ${newState} (${reason})`);
  }
  const oldState = tab.state;
  tab.state = newState;
  tab.timestamp = new Date().toISOString();
  if (newState === "ERROR") tab.lastError = reason;
  if (["CONNECTED", "ERROR", "IDLE"].includes(newState)) tab.currentAction = null;
  appendAudit(tabId, oldState, newState, reason);
  // A2: Update badge and title on state transition
  updateBadge(tabId, newState);
  updateTitle(tabId, newState);
  return tab;
}

function getTabState(tabId) {
  return tabStates.get(tabId) || null;
}

function removeTabState(tabId) {
  const tab = tabStates.get(tabId);
  if (tab) {
    appendAudit(tabId, tab.state, "CLOSED", "tab closed");
    tabStates.delete(tabId);
    tabActionLogs.delete(tabId);
    auditLog.delete(tabId);
    // A2: Clear badge on tab removal
    chrome.action.setBadgeText({ tabId, text: '' });
  }
  return tab;
}

function appendAudit(tabId, fromState, toState, reason) {
  if (!auditLog.has(tabId)) auditLog.set(tabId, []);
  auditLog.get(tabId).push({
    tabId, fromState, toState, reason,
    timestamp: new Date().toISOString(),
  });
}

function logAction(tabId, type, data) {
  const tab = getTabState(tabId);
  if (tab && tab.state === "RECORDING") {
    if (!tabActionLogs.has(tabId)) tabActionLogs.set(tabId, []);
    tabActionLogs.get(tabId).push({
      type, data, timestamp: new Date().toISOString()
    });
  }
}

// ===== A2: Badge and Title Update Functions =====

function updateBadge(tabId, state) {
    const config = BADGE_CONFIG[state] || BADGE_CONFIG.IDLE;
    chrome.action.setBadgeText({ tabId, text: config.text });
    chrome.action.setBadgeBackgroundColor({ tabId, color: config.color });
}

function updateTitle(tabId, state) {
    const title = STATE_TITLES[state] || 'Solace';
    chrome.action.setTitle({ tabId, title });
}

/**
 * Get server configuration from Chrome storage
 */
async function getServerConfig() {
  const stored = await chrome.storage.local.get(['wsUrl']);
  return {
    wsUrl: stored.wsUrl || DEFAULT_WS_URL
  };
}

async function connect() {
  if (ws && ws.readyState === WebSocket.OPEN) return;

  const config = await getServerConfig();
  const wsUrl = config.wsUrl;

  console.log("[Solace] Attempting to connect to", wsUrl);

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log("[Solace] ✅ Connected to Solace CLI");
    sendMessage({
      type: "EXTENSION_READY",
      extension_id: EXTENSION_ID,
      version: "0.1.0",
      timestamp: new Date().toISOString()
    });
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      console.log("[Solace] Received:", msg.type);
      handleCommand(msg);
    } catch (e) {
      console.error("[Solace] Parse error:", e);
    }
  };

  ws.onerror = (error) => {
    console.error("[Solace] WebSocket error:", error);
  };

  ws.onclose = () => {
    console.log("[Solace] Disconnected from Solace CLI");
    // Try to reconnect every 5 seconds
    setTimeout(connect, 5000);
  };
}

function sendMessage(data) {
  if (ws && isConnected) {
    ws.send(JSON.stringify(data));
  } else {
    console.warn("[Solace] Not connected, queuing:", data.type);
  }
}

// Command handlers
async function handleCommand(msg) {
  const { type, payload = {}, request_id, tab_id } = msg;

  // Resolve tab: explicit tab_id or active tab
  let resolvedTabId = tab_id;
  if (!resolvedTabId) {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    resolvedTabId = tab?.id;
  }
  if (!resolvedTabId) {
    sendMessage({ type: "ERROR", error: "No tab available", request_id });
    return;
  }

  // Ensure tab state exists (auto-create on first command)
  if (!getTabState(resolvedTabId) && type !== "PING") {
    try {
      createTabState(resolvedTabId);
    } catch (e) {
      console.warn("[Solace] Tab state already exists:", e.message);
    }
  }

  const tabState = getTabState(resolvedTabId);

  try {
    switch (type) {
      case "PING":
        sendMessage({ type: "PONG", request_id, timestamp: new Date().toISOString() });
        break;

      case "START_RECORDING":
        startRecording(payload, request_id, resolvedTabId);
        break;

      case "STOP_RECORDING":
        stopRecording(request_id, resolvedTabId);
        break;

      case "NAVIGATE":
        if (tabState.state === "RECORDING") {
          await navigateTo(payload.url, request_id, resolvedTabId);
          logAction(resolvedTabId, "navigate", { url: payload.url });
        } else {
          transitionTabState(resolvedTabId, "NAVIGATING", "navigate() called");
          await navigateTo(payload.url, request_id, resolvedTabId);
          transitionTabState(resolvedTabId, "CONNECTED", "page load complete");
        }
        break;

      case "CLICK":
        if (tabState.state === "RECORDING") {
          await clickElement(payload, request_id, resolvedTabId);
          logAction(resolvedTabId, "click", payload);
        } else {
          transitionTabState(resolvedTabId, "CLICKING", "click() called");
          await clickElement(payload, request_id, resolvedTabId);
          transitionTabState(resolvedTabId, "CONNECTED", "click complete");
        }
        break;

      case "TYPE":
        if (tabState.state === "RECORDING") {
          await typeText(payload, request_id, resolvedTabId);
          logAction(resolvedTabId, "type", payload);
        } else {
          transitionTabState(resolvedTabId, "TYPING", "type() called");
          await typeText(payload, request_id, resolvedTabId);
          transitionTabState(resolvedTabId, "CONNECTED", "type complete");
        }
        break;

      case "SNAPSHOT":
        await takeSnapshot(payload, request_id, resolvedTabId);
        break;

      case "EXTRACT_PAGE":
        await extractPageData(payload, request_id, resolvedTabId);
        break;

      case "EXECUTE_SCRIPT":
        await executeScript(payload.script, request_id, resolvedTabId);
        break;

      // Phase 4: Automation API commands
      case "FILL_FIELD":
        await automationCommand("FILL_FIELD", payload, request_id, resolvedTabId);
        break;

      case "CLICK_BUTTON":
        await automationCommand("CLICK_BUTTON", payload, request_id, resolvedTabId);
        break;

      case "SELECT_OPTION":
        await automationCommand("SELECT_OPTION", payload, request_id, resolvedTabId);
        break;

      case "TYPE_TEXT_ADVANCED":
        await automationCommand("TYPE_TEXT_ADVANCED", payload, request_id, resolvedTabId);
        break;

      case "VERIFY_INTERACTION":
        await automationCommand("VERIFY_INTERACTION", payload, request_id, resolvedTabId);
        break;

      default:
        console.warn("[Solace] Unknown command:", type);
    }
  } catch (error) {
    console.error("[Solace] Command error:", error);
    // Transition to ERROR if valid
    try {
      transitionTabState(resolvedTabId, "ERROR", error.message);
    } catch (_) { /* already in ERROR or IDLE */ }
    sendMessage({
      type: "ERROR",
      error: error.message,
      command: type,
      request_id,
      tab_id: resolvedTabId
    });
  }
}

function startRecording(payload, request_id, tabId) {
  const tab = getTabState(tabId);
  if (!tab) return;

  transitionTabState(tabId, "RECORDING", "start recording");

  const session = {
    id: `session_${Date.now()}`,
    domain: payload.domain,
    start_time: new Date().toISOString(),
    actions: []
  };

  tab.recordingSession = session.id;
  if (!tabActionLogs.has(tabId)) {
    tabActionLogs.set(tabId, []);
  }

  console.log("[Solace] Recording started:", session.id);
  sendMessage({
    type: "RECORDING_STARTED",
    session_id: session.id,
    domain: payload.domain,
    request_id,
    tab_id: tabId
  });
}

function stopRecording(request_id, tabId) {
  const tab = getTabState(tabId);
  if (!tab) return;

  const actions = tabActionLogs.get(tabId) || [];
  const episode = {
    session_id: tab.recordingSession,
    domain: "unknown",
    start_time: new Date().toISOString(),
    end_time: new Date().toISOString(),
    actions: actions
  };

  console.log("[Solace] Recording stopped, actions:", actions.length);

  sendMessage({
    type: "RECORDING_STOPPED",
    episode,
    request_id,
    tab_id: tabId
  });

  tab.recordingSession = null;
  tabActionLogs.delete(tabId);
}

async function navigateTo(url, request_id, tabId) {
  try {
    // Validate input
    if (!url) {
      throw new Error("Missing required parameter: url");
    }

    if (typeof url !== 'string') {
      throw new Error(`Invalid url type: ${typeof url}, expected string`);
    }

    // Ensure URL has a protocol
    if (!url.startsWith("http://") && !url.startsWith("https://") && !url.startsWith("data:") && !url.startsWith("about:")) {
      url = "https://" + url;
    }

    console.log("[Solace] Navigating to:", url);

    const tab = await chrome.tabs.get(tabId);
    if (!tab) {
      throw new Error(`Tab ${tabId} not found`);
    }

    await chrome.tabs.update(tabId, { url });

    // Wait for page to load
    await new Promise(resolve => {
      const handler = (changedTabId, changeInfo) => {
        if (changedTabId === tabId && changeInfo.status === "complete") {
          chrome.tabs.onUpdated.removeListener(handler);
          resolve();
        }
      };
      chrome.tabs.onUpdated.addListener(handler);
    });

    // Snapshot is internal - don't send response yet
    try {
      await takeSnapshot({ step: "after_navigate", internal: true }, null, tabId);
    } catch (e) {
      console.warn("[Solace] Snapshot error during navigate:", e.message);
    }

    sendMessage({
      type: "NAVIGATION_COMPLETE",
      url,
      status: "success",
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error("[Solace] Navigation error:", error);
    sendMessage({
      type: "NAVIGATION_ERROR",
      error: error.message,
      command: "NAVIGATE",
      url: url || null,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  }
}

async function clickElement(payload, request_id, tabId) {
  const { selector, reference } = payload;
  console.log("[Solace] Clicking:", selector || reference);

  try {
    // Validate input
    if (!selector && !reference) {
      throw new Error("Missing required parameter: selector or reference");
    }

    const tab = await chrome.tabs.get(tabId);
    if (!tab) {
      throw new Error(`Tab ${tabId} not found`);
    }

    const result = await chrome.tabs.sendMessage(tabId, {
      type: "CLICK_ELEMENT",
      selector,
      reference
    });

    // Check if click was successful
    if (!result.success) {
      console.error("[Solace] Click failed:", result.error);
      sendMessage({
        type: "CLICK_ERROR",
        error: result.error,
        selector,
        reference,
        details: result,
        request_id,
        tab_id: tabId,
        timestamp: new Date().toISOString()
      });
      return;
    }

    await new Promise(r => setTimeout(r, 500)); // Wait for action

    // Snapshot is internal - don't send response
    try {
      await takeSnapshot({ step: "after_click", internal: true }, null, tabId);
    } catch (e) {
      console.warn("[Solace] Snapshot error after click:", e.message);
    }

    sendMessage({
      type: "CLICK_COMPLETE",
      clicked: result.clicked,
      element: result.element,
      selector,
      reference,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error("[Solace] Click error:", error);
    sendMessage({
      type: "CLICK_ERROR",
      error: error.message,
      command: "CLICK",
      selector: payload.selector,
      reference: payload.reference,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  }
}

async function typeText(payload, request_id, tabId) {
  const { selector, text, reference } = payload;
  console.log("[Solace] Typing into:", selector || reference);

  try {
    // Validate input
    if (!selector && !reference) {
      throw new Error("Missing required parameter: selector or reference");
    }

    if (!text) {
      throw new Error("Missing required parameter: text");
    }

    if (typeof text !== 'string') {
      throw new Error(`Invalid text type: ${typeof text}, expected string`);
    }

    const tab = await chrome.tabs.get(tabId);
    if (!tab) {
      throw new Error(`Tab ${tabId} not found`);
    }

    const result = await chrome.tabs.sendMessage(tabId, {
      type: "TYPE_TEXT",
      selector,
      text,
      reference
    });

    // Check if type was successful
    if (!result.success) {
      console.error("[Solace] Type failed:", result.error);
      sendMessage({
        type: "TYPE_ERROR",
        error: result.error,
        selector,
        reference,
        text_length: text.length,
        details: result,
        request_id,
        tab_id: tabId,
        timestamp: new Date().toISOString()
      });
      return;
    }

    // Snapshot is internal - don't send response
    try {
      await takeSnapshot({ step: "after_type", internal: true }, null, tabId);
    } catch (e) {
      console.warn("[Solace] Snapshot error after type:", e.message);
    }

    sendMessage({
      type: "TYPE_COMPLETE",
      typed: result.typed,
      element: result.element,
      selector,
      reference,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error("[Solace] Type error:", error);
    sendMessage({
      type: "TYPE_ERROR",
      error: error.message,
      command: "TYPE",
      selector: payload.selector,
      reference: payload.reference,
      text_length: payload.text ? payload.text.length : 0,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  }
}

async function takeSnapshot(payload = {}, request_id, tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab) {
      throw new Error(`Tab ${tabId} not found`);
    }

    const snapshot = await chrome.tabs.sendMessage(tabId, {
      type: "TAKE_SNAPSHOT"
    });

    // Safe access to metadata (might be error object)
    if (snapshot && snapshot.metadata) {
      logAction(tabId, "snapshot", { step: payload.step, ...snapshot.metadata });
    } else if (snapshot && snapshot.error) {
      console.warn("[Solace] Snapshot error:", snapshot.error);
    }

    // Only send response if this is a direct command (not internal)
    // Internal snapshots (during navigate/click) don't send responses
    if (payload.internal !== true) {
      sendMessage({
        type: "SNAPSHOT_TAKEN",
        snapshot,
        step: payload.step,
        request_id,
        tab_id: tabId,
        timestamp: new Date().toISOString()
      });
    }
  } catch (error) {
    console.warn("[Solace] Snapshot message failed:", error.message);
    if (payload.internal !== true) {
      sendMessage({
        type: "SNAPSHOT_ERROR",
        error: error.message,
        request_id,
        tab_id: tabId,
        timestamp: new Date().toISOString()
      });
    }
  }
}

async function extractPageData(payload = {}, request_id, tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab) {
      throw new Error(`Tab ${tabId} not found`);
    }

    const data = await chrome.tabs.sendMessage(tabId, {
      type: "EXTRACT_PAGE_DATA"
    });

    sendMessage({
      type: "PAGE_DATA_EXTRACTED",
      data,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error("[Solace] Extract error:", error);
    sendMessage({
      type: "EXTRACT_ERROR",
      error: error.message,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  }
}

async function executeScript(script, request_id, tabId) {
  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab) {
      throw new Error(`Tab ${tabId} not found`);
    }

    const result = await chrome.tabs.sendMessage(tabId, {
      type: "EXECUTE_SCRIPT",
      script
    });

    sendMessage({
      type: "SCRIPT_EXECUTED",
      result,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error("[Solace] Script execution error:", error);
    sendMessage({
      type: "SCRIPT_ERROR",
      error: error.message,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  }
}

// ===== Phase 4: Automation API Command Router =====

/**
 * Route automation commands to content script AutomationAPI handlers.
 * Manages state transitions and sends results back over WebSocket.
 *
 * @param {string} commandType - FILL_FIELD, CLICK_BUTTON, SELECT_OPTION, TYPE_TEXT_ADVANCED, VERIFY_INTERACTION
 * @param {Object} payload - Command payload including refmap_data, ref_id, and action-specific params
 * @param {string} request_id - Request correlation ID
 * @param {number} tabId - Target tab ID
 */
async function automationCommand(commandType, payload, request_id, tabId) {
  const actionState = (commandType === 'CLICK_BUTTON') ? 'CLICKING' : 'TYPING';
  const tabState = getTabState(tabId);
  const isRecording = tabState && tabState.state === 'RECORDING';

  try {
    const tab = await chrome.tabs.get(tabId);
    if (!tab) {
      throw new Error(`Tab ${tabId} not found`);
    }

    // Transition state (skip if recording - stays in RECORDING)
    if (!isRecording) {
      transitionTabState(tabId, actionState, `${commandType} called`);
    }

    // Forward to content script
    const result = await chrome.tabs.sendMessage(tabId, {
      type: commandType,
      ...payload
    });

    // Log if recording
    if (isRecording) {
      logAction(tabId, commandType.toLowerCase(), payload);
    }

    // Return to CONNECTED (skip if recording)
    if (!isRecording) {
      transitionTabState(tabId, 'CONNECTED', `${commandType} complete`);
    }

    // Determine response type
    const responseType = result.success
      ? `${commandType}_COMPLETE`
      : `${commandType}_ERROR`;

    sendMessage({
      type: responseType,
      result,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error(`[Solace] ${commandType} error:`, error);
    sendMessage({
      type: `${commandType}_ERROR`,
      error: error.message,
      command: commandType,
      request_id,
      tab_id: tabId,
      timestamp: new Date().toISOString()
    });
  }
}

// Unified message listener for popup and content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Handle PAGE_EVENT from content scripts
  if (request.type === "PAGE_EVENT") {
    logAction(sender.tab.id, "page_event", request.data);
    return; // Don't send response for page events
  }

  // Handle commands from popup (START_RECORDING, STOP_RECORDING)
  if (request.type === "START_RECORDING" || request.type === "STOP_RECORDING") {
    handleCommand(request);
    sendResponse({ status: "command_received" });
    return; // Important: return to prevent further processing
  }

  // Handle GET_STATUS synchronously (don't use async)
  if (request.type === "GET_STATUS") {
    const tabId = sender.tab?.id || 0;
    const tabState = getTabState(tabId);
    sendResponse({
      isConnected: ws && ws.readyState === WebSocket.OPEN,
      tabState: tabState,
      recordingEnabled: tabState?.state === "RECORDING",
      currentSession: tabState?.recordingSession,
      serverUrl: DEFAULT_WS_URL
    });
    return;
  }
});

// Handle tab removal
chrome.tabs.onRemoved.addListener((tabId, removeInfo) => {
  const tab = removeTabState(tabId);
  if (tab && tab.state === "RECORDING") {
    // Auto-stop recording on tab close
    stopRecording(null, tabId);
  }
  console.log(`[Solace] Tab ${tabId} closed, state cleaned up`);
});

// Start connection attempt on load
setTimeout(connect, 1000);
