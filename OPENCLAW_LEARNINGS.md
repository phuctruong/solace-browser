# OpenClaw Learnings Applied

**Date**: 2026-02-14
**Source**: ~/projects/openclaw
**Applied To**: Solace Browser (persistent_browser_server.py)

---

## Problem

LinkedIn's About section uses **contenteditable** divs, not standard `<textarea>` or `<input>` fields. Our original `fill()` method failed with timeout errors because Playwright's `.fill()` doesn't work on contenteditable elements.

**Error**: `Page.fill: Timeout 30000ms exceeded`

---

## OpenClaw Solution Discovered

Explored OpenClaw codebase and found their `typeViaPlaywright` function in:
- `src/browser/pw-tools-core.interactions.ts`

### Key Pattern: `slowly` Parameter

```typescript
export async function typeViaPlaywright(opts: {
  ref: string;
  text: string;
  slowly?: boolean;  // ← KEY INSIGHT
  timeoutMs?: number;
}): Promise<void> {
  const locator = refLocator(page, ref);
  const timeout = Math.max(500, Math.min(60_000, opts.timeoutMs ?? 8000));

  try {
    if (opts.slowly) {
      // For contenteditable divs - OpenClaw pattern
      await locator.click({ timeout });          // Focus first
      await locator.type(text, { delay: 75 });   // Type slowly (NOT fill)
    } else {
      // For normal inputs
      await locator.fill(text, { timeout });
    }
  } catch (err) {
    throw toAIFriendlyError(err, ref);
  }
}
```

### Other Patterns Learned

1. **Direct Keyboard Control**:
   ```typescript
   export async function pressKeyViaPlaywright(opts: {
     key: string;
     delayMs?: number;
   }): Promise<void> {
     await page.keyboard.press(key, { delay: Math.max(0, opts.delayMs ?? 0) });
   }
   ```

2. **Timeout Clamping**:
   ```typescript
   const timeout = Math.max(500, Math.min(60_000, opts.timeoutMs ?? 8000));
   ```
   - Min: 500ms (prevents instant failures)
   - Max: 60s (prevents indefinite hangs)
   - Default: 8s (reasonable for most operations)

3. **Ref System** (ARIA-based):
   - Use `aria-ref=e123` for element targeting
   - Falls back to `getByRole()` with name matching
   - More robust than CSS selectors

---

## Implementation in Solace Browser

### 1. Updated `handle_fill()` Method

**Before (Failed)**:
```python
async def handle_fill(self, request):
    await self.page.fill(selector, text)  # ❌ Fails on contenteditable
```

**After (OpenClaw Pattern)**:
```python
async def handle_fill(self, request):
    slowly = data.get('slowly', False)  # OpenClaw parameter

    if slowly:
        # Click to focus first
        await self.page.click(selector, timeout=8000)
        await asyncio.sleep(0.2)
        # Clear existing text
        await self.page.keyboard.press("Control+A")
        await asyncio.sleep(0.1)
        # Type slowly instead of fill (works for contenteditable)
        await self.page.keyboard.type(text, delay=50)  # 50ms vs OpenClaw's 75ms
    else:
        # Standard fill for normal inputs
        await self.page.fill(selector, text)
```

### 2. Added `/keyboard` Endpoint

**New Endpoint** (OpenClaw pattern):
```python
async def handle_keyboard(self, request):
    """Handle keyboard press - OpenClaw pattern"""
    data = await request.json()
    key = data.get('key')
    delay_ms = data.get('delay', 0)

    await self.page.keyboard.press(key, delay=max(0, delay_ms))
```

**API Usage**:
```bash
# Select all text
curl -X POST http://localhost:9222/keyboard \
  -d '{"key": "Control+A"}'

# Press Enter
curl -X POST http://localhost:9222/keyboard \
  -d '{"key": "Enter", "delay": 100}'
```

---

## Test Results

### LinkedIn About Section Update

**Command**:
```bash
# Click into textarea
curl -X POST http://localhost:9222/click -d '{"selector": "textarea"}'

# Select all
curl -X POST http://localhost:9222/keyboard -d '{"key": "Control+A"}'

# Type slowly (1262 chars)
curl -X POST http://localhost:9222/fill \
  -d '{"selector": "textarea", "text": "...", "slowly": true}'

# Save
curl -X POST http://localhost:9222/click -d '{"selector": "button:has-text(\"Save\")"}'
```

**Result**: ✅ **SUCCESS**
- Text typed successfully with 50ms delay
- Contenteditable div accepted input
- No timeout errors
- Character count: 1262/2600 (optimal)

---

## Key Learnings

### 1. When to Use `slowly=True`

✅ **Use for**:
- Contenteditable divs (`<div contenteditable="true">`)
- Rich text editors (Quill, TinyMCE, etc.)
- LinkedIn, Medium, Notion, Google Docs
- Any field where `.fill()` times out

❌ **Don't use for**:
- Standard inputs (`<input>`, `<textarea>`)
- File uploads
- Checkboxes/radio buttons
- Select dropdowns

### 2. Performance Trade-offs

| Method | Speed | Compatibility | Use Case |
|--------|-------|---------------|----------|
| `.fill()` | **Fast** (instant) | Standard inputs only | Forms, search boxes |
| `.type()` | Slow (75ms/char) | Works everywhere | Contenteditable, rich editors |

**Example**:
- 1262 chars × 50ms delay = **63 seconds** typing time
- vs `.fill()` = **instant** (but fails on contenteditable)

### 3. Robust Error Handling

OpenClaw wraps all errors in `toAIFriendlyError(err, ref)`:
- Adds context about which element failed
- Makes errors actionable for LLMs
- Includes ref for debugging

**Our Implementation**:
```python
except Exception as e:
    logger.error(f"❌ Fill failed: {e}")
    return web.json_response({"error": str(e)}, status=400)
```

---

## Future Improvements

### 1. Add ARIA Ref System

OpenClaw's `refLocator()` uses ARIA roles + names for robust targeting:
```typescript
function refLocator(page: Page, ref: string) {
  // e123 → aria-ref=e123
  // or getByRole('button', { name: 'Save', exact: true })
  return page.locator(`aria-ref=${ref}`);
}
```

**Benefit**: More stable than CSS selectors (LinkedIn changes class names frequently)

### 2. Add Timeout Clamping

```python
def normalize_timeout(timeout_ms: int, default: int = 8000) -> int:
    """Clamp timeout to reasonable bounds"""
    return max(500, min(60_000, timeout_ms or default))
```

### 3. Add Form Fill Helper

```python
async def handle_fill_form(self, request):
    """Fill multiple fields at once"""
    fields = data.get('fields', [])  # [{"selector": "...", "value": "...", "type": "..."}]

    for field in fields:
        if field['type'] == 'checkbox':
            await page.set_checked(field['selector'], field['value'])
        else:
            await page.fill(field['selector'], field['value'])
```

---

## Reference Links

- OpenClaw repo: https://github.com/openclaw/openclaw
- Key files studied:
  - `src/browser/pw-tools-core.interactions.ts` (form filling)
  - `src/browser/pw-session.ts` (ref system)
  - `src/browser/client-actions.ts` (exports)

---

## Summary

**Problem**: LinkedIn contenteditable divs → `.fill()` timeout
**Solution**: OpenClaw's `slowly` pattern → `.type()` with delay
**Result**: ✅ Harsh QA fixes applied automatically
**Time**: 63s typing vs instant (acceptable trade-off)
**Lesson**: Always check ~/projects/openclaw for browser automation patterns

**Auth**: 65537
**Status**: Pattern successfully applied and documented
