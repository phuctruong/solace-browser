/**
 * Solace Browser Phase 4: Automation API
 *
 * Replays recorded actions using RefMap selectors from Phase 3.
 * Resolves ref_ids to DOM elements using prioritized selector strategies,
 * then performs fill, click, select, type, and verify operations.
 *
 * Selector Resolution Priority (from RefMap reliability scores):
 *   data_testid (0.98) > id (0.96) > aria_label (0.95) > css_selector (0.92)
 *   > xpath (0.85) > ref_path (0.75)
 *
 * Error Handling:
 *   - Element not found: return error with resolution details
 *   - Not visible: scroll into view + retry 1x
 *   - Value mismatch: log + continue
 *   - Timeout >2s: abort
 *   - Network delay: auto-wait up to 2s
 *
 * Auth: 65537 | Northstar: Phuc Forecast
 * Version: 0.2.0
 */

// ============================================================
// Constants
// ============================================================

const AUTOMATION_VERSION = '0.2.0';

const SELECTOR_RELIABILITY = {
  data_testid:      0.98,
  id:               0.96,
  aria_label:       0.95,
  aria_describedby: 0.93,
  data_qa:          0.92,
  css_selector:     0.92,
  role:             0.90,
  alt:              0.88,
  placeholder:      0.85,
  xpath:            0.85,
  name:             0.83,
  text:             0.80,
  ref_path:         0.75,
};

const DEFAULT_TIMEOUT_MS = 2000;
const RETRY_DELAY_MS     = 300;
const TYPE_CHAR_DELAY_MS = 30;
const SCROLL_SETTLE_MS   = 200;

// ============================================================
// AutomationAPI Class
// ============================================================

class AutomationAPI {
  /**
   * @param {Object} refmapData - Complete RefMap output from RefMapBuilder.build()
   * @param {Object} [options]
   * @param {number} [options.timeout=2000]        - Max wait for element (ms)
   * @param {number} [options.retryDelay=300]       - Delay before retry on not-visible
   * @param {number} [options.typeCharDelay=30]     - Delay between typed characters
   * @param {boolean} [options.dryRun=false]        - Log actions without executing
   */
  constructor(refmapData, options = {}) {
    if (!refmapData || typeof refmapData !== 'object') {
      throw new Error('AutomationAPI requires a valid RefMap object');
    }
    if (!refmapData.refmap || typeof refmapData.refmap !== 'object') {
      throw new Error('RefMap must contain a refmap field');
    }

    this.refmap    = refmapData.refmap;
    this.refOrder  = refmapData.ref_order || Object.keys(refmapData.refmap);
    this.version   = refmapData.version || AUTOMATION_VERSION;
    this.episodeId = refmapData.episode_id || '';

    this.timeout       = options.timeout       || DEFAULT_TIMEOUT_MS;
    this.retryDelay    = options.retryDelay    || RETRY_DELAY_MS;
    this.typeCharDelay = options.typeCharDelay  || TYPE_CHAR_DELAY_MS;
    this.dryRun        = options.dryRun === true;

    this.log = [];
    this.stats = {
      total_actions:   0,
      successful:      0,
      failed:          0,
      retries:         0,
      selectors_tried: 0,
    };
  }

  // ===== SELECTOR RESOLUTION =====

  /**
   * Resolve a ref_id to a DOM element using the RefMap priority list.
   * Tries selectors in priority order. On not-visible, scrolls and retries 1x.
   *
   * @param {string} ref_id - Reference ID from RefMap (e.g., "ref_a1b2c3d4")
   * @returns {Promise<{ element: Element|null, strategy: string, selectors_tried: Object[], error: string|null }>}
   */
  async resolveSelector(ref_id) {
    const entry = this.refmap[ref_id];
    if (!entry) {
      return { element: null, strategy: 'none', selectors_tried: [], error: `Unknown ref_id: ${ref_id}` };
    }

    const { semantic, structural, priority } = entry;
    const selectors_tried = [];
    const startTime = Date.now();

    for (const selectorType of priority) {
      // Timeout check
      if (Date.now() - startTime > this.timeout) {
        return {
          element: null,
          strategy: 'none',
          selectors_tried,
          error: `Timeout after ${this.timeout}ms trying selectors: ${selectors_tried.map(s => s.strategy).join(', ')}`,
        };
      }

      this.stats.selectors_tried++;
      const attempt = { strategy: selectorType, found: false, visible: false };

      const element = this._trySelector(selectorType, semantic, structural);
      if (element) {
        attempt.found = true;
        const visible = this._isVisible(element);
        attempt.visible = visible;

        if (visible) {
          selectors_tried.push(attempt);
          this._logAction('resolve', ref_id, { strategy: selectorType, success: true });
          return { element, strategy: selectorType, selectors_tried, error: null };
        }

        // Not visible: scroll + retry once
        element.scrollIntoView({ behavior: 'instant', block: 'center' });
        await this._sleep(this.retryDelay);
        this.stats.retries++;

        const visibleAfterScroll = this._isVisible(element);
        attempt.visible_after_retry = visibleAfterScroll;

        if (visibleAfterScroll) {
          selectors_tried.push(attempt);
          this._logAction('resolve', ref_id, { strategy: selectorType, success: true, retried: true });
          return { element, strategy: selectorType, selectors_tried, error: null };
        }
      }

      selectors_tried.push(attempt);
    }

    this._logAction('resolve', ref_id, { strategy: 'none', success: false });
    return {
      element: null,
      strategy: 'none',
      selectors_tried,
      error: `Could not resolve ref_id "${ref_id}" with any selector: [${priority.join(', ')}]`
    };
  }

  /**
   * Try a single selector type against the DOM.
   *
   * @param {string} selectorType - One of: data_testid, aria_label, css_selector, etc.
   * @param {Object} semantic - Semantic fields from RefMap entry
   * @param {Object} structural - Structural fields from RefMap entry
   * @returns {Element|null}
   */
  _trySelector(selectorType, semantic, structural) {
    try {
      switch (selectorType) {
        case 'data_testid':
          return semantic.data_testid
            ? document.querySelector(`[data-testid="${CSS.escape(semantic.data_testid)}"]`)
            : null;

        case 'aria_label':
          return semantic.aria_label
            ? document.querySelector(`[aria-label="${CSS.escape(semantic.aria_label)}"]`)
            : null;

        case 'aria_describedby':
          return semantic.aria_describedby
            ? document.querySelector(`[aria-describedby="${CSS.escape(semantic.aria_describedby)}"]`)
            : null;

        case 'role':
          if (!semantic.role) return null;
          if (semantic.text) {
            const candidates = document.querySelectorAll(`[role="${CSS.escape(semantic.role)}"]`);
            for (const el of candidates) {
              if (el.innerText && el.innerText.trim() === semantic.text.trim()) {
                return el;
              }
            }
            return null;
          }
          return document.querySelector(`[role="${CSS.escape(semantic.role)}"]`);

        case 'role_text': {
          if (!semantic.role) return null;
          const candidates = document.querySelectorAll(`[role="${CSS.escape(semantic.role)}"]`);
          if (!semantic.text) return candidates[0] || null;
          for (const c of candidates) {
            const txt = (c.textContent || c.innerText || '').trim();
            if (txt === semantic.text || txt.includes(semantic.text)) return c;
          }
          return candidates[0] || null;
        }

        case 'data_qa':
          return semantic.data_qa
            ? document.querySelector(`[data-qa="${CSS.escape(semantic.data_qa)}"]`)
            : null;

        case 'alt':
          return semantic.alt
            ? document.querySelector(`[alt="${CSS.escape(semantic.alt)}"]`)
            : null;

        case 'placeholder':
          return semantic.placeholder
            ? document.querySelector(`[placeholder="${CSS.escape(semantic.placeholder)}"]`)
            : null;

        case 'name':
          return semantic.name
            ? document.querySelector(`[name="${CSS.escape(semantic.name)}"]`)
            : null;

        case 'text': {
          if (!semantic.text) return null;
          const searchText = semantic.text.trim();
          const tagSets = ['button', 'a', 'label', 'span', '[role="button"]', '[role="link"]', '[role="tab"]', 'input[type="submit"]'];
          for (const sel of tagSets) {
            const els = document.querySelectorAll(sel);
            for (const el of els) {
              if (el.innerText && el.innerText.trim() === searchText) return el;
            }
          }
          // Partial match fallback
          for (const sel of tagSets) {
            const els = document.querySelectorAll(sel);
            for (const el of els) {
              if (el.innerText && el.innerText.trim().includes(searchText)) return el;
            }
          }
          // Inputs by value
          const inputs = document.querySelectorAll('input');
          for (const inp of inputs) {
            if (inp.value === searchText) return inp;
          }
          return null;
        }

        case 'id':
          return structural.id
            ? document.getElementById(structural.id)
            : null;

        case 'css_selector':
          return structural.css_selector
            ? document.querySelector(structural.css_selector)
            : null;

        case 'xpath':
          if (!structural.xpath) return null;
          const xpResult = document.evaluate(
            structural.xpath, document, null,
            XPathResult.FIRST_ORDERED_NODE_TYPE, null
          );
          return xpResult.singleNodeValue;

        case 'ref_path':
          return structural.ref_path
            ? document.querySelector(structural.ref_path)
            : null;

        default:
          return null;
      }
    } catch (e) {
      return null;
    }
  }

  // ===== CORE METHOD 1: fillField =====

  /**
   * Fill a form field (input/textarea) with a value.
   *
   * @param {string} ref_id - RefMap reference ID
   * @param {string} value - Text value to fill
   * @returns {Promise<Object>} Result with success, element info, verification
   */
  async fillField(ref_id, value) {
    this.stats.total_actions++;

    if (!ref_id || typeof ref_id !== 'string') {
      return this._error('fillField', ref_id, 'ref_id must be a non-empty string');
    }
    if (value === undefined || value === null) {
      return this._error('fillField', ref_id, 'value must not be null/undefined');
    }
    const strValue = String(value);

    const ref = this.refmap[ref_id];
    if (!ref) {
      return this._error('fillField', ref_id, `ref_id "${ref_id}" not found in RefMap`);
    }

    if (this.dryRun) {
      return this._dryRunResult(ref_id, 'fillField', { value: strValue });
    }

    const resolved = await this.resolveSelector(ref_id);
    if (!resolved.element) {
      return this._error('fillField', ref_id, resolved.error, resolved.selectors_tried);
    }

    const element = resolved.element;

    // Verify element is a form field
    if (!this._isEditableElement(element)) {
      return this._error('fillField', ref_id,
        `Element is not editable: <${element.tagName.toLowerCase()}>`, resolved.selectors_tried);
    }

    // Focus the element
    element.focus();
    element.dispatchEvent(new Event('focus', { bubbles: true }));
    await this._sleep(50);

    // Clear existing value
    if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
      // Use native setter to bypass React/Vue controlled components
      const proto = element.tagName === 'INPUT'
        ? window.HTMLInputElement.prototype
        : window.HTMLTextAreaElement.prototype;
      const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (nativeSetter) {
        nativeSetter.call(element, '');
      } else {
        element.value = '';
      }
    } else if (element.contentEditable === 'true') {
      element.textContent = '';
    }
    element.dispatchEvent(new Event('input', { bubbles: true }));
    await this._sleep(50);

    // Set new value
    if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
      const proto = element.tagName === 'INPUT'
        ? window.HTMLInputElement.prototype
        : window.HTMLTextAreaElement.prototype;
      const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
      if (nativeSetter) {
        nativeSetter.call(element, strValue);
      } else {
        element.value = strValue;
      }
    } else if (element.contentEditable === 'true') {
      element.textContent = strValue;
    }

    // Fire events to trigger framework change detection
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));

    // Verify the value was set
    const actualValue = this._getElementValue(element);
    const verified = actualValue === strValue;

    if (!verified) {
      // Value mismatch: log + continue (not a hard failure)
      console.warn(`[AutomationAPI] fillField value mismatch on ${ref_id}: expected="${strValue}", actual="${actualValue}"`);
    }

    this.stats.successful++;
    const result = {
      success: true,
      action: 'fillField',
      ref_id,
      value: strValue,
      value_verified: verified,
      actual_value: actualValue,
      element: this._serializeElement(element),
      strategy: resolved.strategy,
      selectors_tried: resolved.selectors_tried,
      timestamp: new Date().toISOString()
    };

    this._logAction('fillField', ref_id, result);
    return result;
  }

  // ===== CORE METHOD 2: clickButton =====

  /**
   * Click a button, link, or interactive element.
   *
   * @param {string} ref_id - RefMap reference ID
   * @returns {Promise<Object>} Result with success and element info
   */
  async clickButton(ref_id) {
    this.stats.total_actions++;

    if (!ref_id || typeof ref_id !== 'string') {
      return this._error('clickButton', ref_id, 'ref_id must be a non-empty string');
    }

    const ref = this.refmap[ref_id];
    if (!ref) {
      return this._error('clickButton', ref_id, `ref_id "${ref_id}" not found in RefMap`);
    }

    if (this.dryRun) {
      return this._dryRunResult(ref_id, 'clickButton', {});
    }

    const resolved = await this.resolveSelector(ref_id);
    if (!resolved.element) {
      return this._error('clickButton', ref_id, resolved.error, resolved.selectors_tried);
    }

    const element = resolved.element;

    // Check disabled state
    if (element.disabled) {
      return this._error('clickButton', ref_id, 'Element is disabled', resolved.selectors_tried);
    }

    // Perform the click
    element.click();
    await this._sleep(200);

    this.stats.successful++;
    const result = {
      success: true,
      action: 'clickButton',
      ref_id,
      clicked: true,
      element: this._serializeElement(element),
      strategy: resolved.strategy,
      selectors_tried: resolved.selectors_tried,
      timestamp: new Date().toISOString()
    };

    this._logAction('clickButton', ref_id, result);
    return result;
  }

  // ===== CORE METHOD 3: selectOption =====

  /**
   * Select an option from a dropdown (select element).
   *
   * @param {string} ref_id - RefMap reference ID for the select element
   * @param {string} optionValue - Option value or visible text to select
   * @returns {Promise<Object>} Result with success and selected value
   */
  async selectOption(ref_id, optionValue) {
    this.stats.total_actions++;

    if (!ref_id || typeof ref_id !== 'string') {
      return this._error('selectOption', ref_id, 'ref_id must be a non-empty string');
    }
    if (optionValue === undefined || optionValue === null) {
      return this._error('selectOption', ref_id, 'optionValue must not be null/undefined');
    }
    const strOption = String(optionValue);

    const ref = this.refmap[ref_id];
    if (!ref) {
      return this._error('selectOption', ref_id, `ref_id "${ref_id}" not found in RefMap`);
    }

    if (this.dryRun) {
      return this._dryRunResult(ref_id, 'selectOption', { option: strOption });
    }

    const resolved = await this.resolveSelector(ref_id);
    if (!resolved.element) {
      return this._error('selectOption', ref_id, resolved.error, resolved.selectors_tried);
    }

    const element = resolved.element;

    // Must be a select element
    if (element.tagName !== 'SELECT') {
      return this._error('selectOption', ref_id,
        `Element is not a select: <${element.tagName.toLowerCase()}>`, resolved.selectors_tried);
    }

    // Find the option: try by value first, then by visible text
    let found = false;
    const options = element.options;

    for (let i = 0; i < options.length; i++) {
      if (options[i].value === strOption) {
        element.selectedIndex = i;
        found = true;
        break;
      }
    }

    if (!found) {
      for (let i = 0; i < options.length; i++) {
        if (options[i].text.trim() === strOption.trim()) {
          element.selectedIndex = i;
          found = true;
          break;
        }
      }
    }

    // Partial text match fallback
    if (!found) {
      for (let i = 0; i < options.length; i++) {
        if (options[i].text.trim().toLowerCase().includes(strOption.toLowerCase())) {
          element.selectedIndex = i;
          found = true;
          break;
        }
      }
    }

    if (!found) {
      return this._error('selectOption', ref_id,
        `Option not found: "${strOption}". Available: ${Array.from(options).map(o => o.value || o.text).join(', ')}`,
        resolved.selectors_tried);
    }

    // Fire change event
    element.dispatchEvent(new Event('change', { bubbles: true }));

    const selectedOption = options[element.selectedIndex];
    this.stats.successful++;
    const result = {
      success: true,
      action: 'selectOption',
      ref_id,
      option: strOption,
      selected_value: selectedOption.value,
      selected_text: selectedOption.text.trim(),
      element: this._serializeElement(element),
      strategy: resolved.strategy,
      selectors_tried: resolved.selectors_tried,
      timestamp: new Date().toISOString()
    };

    this._logAction('selectOption', ref_id, result);
    return result;
  }

  // ===== CORE METHOD 4: typeText =====

  /**
   * Type text character by character with shift handling for uppercase and symbols.
   * More realistic than fillField -- simulates actual keyboard input events.
   *
   * @param {string} ref_id - RefMap reference ID for the target element
   * @param {string} text - Text to type
   * @param {Object} [shiftHandling] - Options for shift key behavior
   * @param {boolean} [shiftHandling.autoShift=true] - Auto-shift for uppercase
   * @param {boolean} [shiftHandling.dispatchKeyEvents=true] - Fire keydown/keyup events
   * @param {number} [shiftHandling.delay] - Override per-char delay (ms)
   * @returns {Promise<Object>} Result with success and verified value
   */
  async typeText(ref_id, text, shiftHandling = {}) {
    this.stats.total_actions++;

    if (!ref_id || typeof ref_id !== 'string') {
      return this._error('typeText', ref_id, 'ref_id must be a non-empty string');
    }
    if (text === undefined || text === null) {
      return this._error('typeText', ref_id, 'text must not be null/undefined');
    }
    const strText = String(text);

    const ref = this.refmap[ref_id];
    if (!ref) {
      return this._error('typeText', ref_id, `ref_id "${ref_id}" not found in RefMap`);
    }

    if (this.dryRun) {
      return this._dryRunResult(ref_id, 'typeText', { text: strText });
    }

    const resolved = await this.resolveSelector(ref_id);
    if (!resolved.element) {
      return this._error('typeText', ref_id, resolved.error, resolved.selectors_tried);
    }

    const element = resolved.element;
    const delay = shiftHandling.delay || this.typeCharDelay;
    const autoShift = shiftHandling.autoShift !== false;
    const dispatchKeys = shiftHandling.dispatchKeyEvents !== false;

    // Verify element is editable
    if (!this._isEditableElement(element)) {
      return this._error('typeText', ref_id,
        `Element is not editable: <${element.tagName.toLowerCase()}>`, resolved.selectors_tried);
    }

    // Focus
    element.focus();
    element.dispatchEvent(new Event('focus', { bubbles: true }));
    await this._sleep(50);

    // Type character by character
    const shiftSymbols = '~!@#$%^&*()_+{}|:"<>?';
    let charsTyped = 0;

    for (const char of strText) {
      const isUpper = autoShift && char !== char.toLowerCase() && char === char.toUpperCase() && /[A-Z]/.test(char);
      const isShiftSymbol = autoShift && shiftSymbols.includes(char);
      const needsShift = isUpper || isShiftSymbol;

      if (dispatchKeys) {
        if (needsShift) {
          element.dispatchEvent(new KeyboardEvent('keydown', {
            key: 'Shift', code: 'ShiftLeft', shiftKey: true, bubbles: true,
          }));
        }

        element.dispatchEvent(new KeyboardEvent('keydown', {
          key: char, code: this._charToCode(char), shiftKey: needsShift, bubbles: true,
        }));
        element.dispatchEvent(new KeyboardEvent('keypress', {
          key: char, code: this._charToCode(char), shiftKey: needsShift, bubbles: true,
        }));
      }

      // Append character
      if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
        element.value += char;
      } else if (element.contentEditable === 'true') {
        element.textContent += char;
      }

      element.dispatchEvent(new Event('input', { bubbles: true }));

      if (dispatchKeys) {
        element.dispatchEvent(new KeyboardEvent('keyup', {
          key: char, code: this._charToCode(char), shiftKey: needsShift, bubbles: true,
        }));
        if (needsShift) {
          element.dispatchEvent(new KeyboardEvent('keyup', {
            key: 'Shift', code: 'ShiftLeft', shiftKey: false, bubbles: true,
          }));
        }
      }

      charsTyped++;
      await this._sleep(delay);
    }

    // Fire change
    element.dispatchEvent(new Event('change', { bubbles: true }));

    // Verify
    const actualValue = this._getElementValue(element);
    const verified = actualValue.endsWith(strText) || actualValue === strText;

    this.stats.successful++;
    const result = {
      success: true,
      action: 'typeText',
      ref_id,
      text: strText,
      chars_typed: charsTyped,
      shift_handling: { autoShift, dispatchKeyEvents: dispatchKeys },
      element: this._serializeElement(element),
      strategy: resolved.strategy,
      selectors_tried: resolved.selectors_tried,
      verified,
      actual_value: actualValue,
      timestamp: new Date().toISOString()
    };

    this._logAction('typeText', ref_id, result);
    return result;
  }

  // ===== CORE METHOD 5: verifyInteraction =====

  /**
   * Verify an element is in an expected state.
   *
   * @param {string} ref_id - RefMap reference ID
   * @param {Object} expectedState - Expected state to verify
   * @param {string} [expectedState.value]          - Expected input value
   * @param {string} [expectedState.text]           - Expected visible text
   * @param {boolean} [expectedState.visible]       - Expected visibility
   * @param {boolean} [expectedState.disabled]      - Expected disabled state
   * @param {boolean} [expectedState.checked]       - Expected checked state
   * @param {string} [expectedState.selected]       - Expected selected option value
   * @param {string} [expectedState.class_contains] - Expected class substring
   * @param {string} [expectedState.attr]           - Attribute name to check
   * @param {string} [expectedState.attr_value]     - Expected attribute value
   * @returns {Promise<Object>} Result with matches boolean and details
   */
  async verifyInteraction(ref_id, expectedState) {
    this.stats.total_actions++;

    if (!ref_id || typeof ref_id !== 'string') {
      return this._error('verifyInteraction', ref_id, 'ref_id must be a non-empty string');
    }
    if (!expectedState || typeof expectedState !== 'object') {
      return this._error('verifyInteraction', ref_id, 'expectedState must be a non-null object');
    }

    const ref = this.refmap[ref_id];
    if (!ref) {
      return this._error('verifyInteraction', ref_id, `ref_id "${ref_id}" not found in RefMap`);
    }

    if (this.dryRun) {
      return this._dryRunResult(ref_id, 'verifyInteraction', { expectedState });
    }

    const resolved = await this.resolveSelector(ref_id);
    if (!resolved.element) {
      // If expected visible=false and element not found, that is a pass
      if (expectedState.visible === false) {
        this.stats.successful++;
        const result = {
          success: true,
          action: 'verifyInteraction',
          ref_id,
          matches: true,
          checks: { visible: { expected: false, actual: false, match: true } },
          mismatches: [],
          timestamp: new Date().toISOString(),
        };
        this._logAction('verifyInteraction', ref_id, result);
        return result;
      }
      return this._error('verifyInteraction', ref_id, resolved.error, resolved.selectors_tried);
    }

    const element = resolved.element;
    const checks = {};
    const mismatches = [];

    // Check value
    if ('value' in expectedState) {
      const actual = this._getElementValue(element);
      const match = actual === expectedState.value;
      checks.value = { expected: expectedState.value, actual, match };
      if (!match) mismatches.push({ field: 'value', expected: expectedState.value, actual });
    }

    // Check text content
    if ('text' in expectedState) {
      const actual = (element.innerText || element.textContent || '').trim();
      const match = actual === expectedState.text;
      checks.text = { expected: expectedState.text, actual, match };
      if (!match) mismatches.push({ field: 'text', expected: expectedState.text, actual });
    }

    // Check visibility
    if ('visible' in expectedState) {
      const actual = element.offsetParent !== null || element.offsetWidth > 0 || element.offsetHeight > 0;
      const match = actual === expectedState.visible;
      checks.visible = { expected: expectedState.visible, actual, match };
      if (!match) mismatches.push({ field: 'visible', expected: expectedState.visible, actual });
    }

    // Check disabled
    if ('disabled' in expectedState) {
      const actual = !!element.disabled;
      const match = actual === expectedState.disabled;
      checks.disabled = { expected: expectedState.disabled, actual, match };
      if (!match) mismatches.push({ field: 'disabled', expected: expectedState.disabled, actual });
    }

    // Check checked (checkbox/radio)
    if ('checked' in expectedState) {
      const actual = !!element.checked;
      const match = actual === expectedState.checked;
      checks.checked = { expected: expectedState.checked, actual, match };
      if (!match) mismatches.push({ field: 'checked', expected: expectedState.checked, actual });
    }

    // Check selected (select option)
    if ('selected' in expectedState) {
      let actual = '';
      if (element.tagName === 'SELECT' && element.selectedIndex >= 0) {
        actual = element.options[element.selectedIndex].value;
      }
      const match = actual === expectedState.selected;
      checks.selected = { expected: expectedState.selected, actual, match };
      if (!match) mismatches.push({ field: 'selected', expected: expectedState.selected, actual });
    }

    // Check class_contains
    if ('class_contains' in expectedState) {
      const actual = element.className || '';
      const match = actual.includes(expectedState.class_contains);
      checks.class_contains = { expected: expectedState.class_contains, actual, match };
      if (!match) mismatches.push({ field: 'class_contains', expected: expectedState.class_contains, actual });
    }

    // Check arbitrary attribute
    if ('attr' in expectedState && 'attr_value' in expectedState) {
      const actual = element.getAttribute(expectedState.attr);
      const match = actual === expectedState.attr_value;
      checks[`attr:${expectedState.attr}`] = { expected: expectedState.attr_value, actual, match };
      if (!match) mismatches.push({ field: `attr:${expectedState.attr}`, expected: expectedState.attr_value, actual });
    }

    const allMatch = mismatches.length === 0;
    if (allMatch) {
      this.stats.successful++;
    } else {
      this.stats.failed++;
      console.warn(`[AutomationAPI] verifyInteraction mismatches on ${ref_id}:`, mismatches);
    }

    const result = {
      success: true,
      action: 'verifyInteraction',
      ref_id,
      matches: allMatch,
      checks,
      mismatches,
      element: this._serializeElement(element),
      strategy: resolved.strategy,
      selectors_tried: resolved.selectors_tried,
      timestamp: new Date().toISOString()
    };

    this._logAction('verifyInteraction', ref_id, result);
    return result;
  }

  // ===== WORKFLOW EXECUTOR =====

  /**
   * Execute a sequence of actions from a workflow definition.
   * Each step: { action, ref_id, value?, option?, text?, shift_handling?, expected_state?, continueOnError? }
   *
   * @param {Object[]} steps - Array of workflow steps
   * @returns {Promise<Object>} Overall result with per-step results
   */
  async executeWorkflow(steps) {
    if (!Array.isArray(steps)) {
      return { success: false, error: 'Steps must be an array', results: [] };
    }

    const results = [];
    let allSuccess = true;

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];
      let result;

      switch (step.action) {
        case 'fillField':
          result = await this.fillField(step.ref_id, step.value);
          break;
        case 'clickButton':
          result = await this.clickButton(step.ref_id);
          break;
        case 'selectOption':
          result = await this.selectOption(step.ref_id, step.option);
          break;
        case 'typeText':
          result = await this.typeText(step.ref_id, step.text, step.shift_handling || {});
          break;
        case 'verifyInteraction':
          result = await this.verifyInteraction(step.ref_id, step.expected_state);
          break;
        case 'wait':
          await this._sleep(step.duration || 1000);
          result = { success: true, action: 'wait', duration: step.duration || 1000 };
          break;
        default:
          result = { success: false, action: step.action, error: `Unknown action: ${step.action}` };
      }

      result.step_index = i;
      results.push(result);

      if (!result.success) {
        allSuccess = false;
        if (!step.continueOnError) break;
      }
    }

    return {
      success: allSuccess,
      total_steps: steps.length,
      completed_steps: results.length,
      results,
      stats: this.getStats(),
      timestamp: new Date().toISOString(),
    };
  }

  // ===== STATIC: Build workflow from RefMap =====

  /**
   * Generate a replay workflow from a RefMap (using recorded action order).
   *
   * @param {Object} refmapOutput - Complete RefMap JSON
   * @param {Object} [valueMap]   - Map of ref_id -> value for TYPE actions
   * @returns {Object[]} Workflow steps ready for executeWorkflow()
   */
  static buildWorkflowFromRefMap(refmapOutput, valueMap = {}) {
    const steps = [];
    const refmap = refmapOutput.refmap || {};
    const order = refmapOutput.ref_order || Object.keys(refmap);

    for (const ref_id of order) {
      const entry = refmap[ref_id];
      if (!entry || !entry.actions || entry.actions.length === 0) continue;

      const actionType = (entry.actions[0].action_type || '').toUpperCase();

      switch (actionType) {
        case 'NAVIGATE':
          // Navigate actions are handled externally
          break;
        case 'CLICK':
          steps.push({ action: 'clickButton', ref_id });
          break;
        case 'TYPE':
          if (valueMap[ref_id] !== undefined) {
            steps.push({ action: 'typeText', ref_id, text: String(valueMap[ref_id]) });
          } else if (entry.semantic && entry.semantic.text) {
            steps.push({ action: 'typeText', ref_id, text: entry.semantic.text });
          }
          break;
        case 'SELECT':
          if (valueMap[ref_id] !== undefined) {
            steps.push({ action: 'selectOption', ref_id, option: String(valueMap[ref_id]) });
          }
          break;
        default:
          break;
      }
    }

    return steps;
  }

  // ===== UTILITY METHODS =====

  /**
   * Check if an element is an editable form field.
   */
  _isEditableElement(element) {
    if (!element) return false;
    const tag = element.tagName;
    if (tag === 'TEXTAREA') return true;
    if (tag === 'INPUT') {
      const type = (element.type || 'text').toLowerCase();
      const editableTypes = ['text', 'password', 'email', 'search', 'tel', 'url', 'number', 'date', 'time', 'datetime-local', 'month', 'week'];
      return editableTypes.includes(type);
    }
    if (element.contentEditable === 'true') return true;
    return false;
  }

  /**
   * Get the current value of an element.
   */
  _getElementValue(element) {
    if (!element) return '';
    if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
      return element.value || '';
    }
    if (element.tagName === 'SELECT') {
      const opt = element.options[element.selectedIndex];
      return opt ? opt.value : '';
    }
    if (element.contentEditable === 'true') {
      return element.textContent || '';
    }
    return element.innerText || element.textContent || '';
  }

  /**
   * Check if element is visible in the viewport.
   */
  _isVisible(element) {
    if (!element) return false;
    if (element.offsetParent === null && element.tagName !== 'BODY' &&
        (typeof getComputedStyle === 'function' ? getComputedStyle(element).position !== 'fixed' : true)) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  /**
   * Serialize element for result reporting.
   */
  _serializeElement(el) {
    if (!el) return null;
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      class: el.className || null,
      text: (el.innerText || '').substring(0, 100),
      role: el.getAttribute('role') || null,
      aria_label: el.getAttribute('aria-label') || null,
      type: el.type || null,
      name: el.name || null,
      value: el.value !== undefined ? el.value : null,
      disabled: el.disabled === true,
      visible: this._isVisible(el),
    };
  }

  /**
   * Map a character to a KeyboardEvent code value.
   */
  _charToCode(char) {
    if (/^[a-zA-Z]$/.test(char)) return `Key${char.toUpperCase()}`;
    if (/^[0-9]$/.test(char)) return `Digit${char}`;
    switch (char) {
      case ' ':  return 'Space';
      case '\t': return 'Tab';
      case '\n': return 'Enter';
      case '.':  return 'Period';
      case ',':  return 'Comma';
      case '/':  return 'Slash';
      case '\\': return 'Backslash';
      case '-':  return 'Minus';
      case '=':  return 'Equal';
      case '[':  return 'BracketLeft';
      case ']':  return 'BracketRight';
      case ';':  return 'Semicolon';
      case '\'': return 'Quote';
      case '`':  return 'Backquote';
      default:   return 'Unidentified';
    }
  }

  /**
   * Create a standard error result.
   */
  _error(action, ref_id, message, selectors_tried = []) {
    this.stats.failed++;
    const result = {
      success: false,
      action,
      ref_id,
      error: message,
      selectors_tried,
      timestamp: new Date().toISOString()
    };
    this._logAction(action, ref_id, result);
    return result;
  }

  /**
   * Create a dry-run result (action logged but not executed).
   */
  _dryRunResult(ref_id, action, extra) {
    this.stats.successful++;
    const result = {
      success: true,
      action,
      ref_id,
      dry_run: true,
      ...extra,
      timestamp: new Date().toISOString(),
    };
    this._logAction(action, ref_id, result);
    return result;
  }

  /**
   * Append to the internal action log (audit trail).
   */
  _logAction(action, ref_id, data) {
    this.log.push({
      action,
      ref_id,
      success: data.success !== undefined ? data.success : true,
      strategy: data.strategy || null,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Sleep utility.
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get the full audit log.
   * @returns {Object[]}
   */
  getLog() {
    return [...this.log];
  }

  /**
   * Get summary statistics.
   * @returns {Object}
   */
  getStats() {
    const total = this.stats.total_actions;
    const successes = this.stats.successful;
    const failures = this.stats.failed;
    const byAction = {};
    for (const entry of this.log) {
      if (!byAction[entry.action]) {
        byAction[entry.action] = { total: 0, success: 0, fail: 0 };
      }
      byAction[entry.action].total++;
      if (entry.success) byAction[entry.action].success++;
      else byAction[entry.action].fail++;
    }
    return {
      total,
      successes,
      failures,
      retries: this.stats.retries,
      selectors_tried: this.stats.selectors_tried,
      byAction
    };
  }

  /**
   * Reset stats and log for a new run.
   */
  reset() {
    this.log = [];
    this.stats = {
      total_actions: 0,
      successful: 0,
      failed: 0,
      retries: 0,
      selectors_tried: 0,
    };
  }
}

// Export for Node.js / test environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { AutomationAPI, SELECTOR_RELIABILITY, AUTOMATION_VERSION };
}
