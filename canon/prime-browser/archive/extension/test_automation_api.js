/**
 * Solace Browser Phase 4: AutomationAPI v0.2.0 Test Suite
 *
 * 75 tests across 4 verification tiers:
 *   OAuth (25): Basic sanity
 *   641 Edge (25): Edge cases
 *   274177 Stress (13): Scaling and performance
 *   65537 God (12): Integration workflows
 *
 * Runs in Node.js with minimal DOM mock (no JSDOM required).
 *
 * Auth: 65537 | Northstar: Phuc Forecast
 */

// === DOM SIMULATION SETUP ===

let domSetup = false;

function setupDOM() {
  if (domSetup) return;
  domSetup = true;

  if (typeof document !== 'undefined' && typeof document.createElement === 'function') {
    return;
  }

  try {
    const { JSDOM } = require('jsdom');
    const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
      url: 'https://example.com',
      pretendToBeVisual: true
    });
    global.document = dom.window.document;
    global.window = dom.window;
    global.Element = dom.window.Element;
    global.HTMLInputElement = dom.window.HTMLInputElement;
    global.HTMLTextAreaElement = dom.window.HTMLTextAreaElement;
    global.KeyboardEvent = dom.window.KeyboardEvent;
    global.Event = dom.window.Event;
    global.XPathResult = dom.window.XPathResult || { FIRST_ORDERED_NODE_TYPE: 9 };
    global.CSS = dom.window.CSS || { escape: (s) => s.replace(/([^\w-])/g, '\\$1') };
    global.getComputedStyle = dom.window.getComputedStyle;
  } catch (e) {
    console.error('JSDOM not available. Falling back to minimal DOM mock.');
    setupMinimalDOM();
  }
}

function setupMinimalDOM() {
  const elements = new Map();

  class MockElement {
    constructor(tag) {
      this.tagName = tag.toUpperCase();
      this.id = '';
      this.className = '';
      this.value = '';
      this.textContent = '';
      this.innerText = '';
      this.type = 'text';
      this.name = '';
      this.disabled = false;
      this.checked = false;
      this.contentEditable = 'false';
      this.selectedIndex = 0;
      this.options = [];
      this.children = [];
      this.parentNode = null;
      this._attributes = {};
      this.offsetParent = {};
      this.offsetWidth = 100;
      this.offsetHeight = 30;
    }
    getAttribute(name) { return this._attributes[name] || null; }
    setAttribute(name, val) { this._attributes[name] = val; }
    querySelector(sel) { return null; }
    querySelectorAll(sel) { return []; }
    focus() {}
    click() {}
    select() {}
    scrollIntoView() {}
    dispatchEvent() {}
    getBoundingClientRect() { return { width: this.offsetWidth, height: this.offsetHeight, top: 0, left: 0 }; }
  }

  global.document = {
    createElement(tag) { return new MockElement(tag); },
    getElementById(id) { return null; },
    querySelector(sel) { return null; },
    querySelectorAll(sel) { return []; },
    evaluate() { return { singleNodeValue: null }; },
    body: new MockElement('body'),
    documentElement: new MockElement('html')
  };

  global.window = {
    HTMLInputElement: { prototype: {} },
    HTMLTextAreaElement: { prototype: {} }
  };

  global.CSS = { escape: (s) => s };
  global.XPathResult = { FIRST_ORDERED_NODE_TYPE: 9 };
  global.Event = class Event { constructor() {} };
  global.KeyboardEvent = class KeyboardEvent { constructor() {} };
  global.getComputedStyle = () => ({ position: 'static' });
}

// === LOAD MODULES ===
const { AutomationAPI, SELECTOR_RELIABILITY, AUTOMATION_VERSION } = require('./automation_api.js');
const { RefMapBuilder } = require('./refmap_builder.js');

// === TEST FRAMEWORK ===

let testResults = { pass: 0, fail: 0, errors: [] };
let currentTier = '';

function assert(condition, message) {
  if (!condition) throw new Error(`ASSERTION FAILED: ${message}`);
}

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(`ASSERTION FAILED: ${message} | Expected: ${JSON.stringify(expected)}, Got: ${JSON.stringify(actual)}`);
  }
}

function assertTruthy(value, message) {
  if (!value) throw new Error(`ASSERTION FAILED: ${message} | Value is falsy: ${JSON.stringify(value)}`);
}

async function runTest(name, fn) {
  try {
    await fn();
    testResults.pass++;
    console.log(`  PASS: ${name}`);
  } catch (e) {
    testResults.fail++;
    testResults.errors.push({ tier: currentTier, name, error: e.message });
    console.log(`  FAIL: ${name} - ${e.message}`);
  }
}

function tier(name) {
  currentTier = name;
  console.log(`\n=== ${name} ===`);
}

// === HELPERS ===

function makeRefMap(entries) {
  const refmap = {};
  const ref_order = [];
  for (const [ref_id, entry] of Object.entries(entries)) {
    refmap[ref_id] = {
      semantic: entry.semantic || {},
      structural: entry.structural || {},
      priority: entry.priority || [],
      reliability: entry.reliability || {},
      actions: entry.actions || [{ action_index: 0, action_type: 'test', action_timestamp: '' }],
      resolution_strategy: entry.resolution_strategy || 'test'
    };
    ref_order.push(ref_id);
  }
  return { version: '0.2.0', episode_id: 'test', url_source: 'test', generated_at: '', refmap, ref_order, stats: { total_refs: ref_order.length } };
}

// === RUN ALL TESTS ===

async function runAllTests() {
  setupDOM();

  // =====================================================
  // OAUTH (25): Basic sanity
  // =====================================================
  tier('OAuth (25 tests) - Basic Sanity');

  await runTest('O01: Constructor accepts valid refmap', async () => {
    const rm = makeRefMap({ ref_001: { priority: [] } });
    const api = new AutomationAPI(rm);
    assertTruthy(api, 'API created');
  });

  await runTest('O02: Constructor rejects null input', async () => {
    let threw = false;
    try { new AutomationAPI(null); } catch (e) { threw = true; }
    assert(threw, 'Should throw on null');
  });

  await runTest('O03: Constructor rejects missing refmap field', async () => {
    let threw = false;
    try { new AutomationAPI({ version: '0.2.0' }); } catch (e) { threw = true; }
    assert(threw, 'Should throw');
  });

  await runTest('O04: Constructor rejects non-object input', async () => {
    let threw = false;
    try { new AutomationAPI('string'); } catch (e) { threw = true; }
    assert(threw, 'Should throw');
  });

  await runTest('O05: resolveSelector returns error for unknown ref_id', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_nonexistent');
    assertEqual(result.element, null, 'Element null');
    assertTruthy(result.error, 'Has error');
  });

  await runTest('O06: resolveSelector strategy is "none" for unknown ref', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_unknown');
    assertEqual(result.strategy, 'none', 'Strategy none');
  });

  await runTest('O07: fillField returns error for unknown ref_id', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.fillField('ref_unknown', 'test');
    assertEqual(result.success, false, 'Should fail');
    assertTruthy(result.error, 'Has error');
  });

  await runTest('O08: clickButton returns error for unknown ref_id', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.clickButton('ref_unknown');
    assertEqual(result.success, false, 'Should fail');
  });

  await runTest('O09: selectOption returns error for unknown ref_id', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.selectOption('ref_unknown', 'value');
    assertEqual(result.success, false, 'Should fail');
  });

  await runTest('O10: typeText returns error for unknown ref_id', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.typeText('ref_unknown', 'hello');
    assertEqual(result.success, false, 'Should fail');
  });

  await runTest('O11: verifyInteraction returns error for unknown ref_id', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.verifyInteraction('ref_unknown', { value: 'test' });
    assertEqual(result.success, false, 'Should fail');
  });

  await runTest('O12: fillField rejects null value', async () => {
    const rm = makeRefMap({ ref_001: { priority: ['id'], structural: { id: 'x' } } });
    const api = new AutomationAPI(rm);
    const result = await api.fillField('ref_001', null);
    assertEqual(result.success, false, 'Should fail for null value');
  });

  await runTest('O13: selectOption rejects null option', async () => {
    const rm = makeRefMap({ ref_001: { priority: ['id'], structural: { id: 'x' } } });
    const api = new AutomationAPI(rm);
    const result = await api.selectOption('ref_001', null);
    assertEqual(result.success, false, 'Should fail for null option');
  });

  await runTest('O14: typeText rejects null text', async () => {
    const rm = makeRefMap({ ref_001: { priority: ['id'], structural: { id: 'x' } } });
    const api = new AutomationAPI(rm);
    const result = await api.typeText('ref_001', null);
    assertEqual(result.success, false, 'Should fail for null text');
  });

  await runTest('O15: verifyInteraction rejects non-object expected state', async () => {
    const rm = makeRefMap({ ref_001: { priority: ['id'], structural: { id: 'x' } } });
    const api = new AutomationAPI(rm);
    const result = await api.verifyInteraction('ref_001', 'not-object');
    assertEqual(result.success, false, 'Should fail');
  });

  await runTest('O16: getLog returns empty array initially', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const log = api.getLog();
    assert(Array.isArray(log), 'Array');
    assertEqual(log.length, 0, 'Empty');
  });

  await runTest('O17: getStats returns zeroes initially', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const stats = api.getStats();
    assertEqual(stats.total, 0, 'Total 0');
    assertEqual(stats.successes, 0, 'Successes 0');
    assertEqual(stats.failures, 0, 'Failures 0');
  });

  await runTest('O18: getStats counts failures after failed ops', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    await api.fillField('ref_a', 'test');
    const stats = api.getStats();
    assertEqual(stats.total, 1, 'One action');
    assertEqual(stats.failures, 1, 'One failure');
  });

  await runTest('O19: getStats counts multiple failures', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    await api.fillField('ref_a', 'test');
    await api.clickButton('ref_b');
    const stats = api.getStats();
    assertEqual(stats.total, 2, 'Two actions');
    assertEqual(stats.failures, 2, 'Two failures');
  });

  await runTest('O20: RefMapBuilder output accepted by AutomationAPI', async () => {
    const builder = new RefMapBuilder();
    const episode = {
      session_id: 'test_session',
      actions: [{ type: 'click', data: { selector: '#btn', role: 'button', text: 'Go' }, timestamp: '' }]
    };
    const refmapOutput = builder.build(episode);
    const api = new AutomationAPI(refmapOutput);
    assertTruthy(api, 'API created');
  });

  await runTest('O21: refOrder preserves insertion order', async () => {
    const rm = makeRefMap({ ref_aaa: { priority: [] }, ref_bbb: { priority: [] }, ref_ccc: { priority: [] } });
    const api = new AutomationAPI(rm);
    assertEqual(api.refOrder[0], 'ref_aaa', 'First');
    assertEqual(api.refOrder[1], 'ref_bbb', 'Second');
    assertEqual(api.refOrder[2], 'ref_ccc', 'Third');
  });

  await runTest('O22: Error results include action name', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.fillField('ref_x', 'v');
    assertEqual(result.action, 'fillField', 'Action name');
  });

  await runTest('O23: Error results include ref_id', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.clickButton('ref_y');
    assertEqual(result.ref_id, 'ref_y', 'ref_id');
  });

  await runTest('O24: Error results include timestamp', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.typeText('ref_z', 'hello');
    assertTruthy(result.timestamp, 'Has timestamp');
  });

  await runTest('O25: AUTOMATION_VERSION exported', async () => {
    assertTruthy(AUTOMATION_VERSION, 'Version exported');
    assertEqual(AUTOMATION_VERSION, '0.2.0', 'Version is 0.2.0');
  });

  // =====================================================
  // 641 EDGE (25): Edge cases
  // =====================================================
  tier('641 Edge (25 tests) - Edge Cases');

  await runTest('E01: Empty refmap with no refs', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    assertEqual(api.refOrder.length, 0, 'No refs');
  });

  await runTest('E02: Ref with all-null selectors', async () => {
    const rm = makeRefMap({
      ref_null: { semantic: { aria_label: null }, structural: { id: null }, priority: ['aria_label', 'id'] }
    });
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_null');
    assertEqual(result.element, null, 'Not resolved');
  });

  await runTest('E03: Ref with empty priority array', async () => {
    const rm = makeRefMap({ ref_empty: { priority: [] } });
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_empty');
    assertEqual(result.element, null, 'No selectors');
    assertTruthy(result.error, 'Has error');
  });

  await runTest('E04: fillField with empty string value', async () => {
    const rm = makeRefMap({ ref_001: { priority: ['id'], structural: { id: 'none' } } });
    const api = new AutomationAPI(rm);
    const result = await api.fillField('ref_001', '');
    assertEqual(result.success, false, 'Fails - element not found');
  });

  await runTest('E05: typeText with empty string', async () => {
    const rm = makeRefMap({ ref_001: { priority: ['id'], structural: { id: 'none' } } });
    const api = new AutomationAPI(rm);
    const result = await api.typeText('ref_001', '');
    assertEqual(result.success, false, 'Fails - element not found');
  });

  await runTest('E06: Special characters in ref_id', async () => {
    const rm = makeRefMap({ 'ref_sp3c!@l': { priority: [] } });
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_sp3c!@l');
    assertEqual(result.element, null, 'Not found');
  });

  await runTest('E07: Very long value for fillField', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.fillField('ref_001', 'A'.repeat(10000));
    assertEqual(result.success, false, 'Fails (no element)');
  });

  await runTest('E08: Unicode text for typeText', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.typeText('ref_001', 'Hello World');
    assertEqual(result.success, false, 'Fails (no element)');
    assertEqual(result.action, 'typeText', 'Action correct');
  });

  await runTest('E09: verifyInteraction with empty expected state', async () => {
    const rm = makeRefMap({ ref_001: { priority: [] } });
    const api = new AutomationAPI(rm);
    const result = await api.verifyInteraction('ref_001', {});
    assertEqual(result.success, false, 'Fails (no element)');
  });

  await runTest('E10: Multiple operations on same ref_id log correctly', async () => {
    const rm = makeRefMap({ ref_001: { priority: [] } });
    const api = new AutomationAPI(rm);
    await api.fillField('ref_001', 'a');
    await api.fillField('ref_001', 'b');
    await api.clickButton('ref_001');
    const stats = api.getStats();
    assertEqual(stats.total, 3, 'Three actions tracked');
    assertEqual(stats.failures, 3, 'All failed');
  });

  await runTest('E11: selectOption on non-existent element', async () => {
    const rm = makeRefMap({ ref_sel: { priority: ['id'], structural: { id: 'no-select' } } });
    const api = new AutomationAPI(rm);
    const result = await api.selectOption('ref_sel', 'opt1');
    assertEqual(result.success, false, 'Should fail');
  });

  await runTest('E12: Unknown selector type in priority list', async () => {
    const rm = makeRefMap({
      ref_unk: { priority: ['nonexistent_type'], semantic: {} }
    });
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_unk');
    assertEqual(result.element, null, 'Unknown type returns null');
  });

  await runTest('E13: Extra fields in refmap entry ignored', async () => {
    const rm = makeRefMap({ ref_001: { priority: [], extra_field: 'ignored' } });
    const api = new AutomationAPI(rm);
    assertTruthy(api, 'Handles extra fields');
  });

  await runTest('E14: fillField error has correct action', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.fillField('ref_x', 'val');
    assertEqual(result.action, 'fillField', 'Correct');
  });

  await runTest('E15: clickButton error has correct action', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.clickButton('ref_x');
    assertEqual(result.action, 'clickButton', 'Correct');
  });

  await runTest('E16: selectOption error has correct action', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.selectOption('ref_x', 'val');
    assertEqual(result.action, 'selectOption', 'Correct');
  });

  await runTest('E17: typeText error has correct action', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.typeText('ref_x', 'text');
    assertEqual(result.action, 'typeText', 'Correct');
  });

  await runTest('E18: verifyInteraction error has correct action', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.verifyInteraction('ref_x', { value: '' });
    assertEqual(result.action, 'verifyInteraction', 'Correct');
  });

  await runTest('E19: getStats tracks byAction correctly', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    await api.fillField('ref_a', 'v');
    await api.clickButton('ref_b');
    await api.typeText('ref_c', 't');
    const stats = api.getStats();
    assertTruthy(stats.byAction.fillField, 'Tracks fillField');
    assertTruthy(stats.byAction.clickButton, 'Tracks clickButton');
    assertTruthy(stats.byAction.typeText, 'Tracks typeText');
  });

  await runTest('E20: Ref with only structural selectors', async () => {
    const rm = makeRefMap({
      ref_struct: { structural: { css_selector: '.nonexistent' }, priority: ['css_selector'] }
    });
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_struct');
    assertEqual(result.element, null, 'Not in DOM');
  });

  await runTest('E21: Ref with only semantic selectors', async () => {
    const rm = makeRefMap({
      ref_sem: { semantic: { aria_label: 'Nonexistent' }, priority: ['aria_label'] }
    });
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_sem');
    assertEqual(result.element, null, 'Not in DOM');
  });

  await runTest('E22: Constructor without ref_order derives from keys', async () => {
    const rm = { version: '0.2.0', refmap: { ref_a: { semantic: {}, structural: {}, priority: [], reliability: {}, actions: [], resolution_strategy: '' } } };
    const api = new AutomationAPI(rm);
    assertEqual(api.refOrder.length, 1, 'Derived order');
  });

  await runTest('E23: dryRun option prevents DOM interaction', async () => {
    const rm = makeRefMap({ ref_001: { priority: [] } });
    const api = new AutomationAPI(rm, { dryRun: true });
    const result = await api.fillField('ref_001', 'val');
    assertEqual(result.success, true, 'Dry run succeeds');
    assertEqual(result.dry_run, true, 'Marked as dry run');
  });

  await runTest('E24: reset() clears stats and log', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    await api.fillField('ref_a', 'v');
    assert(api.getLog().length > 0, 'Has logs');
    api.reset();
    assertEqual(api.getLog().length, 0, 'Log cleared');
    assertEqual(api.getStats().total, 0, 'Stats cleared');
  });

  await runTest('E25: Concurrent operations complete independently', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    await Promise.all([
      api.fillField('ref_a', 'v1'),
      api.fillField('ref_b', 'v2')
    ]);
    assertEqual(api.getStats().total, 2, 'Both tracked');
  });

  // =====================================================
  // 274177 STRESS (13): Scaling and performance
  // =====================================================
  tier('274177 Stress (13 tests) - Scaling');

  await runTest('S01: 100 ref entries in refmap', async () => {
    const entries = {};
    for (let i = 0; i < 100; i++) {
      entries[`ref_${i.toString().padStart(4, '0')}`] = { priority: [] };
    }
    const rm = makeRefMap(entries);
    const api = new AutomationAPI(rm);
    assertEqual(api.refOrder.length, 100, '100 refs');
  });

  await runTest('S02: 100 sequential fillField calls', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    for (let i = 0; i < 100; i++) {
      await api.fillField(`ref_${i}`, `value_${i}`);
    }
    assertEqual(api.getStats().total, 100, '100 actions');
    assertEqual(api.getStats().failures, 100, 'All fail');
  });

  await runTest('S03: 50 sequential clickButton calls', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    for (let i = 0; i < 50; i++) {
      await api.clickButton(`ref_${i}`);
    }
    assertEqual(api.getStats().total, 50, '50 actions');
  });

  await runTest('S04: Long text (10KB) for typeText', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const result = await api.typeText('ref_long', 'X'.repeat(10240));
    assertEqual(result.success, false, 'Fails (no element)');
  });

  await runTest('S05: 50 parallel operations', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    const promises = [];
    for (let i = 0; i < 50; i++) {
      promises.push(api.fillField(`ref_${i}`, `val_${i}`));
    }
    await Promise.all(promises);
    assertEqual(api.getStats().total, 50, '50 ops');
  });

  await runTest('S06: Large refmap with 500 entries', async () => {
    const entries = {};
    for (let i = 0; i < 500; i++) {
      entries[`ref_${i}`] = {
        semantic: { aria_label: `Label ${i}`, role: 'button' },
        structural: { css_selector: `.btn-${i}`, id: `btn-${i}` },
        priority: ['aria_label', 'id', 'css_selector']
      };
    }
    const rm = makeRefMap(entries);
    const api = new AutomationAPI(rm);
    assertEqual(api.refOrder.length, 500, '500 refs');
  });

  await runTest('S07: Mixed operations (fill + click + type + verify)', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    for (let i = 0; i < 25; i++) {
      await api.fillField(`ref_${i}`, `v${i}`);
      await api.clickButton(`ref_${i}`);
      await api.typeText(`ref_${i}`, `t${i}`);
      await api.verifyInteraction(`ref_${i}`, { value: `v${i}` });
    }
    const stats = api.getStats();
    assertEqual(stats.total, 100, '25*4 = 100');
    assertEqual(Object.keys(stats.byAction).length, 4, '4 action types');
  });

  await runTest('S08: Rapid resolve operations', async () => {
    const entries = {};
    for (let i = 0; i < 200; i++) {
      entries[`ref_${i}`] = { priority: ['id'], structural: { id: `el-${i}` } };
    }
    const rm = makeRefMap(entries);
    const api = new AutomationAPI(rm);
    const start = Date.now();
    for (let i = 0; i < 200; i++) {
      await api.resolveSelector(`ref_${i}`);
    }
    const elapsed = Date.now() - start;
    assert(elapsed < 5000, `200 resolves in <5s (${elapsed}ms)`);
  });

  await runTest('S09: getLog consistent after many ops', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    for (let i = 0; i < 30; i++) {
      await api.clickButton(`ref_${i}`);
    }
    const log = api.getLog();
    assert(log.length >= 30, 'At least 30 entries');
    for (const entry of log) {
      assertTruthy(entry.timestamp, 'Has timestamp');
    }
  });

  await runTest('S10: Priority list with many selector types', async () => {
    const rm = makeRefMap({
      ref_all: {
        semantic: { data_testid: 'test', aria_label: 'label', role: 'button', text: 'Text', placeholder: 'hint', name: 'field', alt: 'img' },
        structural: { id: 'el', css_selector: '.cls', xpath: '//div', ref_path: 'body>div' },
        priority: ['data_testid', 'aria_label', 'role', 'text', 'placeholder', 'name', 'alt', 'id', 'css_selector', 'xpath', 'ref_path']
      }
    });
    const api = new AutomationAPI(rm);
    const result = await api.resolveSelector('ref_all');
    assertEqual(result.element, null, 'No DOM');
    assert(result.selectors_tried.length > 0, 'Tried selectors');
  });

  await runTest('S11: Bulk refmap from RefMapBuilder', async () => {
    const builder = new RefMapBuilder();
    const actions = [];
    for (let i = 0; i < 50; i++) {
      actions.push({ type: 'click', data: { selector: `#btn-${i}`, role: 'button', text: `Btn ${i}` }, timestamp: '' });
    }
    const refmapOutput = builder.build({ session_id: 'bulk', actions });
    const api = new AutomationAPI(refmapOutput);
    assert(api.refOrder.length > 0, 'Has refs');
  });

  await runTest('S12: Stats byAction breakdown accurate', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    for (let i = 0; i < 10; i++) await api.fillField(`ref_${i}`, 'v');
    for (let i = 0; i < 5; i++) await api.clickButton(`ref_${i}`);
    for (let i = 0; i < 3; i++) await api.selectOption(`ref_${i}`, 'opt');
    const stats = api.getStats();
    assertEqual(stats.total, 18, '10+5+3 = 18');
  });

  await runTest('S13: 1000 resolves under 10s', async () => {
    const entries = {};
    for (let i = 0; i < 100; i++) {
      entries[`ref_${i}`] = { priority: ['id'], structural: { id: `el-${i}` } };
    }
    const rm = makeRefMap(entries);
    const api = new AutomationAPI(rm);
    const start = Date.now();
    for (let i = 0; i < 1000; i++) {
      await api.resolveSelector(`ref_${i % 100}`);
    }
    assert(Date.now() - start < 10000, 'Under 10s');
  });

  // =====================================================
  // 65537 GOD (12): Integration workflows
  // =====================================================
  tier('65537 God (12 tests) - Integration Workflows');

  await runTest('G01: Full RefMapBuilder -> AutomationAPI pipeline', async () => {
    const builder = new RefMapBuilder();
    const episode = {
      session_id: 'int_test',
      actions: [
        { type: 'navigate', data: { url: 'https://example.com/form' }, timestamp: '' },
        { type: 'click', data: { selector: '#username', role: 'textbox' }, timestamp: '' },
        { type: 'type', data: { selector: '#username', text: 'testuser' }, timestamp: '' },
        { type: 'click', data: { selector: '#submit-btn', role: 'button', text: 'Submit' }, timestamp: '' }
      ]
    };
    const refmapOutput = builder.build(episode);
    const issues = RefMapBuilder.validate(refmapOutput);
    assertEqual(issues.length, 0, `Validation: ${issues.join(', ')}`);
    const api = new AutomationAPI(refmapOutput);
    assert(api.refOrder.length > 0, 'Has refs');
  });

  await runTest('G02: Form fill workflow fails gracefully', async () => {
    const rm = makeRefMap({
      ref_title: { priority: ['id'], structural: { id: 'title' } },
      ref_body: { priority: ['id'], structural: { id: 'body' } },
      ref_submit: { priority: ['id'], structural: { id: 'submit' } }
    });
    const api = new AutomationAPI(rm);
    const r1 = await api.fillField('ref_title', 'My Post');
    const r2 = await api.fillField('ref_body', 'Body text');
    const r3 = await api.clickButton('ref_submit');
    assertEqual(r1.success, false, 'Fill title fails');
    assertEqual(r2.success, false, 'Fill body fails');
    assertEqual(r3.success, false, 'Click submit fails');
  });

  await runTest('G03: Verify interaction after fill', async () => {
    const rm = makeRefMap({ ref_input: { priority: ['id'], structural: { id: 'search' } } });
    const api = new AutomationAPI(rm);
    await api.fillField('ref_input', 'query');
    const verify = await api.verifyInteraction('ref_input', { value: 'query' });
    assertEqual(verify.success, false, 'Fails without DOM');
  });

  await runTest('G04: Multi-step workflow with stats', async () => {
    const rm = makeRefMap({
      ref_email: { priority: ['name'], semantic: { name: 'email' } },
      ref_pass: { priority: ['name'], semantic: { name: 'password' } },
      ref_login: { priority: ['text'], semantic: { text: 'Log In' } }
    });
    const api = new AutomationAPI(rm);
    await api.fillField('ref_email', 'user@example.com');
    await api.fillField('ref_pass', 'secret123');
    await api.clickButton('ref_login');
    const stats = api.getStats();
    assertEqual(stats.total, 3, 'Three actions');
    assertEqual(stats.failures, 3, 'All failed (no DOM)');
  });

  await runTest('G05: Dropdown select workflow', async () => {
    const rm = makeRefMap({
      ref_country: { priority: ['id'], structural: { id: 'country' } },
      ref_state: { priority: ['id'], structural: { id: 'state' } }
    });
    const api = new AutomationAPI(rm);
    const r1 = await api.selectOption('ref_country', 'US');
    assertEqual(r1.success, false, 'Fails without DOM');
    assertEqual(r1.action, 'selectOption', 'Correct action');
  });

  await runTest('G06: typeText with shift handling options', async () => {
    const rm = makeRefMap({ ref_msg: { priority: ['placeholder'], semantic: { placeholder: 'Type...' } } });
    const api = new AutomationAPI(rm);
    const result = await api.typeText('ref_msg', 'Hello!', { autoShift: true, delay: 10 });
    assertEqual(result.success, false, 'Fails without DOM');
  });

  await runTest('G07: Error recovery - API remains usable after failures', async () => {
    const rm = makeRefMap({ ref_a: { priority: [] }, ref_b: { priority: [] } });
    const api = new AutomationAPI(rm);
    await api.fillField('ref_a', 'v1');
    await api.clickButton('ref_b');
    await api.typeText('ref_a', 'text');
    assertEqual(api.getStats().total, 3, 'All tracked');
    await api.verifyInteraction('ref_a', { value: 'v1' });
    assertEqual(api.getStats().total, 4, 'Still functional');
  });

  await runTest('G08: Gmail compose pipeline', async () => {
    const builder = new RefMapBuilder();
    const episode = {
      session_id: 'gmail_compose',
      domain: 'mail.google.com',
      actions: [
        { type: 'click', data: { selector: '[data-tooltip="Compose"]', role: 'button' }, timestamp: '' },
        { type: 'click', data: { selector: '[aria-label="To recipients"]' }, timestamp: '' },
        { type: 'type', data: { selector: '[aria-label="To recipients"]', text: 'friend@gmail.com' }, timestamp: '' },
        { type: 'click', data: { selector: '[aria-label="Subject"]' }, timestamp: '' },
        { type: 'type', data: { selector: '[aria-label="Subject"]', text: 'Hello' }, timestamp: '' },
        { type: 'click', data: { selector: '[data-tooltip="Send"]', role: 'button' }, timestamp: '' }
      ]
    };
    const refmapOutput = builder.build(episode);
    const issues = RefMapBuilder.validate(refmapOutput);
    assertEqual(issues.length, 0, `Validation: ${issues.join(', ')}`);
    const api = new AutomationAPI(refmapOutput);
    assertTruthy(api.refOrder.length >= 1, 'Refs extracted');
  });

  await runTest('G09: executeWorkflow with multiple steps', async () => {
    const rm = makeRefMap({
      ref_a: { priority: [] },
      ref_b: { priority: [] }
    });
    const api = new AutomationAPI(rm);
    const workflow = [
      { action: 'fillField', ref_id: 'ref_a', value: 'test', continueOnError: true },
      { action: 'clickButton', ref_id: 'ref_b', continueOnError: true },
      { action: 'verifyInteraction', ref_id: 'ref_a', expected_state: { value: 'test' }, continueOnError: true }
    ];
    const result = await api.executeWorkflow(workflow);
    assertEqual(result.total_steps, 3, 'Three steps');
    assertEqual(result.completed_steps, 3, 'All completed (with continueOnError)');
    assertEqual(result.success, false, 'Overall fails (no DOM)');
  });

  await runTest('G10: executeWorkflow stops on error without continueOnError', async () => {
    const rm = makeRefMap({ ref_a: { priority: [] } });
    const api = new AutomationAPI(rm);
    const workflow = [
      { action: 'fillField', ref_id: 'ref_a', value: 'test' },
      { action: 'clickButton', ref_id: 'ref_a' }
    ];
    const result = await api.executeWorkflow(workflow);
    assertEqual(result.completed_steps, 1, 'Stopped at first error');
  });

  await runTest('G11: getLog returns copy (not mutable reference)', async () => {
    const rm = makeRefMap({});
    const api = new AutomationAPI(rm);
    await api.fillField('ref_a', 'v');
    const log1 = api.getLog();
    log1.push({ fake: true });
    const log2 = api.getLog();
    assert(log2.length < log1.length, 'Original unaffected');
  });

  await runTest('G12: buildWorkflowFromRefMap generates steps', async () => {
    const builder = new RefMapBuilder();
    const episode = {
      session_id: 'e2e',
      actions: [
        { type: 'click', data: { selector: '#login', role: 'button', text: 'Login' }, timestamp: '' },
        { type: 'type', data: { selector: '#user', name: 'username', text: 'admin' }, timestamp: '' },
        { type: 'click', data: { selector: '#go', role: 'button', text: 'Go' }, timestamp: '' }
      ]
    };
    const refmapOutput = builder.build(episode);
    const steps = AutomationAPI.buildWorkflowFromRefMap(refmapOutput);
    assert(Array.isArray(steps), 'Steps is array');
    assert(steps.length > 0, 'Has steps');
  });

  // =====================================================
  // SUMMARY
  // =====================================================
  console.log('\n========================================');
  console.log(`TOTAL: ${testResults.pass + testResults.fail} tests`);
  console.log(`PASS:  ${testResults.pass}`);
  console.log(`FAIL:  ${testResults.fail}`);

  if (testResults.errors.length > 0) {
    console.log('\nFAILED TESTS:');
    for (const err of testResults.errors) {
      console.log(`  [${err.tier}] ${err.name}: ${err.error}`);
    }
  }

  console.log('========================================');
  return testResults;
}

// Run
runAllTests().then(results => {
  if (results.fail > 0) process.exit(1);
});
