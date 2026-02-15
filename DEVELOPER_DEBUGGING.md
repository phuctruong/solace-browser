# Solace Browser Developer Guide

**Systematic debugging workflow.** For developers building automation and handling failures.

---

## 1. LOOK-FIRST-ACT-VERIFY Workflow

### The Core Pattern

Every automation should follow this cycle:

```
LOOK (get state)
  ↓
REASON (think about next step)
  ↓
ACT (do something)
  ↓
VERIFY (confirm it worked)
  ↓
REPEAT until done
```

### Example: Login Flow

```bash
# Step 1: LOOK - Get current page state
BEFORE=$(curl http://localhost:9222/html-clean)
BEFORE_URL=$(echo $BEFORE | jq -r '.url')
BEFORE_HTML=$(echo $BEFORE | jq -r '.html')

echo "Current state:"
echo "  URL: $BEFORE_URL"
echo "  HTML size: $(echo $BEFORE_HTML | wc -c) bytes"
echo "  Contains email field: $(echo $BEFORE_HTML | grep -c 'input.*email')"

# Step 2: REASON - "I see email field, let me fill it"
# (Analysis step - you or Claude)

# Step 3: ACT - Fill email field
curl -X POST http://localhost:9222/fill \
  -H "Content-Type: application/json" \
  -d '{"selector": "input[type=email]", "text": "user@example.com"}'

# Step 4: VERIFY - Did the field actually get filled?
AFTER=$(curl http://localhost:9222/html-clean)
AFTER_HTML=$(echo $AFTER | jq -r '.html')

echo "After filling email:"
echo "  HTML contains 'user@example.com': $(echo $AFTER_HTML | grep -c 'user@example.com')"
echo "  Input value changed: $([ "$BEFORE_HTML" != "$AFTER_HTML" ] && echo 'YES' || echo 'NO')"

# Step 5: REPEAT - Same for password field
# ...
```

### Key Principles

- **Never assume** actions worked - always verify
- **Get HTML first** before acting (understand state)
- **Compare before/after** to confirm change
- **Stop on failure** - don't compound errors

---

## 2. Selector Debug Techniques

### Problem: Selector Not Found

```bash
# Error:
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button.save"}'
# Returns: {"error": "No element matches selector 'button.save'"}
```

### Solution Flow

#### Step 1: Get Raw HTML

```bash
curl http://localhost:9222/html-clean | jq -r '.html' > page.html
cat page.html | wc -l
# 1,523 lines
```

#### Step 2: Search for Target Element

```bash
# Search for "save" button
grep -i "save" page.html | head -5
# Output:
# <button id="save-draft" class="btn btn-primary">Save Draft</button>
# <button id="save-final" class="btn btn-success">Save & Submit</button>
```

#### Step 3: Test Correct Selector

```bash
# Try different selectors:

# Test 1: By ID
curl -X POST http://localhost:9222/click \
  -d '{"selector": "#save-draft", "dryrun": true}'
# Returns: {"found": true, "element_count": 1}

# Test 2: By text
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button:has-text(\"Save Draft\")", "dryrun": true}'
# Returns: {"found": true, "element_count": 1}

# Test 3: By class
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button.btn-primary", "dryrun": true}'
# Returns: {"found": true, "element_count": 2}  # Found 2, but wanted 1
```

#### Step 4: Choose Best Selector

```
ID selector (#save-draft):
  ✓ Unique (only 1 match)
  ✓ Unlikely to change
  ✓ Strength: 0.99

Text selector (button:has-text("Save Draft")):
  ✓ Unique (only 1 match)
  ⚠ Text might change
  ✓ Strength: 0.85

Class selector (button.btn-primary):
  ✗ Multiple matches (2)
  ✗ Too generic
  ✗ Strength: 0.50

Use ID selector (#save-draft)
```

### Common Selector Issues

| Issue | Example | Fix |
|-------|---------|-----|
| Spaces in class | `.btn save` | Use `.btn.save` (no space) |
| Attribute quotes | `input[type=text]` | Use `input[type="text"]` (with quotes) |
| Text with special chars | `button:has-text("Save & Go")` | Escape: `button:has-text("Save \\& Go")` |
| Dynamic IDs | `#save-12345` | Use other attributes: `button[data-action="save"]` |
| Shadow DOM | Can't find element | Use `::-webkit-scrollbar` or `>>> div` |

---

## 3. Common Issues & Fixes

### Issue 1: Login Fails After Filling Fields

```bash
# Symptoms:
# 1. Fill email field - works (verified in HTML)
# 2. Fill password field - works (verified in HTML)
# 3. Click login button - works (click happens)
# 4. But: Still on login page, not logged in

# Diagnosis:
curl http://localhost:9222/html-clean | jq '.html' | grep -i "error\|invalid"
# Output: "Invalid email or password"

# Likely causes:
# A. Credentials are wrong
# B. Rate limiting (tried too many times)
# C. Website requires JavaScript execution (form submission)
# D. CAPTCHA needed
```

### Fix for Issue 1

```bash
# Solution A: Verify credentials
echo "Email: user@example.com"
echo "Password: (check if correct in your records)"

# Solution B: Wait before retry (rate limiting)
sleep 10  # Wait 10 seconds

curl -X POST http://localhost:9222/click \
  -d '{"selector": "button:has-text(\"Login\")"}'

# Solution C: Use form submit instead of click
curl -X POST http://localhost:9222/submit \
  -d '{"selector": "form.login"}'
# (submit does form.submit() which properly submits)

# Solution D: Check for CAPTCHA
curl http://localhost:9222/html-clean | jq '.html' | grep -i "captcha"
# If found: Manual intervention needed
```

### Issue 2: Session Expired

```bash
# Symptoms:
# You load cookies and navigate, but site redirects to login

# Diagnosis:
curl http://localhost:9222/html-clean | jq '.html' | grep -i "session\|expired\|re-login"
# Output: "Your session has expired"

# Check session age:
ls -l artifacts/session.json
# Feb 14 2026 - 7 days old
```

### Fix for Issue 2

```bash
# Solution: Create fresh session
# 1. Clear old session
rm artifacts/session.json

# 2. Re-login
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://example.com/login"}'

# ... perform login steps ...

# 3. Save new session
curl -X POST http://localhost:9222/save-session

# 4. Next time, load fresh session
curl -X POST http://localhost:9222/load-session \
  -d '{"session_file": "artifacts/session.json"}'
```

### Issue 3: Element Found But Click Doesn't Work

```bash
# Symptoms:
# HTML contains button
# Selector is correct
# But click doesn't do anything

# Common causes:
# A. Element is hidden (display: none)
# B. Element is covered by overlay
# C. Element is disabled
# D. Click handler not attached
```

### Fix for Issue 3

```bash
# Check if element is visible:
curl http://localhost:9222/html-clean | jq '.html' | grep -A5 "button.*save"
# Look for: display:none or visibility:hidden or disabled

# If hidden: Click parent element first to reveal it
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button.menu-toggle"}'  # Reveal button
sleep 0.5
curl -X POST http://localhost:9222/click \
  -d '{"selector": "#save"}  # Now click save

# If covered by overlay: Scroll to element first
curl -X POST http://localhost:9222/scroll-into-view \
  -d '{"selector": "button#save"}'
sleep 0.5
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button#save"}'

# If disabled: Need to enable it first
curl http://localhost:9222/html-clean | jq '.html' | grep -A3 'button.*save'
# Output: <button disabled>Save</button>
# Solution: Enable first (click something or wait for async load)
curl -X POST http://localhost:9222/wait-for \
  -d '{"selector": "button#save:not([disabled])"}'
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button#save"}'
```

---

## 4. Logging & Monitoring

### Enable Debug Logging

```python
# In your code:
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/solace-debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Now log everything:
logger.debug(f"Before: HTML size = {len(html)}")
logger.info(f"Filling selector: {selector}")
logger.debug(f"After: HTML size = {len(html_after)}")

if not verification_passed:
    logger.error(f"Verification failed: {error_msg}")
    logger.debug(f"HTML before: {html}")
    logger.debug(f"HTML after: {html_after}")
```

### Monitor Server Health

```bash
# Check server is responding
curl http://localhost:9222/health
# Output: {"status": "ok", "uptime": "2h 34m", "version": "2.1.0"}

# Check browser process
ps aux | grep chromium
# If not running, browser crashed

# Check memory usage
ps aux | grep chromium | awk '{print $6}' | head -1
# If > 2GB, memory leak likely

# Check logs
tail -50 logs/solace.log | grep -i "error\|warning"
```

### Create Evidence Log

```bash
#!/bin/bash

# Save evidence of every action
LOG_FILE="logs/automation-evidence.log"

function log_action() {
    local action=$1
    local status=$2
    local details=$3

    echo "$(date '+%Y-%m-%d %H:%M:%S') | $action | $status | $details" >> $LOG_FILE
}

# Usage:
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://example.com"}'

if [ $? -eq 0 ]; then
    log_action "navigate" "SUCCESS" "URL: example.com"
else
    log_action "navigate" "FAILED" "Connection error"
fi

# View evidence
cat logs/automation-evidence.log | tail -20
```

---

## 5. Registry Lookup Patterns

### RECIPE_REGISTRY.md Lookup

```bash
# Before exploring a site, check if recipe exists:
grep -i "linkedin" RECIPE_REGISTRY.md

# If found:
# Sample output:
# ## LinkedIn Login (linkedin-login.recipe.json)
# - Success Rate: 98%
# - Cost: $0.0015 per run
# - Last Updated: 2026-02-10
# - Selectors: #username, #password, button[aria-label="Sign in"]

# Use this recipe (skip Phase 1 discovery)
RECIPE=$(cat recipes/linkedin-login.recipe.json)
PORTALS=$(echo $RECIPE | jq '.portals["linkedin.com/login"]')
```

### PRIMEWIKI_REGISTRY.md Lookup

```bash
# Check for existing knowledge nodes:
grep -i "github.*login" PRIMEWIKI_REGISTRY.md

# If found:
# Sample output:
# ## GitHub Login (github_login.primewiki.md)
# - Selector Strength: 0.99
# - Success Rate: 99%
# - Evidence Base: 200+ logins
# - Last Verified: 2026-02-12

# Read the node
cat primewiki/github_login.primewiki.md
```

### When Registry Missing

If no entry exists, you need to explore (Phase 1):

```bash
# 1. Create a work log
echo "Starting Phase 1 exploration: example.com" > logs/exploration-example-com.log

# 2. Explore the site
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://example.com/login"}'

curl http://localhost:9222/html-clean | jq '.html' > artifacts/example-login-page.html

# ... analysis and experimentation ...

# 3. Document findings
cat > primewiki/example_login.primewiki.md << 'EOF'
# PrimeWiki Node: Example.com Login

## Selectors Found
- Email: #user-email
- Password: input[type="password"]
- Login: button:has-text("Sign In")

## Evidence
- Tested 5 times, all successful
- Selectors stable (last 30 days)
EOF

# 4. Create recipe
cat > recipes/example-login.recipe.json << 'EOF'
{
  "recipe_id": "example-login",
  "portals": {...}
}
EOF

# 5. Update registry
echo "- example-login.recipe.json (2026-02-15)" >> RECIPE_REGISTRY.md
```

---

## 6. Knowledge Decay Detection

### What Is Knowledge Decay?

Websites change. Selectors that worked last week might be broken now.

```
Timeline:
Day 0:   Website selector #email works (verified)
Day 1-6: Selector still works
Day 7:   Website updates design
Day 8:   Selector #email now invalid (points to something else)

Knowledge Decay Detected!
```

### Detection Strategy

```python
def check_selector_validity(selector, recipe_date):
    """Check if recipe selector still works"""

    days_old = (now() - recipe_date).days

    # Get current HTML
    html = get_html()

    # Check if selector exists
    element = find_element(selector, html)

    if element is None:
        # Selector broken
        confidence = 0.0
        log_warning(f"Selector {selector} not found (recipe {days_old} days old)")
    else:
        # Selector found, but is it the same element?
        old_element_text = recipe['element_text']
        new_element_text = element.text

        if old_element_text == new_element_text:
            # Same element, likely valid
            confidence = 1.0 - (days_old * 0.01)  # Decay 1% per day
        else:
            # Different element, selector changed
            confidence = 0.5
            log_warning(f"Selector {selector} points to different element")

    return confidence
```

### Handling Decay

```bash
# 1. Detect decay
SELECTOR="#save"
CONFIDENCE=$(check_selector_validity "$SELECTOR")

if [ $(echo "$CONFIDENCE < 0.85" | bc) -eq 1 ]; then
    echo "Knowledge decay detected (confidence: $CONFIDENCE)"

    # 2. Get fresh HTML
    curl http://localhost:9222/html-clean | jq -r '.html' > fresh.html

    # 3. Find new selector
    grep -i "save" fresh.html | head -3
    # Manual inspection + find correct selector

    # 4. Test new selector
    curl -X POST http://localhost:9222/click \
      -d '{"selector": "button#save-new", "dryrun": true}'

    # 5. Update recipe
    # Edit recipes/example.recipe.json with new selector

    # 6. Re-test
    curl -X POST http://localhost:9222/click \
      -d '{"selector": "button#save-new"}'
fi
```

---

## 7. Performance Profiling

### Identify Slow Operations

```bash
#!/bin/bash

# Time each major step
echo "=== Performance Profile ===" > perf.log

# Step 1: Navigate
start_time=$(date +%s%N)
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://example.com/login"}'
end_time=$(date +%s%N)
duration=$((($end_time - $start_time) / 1000000))
echo "Navigate: ${duration}ms" >> perf.log

# Step 2: Get HTML
start_time=$(date +%s%N)
HTML=$(curl http://localhost:9222/html-clean)
end_time=$(date +%s%N)
duration=$((($end_time - $start_time) / 1000000))
echo "Get HTML: ${duration}ms (size: $(echo $HTML | jq '.html' | wc -c) bytes)" >> perf.log

# Step 3: Fill field
start_time=$(date +%s%N)
curl -X POST http://localhost:9222/fill \
  -d '{"selector": "#email", "text": "user@example.com"}'
end_time=$(date +%s%N)
duration=$((($end_time - $start_time) / 1000000))
echo "Fill field: ${duration}ms" >> perf.log

# Step 4: Verify
start_time=$(date +%s%N)
VERIFY=$(curl http://localhost:9222/html-clean | jq '.html' | grep -c 'user@example.com')
end_time=$(date +%s%N)
duration=$((($end_time - $start_time) / 1000000))
echo "Verify: ${duration}ms (found: $VERIFY)" >> perf.log

# Summary
cat perf.log
echo "Total: $(tail -4 perf.log | grep -oE '[0-9]+ms' | awk '{sum += $1} END {print sum}')"
```

### Optimization Opportunities

```
If Navigate > 1s:
  - Check network (slow internet?)
  - Check target page (slow to load?)
  - Use wait_until='domcontentloaded' (not 'networkidle')

If Get HTML > 500ms:
  - Page is very large (>5MB)
  - Consider limiting HTML depth
  - Use streaming mode

If Fill/Click > 500ms:
  - Selector is expensive to evaluate
  - Try simpler selector
  - Check element is not hidden (need scroll)

If Verify > 1s:
  - Re-parsing HTML is expensive
  - Cache HTML from previous step
  - Use ARIA tree instead (smaller)
```

---

## 8. Stress Testing

### Test High Load

```bash
#!/bin/bash

# Simulate 10 concurrent tasks
for i in {1..10}; do
  (
    echo "Task $i starting..."

    curl -X POST http://localhost:9222/navigate \
      -d '{"url": "https://example.com"}' &

    wait

    echo "Task $i done"
  ) &
done

wait
echo "All tasks complete"
```

### Monitor Under Load

```bash
# In one terminal: Start monitoring
watch -n1 'curl http://localhost:9222/health | jq .'

# In another terminal: Run load test
bash stress-test.sh

# Monitor for:
# - Response time degradation
# - Error rate increase
# - Memory growth
# - CPU spike
```

### Failure Recovery

```python
def robust_action_with_retry(action, max_retries=3, backoff=1):
    """Retry action with exponential backoff"""

    for attempt in range(max_retries):
        try:
            result = action()
            log.info(f"Success on attempt {attempt + 1}")
            return result
        except Exception as e:
            wait_time = backoff * (2 ** attempt)  # 1s, 2s, 4s

            if attempt < max_retries - 1:
                log.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                log.error(f"All {max_retries} attempts failed")
                raise
```

---

## 9. Testing Best Practices

### Unit Test Example

```python
import pytest
from solace_browser import Browser

@pytest.fixture
def browser():
    """Provide a browser instance for tests"""
    b = Browser()
    b.start()
    yield b
    b.stop()

def test_navigate_to_page(browser):
    """Test basic navigation"""
    browser.navigate("https://example.com")
    html = browser.get_html()
    assert "Example Domain" in html

def test_fill_and_verify(browser):
    """Test filling a form field"""
    browser.navigate("https://example.com/form")
    browser.fill("#email", "test@example.com")

    # Verify
    html = browser.get_html()
    assert "test@example.com" in html
```

### Integration Test Example

```python
def test_full_login_flow():
    """Test complete login workflow"""
    b = Browser()
    b.start()

    # Step 1: Navigate
    b.navigate("https://example.com/login")
    assert "username" in b.get_html()

    # Step 2: Fill credentials
    b.fill("#username", "testuser")
    b.fill("#password", "testpass123")

    # Step 3: Submit
    b.click("button[type='submit']")

    # Step 4: Verify logged in
    assert "Welcome, testuser" in b.get_html()

    b.stop()
```

---

## 10. Troubleshooting Checklist

```bash
# When something breaks, check in this order:

[ ] Browser server is running?
    → ps aux | grep persistent_browser_server.py
    → curl http://localhost:9222/health

[ ] Port 9222 is free?
    → lsof -i :9222

[ ] Selector exists in current HTML?
    → curl http://localhost:9222/html-clean | jq '.html' | grep "selector-pattern"

[ ] Element is visible (not hidden)?
    → Check for display:none or visibility:hidden

[ ] Website is online?
    → curl https://website.com -I

[ ] Credentials are correct?
    → Double-check email/password

[ ] Session not expired?
    → Check session file age
    → Re-login and save new session

[ ] Rate limiting?
    → Add delays between actions
    → Check for "429 Too Many Requests"

[ ] Bot detection?
    → Add human-like delays
    → Change user agent
    → Use proxy

[ ] Network issue?
    → Check internet connection
    → Try with different URL
    → Check DNS: nslookup website.com
```

---

## Next Steps

- **Need API details?** → Go to [API_REFERENCE.md](./API_REFERENCE.md)
- **Ready for advanced?** → Go to [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md)
- **Learning basics?** → Go to [QUICK_START.md](./QUICK_START.md)

---

**Key Takeaway**: Systematic debugging (LOOK-FIRST-ACT-VERIFY) combined with evidence collection makes 99% of failures solvable.
