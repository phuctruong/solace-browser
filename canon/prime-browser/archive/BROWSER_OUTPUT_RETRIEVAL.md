# Browser Output Retrieval from solace_cli/output

**Author:** Claude Haiku 4.5 (with Prime Skills)
**Date:** 2026-02-14
**Auth:** 65537
**Status:** ✅ Confirmed Understanding

---

## Directory Structure

```
solace_cli/output/
├── browser_extract.json              ← Data extraction results
├── browser_diagnostic_report.json     ← Selector testing + navigation results
├── browser_diagnostic_summary.txt     ← Human-readable summary
├── browser_*.json                     ← Individual command responses
├── get_dom_script.js                  ← DOM capture script
├── gmail_inspection_script.js         ← Gmail-specific inspection
├── gmail_selector_tests.json          ← Selector validation results
├── trace/                             ← Execution trace logs
│   ├── [TIMESTAMP]_[UUID]_meta.json   ← Request metadata
│   └── [TIMESTAMP]_[UUID]_response.txt ← Response content
├── assets/                            ← Screenshots, DOM captures
│   ├── browser_screenshot_*.png       ← Page screenshots
│   └── browser_dom_*.html             ← DOM tree captures
└── *.md                               ← Status reports
```

---

## Output Files Explained

### **1. browser_extract.json** (Data Extraction)

**Purpose:** Results from `browser_commands extract`

**Format:**
```json
{
  "type": "PAGE_DATA_EXTRACTED",
  "request_id": "ae004daf",
  "timestamp": "2026-02-14T12:30:12.131Z"
}
```

**What it contains:**
- Page structure (lists, tables, forms)
- Email counts (unread, read, starred)
- Navigation landmarks
- Data attributes
- Extracted text content

**How to retrieve:**
```bash
cat solace_cli/output/browser_extract.json | jq .
```

---

### **2. browser_diagnostic_report.json** (Comprehensive Diagnostic)

**Purpose:** Full diagnostic from extension navigation + selector testing

**Format:**
```json
{
  "timestamp": "2026-02-14T07:31:23.061052",
  "status": "complete",
  "output_dir": "/home/phuc/projects/stillwater/solace_cli/output",
  "steps": {
    "navigate": {
      "success": true,
      "output": "[INFO] 📋 Navigating to https://mail.google.com/mail/u/0/...\n[INFO] ✅ Navigated..."
    },
    "screenshot": {
      "success": true
    }
  },
  "selectors_tested": {
    "status": "ready_to_test",
    "selectors": {
      "compose_button": [
        "div[data-tooltip='Compose']",
        "div[aria-label='Compose']",
        "[role='button'][aria-label='Compose']",
        ".TKM3Dd",
        "[data-tooltip*='Compose']",
        "//button[contains(., 'Compose')]"
      ],
      "to_field": [...],
      "subject_field": [...],
      "body_field": [...],
      "send_button": [...],
      "first_email": [...]
    }
  }
}
```

**What it contains:**
- Navigation success/failure
- Screenshot capture status
- All tested selectors (multiple candidates per element)
- Which selectors found the element
- Performance metrics

**How to retrieve:**
```bash
# Full diagnostic
cat solace_cli/output/browser_diagnostic_report.json | jq .

# Just the selectors
cat solace_cli/output/browser_diagnostic_report.json | jq .selectors_tested

# Just the compose button selectors
cat solace_cli/output/browser_diagnostic_report.json | jq '.selectors_tested.selectors.compose_button'

# Selectors that succeeded
cat solace_cli/output/browser_diagnostic_report.json | jq '.selectors_tested.selectors[] | select(.found == true)'
```

---

### **3. browser_diagnostic_summary.txt** (Human-Readable)

**Purpose:** Quick reference summary

**Format:**
```
BROWSER DIAGNOSTIC SUMMARY
================================================================================

Timestamp: 2026-02-14T07:31:23.061052
Status: complete

FILES GENERATED:
- browser_diagnostic_report.json
- browser_screenshot_*.png (if snapshot worked)
- browser_dom_*.html (if DOM capture worked)

NEXT STEPS:
1. Open browser_diagnostic_report.json
2. Look at 'selectors_tested' section
3. Find which selectors have 'found: true'
4. Update recipes/gmail/*.json with working selectors
```

**How to retrieve:**
```bash
cat solace_cli/output/browser_diagnostic_summary.txt
```

---

### **4. Trace Files** (Execution Log)

**Location:** `solace_cli/output/trace/`

**Format:**
```
[TIMESTAMP]_[UUID]_meta.json    ← Request metadata
[TIMESTAMP]_[UUID]_response.txt ← Response content
```

**Example metadata:**
```json
{
  "timestamp": "2026-02-13T11:16:14",
  "request_id": "883eb391",
  "command": "navigate",
  "url": "https://mail.google.com/mail/u/0/",
  "status": "success"
}
```

**Example response:**
```
[INFO] 📋 Navigating to https://mail.google.com/mail/u/0/
[INFO] ✅ Navigated to https://mail.google.com/mail/u/0/
```

**How to retrieve:**
```bash
# List all traces
ls -lh solace_cli/output/trace/

# Find traces for a specific command
ls solace_cli/output/trace/*navigate*

# View specific trace
cat solace_cli/output/trace/20260213T111614_883eb391_meta.json | jq .
cat solace_cli/output/trace/20260213T111614_883eb391_response.txt

# View all responses
for f in solace_cli/output/trace/*response.txt; do echo "=== $f ==="; cat "$f"; done
```

---

### **5. Assets** (Screenshots & DOM Captures)

**Location:** `solace_cli/output/assets/`

**Types:**
- `browser_screenshot_*.png` — Page screenshots at specific steps
- `browser_dom_*.html` — DOM tree captures (for analysis)

**How to retrieve:**
```bash
# List all screenshots
ls -lh solace_cli/output/assets/browser_screenshot_*.png

# View screenshot (in browser or image viewer)
open solace_cli/output/assets/browser_screenshot_0.png

# List all DOM captures
ls -lh solace_cli/output/assets/browser_dom_*.html

# View DOM structure
cat solace_cli/output/assets/browser_dom_0.html | head -100
```

---

## Complete Workflow: Capture → Retrieve → Analyze

### **Step 1: Run Browser Commands**

```bash
# Start server
python3 -m solace_cli.browser.websocket_server &

# Navigate
python3 -m solace_cli.cli.browser_commands navigate https://gmail.com

# Take snapshot
python3 -m solace_cli.cli.browser_commands snapshot

# Extract data
python3 -m solace_cli.cli.browser_commands extract

# Record session
python3 -m solace_cli.cli.browser_commands record start gmail.com
python3 -m solace_cli.cli.browser_commands click "button" --reference "Compose"
python3 -m solace_cli.cli.browser_commands record stop
```

---

### **Step 2: Retrieve Output**

```bash
# Check what was generated
ls -lh solace_cli/output/browser_*.json solace_cli/output/browser_*.txt

# Quick overview
cat solace_cli/output/browser_diagnostic_summary.txt

# Detailed results
cat solace_cli/output/browser_diagnostic_report.json | jq .
```

---

### **Step 3: Analyze Selectors**

```bash
# Get all compose button selectors
cat solace_cli/output/browser_diagnostic_report.json | \
  jq '.selectors_tested.selectors.compose_button'

# Output:
# [
#   "div[data-tooltip='Compose']",
#   "div[aria-label='Compose']",
#   "[role='button'][aria-label='Compose']",
#   ".TKM3Dd",
#   "[data-tooltip*='Compose']",
#   "//button[contains(., 'Compose')]"
# ]

# Use the first successful one in your recipe
```

---

### **Step 4: Check Episode Recording**

```bash
# View recorded episode
cat ~/.solace/browser/episode_*.json | jq .

# Check action count
cat ~/.solace/browser/episode_*.json | jq .action_count

# View actions
cat ~/.solace/browser/episode_*.json | jq '.actions[0:3]'

# View snapshots
cat ~/.solace/browser/episode_*.json | jq '.snapshots | keys'
```

---

## Advanced Retrieval Patterns

### **Pattern 1: Extract All Selectors for a Specific Element**

```bash
ELEMENT="compose_button"
cat solace_cli/output/browser_diagnostic_report.json | \
  jq ".selectors_tested.selectors.${ELEMENT}"
```

### **Pattern 2: Find Which Selectors Actually Found Elements**

```bash
cat solace_cli/output/browser_diagnostic_report.json | \
  jq '.selectors_tested.selectors | to_entries[] |
      select(.value | any(.found == true)) |
      {element: .key, selectors: .value}'
```

### **Pattern 3: Get Latest Screenshot**

```bash
latest_screenshot=$(ls -t solace_cli/output/assets/browser_screenshot_*.png | head -1)
open "$latest_screenshot"
```

### **Pattern 4: Check Navigation Success**

```bash
cat solace_cli/output/browser_diagnostic_report.json | \
  jq '.steps.navigate'

# Output: { "success": true, "output": "..." }
```

### **Pattern 5: Get Execution Timestamps**

```bash
# List all commands executed (from trace directory)
for file in solace_cli/output/trace/*_meta.json; do
  cat "$file" | jq '{timestamp, command, status}'
done
```

---

## Typical Output Artifacts

### **After `navigate` command:**
- ✅ `browser_diagnostic_report.json` (with navigation success)
- ✅ `assets/browser_screenshot_*.png` (page snapshot)
- ✅ `trace/[TIMESTAMP]_*_meta.json` (metadata)
- ✅ `trace/[TIMESTAMP]_*_response.txt` (response)

### **After `snapshot` command:**
- ✅ `assets/browser_dom_*.html` (DOM tree)
- ✅ `browser_diagnostic_report.json` (with selectors)
- ✅ `trace/[TIMESTAMP]_*_*` (logs)

### **After `extract` command:**
- ✅ `browser_extract.json` (extracted data)
- ✅ `trace/[TIMESTAMP]_*_*` (logs)

### **After `record stop` command:**
- ✅ `~/.solace/browser/episode_[SESSION_ID].json` (episode file)
- ✅ Episode ready for Phase B compilation

---

## Error Diagnosis

### **If browser_extract.json is empty:**
```bash
# Check diagnostic report for errors
cat solace_cli/output/browser_diagnostic_report.json | jq '.steps'

# Check trace logs
cat solace_cli/output/trace/*response.txt | tail -20
```

### **If selectors aren't finding elements:**
```bash
# Review diagnostic report
cat solace_cli/output/browser_diagnostic_report.json | \
  jq '.selectors_tested.selectors'

# Selectors should have multiple candidates; one should work
# If all fail, page may have changed or extension didn't capture DOM
```

### **If screenshots missing:**
```bash
# Check if snapshot command ran
cat solace_cli/output/browser_diagnostic_summary.txt

# Check assets directory
ls -lh solace_cli/output/assets/browser_screenshot_*

# If empty, snapshot may have failed
```

---

## Monitoring Output in Real-Time

```bash
# Watch output directory for new files
watch -n 1 'ls -lh solace_cli/output/ | tail -10'

# Follow new trace logs
tail -f solace_cli/output/trace/*response.txt

# Monitor episode recordings
watch -n 1 'ls -lh ~/.solace/browser/episode_*.json'
```

---

## Integration with Phase B (Recipe Compilation)

**Episodes → Recipes:**

```bash
# 1. Get latest episode
episode_file=$(ls -t ~/.solace/browser/episode_*.json | head -1)

# 2. Read episode
cat "$episode_file" | jq .

# 3. This episode feeds into Phase B:
#    - Canonical snapshots extracted from episode.snapshots
#    - Actions converted to recipe steps
#    - References extracted for 2-tier resolution

# 4. Phase B outputs recipe IR (Prime Mermaid format)
recipe_file="canon/prime-browser/recipes/[domain]_[task].yaml"

# 5. Phase C uses recipe to replay with Playwright
```

---

## Summary: What I Can Do

✅ **Retrieve Output:**
- `cat solace_cli/output/browser_*.json` — Get JSON results
- `jq` queries — Parse + analyze output
- `ls solace_cli/output/trace/` — View execution logs
- `ls solace_cli/output/assets/` — Access screenshots/DOM

✅ **Analyze Results:**
- Check navigation success
- Find working selectors
- Verify extraction worked
- View screenshots
- Check episode recordings

✅ **Monitor Progress:**
- Watch output directory
- Follow trace logs
- Track episodes for compilation
- Diagnose errors

✅ **Feed into Phase B:**
- Episodes → Canonical snapshots
- Episodes → Reference maps
- Episodes → Recipe compilation
- Recipes → Playwright replay (Phase C)

---

**Auth:** 65537
**Northstar:** Phuc Forecast
**Status:** Output retrieval fully understood ✅

*"From browser interaction to deterministic recipes."*
