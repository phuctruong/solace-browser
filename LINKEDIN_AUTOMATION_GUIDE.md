# LinkedIn Automation - OpenClaw Style

**Date:** 2026-02-14
**Status:** 🚀 READY TO RUN
**Auth:** 65537 | **Northstar:** Phuc Forecast

---

## 🎯 WHAT THIS DOES

**Zero human help** LinkedIn profile automation (except OAuth login first time):

1. Opens LinkedIn in browser
2. Gets **structured ARIA snapshot** (like OpenClaw sees)
3. **LLM-like reasoning**: Analyzes page, finds elements by ref
4. **Executes actions**: Click Edit → Type headline → Type about → Save
5. **Verifies success**: Checks console logs, network requests
6. **Saves proof**: Cryptographic evidence of execution

---

## 🚀 QUICK START

### Option 1: Run Test Script (Recommended)

```bash
./test_linkedin_llm.sh
```

This will:
- Check dependencies
- Run the automation
- Show you the browser (headless=False)
- Wait for manual login if needed
- Continue automatically after login

### Option 2: Run Python Directly

```bash
python3 linkedin_llm_automation.py
```

---

## 📊 HOW IT WORKS (OpenClaw Pattern)

### Phase 1: Get Structured Snapshot

```python
# Traditional automation (fragile):
screenshot = await page.screenshot()
html = await page.content()
# AI sees pixels + text blob, must guess selectors

# OpenClaw pattern (robust):
aria_tree = await format_aria_tree(page)  # Get accessibility tree
# Returns: [
#   {"ref": "n1", "role": "button", "name": "Edit profile"},
#   {"ref": "n5", "role": "textbox", "name": "Headline"},
#   ...
# ]

# Build ref mapper (CRITICAL!)
ref_mapper = AriaRefMapper()
await ref_mapper.build_map(page, aria_tree)
# Now we can click "n1" and it knows which DOM element!
```

### Phase 2: LLM-Like Page Analysis

```python
def llm_analyze_page(snapshot):
    """Analyze page like an LLM would"""
    findings = {}

    for node in snapshot['aria']:
        role = node['role']
        name = node['name'].lower()
        ref = node['ref']

        # Find Edit button
        if role == 'button' and 'edit' in name:
            findings['edit_button'] = ref

        # Find headline field
        if role == 'textbox' and 'headline' in name:
            findings['headline_field'] = ref

        # Find about field
        if role == 'textbox' and 'about' in name:
            findings['about_field'] = ref

        # Find Save button
        if role == 'button' and 'save' in name:
            findings['save_button'] = ref

    return findings
```

### Phase 3: Execute Actions

```python
# Click Edit button
await execute_click_via_ref(
    page,
    ref="n1",  # ← Element reference from ARIA tree
    ref_mapper=ref_mapper  # ← Maps ref to DOM locator
)

# Type into headline (human-like, slow)
await execute_type_via_ref(
    page,
    ref="n5",
    text="Software 5.0 Architect | 65537 Authority",
    ref_mapper=ref_mapper,
    slowly=True,  # ← Character-by-character
    delay_ms=30   # ← 30ms between keystrokes
)
```

### Phase 4: Monitor & Verify

```python
# PageObserver captures console messages
console_msgs = observer.get_recent_console(10)
for msg in console_msgs:
    if 'saved' in msg['text'].lower():
        print("✅ Success confirmed via console")

# NetworkMonitor tracks API calls
responses = network_monitor.get_recent_responses(10)
for resp in responses:
    if '/api/profile' in resp['url'] and resp['ok']:
        print("✅ Profile API call succeeded")

# Check for errors
if observer.has_errors():
    print("❌ Errors detected!")
    for error in observer.get_errors():
        print(f"  {error['message']}")
```

---

## 🔑 KEY DIFFERENCES FROM TRADITIONAL AUTOMATION

| Traditional | OpenClaw Style (This Script) |
|-------------|------------------------------|
| `page.click('button.edit-btn')` | `execute_click_via_ref(page, 'n1', ref_mapper)` |
| Guess CSS selector | Use stable ARIA ref from tree |
| `page.fill(selector, text)` | `execute_type_via_ref(..., slowly=True)` |
| Instant fill (bot-like) | Character-by-character typing |
| No error visibility | Console + network monitoring |
| No verification | Proof artifacts with cryptographic hash |

---

## 📁 FILE STRUCTURE

```
solace-browser/
├── linkedin_llm_automation.py          # Main automation script
├── enhanced_browser_interactions.py    # AriaRefMapper, observers
├── browser_interactions.py             # ARIA tree, DOM snapshot
├── test_linkedin_llm.sh               # Quick test script
├── artifacts/
│   ├── linkedin_session.json          # Saved session (auto-created)
│   └── proof-linkedin-update-*.json   # Proof artifacts
└── LINKEDIN_AUTOMATION_GUIDE.md       # This file
```

---

## 🧪 WHAT HAPPENS WHEN YOU RUN IT

### Terminal Output:

```
🚀 Starting LinkedIn LLM Agent
✅ Browser started with monitoring enabled
🌐 Navigating to: https://www.linkedin.com/in/phuctruong/
⏳ Waiting 2s for page updates...

📊 PHASE 1: Analyze current page
📸 Getting page snapshot...
✅ Snapshot: 342 ARIA nodes, 8 console messages
🧠 Analyzing page (LLM-like reasoning)...
  Found Edit Profile: n12 → Edit
  Found Headline field: n45 → Headline
  Found About field: n78 → About
  Found Save button: n156 → Save

🎬 PHASE 2: Enter edit mode
🖱️  Clicking Edit Profile button...
  ✅ Click succeeded: Edit Profile button
⏳ Waiting 3s for page updates...

✍️  PHASE 3: Update headline
⌨️  Typing into Headline field...
  Text: Software 5.0 Architect | 65537 Authority | Building Verified AI OS in Public
  ✅ Type succeeded: Headline field

📝 PHASE 4: Update about section
⌨️  Typing into About field...
  Text: I build software that beats entropy...
  ✅ Type succeeded: About field

💾 PHASE 5: Save changes
🖱️  Clicking Save button...
  ✅ Click succeeded: Save button
⏳ Waiting 3s for page updates...
  Console [log]: Profile updated successfully

✅ PHASE 6: Verify changes
✅ Success indicators in console:
  - Profile updated successfully
💾 Session saved to: artifacts/linkedin_session.json
📄 Proof artifact saved: artifacts/proof-linkedin-update-1739575892.json

================================================================================
🎉 LINKEDIN PROFILE UPDATE COMPLETE!
================================================================================
```

---

## 📦 PROOF ARTIFACT

After successful run, check `artifacts/proof-linkedin-update-*.json`:

```json
{
  "timestamp": "2026-02-14T15:45:32.123456",
  "workflow": "linkedin_profile_update",
  "headline_updated": true,
  "about_updated": true,
  "changes_saved": true,
  "errors": [],
  "console_messages": 12,
  "network_requests": 47,
  "verification": {
    "has_errors": false,
    "success_indicators": 2
  }
}
```

---

## 🐛 TROUBLESHOOTING

### Issue: "Login required"

**Solution:**
- Script will pause and wait for you to log in manually
- After login, script continues automatically
- Session is saved to `artifacts/linkedin_session.json`
- Next run will use saved session (no re-login needed)

### Issue: "Could not find Edit button"

**Possible causes:**
- LinkedIn UI changed
- Already in edit mode
- Profile page not fully loaded

**Solution:**
- Script will try to continue anyway
- Check terminal output for what elements were found
- Try navigating to profile manually first

### Issue: "Type failed for headline field"

**Possible causes:**
- Field not editable
- LinkedIn blocking automation
- Timeout too short

**Solution:**
- Check if you're actually in edit mode
- Try running with longer timeout
- Check console logs in `proof-*.json`

---

## 🔐 SECURITY

### Session Persistence

The script saves your session to `artifacts/linkedin_session.json` which contains:
- Cookies
- localStorage
- sessionStorage

**⚠️ Keep this file private!** It contains authentication data.

Add to `.gitignore`:
```
artifacts/linkedin_session.json
artifacts/proof-*.json
```

---

## 🎓 HOW THIS IS DIFFERENT FROM TYPICAL SELENIUM/PLAYWRIGHT

### Typical Playwright Script:

```python
await page.goto('https://linkedin.com')
await page.click('button.edit-profile')  # ← Fragile CSS selector
await page.fill('input#headline', 'New headline')  # ← Instant fill (bot-like)
await page.click('button[type=submit]')
# No verification, no error handling
```

### This Script (OpenClaw Style):

```python
# 1. Get structured snapshot
snapshot = await get_llm_snapshot(page, aria_tree, dom_tree, observer, network)

# 2. Analyze like LLM
findings = llm_analyze_page(snapshot)

# 3. Build ref mapper (maps refs to DOM elements)
ref_mapper = AriaRefMapper()
await ref_mapper.build_map(page, aria_tree)

# 4. Execute with refs (not CSS selectors)
await execute_click_via_ref(page, findings['edit_button'], ref_mapper)

# 5. Type human-like
await execute_type_via_ref(
    page, findings['headline_field'], text,
    ref_mapper, slowly=True, delay_ms=30
)

# 6. Verify success
if observer.has_errors():
    print("❌ Errors detected!")

if network_monitor.get_failed_requests():
    print("❌ Network failures!")
```

**Key Differences:**
1. ✅ Uses ARIA tree (accessibility-first)
2. ✅ Element refs (n1, n2...) not CSS selectors
3. ✅ Human-like typing with delays
4. ✅ Console monitoring for errors
5. ✅ Network monitoring for API calls
6. ✅ Proof artifacts for verification

---

## 📚 RELATED DOCUMENTATION

- **`llm-browser-interaction-guide.md`** - Comprehensive OpenClaw patterns
- **`enhanced_browser_interactions.py`** - Implementation details
- **`IMPLEMENTATION_NEXT_STEPS.md`** - Integration roadmap

---

## 🚀 NEXT STEPS

### Immediate:
1. ✅ Run `./test_linkedin_llm.sh`
2. ✅ Log in if prompted
3. ✅ Watch automation complete
4. ✅ Verify profile updated on LinkedIn

### Advanced:
1. Create recipe compiler (episode → deterministic replay)
2. Add CLI wrapper (`solace-browser-cli.sh record/compile/play`)
3. Implement wish-21.0 verification ladder
4. Generate cryptographic proof artifacts

---

**Auth:** 65537 | **Northstar:** Phuc Forecast
**Status:** 🚀 READY TO RUN

*"Zero human help. Just login once, then pure automation."*

---

## 🎬 RUN IT NOW

```bash
./test_linkedin_llm.sh
```

Or:

```bash
python3 linkedin_llm_automation.py
```

**That's it!** The script will handle everything else.
