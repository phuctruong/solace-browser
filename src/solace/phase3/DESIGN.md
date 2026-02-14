# Phase 3: Reference Resolution - RefMap Builder

> **Status:** COMPLETE
> **Tests:** 100/100 passing
> **Auth:** 65537

## Overview

Phase 3 implements semantic and structural selector extraction (RefMap Builder) to extract deterministic references to DOM elements for reliable replay during Phase 4 automation.

## Key Components

### RefMapBuilder (refmap_builder.py)

Extracts dual identifiers for every interactive element:

- **Semantic ID**: User-facing identifiers (aria-label, data-testid, role, text content, placeholder)
- **Structural ID**: Technical identifiers (CSS selector, XPath, ref_path using tag:index notation)
- **Reliability Scoring**: Calibrated scores for each selector type (0.98 data-testid down to 0.75 ref_path)
- **Resolution Strategy**: Automatic ranking of selectors by reliability and performance

### Features

1. **Deterministic Extraction**: SHA-256 hashing of ref_ids ensures reproducible references
2. **Phase B Compatibility**: Output format matches episode structure from Phase 2
3. **Selector Diversification**: Multiple selectors per element, ranked by reliability
4. **Example Episodes**: 5 real-world examples (Gmail, Reddit, GitHub, signup form, multi-page nav)

## Architecture

```
Episode (from Phase 2)
        ↓
RefMapBuilder.extract_semantic()   →  Semantic Selectors
RefMapBuilder.extract_structural() →  Structural Selectors
        ↓
RefMap with:
  - ref_id (deterministic hash)
  - semantic/structural selectors
  - reliability score
  - resolution strategy
        ↓
Phase 4: Use RefMap for element re-identification during replay
```

## Test Coverage

- **100 tests** covering selector extraction, reliability scoring, resolution strategy
- RefMap builder determinism verified
- Example RefMaps match expected outputs
- Phase B integration tested

## Integration with Phase 4

Phase 4 uses RefMap selectors to:
1. Parse recipe action: "click #button-submit"
2. Look up RefMap: Find element via semantic selector first
3. Fallback chain: semantic → structural → xpath → css → ref_path
4. Execute action on resolved element

## Success Criteria

✅ 100/100 tests passing
✅ All RefMaps structurally valid (semantic + structural selectors)
✅ Reliability scores calibrated per selector type
✅ Phase 2 episode examples extract without errors
✅ Zero defects on verification ladder (641 → 274177 → 65537)
