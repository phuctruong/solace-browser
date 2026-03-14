// Diagram: 02-dashboard-login
/**
 * chat.js — YinYang AI Chat Widget for Solace Hub
 * Laws:
 *   - No CDN, no jQuery, no dynamic code execution, vanilla JS only.
 *   - Advisory only: chat NEVER auto-executes actions.
 *   - No dynamic code execution — eval is banned.
 *   - Port 8888 ONLY. Port 9222 BANNED.
 *   - Auth via localStorage("solace_token") — SHA-256 hex only.
 */

"use strict";

(function () {
  var BASE = "";  // same-origin

  // ---------------------------------------------------------------------------
  // Auth
  // ---------------------------------------------------------------------------
  function getAuthHeader() {
    var token = localStorage.getItem("solace_token") || "";
    return token ? { "Authorization": "Bearer " + token } : {};
  }

  // ---------------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------------
  var chatMessages   = document.getElementById("chat-messages");
  var chatEmpty      = document.getElementById("chat-empty");
  var chatLoading    = document.getElementById("chat-loading");
  var chatInput      = document.getElementById("chat-input");
  var btnSend        = document.getElementById("btn-send");
  var btnClear       = document.getElementById("btn-clear");
  var modelBadge     = document.getElementById("model-badge");
  var costDisplay    = document.getElementById("cost-display");
  var chatSuggestions = document.getElementById("chat-suggestions");
  var charCount      = document.getElementById("chat-char-count");

  // ---------------------------------------------------------------------------
  // API helpers
  // ---------------------------------------------------------------------------
  function apiGet(path) {
    return fetch(BASE + path, {
      credentials: "same-origin",
      headers: getAuthHeader(),
    }).then(function (r) {
      return r.json().then(function (d) { return { status: r.status, data: d }; });
    });
  }

  function apiPost(path, body) {
    var headers = Object.assign({ "Content-Type": "application/json" }, getAuthHeader());
    return fetch(BASE + path, {
      method: "POST",
      credentials: "same-origin",
      headers: headers,
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (d) { return { status: r.status, data: d }; });
    });
  }

  function apiDelete(path) {
    return fetch(BASE + path, {
      method: "DELETE",
      credentials: "same-origin",
      headers: getAuthHeader(),
    }).then(function (r) {
      return r.json().then(function (d) { return { status: r.status, data: d }; });
    });
  }

  // ---------------------------------------------------------------------------
  // Escape helper (no innerHTML from untrusted data)
  // ---------------------------------------------------------------------------
  function _esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ---------------------------------------------------------------------------
  // Render a single message bubble
  // ---------------------------------------------------------------------------
  function renderBubble(msg) {
    var wrapper = document.createElement("div");
    wrapper.className = "chat-bubble chat-bubble--" + (msg.role === "user" ? "user" : "assistant");
    var roleLabel = msg.role === "user" ? "You" : "YinYang";
    var ts = msg.timestamp ? msg.timestamp.replace("T", " ").slice(0, 19) + "Z" : "";
    wrapper.innerHTML = (
      "<div class=\"bubble-role\">" + _esc(roleLabel) + "</div>" +
      "<div class=\"bubble-content\">" + _esc(msg.content) + "</div>" +
      "<div class=\"bubble-ts\">" + _esc(ts) + "</div>"
    );
    return wrapper;
  }

  // ---------------------------------------------------------------------------
  // Render full history
  // ---------------------------------------------------------------------------
  function renderHistory(messages) {
    chatMessages.innerHTML = "";
    if (!messages || messages.length === 0) {
      chatMessages.appendChild(chatEmpty);
      chatEmpty.hidden = false;
      return;
    }
    chatEmpty.hidden = true;
    messages.forEach(function (msg) {
      chatMessages.appendChild(renderBubble(msg));
    });
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  // ---------------------------------------------------------------------------
  // Load suggestions
  // ---------------------------------------------------------------------------
  function loadSuggestions(context) {
    var path = "/api/v1/chat/suggestions";
    if (context) {
      path += "?context=" + encodeURIComponent(context);
    }
    apiGet(path).then(function (res) {
      if (res.status === 200 && Array.isArray(res.data.suggestions)) {
        renderSuggestions(res.data.suggestions);
      }
    }).catch(function () {
      // Network error — suggestions are non-critical
    });
  }

  function renderSuggestions(suggestions) {
    chatSuggestions.innerHTML = "";
    suggestions.forEach(function (text) {
      var chip = document.createElement("button");
      chip.type = "button";
      chip.className = "suggestion-chip";
      chip.textContent = text;
      chip.addEventListener("click", function () {
        chatInput.value = text;
        updateCharCount();
        chatInput.focus();
      });
      chatSuggestions.appendChild(chip);
    });
  }

  // ---------------------------------------------------------------------------
  // Load chat history on init
  // ---------------------------------------------------------------------------
  function loadHistory() {
    apiGet("/api/v1/chat/history").then(function (res) {
      if (res.status === 200) {
        renderHistory(res.data.messages || []);
      }
    }).catch(function () {
      // Network error — start fresh
    });
  }

  // ---------------------------------------------------------------------------
  // Send message
  // ---------------------------------------------------------------------------
  function sendMessage() {
    var content = chatInput.value.trim();
    if (content.length === 0) {
      return;
    }
    if (content.length > 2000) {
      return;
    }

    chatInput.value = "";
    updateCharCount();
    btnSend.disabled = true;
    chatLoading.hidden = false;

    // Optimistically render user bubble
    if (chatEmpty.parentNode === chatMessages) {
      chatEmpty.hidden = true;
    }
    var userMsg = { role: "user", content: content, timestamp: new Date().toISOString() };
    chatMessages.appendChild(renderBubble(userMsg));
    chatMessages.scrollTop = chatMessages.scrollHeight;

    apiPost("/api/v1/chat/message", { content: content }).then(function (res) {
      chatLoading.hidden = true;
      btnSend.disabled = false;
      if (res.status !== 200) {
        var errMsg = (res.data && res.data.error) || "Error sending message.";
        var errBubble = { role: "assistant", content: "[Error: " + errMsg + "]", timestamp: new Date().toISOString() };
        chatMessages.appendChild(renderBubble(errBubble));
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return;
      }
      var d = res.data;
      var assistantMsg = {
        role: "assistant",
        content: d.reply || "",
        timestamp: d.timestamp || new Date().toISOString(),
      };
      chatMessages.appendChild(renderBubble(assistantMsg));
      chatMessages.scrollTop = chatMessages.scrollHeight;

      // Update model badge and cost
      if (d.model_used) {
        modelBadge.textContent = d.model_used;
      }
      if (d.cost_usd !== undefined) {
        costDisplay.textContent = "cost: $" + String(d.cost_usd);
      }
      // Refresh suggestions from reply
      if (Array.isArray(d.suggestions) && d.suggestions.length > 0) {
        renderSuggestions(d.suggestions);
      }
    }).catch(function () {
      chatLoading.hidden = true;
      btnSend.disabled = false;
      var netErrMsg = { role: "assistant", content: "[Network error — is Yinyang server running on port 8888?]", timestamp: new Date().toISOString() };
      chatMessages.appendChild(renderBubble(netErrMsg));
      chatMessages.scrollTop = chatMessages.scrollHeight;
    });
  }

  // ---------------------------------------------------------------------------
  // Clear history
  // ---------------------------------------------------------------------------
  function clearHistory() {
    apiDelete("/api/v1/chat/history").then(function () {
      renderHistory([]);
      modelBadge.textContent = "stub";
      costDisplay.textContent = "cost: $0.000";
      loadSuggestions(null);
    }).catch(function () {
      // Non-critical
    });
  }

  // ---------------------------------------------------------------------------
  // Char counter
  // ---------------------------------------------------------------------------
  function updateCharCount() {
    var len = chatInput.value.length;
    charCount.textContent = len + " / 2000";
    if (len > 1900) {
      charCount.style.color = "var(--hub-warning)";
    } else {
      charCount.style.color = "var(--hub-text-muted)";
    }
  }

  // ---------------------------------------------------------------------------
  // Event listeners
  // ---------------------------------------------------------------------------
  btnSend.addEventListener("click", sendMessage);

  chatInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  chatInput.addEventListener("input", updateCharCount);

  btnClear.addEventListener("click", clearHistory);

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  document.addEventListener("DOMContentLoaded", function () {
    loadHistory();
    loadSuggestions(null);
    updateCharCount();
  });

}());
