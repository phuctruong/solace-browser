/**
 * Options page script for Solace Browser Bridge
 * Handles configuration storage and UI updates
 */

const DEFAULT_WS_URL = "ws://localhost:9222";

/**
 * Save options to Chrome storage
 */
function saveOptions() {
  const wsUrl = document.getElementById('wsUrl').value.trim();

  if (!wsUrl) {
    showStatus("WebSocket URL cannot be empty", "error");
    return;
  }

  chrome.storage.local.set({ wsUrl }, () => {
    showStatus("✓ Settings saved successfully", "success");
    setTimeout(() => {
      document.getElementById('status').style.display = 'none';
    }, 2000);
  });
}

/**
 * Restore options from Chrome storage
 */
function restoreOptions() {
  chrome.storage.local.get({ wsUrl: DEFAULT_WS_URL }, (items) => {
    document.getElementById('wsUrl').value = items.wsUrl;
  });
}

/**
 * Reset to default values
 */
function resetOptions() {
  document.getElementById('wsUrl').value = DEFAULT_WS_URL;
  showStatus("Reset to default values", "success");
  chrome.storage.local.set({ wsUrl: DEFAULT_WS_URL });
  setTimeout(() => {
    document.getElementById('status').style.display = 'none';
  }, 2000);
}

/**
 * Show status message
 */
function showStatus(message, type) {
  const status = document.getElementById('status');
  status.textContent = message;
  status.className = type;
  status.style.display = 'block';
}

// Initialize page when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  restoreOptions();
});

// Save button click handler
document.getElementById('save').addEventListener('click', saveOptions);

// Reset button click handler
document.getElementById('reset').addEventListener('click', resetOptions);

// Allow Enter key to save
document.getElementById('wsUrl').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    saveOptions();
  }
});
