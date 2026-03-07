/**
 * Solace Browser — Yinyang Service Worker (MV3)
 * Background script for URL detection, app matching, and IPC.
 *
 * MV3 service workers die after 30s of inactivity.
 * Design for resurrection, not prevention.
 */

const SOLACE_API = 'http://localhost:9222';

// Open side panel on action click
chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });

// Auto-open side panel when browser starts (bundled browser — always show sidebar)
chrome.runtime.onInstalled.addListener(() => {
  // Open side panel on all tabs by default
  chrome.sidePanel.setOptions({
    enabled: true,
  });
});

// When a new tab is created, open the side panel
chrome.tabs.onCreated.addListener(async (tab) => {
  try {
    if (tab.windowId) {
      await chrome.sidePanel.open({ windowId: tab.windowId });
    }
  } catch {
    // Side panel may already be open — that's fine
  }
});

// Track current tab URL for app detection
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.url) {
    matchAppsForUrl(changeInfo.url, tabId);
  }
});

chrome.tabs.onActivated.addListener(async (activeInfo) => {
  const tab = await chrome.tabs.get(activeInfo.tabId);
  if (tab.url) {
    matchAppsForUrl(tab.url, activeInfo.tabId);
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
 */
function matchesUrl(app, url) {
  if (!app.site) return false;
  try {
    const appHost = new URL(app.site.startsWith('http') ? app.site : `https://${app.site}`).hostname;
    const pageHost = new URL(url).hostname;
    return pageHost === appHost || pageHost.endsWith(`.${appHost}`);
  } catch {
    return false;
  }
}

/**
 * Fetch installed apps from Solace API (cached in session storage).
 */
async function getInstalledApps() {
  const cached = await chrome.storage.session.get('installed_apps');
  if (cached.installed_apps && Date.now() - cached.installed_apps.ts < 60000) {
    return cached.installed_apps.data;
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
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
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

console.log('[Yinyang SW] Service worker initialized');
