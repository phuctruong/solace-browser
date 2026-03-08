/**
 * Solace Browser -- Yinyang Service Worker (MV3)
 * Background script for URL detection, app matching, and IPC.
 *
 * MV3 service workers die after 30s of inactivity.
 * Design for resurrection, not prevention.
 *
 * ARCHITECTURE NOTE: WebSocket connections are owned by sidepanel.js,
 * NOT this service worker. SW↔panel communication uses chrome.runtime
 * messaging. This is intentional — WS in SW would die on SW suspension.
 *
 * Paper: 47 Section 24 | Auth: 65537
 */

// --- Constants (duplicated from constants.js because SW can't import scripts) ---
const SOLACE_PORT_RANGE_START = 8888;
const SOLACE_PORT_RANGE_END = 8899;
let SOLACE_API_PORT = 8888;
let SOLACE_API = `http://localhost:${SOLACE_API_PORT}`;
const APP_CACHE_TTL_MS = 60000;

// Dynamic port discovery for service worker context
async function swDiscoverPort() {
  // Try cached port first
  try {
    const stored = await chrome.storage.local.get('solace_port');
    if (stored.solace_port) {
      const resp = await fetch(`http://localhost:${stored.solace_port}/api/health`, { signal: AbortSignal.timeout(1000) });
      if (resp.ok) {
        SOLACE_API_PORT = stored.solace_port;
        SOLACE_API = `http://localhost:${stored.solace_port}`;
        return stored.solace_port;
      }
    }
  } catch { /* proceed with scan */ }
  for (let port = SOLACE_PORT_RANGE_START; port <= SOLACE_PORT_RANGE_END; port++) {
    try {
      const resp = await fetch(`http://localhost:${port}/api/health`, { signal: AbortSignal.timeout(1000) });
      if (resp.ok) {
        SOLACE_API_PORT = port;
        SOLACE_API = `http://localhost:${port}`;
        try { await chrome.storage.local.set({ solace_port: port }); } catch { /* ok */ }
        return port;
      }
    } catch { continue; }
  }
  return null;
}

// Storage schema version for migration guards
const CURRENT_SCHEMA_VERSION = 1;

// Open side panel on action click
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

// Auto-open side panel when browser starts + handle storage migrations
chrome.runtime.onInstalled.addListener(async ({ reason, previousVersion }) => {
  chrome.sidePanel.setOptions({ enabled: true });

  // Storage schema migration on update
  if (reason === 'update') {
    const data = await chrome.storage.local.get('schemaVersion');
    const oldVersion = data.schemaVersion ?? 0;
    if (oldVersion < CURRENT_SCHEMA_VERSION) {
      // Future migrations go here: if (oldVersion < 2) { ... }
      console.log(`[YY] Migrated storage schema ${oldVersion} → ${CURRENT_SCHEMA_VERSION}`);
    }
  }
  await chrome.storage.local.set({ schemaVersion: CURRENT_SCHEMA_VERSION });
});

// When a new tab is created, open the side panel
chrome.tabs.onCreated.addListener(async (tab) => {
  try {
    if (tab.windowId) {
      await chrome.sidePanel.open({ windowId: tab.windowId });
    }
  } catch {
    // Side panel may already be open
  }
});

// Track current tab URL for app detection
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.url) {
    matchAppsForUrl(changeInfo.url, tabId);
  }
});

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  try {
    const tab = await chrome.tabs.get(activeInfo.tabId);
    if (tab.url) {
      matchAppsForUrl(tab.url, activeInfo.tabId);
    }
  } catch {
    // Tab may have been closed
  }
});

/**
 * Match URL against installed app manifests.
 * Updates badge and notifies side panel.
 */
async function matchAppsForUrl(url, tabId) {
  try {
    const apps = await getInstalledApps();
    const matched = apps.filter(app => matchesUrl(app, url));

    // Update badge
    const count = matched.length;
    chrome.action.setBadgeText({ text: count > 0 ? String(count) : '', tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#6C5CE7', tabId });

    // Store matched apps for side panel to read
    await chrome.storage.session.set({
      [`matched_${tabId}`]: matched.map(a => a.id),
      currentUrl: url,
      currentTabId: tabId
    });
  } catch (err) {
    console.error('[Yinyang SW] App match error:', err.message);
  }
}

/**
 * Check if an app manifest matches the given URL.
 * Supports exact domain, subdomain, and glob patterns.
 */
function matchesUrl(app, url) {
  if (!app.site) return false;
  try {
    const parsed = new URL(url);
    const pageHost = parsed.hostname;
    const pagePath = parsed.pathname;

    // Support comma-separated domains
    const sites = Array.isArray(app.site) ? app.site : [app.site];
    for (const site of sites) {
      const siteStr = String(site).trim();
      let domainMatch = false;

      // Glob pattern: *.example.com
      if (siteStr.startsWith('*.')) {
        const baseDomain = siteStr.slice(2);
        if (pageHost === baseDomain || pageHost.endsWith(`.${baseDomain}`)) {
          domainMatch = true;
        }
      } else {
        // Exact or subdomain match
        const appHost = new URL(siteStr.startsWith('http') ? siteStr : `https://${siteStr}`).hostname;
        if (pageHost === appHost || pageHost.endsWith(`.${appHost}`)) {
          domainMatch = true;
        }
      }

      if (!domainMatch) continue;

      // Path prefix filter: if app.path_prefix is set, URL path must start with it
      if (app.path_prefix) {
        const prefix = String(app.path_prefix);
        if (!pagePath.startsWith(prefix)) continue;
      }

      return true;
    }
  } catch {
    // URL parse error
  }
  return false;
}

/**
 * Fetch installed apps from Solace API (cached in session storage).
 */
async function getInstalledApps() {
  try {
    const cached = await chrome.storage.session.get('installed_apps');
    if (cached.installed_apps && Date.now() - cached.installed_apps.ts < APP_CACHE_TTL_MS) {
      return cached.installed_apps.data;
    }
  } catch {
    // Storage access error
  }

  try {
    const resp = await fetch(`${SOLACE_API}/api/apps`);
    if (!resp.ok) throw new Error(`API ${resp.status}`);
    const apps = await resp.json();
    await chrome.storage.session.set({
      installed_apps: { data: apps, ts: Date.now() }
    });
    return apps;
  } catch (err) {
    console.error('[Yinyang SW] Failed to fetch apps:', err.message);
    return [];
  }
}

// Message handler for side panel communication
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.type === 'GET_MATCHED_APPS') {
    chrome.storage.session.get([`matched_${msg.tabId}`, 'currentUrl'])
      .then(data => {
        sendResponse({
          apps: data[`matched_${msg.tabId}`] || [],
          url: data.currentUrl || ''
        });
      });
    return true; // async response
  }

  if (msg.type === 'PING') {
    sendResponse({ type: 'PONG', ts: Date.now() });
  }
});

// --- MV3 Lifecycle: chrome.alarms for periodic app cache refresh ---
// MV3 service workers die after 30s idle. Alarms wake the SW periodically
// to keep the app cache fresh even without user interaction.
const APP_CACHE_REFRESH_ALARM = 'app-cache-refresh';

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create(APP_CACHE_REFRESH_ALARM, { periodInMinutes: 5 });
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === APP_CACHE_REFRESH_ALARM) {
    console.log('[Yinyang SW] Alarm: refreshing app cache');
    await getInstalledApps();
  }
});

console.log(`[Yinyang SW] Service worker initialized (API: ${SOLACE_API})`);
