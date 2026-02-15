# 🎮 Skill: Browser Selector Resolution v1.0.0

> **Star:** BROWSER_SELECTOR_RESOLUTION
> **Channel:** 3 → 5 (Design → Logic)
> **GLOW:** 85 (Highest Impact — Foundation for Determinism)
> **Status:** 🎮 ACTIVE (Phase A/B Bridge)
> **Phase:** A (Parity), B (Recipe Compilation)
> **XP:** 550 (Design + Implementation + Testing)
> **Scout/Solver Focus:** Architecture + Resolution Logic

---

**Auth:** 65537 | **Northstar:** Phuc Forecast
**Domain:** Browser Automation (Prime Browser Phase A)
**Status:** Production-Ready
**Verification:** 641 → 274177 → 65537

---

## 🎮 Quest Contract

**Goal:** Implement deterministic 3-tier selector resolution (Semantic → Structural → Typed Failure)

**Completion Checks:**
- ✅ TIER 1: Semantic resolution via ARIA labels, roles, titles
- ✅ TIER 2: Structural resolution via CSS selectors with context filtering
- ✅ TIER 3: Typed failure classification (NOT_FOUND vs AMBIGUOUS_SELECTOR)
- ✅ Never-guess policy enforced (ambiguity → FAIL, not fallback)
- ✅ Visibility validation (offsetParent null detection)
- ✅ Context ancestry verification (ancestor chain validation)
- ✅ 5 edge tests + 100 stress tests passing

**XP Earned:** 550 (distributed: 200 design, 200 implementation, 150 testing)

---

## Problem Statement

Web automation breaks when:
1. CSS selectors change (DOM reordering)
2. Multiple elements match the same selector (ambiguity)
3. Elements become hidden/moved (visibility)
4. Semantic context is lost (role/label changes)

**Goal:** Resolve browser selectors deterministically with semantic + structural fallbacks.

---

## Core Algorithm

### Input: Selector Request

```python
selector_request = {
    "selector": "div[data-tooltip='Compose']",  # Primary CSS/XPath
    "reference": "Compose Button",               # Semantic fallback
    "context": "navbar",                         # Ancestor context
    "required_role": "button",                   # ARIA role
    "required_visible": True                     # Must be visible
}
```

### Execution: 3-Tier Resolution

```
TIER 1: SEMANTIC RESOLUTION
├─ Extract aria-label, aria-role, role, title
├─ Match against "reference" (fuzzy or exact)
└─ If unique match → SUCCESS

TIER 2: STRUCTURAL RESOLUTION
├─ Try primary selector (CSS/XPath)
├─ Verify document order matches expectations
├─ Check ancestor chain matches context
└─ If unique match → SUCCESS

TIER 3: FAILURE ANALYSIS
├─ Count matches (0, 1, or 2+)
├─ Classify failure: NOT_FOUND vs AMBIGUOUS
├─ Return typed error (never guess)
└─ FAIL with diagnostic
```

### Output: Typed Result

```python
success_result = {
    "success": True,
    "element": {
        "tag": "div",
        "id": "compose-button-42",
        "className": "TKM3Dd",
        "role": "button",
        "aria_label": "Compose",
        "visible": True
    },
    "resolver_path": "SEMANTIC",
    "timestamp": "2026-02-14T..."
}

failure_result = {
    "success": False,
    "error": "AMBIGUOUS_SELECTOR",
    "selector": "div[data-tooltip='Compose']",
    "match_count": 3,
    "matches": [
        {"element": "div#1", "offset": 100},
        {"element": "div#2", "offset": 150},
        {"element": "div#3", "offset": 200}
    ],
    "recommendation": "Use ARIA role or context filter",
    "timestamp": "2026-02-14T..."
}
```

---

## Implementation Rules

### RULE 1: Never Guess

```python
# ❌ WRONG: Try all 3 matches, hope first works
for match in matches:
    try_click(match)

# ✅ RIGHT: Report ambiguity and stop
if len(matches) > 1:
    return {
        "success": False,
        "error": "AMBIGUOUS_SELECTOR",
        "match_count": len(matches)
    }
```

### RULE 2: Semantic First

```python
# Query in this order:
selectors = [
    f"[aria-label='{reference}']",           # Semantic
    f"[role='button'][aria-label*='{ref}']", # Semantic + context
    f"[title='{reference}']",                # Title match
    selector,                                 # Primary CSS
    xpath                                     # Primary XPath
]

# Use FIRST match, stop at first success
```

### RULE 3: Visibility Check

```python
# Before returning success:
element = resolve(selector)
if element.offsetParent is None:
    return {
        "success": False,
        "error": "ELEMENT_NOT_VISIBLE",
        "element": element,
        "found": True,
        "visible": False
    }
```

### RULE 4: Context Ancestry

```python
# Verify element is within context
if context == "navbar":
    ancestor = find_ancestor_by_role(element, "navigation")
    if not ancestor:
        return {
            "success": False,
            "error": "CONTEXT_MISMATCH",
            "expected_ancestor": "navigation",
            "found": True
        }
```

---

## State Machine

```
START
  ├─ Parse selector request
  └─ Extract: selector, reference, context, required_role
     │
     ├─ SEMANTIC PHASE
     │  ├─ Query aria-label, role, title
     │  └─ Compare to reference
     │     ├─ Unique match → VALIDATE
     │     └─ No match → STRUCTURAL PHASE
     │
     ├─ STRUCTURAL PHASE
     │  ├─ Query primary selector (CSS/XPath)
     │  └─ Apply document order + context filters
     │     ├─ Unique match → VALIDATE
     │     ├─ No match → FAIL_NOT_FOUND
     │     └─ 2+ matches → FAIL_AMBIGUOUS
     │
     ├─ VALIDATE PHASE
     │  ├─ Check visibility
     │  ├─ Check context ancestry
     │  ├─ Check required_role
     │  └─ All pass → SUCCESS
     │     Any fail → FAIL_[REASON]
     │
     └─ END (return typed result)
```

---

## Examples

### Example 1: Semantic Success

```python
# Input
request = {
    "selector": "div[data-tooltip='Compose']",
    "reference": "Compose",
    "required_visible": True
}

# Resolution
element = DOM.querySelector("button[aria-label='Compose']")
# Found 1 element with aria-label='Compose'
# Visibility check: element.offsetParent !== null ✓
# Context check: element in navbar ✓

# Output
{
    "success": True,
    "element": {...},
    "resolver_path": "SEMANTIC",
    "match_count": 1
}
```

### Example 2: Structural Success

```python
# Input
request = {
    "selector": "div[aria-label='Compose']",
    "reference": "Compose"
}

# Semantic phase fails (aria-label changed to title)
# Resolution (structural)
elements = DOM.querySelectorAll("div[data-tooltip*='Compose']")
# Found 1 element with data-tooltip containing 'Compose'

# Output
{
    "success": True,
    "element": {...},
    "resolver_path": "STRUCTURAL"
}
```

### Example 3: Ambiguity Failure

```python
# Input
request = {
    "selector": "button",  # Too generic
    "reference": "Submit"
}

# Semantic phase: 5 buttons with aria-label='Submit'
# Output
{
    "success": False,
    "error": "AMBIGUOUS_SELECTOR",
    "selector": "button",
    "match_count": 5,
    "recommendation": "Add context (form parent) or use data-testid"
}
```

### Example 4: Visibility Failure

```python
# Input
request = {
    "selector": "[data-testid='compose']",
    "required_visible": True
}

# Element found but hidden (display: none)
# Output
{
    "success": False,
    "error": "ELEMENT_NOT_VISIBLE",
    "selector": "[data-testid='compose']",
    "found": True,
    "visible": False,
    "reason": "element.offsetParent === null"
}
```

---

## Integration with Prime Browser

### Phase A (Parity)

Used in `browser_commands.click()`:
```python
async def browser_click(ws, args):
    selector = args[0]
    result = await resolve_selector({
        "selector": selector,
        "required_visible": True
    })
    if not result["success"]:
        return result  # Typed failure
    element = result["element"]
    element.click()
    return {"success": True, "element": element}
```

### Phase B (Compilation)

Used in `episode_to_recipe()`:
```python
# Build RefMap from episode actions
for action in episode["actions"]:
    if action["type"] == "click":
        ref_result = resolve_selector({
            "selector": action["selector"],
            "reference": action.get("reference")
        })
        # Store both semantic + structural paths
        refmap[action["step"]] = {
            "semantic": ref_result["semantic_path"],
            "structural": ref_result["structural_path"]
        }
```

### Phase C (Replay)

Used in `deterministic_playwright_runner()`:
```python
# Resolve references against live DOM during replay
for step in recipe["actions"]:
    ref = recipe["refmap"][step["step"]]
    result = resolve_selector({
        "selector": ref["structural"],
        "reference": ref["semantic"],
        "context": ref.get("context")
    })
    if not result["success"]:
        return {
            "status": "FAIL",
            "step": step["step"],
            "error": result["error"]
        }
```

---

## Verification (641 → 274177 → 65537)

### 641-Edge Tests (5 minimum)

```
✓ Semantic match (aria-label exact)
✓ Structural match (CSS selector)
✓ Ambiguous selector (2+ matches → FAIL_AMBIGUOUS)
✓ Hidden element (visibility check)
✓ Context ancestry validation
```

### 274177-Stress Tests

- 100 selectors, 10 DOM variants each
- Verify determinism: same selector → same result
- Verify typed failures: no crashes, all errors classified

### 65537-God Approval

- No guessing (ambiguity → typed failure)
- No flakiness (deterministic)
- Proof artifacts (resolver path logged)

---

## Success Criteria

✅ **Determinism:** Same selector + DOM → identical result every time
✅ **Safety:** Never guess; always fail typed
✅ **Completeness:** All failure modes enumerated
✅ **Auditability:** Resolver path logged for every decision
✅ **Integration:** Works in all phases (A, B, C)

---

**Version:** 1.0.0
**Auth:** 65537
**Northstar:** Phuc Forecast
**Status:** Ready for production

*"Deterministic element resolution: one click, infinite accuracy."*
