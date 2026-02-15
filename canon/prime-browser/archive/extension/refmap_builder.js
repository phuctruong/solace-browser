/**
 * Solace Browser Phase 3: RefMap Builder
 *
 * Extracts RefMap (reference map) from recorded episodes.
 * Each RefMap entry maps a unique element to its semantic + structural
 * selectors with reliability scores and resolution strategies.
 *
 * Input:  Episode JSON from Phase 2 recording
 * Output: RefMap JSON for Phase 4 replay
 *
 * Auth: 65537 | Northstar: Phuc Forecast
 * Version: 0.1.0
 */

class RefMapBuilder {
  constructor() {
    this.refmap = {};
    this.refs = [];
    this.episode = null;
    this.stats = {
      total_refs: 0,
      action_count: 0,
      pages: 1,
      semantic_only_count: 0,
      structural_only_count: 0,
      complete_count: 0
    };
  }

  /**
   * Main entry point: build RefMap from episode.
   * @param {Object} episode - Phase 2 episode JSON
   * @returns {Object} Complete RefMap with stats and metadata
   */
  build(episode) {
    if (!episode || typeof episode !== 'object') {
      throw new Error('Episode must be a non-null object');
    }

    this.episode = episode;
    this.refmap = {};
    this.refs = [];

    const actions = episode.actions || [];

    // Process each action
    actions.forEach((action, idx) => {
      this.processAction(action, idx);
    });

    return this.getRefMap();
  }

  /**
   * Process a single action from the episode.
   * Extracts semantic and structural selectors, generates ref_id,
   * deduplicates against existing refs.
   *
   * @param {Object} action - Episode action object
   * @param {number} actionIndex - Index of action in episode
   */
  processAction(action, actionIndex) {
    if (!action || typeof action !== 'object') {
      return;
    }

    const actionType = action.type || 'unknown';
    const actionData = action.data || {};
    const timestamp = action.timestamp || '';

    // Extract target info from the action
    const semantic = this.extractSemanticFromAction(actionData, actionType);
    const structural = this.extractStructuralFromAction(actionData, actionType);

    // Skip actions without any target (e.g., pure navigate with just a URL)
    const hasSemantic = this.hasValues(semantic);
    const hasStructural = this.hasValues(structural);

    // For navigate actions, URL is the target - always create a ref
    if (actionType === 'navigate' || actionType === 'NAVIGATE') {
      const url = actionData.url || '';
      if (url) {
        const ref_id = this.generateRefId({ text: url });
        if (this.refmap[ref_id]) {
          this.refmap[ref_id].actions.push({
            action_index: actionIndex,
            action_type: actionType,
            action_timestamp: timestamp
          });
          return;
        }
        this.refmap[ref_id] = {
          semantic: { text: url, role: null, aria_label: null, data_testid: null, data_qa: null, placeholder: null, alt: null, title: null, name: null, type: null, for_attr: null, aria_describedby: null },
          structural: { css_selector: null, xpath: null, ref_path: null, tag: null, id: null, nth_child: null },
          priority: ['text'],
          reliability: { text: 0.80 },
          actions: [{ action_index: actionIndex, action_type: actionType, action_timestamp: timestamp }],
          resolution_strategy: 'url (navigate action)'
        };
        this.refs.push(ref_id);
        return;
      }
    }

    if (!hasSemantic && !hasStructural) {
      return;
    }

    // Generate ref_id from semantic identifiers
    const ref_id = this.generateRefId(semantic);

    // Dedup: if ref_id already exists, just add the action reference
    if (this.refmap[ref_id]) {
      this.refmap[ref_id].actions.push({
        action_index: actionIndex,
        action_type: actionType,
        action_timestamp: timestamp
      });
      return;
    }

    // Create new ref entry
    const ref_entry = {
      semantic: this.normalizeSemantic(semantic),
      structural: this.normalizeStructural(structural),
      priority: this.calculatePriority(semantic, structural),
      reliability: this.scoreReliability(semantic, structural),
      actions: [{
        action_index: actionIndex,
        action_type: actionType,
        action_timestamp: timestamp
      }],
      resolution_strategy: this.determineStrategy(semantic, structural)
    };

    this.refmap[ref_id] = ref_entry;
    this.refs.push(ref_id);
  }

  /**
   * Extract semantic selectors from action data.
   * @param {Object} data - Action data object
   * @param {string} actionType - Action type
   * @returns {Object} Semantic selector fields
   */
  extractSemanticFromAction(data, actionType) {
    const semantic = {};

    // From target/reference object
    const target = data.target || {};
    const reference = data.reference || {};

    if (typeof reference === 'object' && reference !== null) {
      semantic.aria_label = reference.aria_label || reference.ariaLabel || reference.name || null;
      semantic.role = reference.role || null;
    } else if (typeof reference === 'string') {
      semantic.text = reference;
    }

    // Direct fields from action data
    semantic.aria_label = semantic.aria_label || data['aria-label'] || data.ariaLabel || null;
    semantic.aria_describedby = data['aria-describedby'] || data.ariaDescribedby || null;
    semantic.data_testid = data['data-testid'] || data.testId || data.dataTestid || null;
    semantic.data_qa = data['data-qa'] || data.dataQa || null;
    semantic.role = semantic.role || data.role || null;
    semantic.placeholder = data.placeholder || null;
    semantic.alt = data.alt || null;
    semantic.title = data.title || null;
    semantic.text = semantic.text || data.text || data.value || null;
    semantic.name = data.name || null;
    semantic.type = data.type || null;
    semantic.for_attr = data['for'] || data.for_attr || null;

    // From selector if it looks semantic
    const selector = data.selector || '';
    if (selector) {
      this.enrichSemanticFromSelector(semantic, selector);
    }

    return semantic;
  }

  /**
   * Parse CSS/XPath selectors to extract embedded semantic info.
   * @param {Object} semantic - Semantic object to enrich
   * @param {string} selector - CSS or XPath selector string
   */
  enrichSemanticFromSelector(semantic, selector) {
    // aria-label from selector: [aria-label="..."]
    const ariaMatch = selector.match(/\[aria-label=["']([^"']+)["']\]/);
    if (ariaMatch && !semantic.aria_label) {
      semantic.aria_label = ariaMatch[1];
    }

    // data-testid from selector: [data-testid="..."]
    const testidMatch = selector.match(/\[data-testid=["']([^"']+)["']\]/);
    if (testidMatch && !semantic.data_testid) {
      semantic.data_testid = testidMatch[1];
    }

    // data-tooltip from selector: [data-tooltip="..."]
    const tooltipMatch = selector.match(/\[data-tooltip=["']([^"']+)["']\]/);
    if (tooltipMatch && !semantic.aria_label) {
      semantic.aria_label = tooltipMatch[1];
    }

    // role from selector: [role="..."]
    const roleMatch = selector.match(/\[role=["']([^"']+)["']\]/);
    if (roleMatch && !semantic.role) {
      semantic.role = roleMatch[1];
    }

    // placeholder from selector: [placeholder="..."]
    const placeholderMatch = selector.match(/\[placeholder=["']([^"']+)["']\]/);
    if (placeholderMatch && !semantic.placeholder) {
      semantic.placeholder = placeholderMatch[1];
    }

    // name from selector: [name="..."]
    const nameMatch = selector.match(/\[name=["']([^"']+)["']\]/);
    if (nameMatch && !semantic.name) {
      semantic.name = nameMatch[1];
    }
  }

  /**
   * Extract structural selectors from action data.
   * @param {Object} data - Action data object
   * @param {string} actionType - Action type
   * @returns {Object} Structural selector fields
   */
  extractStructuralFromAction(data, actionType) {
    const structural = {};

    const selector = data.selector || data.target || '';

    if (typeof selector === 'string' && selector.length > 0) {
      // Classify the selector
      if (selector.startsWith('xpath=')) {
        structural.xpath = selector.replace('xpath=', '');
      } else if (selector.startsWith('//') || selector.startsWith('(//')) {
        structural.xpath = selector;
      } else {
        structural.css_selector = selector;
      }
    }

    structural.ref_path = data.ref_path || data.refPath || null;
    structural.tag = data.tag || data.tagName || null;
    structural.id = data.id || null;
    structural.nth_child = data.nth_child !== undefined ? data.nth_child : (data.nthChild !== undefined ? data.nthChild : null);

    // Extract ID from CSS selector if present: #some-id
    if (structural.css_selector && !structural.id) {
      const idMatch = structural.css_selector.match(/^#([a-zA-Z0-9_-]+)$/);
      if (idMatch) {
        structural.id = idMatch[1];
      }
    }

    return structural;
  }

  /**
   * Generate deterministic ref_id from semantic identifiers.
   * Uses the most stable identifiers available.
   *
   * @param {Object} semantic - Semantic selector fields
   * @returns {string} Deterministic ref_id like "ref_a1b2c3d4"
   */
  generateRefId(semantic) {
    const key = [
      semantic.aria_label,
      semantic.data_testid,
      semantic.role,
      semantic.text,
      semantic.alt,
      semantic.aria_describedby,
      semantic.placeholder,
      semantic.name,
      semantic.type,
      semantic.for_attr
    ].filter(Boolean).join('|') || 'generic';

    const hash = this.simpleHash(key);
    return `ref_${hash.substring(0, 8)}`;
  }

  /**
   * Simple deterministic hash function.
   * NOT cryptographic - for ref_id generation only.
   *
   * @param {string} str - Input string
   * @returns {string} Hex hash string
   */
  simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(16).padStart(8, '0');
  }

  /**
   * Normalize semantic object: ensure all fields exist with null defaults.
   * @param {Object} semantic - Raw semantic fields
   * @returns {Object} Normalized semantic with all fields
   */
  normalizeSemantic(semantic) {
    return {
      aria_label: semantic.aria_label || null,
      aria_describedby: semantic.aria_describedby || null,
      data_testid: semantic.data_testid || null,
      data_qa: semantic.data_qa || null,
      role: semantic.role || null,
      placeholder: semantic.placeholder || null,
      alt: semantic.alt || null,
      title: semantic.title || null,
      text: semantic.text || null,
      name: semantic.name || null,
      type: semantic.type || null,
      for_attr: semantic.for_attr || null
    };
  }

  /**
   * Normalize structural object: ensure all fields exist with null defaults.
   * @param {Object} structural - Raw structural fields
   * @returns {Object} Normalized structural with all fields
   */
  normalizeStructural(structural) {
    return {
      css_selector: structural.css_selector || null,
      xpath: structural.xpath || null,
      ref_path: structural.ref_path || null,
      tag: structural.tag || null,
      id: structural.id || null,
      nth_child: structural.nth_child !== undefined && structural.nth_child !== null ? structural.nth_child : null
    };
  }

  /**
   * Calculate selector priority (order to try during replay).
   * Ordered from most reliable to least reliable.
   *
   * @param {Object} semantic - Semantic selectors
   * @param {Object} structural - Structural selectors
   * @returns {string[]} Ordered list of available selector strategies
   */
  calculatePriority(semantic, structural) {
    const priority = [];

    // Semantic selectors (most stable, try first)
    if (semantic.data_testid) priority.push('data_testid');
    if (semantic.aria_label) priority.push('aria_label');
    if (semantic.aria_describedby) priority.push('aria_describedby');
    if (semantic.role) priority.push('role');
    if (semantic.data_qa) priority.push('data_qa');
    if (semantic.alt) priority.push('alt');
    if (semantic.placeholder) priority.push('placeholder');
    if (semantic.name) priority.push('name');
    if (semantic.text) priority.push('text');

    // Structural selectors (less stable, try last)
    if (structural.id) priority.push('id');
    if (structural.css_selector) priority.push('css_selector');
    if (structural.xpath) priority.push('xpath');
    if (structural.ref_path) priority.push('ref_path');

    return priority;
  }

  /**
   * Score reliability of each available selector.
   * Returns a map of selector_type -> reliability_score (0.0 to 1.0).
   *
   * Reliability scores based on DOM stability research:
   *   - data_testid: 0.98 (purpose-built for testing, rarely changes)
   *   - id: 0.96 (stable but can conflict)
   *   - aria_label: 0.95 (accessibility, stable across deploys)
   *   - aria_describedby: 0.93 (less common but stable)
   *   - data_qa: 0.92 (QA-specific)
   *   - css_selector: 0.92 (structural, depends on DOM)
   *   - role: 0.90 (semantic, stable)
   *   - alt: 0.88 (image alt text)
   *   - placeholder: 0.85 (input hints)
   *   - xpath: 0.85 (fragile to DOM changes)
   *   - name: 0.83 (form names)
   *   - text: 0.80 (content changes frequently)
   *   - ref_path: 0.75 (custom path, fallback)
   *
   * @param {Object} semantic - Semantic selectors
   * @param {Object} structural - Structural selectors
   * @returns {Object} Map of available selector types to reliability scores
   */
  scoreReliability(semantic, structural) {
    const scores = {};

    if (semantic.data_testid) scores.data_testid = 0.98;
    if (structural.id) scores.id = 0.96;
    if (semantic.aria_label) scores.aria_label = 0.95;
    if (semantic.aria_describedby) scores.aria_describedby = 0.93;
    if (semantic.data_qa) scores.data_qa = 0.92;
    if (structural.css_selector) scores.css_selector = 0.92;
    if (semantic.role) scores.role = 0.90;
    if (semantic.alt) scores.alt = 0.88;
    if (semantic.placeholder) scores.placeholder = 0.85;
    if (structural.xpath) scores.xpath = 0.85;
    if (semantic.name) scores.name = 0.83;
    if (semantic.text) scores.text = 0.80;
    if (structural.ref_path) scores.ref_path = 0.75;

    return scores;
  }

  /**
   * Determine the best resolution strategy for replay.
   * Returns a human-readable description of the recommended approach.
   *
   * @param {Object} semantic - Semantic selectors
   * @param {Object} structural - Structural selectors
   * @returns {string} Resolution strategy description
   */
  determineStrategy(semantic, structural) {
    if (semantic.data_testid) return 'data_testid (highest reliability)';
    if (structural.id) return 'id (DOM identifier)';
    if (semantic.aria_label) return 'aria_label (semantic, stable)';
    if (semantic.aria_describedby) return 'aria_describedby (semantic)';
    if (semantic.data_qa) return 'data_qa (QA identifier)';
    if (semantic.role && semantic.text) return 'role+text (semantic combo)';
    if (semantic.role) return 'role (semantic)';
    if (structural.css_selector) return 'css_selector (structural)';
    if (structural.xpath) return 'xpath (absolute path)';
    if (semantic.text) return 'text (content match)';
    if (semantic.placeholder) return 'placeholder (input hint)';
    if (semantic.name) return 'name (form field)';
    if (structural.ref_path) return 'ref_path (fallback)';
    return 'none (no selectors available)';
  }

  /**
   * Check if an object has any non-null/non-empty values.
   * @param {Object} obj - Object to check
   * @returns {boolean} True if at least one value is truthy
   */
  hasValues(obj) {
    if (!obj || typeof obj !== 'object') return false;
    return Object.values(obj).some(v => v !== null && v !== undefined && v !== '');
  }

  /**
   * Assemble the final RefMap output with metadata and stats.
   * @returns {Object} Complete RefMap JSON
   */
  getRefMap() {
    const refmapEntries = this.refmap;
    const refIds = this.refs;

    // Compute stats
    let semantic_only = 0;
    let structural_only = 0;
    let complete = 0;

    for (const ref_id of refIds) {
      const entry = refmapEntries[ref_id];
      if (!entry) continue;

      const hasSem = this.hasValues(entry.semantic);
      const hasStr = this.hasValues(entry.structural);

      if (hasSem && hasStr) {
        complete++;
      } else if (hasSem) {
        semantic_only++;
      } else if (hasStr) {
        structural_only++;
      }
    }

    return {
      version: '0.1.0',
      episode_id: this.episode.session_id || this.episode.episode_id || '',
      url_source: this.episode.url_start || this.episode.domain || '',
      generated_at: new Date().toISOString(),
      refmap: refmapEntries,
      ref_order: refIds,
      stats: {
        total_refs: refIds.length,
        action_count: (this.episode.actions || []).length,
        pages: this._countPages(),
        semantic_only_count: semantic_only,
        structural_only_count: structural_only,
        complete_count: complete
      }
    };
  }

  /**
   * Count unique pages from navigate actions.
   * @returns {number} Number of unique page navigations
   */
  _countPages() {
    const actions = (this.episode && this.episode.actions) || [];
    const urls = new Set();
    for (const action of actions) {
      if ((action.type === 'navigate' || action.type === 'NAVIGATE') && action.data && action.data.url) {
        urls.add(action.data.url);
      }
    }
    return Math.max(1, urls.size);
  }

  /**
   * Validate a RefMap for completeness and consistency.
   * Returns an array of validation issues (empty = valid).
   *
   * @param {Object} refmapOutput - RefMap output from build()
   * @returns {string[]} List of validation issues
   */
  static validate(refmapOutput) {
    const issues = [];

    if (!refmapOutput) {
      issues.push('RefMap output is null/undefined');
      return issues;
    }

    if (!refmapOutput.version) {
      issues.push('Missing version field');
    }

    if (!refmapOutput.refmap || typeof refmapOutput.refmap !== 'object') {
      issues.push('Missing or invalid refmap field');
      return issues;
    }

    if (!refmapOutput.stats || typeof refmapOutput.stats !== 'object') {
      issues.push('Missing or invalid stats field');
    }

    const refmap = refmapOutput.refmap;
    const refIds = Object.keys(refmap);

    for (const ref_id of refIds) {
      const entry = refmap[ref_id];

      if (!ref_id.startsWith('ref_')) {
        issues.push(`Invalid ref_id format: ${ref_id}`);
      }

      if (!entry.semantic || typeof entry.semantic !== 'object') {
        issues.push(`${ref_id}: missing semantic field`);
      }

      if (!entry.structural || typeof entry.structural !== 'object') {
        issues.push(`${ref_id}: missing structural field`);
      }

      if (!Array.isArray(entry.priority)) {
        issues.push(`${ref_id}: priority must be an array`);
      }

      if (!entry.reliability || typeof entry.reliability !== 'object') {
        issues.push(`${ref_id}: missing reliability scores`);
      }

      if (!Array.isArray(entry.actions) || entry.actions.length === 0) {
        issues.push(`${ref_id}: must have at least one action reference`);
      }

      if (typeof entry.resolution_strategy !== 'string') {
        issues.push(`${ref_id}: resolution_strategy must be a string`);
      }

      // Validate reliability scores are in range [0, 1]
      if (entry.reliability) {
        for (const [key, score] of Object.entries(entry.reliability)) {
          if (typeof score !== 'number' || score < 0 || score > 1) {
            issues.push(`${ref_id}: invalid reliability score for ${key}: ${score}`);
          }
        }
      }
    }

    // Validate stats consistency
    if (refmapOutput.stats) {
      const expectedTotal = refIds.length;
      if (refmapOutput.stats.total_refs !== expectedTotal) {
        issues.push(`Stats total_refs (${refmapOutput.stats.total_refs}) != actual refs (${expectedTotal})`);
      }
    }

    return issues;
  }
}

// Export for Node.js / test environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { RefMapBuilder };
}
