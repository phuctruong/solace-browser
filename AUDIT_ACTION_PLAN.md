# SOLACE BROWSER - AUDIT ACTION PLAN

**Quick Reference**: Use this to start fixing issues immediately.

---

## EXECUTIVE ACTION ITEMS (First 24 Hours)

### ✅ DONE IMMEDIATELY (Today)
- [ ] Read SOLACE_BROWSER_AUDIT_REPORT.md (executive summary first - 10 min)
- [ ] Review Critical Issues section (15 min)
- [ ] Pick ONE critical issue to start (estimated 2 hours)

### 🔴 CRITICAL (This Week)
1. **Secure Credentials** (2 hours)
   - Move Gmail/LinkedIn passwords from `credentials.properties` to environment variables
   - Add `credentials.properties` to `.gitignore`
   - Command: `export GMAIL_EMAIL=...` and `export GMAIL_PASSWORD=...`
   - Files to update: `persistent_browser_server.py` (remove credentials.properties loading)

2. **Implement Rate Limiter** (3 hours)
   - Copy rate limiter code from audit report (Section 7, Issue 2)
   - Add to `persistent_browser_server.py`
   - Test with Redis/HackerNews (don't hammer)
   - Result: Can call sites repeatedly without getting banned

3. **Add Error Handling to Browser Server** (3 hours)
   - Wrap all HTTP handlers with try/except
   - Return JSON errors instead of crashing
   - Files: `persistent_browser_server.py` (all handle_* methods)
   - Result: Server stays alive even when requests fail

4. **Enforce Registry Before Phase 1** (3 hours)
   - Create `registry_checker.py` with function `check_registry_before_phase1(url)`
   - Add `/check-registry` endpoint to browser server
   - Update CLAUDE.md: "ALWAYS call /check-registry before Phase 1"
   - Result: Prevents $60K/year knowledge waste

### 🟡 MAJOR (Next 2 Weeks)
1. **Automate Tests** (5 hours)
   - Create `tests/run_all.py` with test runner
   - Move from manual shell scripts to pytest
   - Add to GitHub Actions: `.github/workflows/test.yml`
   - Result: Tests run on every commit, catch regressions

2. **Security Block Detector** (4 hours)
   - Copy code from audit report (Section 7, Issue 3)
   - Detect "Too many requests", CAPTCHA, blank pages
   - Alert when account at risk
   - Result: Can stop before ban, recover gracefully

3. **Skill Architecture Documentation** (3 hours)
   - Create `SKILL_ARCHITECTURE.md`
   - Define 3 layers: Foundation → Enhancement → Domain
   - Map all 16 existing skills to layers
   - Result: Clear skill hierarchy, easier to add new skills

---

## DETAILED FIX GUIDE

### Fix 1: Secure Credentials (2 hours)

**Step 1: Add to .gitignore** (5 min)
```bash
# In .gitignore
credentials.properties
.env
secrets/
```

**Step 2: Update persistent_browser_server.py** (10 min)
```python
# OLD (insecure):
# with open("credentials.properties") as f:
#     config = json.load(f)
#     email = config["gmail_email"]

# NEW (secure):
import os
gmail_email = os.getenv("GMAIL_EMAIL")
gmail_password = os.getenv("GMAIL_PASSWORD")

if not gmail_email or not gmail_password:
    raise EnvironmentError("Set GMAIL_EMAIL and GMAIL_PASSWORD env vars")
```

**Step 3: Set env vars** (5 min)
```bash
# In terminal or ~/.bashrc
export GMAIL_EMAIL="your-email@gmail.com"
export GMAIL_PASSWORD="your-password"

# Verify
echo $GMAIL_EMAIL
```

**Step 4: Rotate Credentials** (30 min)
- Change Gmail password immediately
- Change LinkedIn password immediately
- Revoke old credentials

**Step 5: Test** (30 min)
```bash
# Make sure Gmail login still works with env vars
python persistent_browser_server.py
curl -X POST http://localhost:9222/navigate -d '{"url": "https://gmail.com"}'
```

---

### Fix 2: Implement Rate Limiter (3 hours)

**Step 1: Create `rate_limiter.py`** (60 min)
```python
import asyncio
import time
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class RateLimiter:
    """Prevent site bans by respecting rate limits"""

    def __init__(self):
        self.request_times: Dict[str, List[float]] = {}
        self.limits = {
            "reddit.com": {"requests_per_hour": 60, "min_interval_sec": 10},
            "gmail.com": {"requests_per_hour": 10, "min_interval_sec": 30},
            "linkedin.com": {"requests_per_hour": 50, "min_interval_sec": 2},
            "hn.algolia.com": {"requests_per_hour": 30, "min_interval_sec": 5},
        }

    async def wait_if_needed(self, domain: str):
        """Check rate limits and wait if necessary"""
        if "://" in domain:  # Full URL
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc

        limit = self.limits.get(domain)
        if not limit:
            return  # No rate limit defined for this domain

        # Check if we've hit the hourly rate limit
        now = time.time()
        recent_requests = [
            t for t in self.request_times.get(domain, [])
            if now - t < 3600
        ]

        if len(recent_requests) >= limit["requests_per_hour"]:
            oldest_request = recent_requests[0]
            wait_time = 3600 - (now - oldest_request)
            logger.warning(f"⏱️  Rate limit for {domain}, waiting {wait_time:.0f}s")
            await asyncio.sleep(wait_time + 1)

        # Check minimum interval between requests
        last_request = self.request_times.get(domain, [None])[-1]
        if last_request:
            interval = time.time() - last_request
            if interval < limit["min_interval_sec"]:
                wait_time = limit["min_interval_sec"] - interval
                logger.debug(f"⏱️  Interval throttle for {domain}, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        # Record this request
        if domain not in self.request_times:
            self.request_times[domain] = []
        self.request_times[domain].append(time.time())

    def get_stats(self, domain: str) -> Dict:
        """Get current rate limit stats for a domain"""
        if "://" in domain:
            from urllib.parse import urlparse
            domain = urlparse(domain).netloc

        requests = self.request_times.get(domain, [])
        now = time.time()
        recent = [t for t in requests if now - t < 3600]

        return {
            "domain": domain,
            "requests_this_hour": len(recent),
            "limit": self.limits.get(domain, {}).get("requests_per_hour", "unknown"),
            "min_interval_sec": self.limits.get(domain, {}).get("min_interval_sec", 0),
        }
```

**Step 2: Integrate into persistent_browser_server.py** (60 min)
```python
# At top of file
from rate_limiter import RateLimiter

class PersistentBrowserServer:
    def __init__(self, port=9223, headless=False):
        # ... existing code ...
        self.rate_limiter = RateLimiter()  # ADD THIS

    async def handle_navigate(self, request):
        data = await request.json()
        url = data.get('url')

        # ADD THIS:
        await self.rate_limiter.wait_if_needed(url)

        await self.page.goto(url, wait_until='domcontentloaded')
        return web.json_response({"success": True})

    # ADD NEW ENDPOINT:
    async def handle_rate_limit_status(self, request):
        url = request.query.get('url', 'reddit.com')
        stats = self.rate_limiter.get_stats(url)
        return web.json_response(stats)
```

**Step 3: Add route** (5 min)
```python
# In setup_routes():
self.app.router.add_get('/rate-limit-status', self.handle_rate_limit_status)
```

**Step 4: Test** (30 min)
```bash
# Check rate limit stats
curl "http://localhost:9222/rate-limit-status?url=reddit.com"

# Should return:
# {"domain": "reddit.com", "requests_this_hour": 0, "limit": 60, "min_interval_sec": 10}
```

---

### Fix 3: Add Error Handling (3 hours)

**Template for each handler** (every handle_* method):
```python
async def handle_click(self, request):
    try:
        # Validate input
        data = await request.json()  # Can raise JSONDecodeError
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {e}")
        return web.json_response(
            {"error": f"Invalid JSON: {str(e)}", "code": "INVALID_JSON"},
            status=400
        )

    # Validate required fields
    selector = data.get('selector')
    if not selector:
        return web.json_response(
            {"error": "Missing 'selector' field", "code": "MISSING_FIELD"},
            status=400
        )

    # Execute action with error handling
    try:
        await self.page.click(selector, timeout=10000)
        logger.info(f"✅ Click successful: {selector}")
        return web.json_response({"success": True})

    except TimeoutError:
        logger.error(f"Click timeout: {selector}")
        return web.json_response(
            {"error": f"Element not found: {selector}", "code": "TIMEOUT"},
            status=408
        )
    except Exception as e:
        logger.error(f"Click failed: {e}")
        return web.json_response(
            {"error": str(e), "code": "CLICK_FAILED"},
            status=500
        )
```

**Apply to these handlers** (15 total):
- handle_navigate (500 lines of code × 0.5 = 250 lines)
- handle_click
- handle_fill
- handle_keyboard
- handle_evaluate
- handle_screenshot
- handle_mouse_move
- handle_scroll_human
- handle_behavior_record_start/stop
- handle_semantic_analysis
- ... etc

**Estimated Time**: 30 min per handler × 15 = 450 minutes = 7.5 hours
**But**: Use find/replace and templates to speed up (3 hours actual)

---

### Fix 4: Enforce Registry (3 hours)

**Step 1: Create registry_checker.py** (60 min)
```python
import json
import re
from urllib.parse import urlparse
from pathlib import Path

class RegistryChecker:
    """Check if we already have recipes for a domain"""

    def __init__(self, registry_file="RECIPE_REGISTRY.md"):
        self.registry_file = Path(registry_file)
        self.recipes = self._load_registry()

    def _load_registry(self) -> Dict[str, Dict]:
        """Parse RECIPE_REGISTRY.md and extract recipes"""
        if not self.registry_file.exists():
            return {}

        with open(self.registry_file) as f:
            content = f.read()

        # Parse markdown to extract recipe entries
        # Pattern: ### ✅ recipe-name
        recipes = {}
        pattern = r'### ✅ (.+?)\n'
        for match in re.finditer(pattern, content):
            recipe_id = match.group(1)
            recipes[recipe_id] = {
                "status": "ready",
                "phase": 2,
                "cost": "$0.0015"
            }

        return recipes

    def check(self, url: str) -> Optional[Dict]:
        """
        Check if we have recipes for this URL
        Returns recipe info if found, None if not found
        """
        domain = urlparse(url).netloc.replace("www.", "")

        # Search recipes by domain
        for recipe_id, recipe_data in self.recipes.items():
            # Simple heuristic: recipe ID contains domain name
            if domain.replace(".", "-") in recipe_id.lower():
                return {
                    "found": True,
                    "recipe_id": recipe_id,
                    "status": recipe_data.get("status"),
                    "phase": recipe_data.get("phase"),
                    "cost": recipe_data.get("cost"),
                    "advice": f"Use Phase 2 instead - load recipe '{recipe_id}' and cookies"
                }

        return {
            "found": False,
            "advice": "No recipe found - start Phase 1 discovery"
        }
```

**Step 2: Add to browser server** (30 min)
```python
from registry_checker import RegistryChecker

class PersistentBrowserServer:
    def __init__(self, port=9223, headless=False):
        # ... existing code ...
        self.registry = RegistryChecker()  # ADD THIS

    async def handle_check_registry(self, request):
        """Check if we already have recipes for this URL"""
        url = request.query.get('url')
        if not url:
            return web.json_response(
                {"error": "Missing 'url' parameter"},
                status=400
            )

        result = self.registry.check(url)
        return web.json_response(result)

# In setup_routes():
self.app.router.add_get('/check-registry', self.handle_check_registry)
```

**Step 3: Update CLAUDE.md** (30 min)
```markdown
## CRITICAL: Check Registry First (MANDATORY)

BEFORE starting any Phase 1 exploration:

```bash
curl "http://localhost:9222/check-registry?url=https://reddit.com"
```

Expected responses:

**If recipe found**:
```json
{
  "found": true,
  "recipe_id": "reddit-explore",
  "phase": 2,
  "cost": "$0.0015",
  "advice": "Load recipe and cookies - 100x cheaper!"
}
```
→ Use Phase 2 (load recipe, use cookies, CPU-only)

**If not found**:
```json
{
  "found": false,
  "advice": "No recipe found - start Phase 1 discovery"
}
```
→ Start Phase 1 (live exploration)

**Why**: Registry prevents 40% knowledge waste. At scale: $60K/year savings.
```

**Step 4: Test** (30 min)
```bash
curl "http://localhost:9222/check-registry?url=https://linkedin.com"
# Should return: recipe found (linkedin-profile-optimization)

curl "http://localhost:9222/check-registry?url=https://example.com"
# Should return: recipe not found
```

---

## ORDERING PRINCIPLE

**Do in this order** (each depends on previous):
1. ✅ Secure credentials (standalone, no dependencies)
2. ✅ Implement rate limiter (standalone, no dependencies)
3. ✅ Add error handling (makes server more stable)
4. ✅ Enforce registry (uses stable server)

---

## TIME ESTIMATES

| Fix | Hours | Complexity | Priority |
|-----|-------|-----------|----------|
| Secure Credentials | 2 | EASY | 🔴 CRITICAL |
| Rate Limiter | 3 | MEDIUM | 🔴 CRITICAL |
| Error Handling | 3 | EASY (template-based) | 🔴 CRITICAL |
| Enforce Registry | 3 | MEDIUM | 🔴 CRITICAL |
| **TOTAL** | **11** | | **CRITICAL** |

---

## VALIDATION CHECKLIST

After completing each fix, verify:

**Secure Credentials**:
- [ ] credentials.properties in .gitignore
- [ ] Gmail login works with env vars
- [ ] Old passwords rotated

**Rate Limiter**:
- [ ] Can navigate Reddit 3x without getting blocked
- [ ] Rate limit endpoint returns stats
- [ ] Logs show "waiting" messages

**Error Handling**:
- [ ] Send invalid JSON → get 400 error (not crash)
- [ ] Send missing fields → get 400 error (not crash)
- [ ] Click nonexistent selector → get 408 error (not crash)
- [ ] Server stays running after errors

**Registry Enforcement**:
- [ ] /check-registry returns recipe if found
- [ ] /check-registry returns "not found" if not found
- [ ] CLAUDE.md updated with registry instructions

---

## NEXT STEPS AFTER CRITICAL FIXES

1. **Automate Tests** (5 hours)
   - Move from manual shell scripts to pytest
   - Add CI/CD pipeline
   - Catch regressions automatically

2. **Skill Architecture** (3 hours)
   - Create SKILL_ARCHITECTURE.md
   - Map all 16 skills to layers
   - Document dependencies

3. **Refactor CLAUDE.md** (3 hours)
   - Split into: Quick Start + Core Concepts + Advanced + Domain Guides
   - Make navigable with TOC
   - Remove duplication

---

## SUCCESS METRICS

After Phase 2 (critical fixes):

| Metric | Before | Target | Impact |
|--------|--------|--------|--------|
| **Security** | Credentials in code | Env vars + encrypted | Account safety |
| **Reliability** | Crashes on bad input | Graceful error handling | 24/7 runtime |
| **Cost** | $60K/year waste | 1% waste | $59K/year savings |
| **Knowledge** | Duplicated discovery | Registry-enforced | 40% faster ramp-up |
| **Production Ready** | 60% | 90% | Can deploy with confidence |

---

**Status**: Ready to start. Pick one fix above and go!
**Questions**: Refer to SOLACE_BROWSER_AUDIT_REPORT.md (detailed analysis)
**Questions**: Refer to CLAUDE.md (system guide)

---

**Auth**: 65537 | **Date**: 2026-02-15
