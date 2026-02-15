/**
 * Popup UI for Solace Browser Control
 */

function updateStatus() {
  chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
    const statusDiv = document.getElementById("status");
    const connectionSpan = document.getElementById("connection");
    const recordingSpan = document.getElementById("recording");
    const sessionSpan = document.getElementById("session");

    if (response.isConnected) {
      statusDiv.className = "status connected";
      connectionSpan.textContent = "✅ Connected";
    } else {
      statusDiv.className = "status disconnected";
      connectionSpan.textContent = "❌ Disconnected";
    }

    if (response.recordingEnabled) {
      statusDiv.className = "status recording";
      recordingSpan.textContent = "🔴 Recording";
      sessionSpan.textContent = response.currentSession?.id || "Active";
      document.getElementById("startBtn").disabled = true;
      document.getElementById("stopBtn").disabled = false;
    } else {
      recordingSpan.textContent = "⚪ Inactive";
      sessionSpan.textContent = "None";
      document.getElementById("startBtn").disabled = false;
      document.getElementById("stopBtn").disabled = true;
    }
  });
}

function startRecording() {
  // Get current tab's hostname
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    const url = new URL(tab.url);
    const domain = url.hostname || "unknown";

    chrome.runtime.sendMessage(
      { type: "START_RECORDING", payload: { domain } },
      (response) => {
        console.log("Recording started:", response);
        setTimeout(updateStatus, 100);
      }
    );
  });
}

function stopRecording() {
  chrome.runtime.sendMessage(
    { type: "STOP_RECORDING" },
    (response) => {
      console.log("Recording stopped:", response);
      setTimeout(updateStatus, 100);
    }
  );
}

// Update status every second
updateStatus();
setInterval(updateStatus, 1000);
