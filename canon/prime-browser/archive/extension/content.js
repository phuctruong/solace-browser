/**
 * Solace Browser Control - Content Script
 * Runs on every webpage, handles DOM interactions
 */

console.log("[Solace] Content script loaded");

// Listen for messages from background worker
chrome.runtime.onMessage.addListener(async (request, sender, sendResponse) => {
  try {
    switch (request.type) {
      case "CLICK_ELEMENT":
        sendResponse(await clickElement(request));
        break;

      case "TYPE_TEXT":
        sendResponse(await typeText(request));
        break;

      case "TAKE_SNAPSHOT":
        sendResponse(await takeSnapshot());
        break;

      case "EXTRACT_PAGE_DATA":
        sendResponse(await extractPageData());
        break;

      case "EXECUTE_SCRIPT":
        sendResponse(await executeScript(request.script));
        break;

      // Phase 4: Automation API commands
      case "FILL_FIELD":
        sendResponse(await handleFillField(request));
        break;

      case "CLICK_BUTTON":
        sendResponse(await handleClickButton(request));
        break;

      case "SELECT_OPTION":
        sendResponse(await handleSelectOption(request));
        break;

      case "TYPE_TEXT_ADVANCED":
        sendResponse(await handleTypeTextAdvanced(request));
        break;

      case "VERIFY_INTERACTION":
        sendResponse(await handleVerifyInteraction(request));
        break;

      default:
        sendResponse({ error: "Unknown command: " + request.type });
    }
  } catch (error) {
    sendResponse({ error: error.message });
  }
});

// Click element by selector or semantic reference
async function clickElement(request) {
  const { selector, reference } = request;
  let element = null;

  try {
    if (!selector && !reference) {
      return {
        success: false,
        error: "Missing required parameter: selector or reference",
        selector,
        reference
      };
    }

    if (selector) {
      // Direct selector (XPath or CSS)
      if (selector.startsWith("xpath=")) {
        const xpath = selector.replace("xpath=", "");
        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        element = result.singleNodeValue;
      } else {
        element = document.querySelector(selector);
      }
    } else if (reference) {
      // Semantic reference lookup
      element = findElementByReference(reference);
    }

    if (!element) {
      return {
        success: false,
        error: `Failed to click: selector not found "${selector || reference}"`,
        selector,
        reference,
        found: false
      };
    }

    // Check visibility
    const isVisible = element.offsetParent !== null;
    if (!isVisible) {
      return {
        success: false,
        error: `Element found but not visible: ${selector || reference}`,
        element: serializeElement(element),
        found: true,
        visible: false
      };
    }

    // Scroll into view
    element.scrollIntoView({ behavior: "smooth", block: "center" });
    await sleep(300);

    // Click
    element.click();
    console.log("[Solace] Clicked:", element.tagName, element.id, element.className);

    return {
      success: true,
      clicked: true,
      element: serializeElement(element),
      found: true,
      visible: true,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      selector,
      reference
    };
  }
}

// Type text into element
async function typeText(request) {
  const { selector, text, reference } = request;
  let element = null;

  try {
    if (!selector && !reference) {
      return {
        success: false,
        error: "Missing required parameter: selector or reference",
        selector,
        reference
      };
    }

    if (!text) {
      return {
        success: false,
        error: "Missing required parameter: text",
        selector,
        reference
      };
    }

    if (typeof text !== 'string') {
      return {
        success: false,
        error: `Invalid text type: ${typeof text}, expected string`,
        selector,
        reference
      };
    }

    if (selector) {
      if (selector.startsWith("xpath=")) {
        const xpath = selector.replace("xpath=", "");
        const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
        element = result.singleNodeValue;
      } else {
        element = document.querySelector(selector);
      }
    } else if (reference) {
      element = findElementByReference(reference);
    }

    if (!element) {
      return {
        success: false,
        error: `Failed to type: selector not found "${selector || reference}"`,
        selector,
        reference,
        found: false
      };
    }

    // Check if element is text-editable
    const isTextInput = ['TEXTAREA', 'INPUT'].includes(element.tagName) || element.contentEditable === 'true';
    if (!isTextInput) {
      return {
        success: false,
        error: `Element is not a text input: ${element.tagName}`,
        element: serializeElement(element),
        found: true,
        isTextInput: false
      };
    }

    // Check visibility
    const isVisible = element.offsetParent !== null;
    if (!isVisible) {
      return {
        success: false,
        error: `Element found but not visible: ${selector || reference}`,
        element: serializeElement(element),
        found: true,
        visible: false
      };
    }

    // Focus and clear
    element.focus();
    element.select();
    await sleep(100);

    // Type character by character
    for (const char of text) {
      element.value += char;
      element.dispatchEvent(new Event("input", { bubbles: true }));
      await sleep(50);
    }

    console.log("[Solace] Typed into:", element.tagName, element.id);

    return {
      success: true,
      typed: text.length,
      element: serializeElement(element),
      found: true,
      visible: true,
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    return {
      success: false,
      error: error.message,
      selector,
      reference
    };
  }
}

// Take canonical snapshot of page
async function takeSnapshot() {
  try {
    const html = document.documentElement.outerHTML;
    const canonicalized = canonicalizeDOM(html);
    const hash = hashString(canonicalized);

    // Extract key information
    const title = document.title;
    const url = window.location.href;
    const meta = {
      title,
      url,
      domain: new URL(url).hostname,
      timestamp: new Date().toISOString()
    };

    // Get accessible tree
    const a11yTree = extractAccessibilityTree();

    return {
      metadata: meta,
      a11y_tree: a11yTree,
      canonical_hash: hash,
      html_length: html.length,
      screenshot: await captureScreenshot()
    };
  } catch (error) {
    return { error: error.message };
  }
}

// Extract page data (structure, content)
async function extractPageData() {
  try {
    const data = {
      title: document.title,
      url: window.location.href,
      body_text: document.body.innerText.substring(0, 10000),
      links: Array.from(document.querySelectorAll("a")).map(a => ({
        text: a.innerText,
        href: a.href
      })).slice(0, 50),
      forms: Array.from(document.querySelectorAll("form")).map(f => ({
        action: f.action,
        method: f.method,
        inputs: Array.from(f.querySelectorAll("input")).map(i => ({
          name: i.name,
          type: i.type,
          placeholder: i.placeholder
        }))
      })),
      buttons: Array.from(document.querySelectorAll("button")).map(b => ({
        text: b.innerText,
        id: b.id,
        class: b.className
      })).slice(0, 20),
      semantic_elements: {
        nav: document.querySelectorAll("nav").length,
        main: document.querySelectorAll("main").length,
        article: document.querySelectorAll("article").length,
        section: document.querySelectorAll("section").length
      }
    };

    return data;
  } catch (error) {
    return { error: error.message };
  }
}

// Execute arbitrary script in page context
async function executeScript(script) {
  try {
    const result = eval(script);
    return { success: true, result };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// UTILITY FUNCTIONS

function canonicalizeDOM(html) {
  // Remove script tags, event handlers, dynamic content
  let clean = html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
    .replace(/on\w+="[^"]*"/g, "")
    .replace(/\s+/g, " ")
    .trim();

  // Normalize whitespace
  clean = clean
    .replace(/>\s+</g, "><")
    .replace(/\s+/g, " ");

  return clean;
}

function hashString(str) {
  // Simple hash function (not cryptographic, for demo)
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16);
}

function findElementByReference(ref) {
  // Find element by semantic properties
  // { role: "button", name: "Reply", semantic_id: "ref#1" }

  let elements = document.querySelectorAll("[role]");

  for (const el of elements) {
    const role = el.getAttribute("role");
    const ariaLabel = el.getAttribute("aria-label");
    const text = el.innerText;

    if (role === ref.role) {
      if (ref.name && (ariaLabel === ref.name || text === ref.name)) {
        return el;
      } else if (!ref.name) {
        return el;
      }
    }
  }

  // Fallback: try to find by text content
  if (ref.name) {
    const buttons = document.querySelectorAll("button");
    for (const btn of buttons) {
      if (btn.innerText.includes(ref.name)) {
        return btn;
      }
    }

    const inputs = document.querySelectorAll("input, textarea");
    for (const input of inputs) {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (label && label.innerText.includes(ref.name)) {
        return input;
      }
    }
  }

  return null;
}

function serializeElement(el) {
  return {
    tag: el.tagName,
    id: el.id,
    class: el.className,
    text: el.innerText.substring(0, 100),
    role: el.getAttribute("role"),
    aria_label: el.getAttribute("aria-label")
  };
}

function extractAccessibilityTree() {
  const tree = [];

  function walk(node, depth = 0) {
    if (depth > 5) return; // Limit depth

    if (node.nodeType === Node.ELEMENT_NODE) {
      const role = node.getAttribute("role") || node.tagName.toLowerCase();
      const label = node.getAttribute("aria-label") || node.innerText?.substring(0, 50) || "";

      tree.push({
        role,
        label,
        tag: node.tagName,
        depth
      });

      for (let child of node.children) {
        walk(child, depth + 1);
      }
    }
  }

  walk(document.body);
  return tree.slice(0, 200); // Limit output
}

async function captureScreenshot() {
  try {
    const canvas = await html2canvas(document.body);
    return canvas.toDataURL("image/png").substring(0, 1000) + "..."; // Truncate for demo
  } catch (e) {
    return null;
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ===== PHASE 4: AUTOMATION API HANDLERS =====
// These handlers create an AutomationAPI instance per request using
// the provided refmap_data, then delegate to the appropriate method.

/**
 * Instantiate AutomationAPI from request payload.
 * @param {Object} request - Must contain refmap_data
 * @returns {AutomationAPI}
 */
function getAutomationAPI(request) {
  if (!request.refmap_data) {
    throw new Error("Missing refmap_data in request");
  }
  // AutomationAPI is loaded via automation_api.js in manifest content_scripts
  return new AutomationAPI(request.refmap_data);
}

async function handleFillField(request) {
  try {
    const api = getAutomationAPI(request);
    return await api.fillField(request.ref_id, request.value);
  } catch (error) {
    return { success: false, action: 'fillField', error: error.message };
  }
}

async function handleClickButton(request) {
  try {
    const api = getAutomationAPI(request);
    return await api.clickButton(request.ref_id);
  } catch (error) {
    return { success: false, action: 'clickButton', error: error.message };
  }
}

async function handleSelectOption(request) {
  try {
    const api = getAutomationAPI(request);
    return await api.selectOption(request.ref_id, request.option_value);
  } catch (error) {
    return { success: false, action: 'selectOption', error: error.message };
  }
}

async function handleTypeTextAdvanced(request) {
  try {
    const api = getAutomationAPI(request);
    return await api.typeText(request.ref_id, request.text, request.options || {});
  } catch (error) {
    return { success: false, action: 'typeText', error: error.message };
  }
}

async function handleVerifyInteraction(request) {
  try {
    const api = getAutomationAPI(request);
    return await api.verifyInteraction(request.ref_id, request.expected_state);
  } catch (error) {
    return { success: false, action: 'verifyInteraction', error: error.message };
  }
}
