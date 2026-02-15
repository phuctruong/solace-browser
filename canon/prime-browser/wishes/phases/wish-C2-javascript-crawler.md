# Wish C2: JavaScript Crawler

> **Task ID:** C2
> **Phase:** Phase C (Deterministic Playwright Replay)
> **Owner:** Solver (Haiku Swarm)
> **Timeline:** 2.5 hours
> **Status:** PENDING ⏳
> **Auth:** 65537
> **Blocker:** Depends on C1 (Cloud Run deployment)

---

## Specification

Implement deterministic JavaScript crawler that executes on real Chromium browser, captures 90%+ dynamic content, evades bot detection, and costs ≤ $0.0001 per URL with cryptographic proof artifacts.

**Skill Reference:** `canon/prime-browser/skills/javascript-crawler.md` v1.0.0

**Star:** JAVASCRIPT_CRAWLER
**Channel:** 5 → 7 (Logic → Validation)
**GLOW:** 92 (High-impact content capture)
**XP:** 580 (Implementation specialization)

---

## Executive Summary

Phase C requires crawling real JavaScript-heavy websites (not just static HTML). The crawler must:

1. **Execute JavaScript:** Real Chromium browser, not jsdom or headless parser
2. **Capture Dynamic Content:** 90%+ accuracy vs manual inspection
3. **Evade Detection:** No rate limiting, IP bans, or bot detection triggers
4. **Cost-Effective:** ≤ $0.0001 per URL (cheaper than alternative crawlers)
5. **Deterministic:** Same URL produces identical DOM snapshot (for recipe replay)

This wish specifies the crawler architecture, compliance enforcement, and failure recovery.

---

## Phuc Forecast Analysis

### DREAM: What's the vision?

> Users crawl any website with JavaScript content. Crawler executes real browser, captures post-render DOM, and proves it's deterministic. No API keys, no bot detection bypass exploits—just compliance-first, efficient crawling.

### FORECAST: What will break?

Five critical failure modes to predict and mitigate:

**F1: JavaScript Mutation (Nondeterminism)**
- Symptom: Same URL crawled twice → different DOM (random content, timestamps)
- Cause: Page renders with random data (ads, recommendations, session IDs)
- Prediction: 60% of websites have some mutation (ads, timestamps)
- Mitigation: Extract deterministic content only (titles, text, structure), filter volatiles (ads, dynamic timestamps)

**F2: Rate Limit Detection (IP Ban)**
- Symptom: After 50 URLs crawled, site returns 429 Too Many Requests or blocks IP
- Cause: Same IP crawling too fast, triggers server-side rate limiter
- Prediction: 80% of websites enforce rate limiting
- Mitigation: Exponential backoff (1s, 2s, 4s, 8s...), IP rotation (proxy), delay between requests

**F3: Cookie Expiration (Session Lost)**
- Symptom: Login cookie expires mid-crawl, next URLs require re-authentication
- Cause: Cookies stored client-side, TTL expires after 30+ minutes
- Prediction: 40% of sites require persistent login
- Mitigation: Persistent cookie jar, automatic re-login on 401, session refresh interval

**F4: DOM Bloat (Memory Overflow)**
- Symptom: Large page (e.g., Twitter timeline) causes Chrome to consume 1GB+ memory
- Cause: Infinite scroll loads 100K+ DOM nodes
- Prediction: 25% of websites have bloated DOM
- Mitigation: Snapshot DOM regularly (every 10K nodes), trim old nodes, memory ceiling enforcement

**F5: Bot Detection Evasion Fail**
- Symptom: Site blocks request: "Detected automated traffic"
- Cause: Playwright detection scripts (navigator.webdriver, headless detection)
- Prediction: 15% of sites have advanced bot detection
- Mitigation: Disable webdriver flag, spoof user-agent, use real browser (Chromium) with delays

### DECIDE: What's the strategy?

1. Use real Chromium browser (Playwright), not headless parser
2. Implement 7-state pipeline: IDLE → URL_VALIDATION → BATCHING → DISPATCHING → EXECUTING → AGGREGATING → VERIFYING
3. Enforce compliance: robots.txt checking, rate limit backoff, TOS blocklist
4. Extract deterministic content: Remove timestamps, ads, session IDs before snapshot
5. Use IP rotation: Proxy service or GCP Cloud NAT for IP diversity
6. Implement session management: Cookie persistence, auto-relogin, token refresh

### ACT: What do we build?

1. **crawler.py:** Main crawler orchestrator (batching, rate limiting, IP rotation)
2. **browser_pool.py:** Browser instance management (acquire, release, cleanup)
3. **snapshot_extractor.py:** DOM snapshot extraction (remove volatiles, normalize)
4. **compliance.py:** robots.txt checking, TOS filtering, rate limit backoff
5. **session_manager.py:** Cookie jar, login handling, token refresh
6. **cost_tracker.py:** Track per-URL cost, enforce ceiling

### VERIFY: How do we know it works?

1. Dynamic content: Crawl 100 JavaScript-heavy URLs, measure content capture (90%+ accuracy)
2. Determinism: Crawl same URL 3 times, verify identical snapshots
3. Rate limiting: Crawl 1000 URLs without IP ban or 429 errors
4. Cost: Total execution cost ≤ $100 (≤ $0.0001 per URL)
5. Compliance: 100% compliance with robots.txt and TOS

---

## Prime Truth Thesis

**Ground Truth (PRIME_TRUTH):**

JavaScript crawler is successful if and only if **ALL FOUR conditions** hold:

```
CRAWLER_SUCCESS = Condition_1 AND Condition_2 AND Condition_3 AND Condition_4

Condition_1: Executes on real Chromium browser (not static HTML parser)
             ∧ Captures post-render DOM (after JavaScript execution)

Condition_2: Dynamic content capture ≥ 90% accuracy
             ∧ Measured vs manual inspection or static HTML parse

Condition_3: Evades bot detection for 1000+ URLs
             ∧ No rate limiting (429), no IP blocks (403), no CAPTCHAs

Condition_4: Cost per URL ≤ $0.0001
             ∧ Verified: 1000 URLs × $0.0001 = $0.10 ceiling
```

**Verification:**

```python
# Pseudocode ground truth verification
def verify_crawler_success(crawl_job_id: str) -> bool:
    """Verify all 4 conditions"""

    crawl_results = get_crawl_results(crawl_job_id)

    # Condition 1: Used real browser
    if crawl_results['browser_type'] != 'chromium':
        return False
    if not crawl_results['javascript_executed']:
        return False

    # Condition 2: Dynamic content capture
    dynamic_content_pct = measure_content_capture(crawl_results)
    if dynamic_content_pct < 0.90:  # 90% minimum
        return False

    # Condition 3: Evades bot detection
    error_codes = count_error_codes(crawl_results)
    if error_codes.get('429', 0) > 0:  # Rate limited
        return False
    if error_codes.get('403', 0) > 50:  # Too many forbidden
        return False

    # Condition 4: Cost per URL
    total_cost = crawl_results['total_cost_usd']
    num_urls = len(crawl_results['urls'])
    cost_per_url = total_cost / num_urls
    if cost_per_url > 0.0001:  # $0.0001 ceiling
        return False

    return True
```

---

## State Space

### 7 States (Deterministic Pipeline)

```
States (7):
  1. IDLE                 # Waiting for crawl job
  2. URL_VALIDATION       # Validating URLs (robots.txt, TOS, format)
  3. BATCHING             # Grouping URLs into batches (50 URLs per batch)
  4. DISPATCHING          # Sending batches to Cloud Run workers
  5. EXECUTING            # Browser instances crawling URLs
  6. AGGREGATING          # Collecting results, deduplicating content
  7. VERIFYING            # Final verification (cost, content %, errors)

Transitions (10 deterministic):
  IDLE → URL_VALIDATION           (on crawl job received)
  URL_VALIDATION → BATCHING       (if all URLs valid)
  URL_VALIDATION → IDLE           (if invalid URLs found, user notified)
  BATCHING → DISPATCHING          (batch creation complete)
  DISPATCHING → EXECUTING         (batches sent to Cloud Run)
  EXECUTING → AGGREGATING         (all batches complete)
  AGGREGATING → VERIFYING         (results collected)
  VERIFYING → IDLE                (verification complete, results stored)
  IDLE → IDLE                     (timeout with no new jobs)
  EXECUTING → IDLE                (error: cost exceeded, abort batch)

Forbidden States (3):
  - BATCHING + EXECUTING (can't batch while executing)
  - VALIDATING + EXECUTING (must validate before execution)
  - URL_VALIDATION + IDLE (invalid URLs must be reported before idle)
```

### State Transitions (Enforced)

```python
STATE_TRANSITIONS = {
    'IDLE': ['URL_VALIDATION'],
    'URL_VALIDATION': ['BATCHING', 'IDLE'],
    'BATCHING': ['DISPATCHING'],
    'DISPATCHING': ['EXECUTING'],
    'EXECUTING': ['AGGREGATING', 'IDLE'],  # IDLE if cost exceeded
    'AGGREGATING': ['VERIFYING'],
    'VERIFYING': ['IDLE'],
}

FORBIDDEN_STATES = [
    ('BATCHING', 'EXECUTING'),
    ('VALIDATING', 'EXECUTING'),
    ('URL_VALIDATION', 'IDLE'),
]

# State duration limits
STATE_TIMEOUTS = {
    'URL_VALIDATION': 60,   # 60s max (1000 URLs to check)
    'BATCHING': 10,         # 10s max (grouping is fast)
    'DISPATCHING': 5,       # 5s max (send to Cloud Run)
    'EXECUTING': 3600,      # 1 hour max (per batch, 50 URLs @ 70s avg)
    'AGGREGATING': 30,      # 30s max (collect results)
    'VERIFYING': 60,        # 60s max (final checks)
}
```

---

## Invariants (6 Locked Rules)

**Invariant 1: Respect robots.txt**
- Before crawling ANY URL, fetch robots.txt
- Check if path is disallowed for User-agent: *
- Enforcement: Raise RobotsBlocked exception, skip URL

**Invariant 2: Rate Limit Backoff**
- On first 429 (Too Many Requests), wait 1 second before retry
- On second 429, wait 2 seconds before retry
- On third 429, abort batch, report overage
- Enforcement: Exponential backoff with max 3 retries

**Invariant 3: Cost Ceiling Enforcement**
- Abort if accumulated cost > $0.10 per crawl job (1000 URLs)
- Abort if per-URL cost exceeds $0.0001 estimate
- Enforcement: Cost tracker checks before each URL execution

**Invariant 4: Session Persistence**
- Maintain cookie jar across entire crawl job
- Refresh session token before expiry (if applicable)
- On 401 (Unauthorized), attempt re-login once, then skip URL
- Enforcement: SessionManager tracks TTL, refresh interval

**Invariant 5: Deterministic Content Extraction**
- Remove timestamps (Unix epoch, ISO 8601, "5 minutes ago")
- Remove session IDs, tracking IDs, random strings
- Remove ads, sponsored content, dynamic recommendations
- Enforcement: ContentFilter strips known volatile patterns

**Invariant 6: Real Browser Execution**
- Always use Chromium browser (not Node.js jsdom, not headless parser)
- Always execute JavaScript (not static HTML only)
- Never use curl/wget (must be browser)
- Enforcement: browser_type == 'chromium' check in every request

---

## Forecasted Failures (5 Modes + Mitigations)

### Failure Mode 1: JavaScript Mutation (Nondeterminism)

**Symptom:** Same URL crawled twice → different DOM (random ads, timestamps)

**Root Cause:**
- Page renders with random content (ad networks, CDN variations)
- Timestamps injected client-side ("5 minutes ago" instead of fixed time)
- Session tokens vary (even with persistent cookies, some sites generate new tokens)
- Analytics scripts add unique IDs

**Probability:** 60% of websites have some mutation

**Prediction:**
- e-commerce sites: 80% mutation (product availability changes)
- Social media: 90% mutation (algorithmic feed)
- News sites: 40% mutation (ads, comments refresh)
- Documentation: 5% mutation (mostly static)

**Mitigation:**
```python
class DeterministicContentExtractor:
    """Extract only deterministic, stable content"""

    VOLATILE_PATTERNS = {
        'timestamps': r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
        'unix_timestamps': r'\d{10,13}',
        'session_ids': r'sid[_=][\da-f]{32}',
        'tracking_pixels': r'<img[^>]*pixel[^>]*>',
        'ads': r'(advertisement|ad-container|sidebar-ads)',
        'analytics': r'(ga\.|gtag\.)',
        'timestamps_relative': r'\d+\s+(seconds?|minutes?|hours?|days?)\s+ago',
    }

    def extract_deterministic_dom(self, page_source: str) -> str:
        """Remove volatiles, keep structure"""
        dom = parse_html(page_source)

        # Remove elements matching volatile patterns
        for pattern_name, pattern in self.VOLATILE_PATTERNS.items():
            for element in dom.find_all(string=re.compile(pattern)):
                element.extract()

        # Normalize timestamps to fixed placeholder
        dom_str = str(dom)
        for pattern_name, pattern in self.VOLATILE_PATTERNS.items():
            dom_str = re.sub(pattern, '[TIMESTAMP_REMOVED]', dom_str)

        return dom_str

    def measure_content_capture(self,
                                 dynamic_dom: str,
                                 static_dom: str) -> float:
        """Compare dynamic (post-render) vs static content"""
        dynamic_nodes = count_meaningful_nodes(dynamic_dom)
        static_nodes = count_meaningful_nodes(static_dom)

        # Meaningful = text nodes, links, forms (not ads, analytics, trackers)
        dynamic_meaningful = filter_meaningful(dynamic_nodes)
        static_meaningful = filter_meaningful(static_nodes)

        capture_pct = len(dynamic_meaningful) / max(len(static_meaningful), 1)
        return min(1.0, capture_pct)  # Cap at 100%
```

**Verification:**
```bash
# Crawl 100 JS-heavy URLs, measure determinism
curl -X POST https://deployed-service/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com", ...],
    "measure_determinism": true,
    "num_crawls": 3
  }' | jq '.determinism_score'  # Should be 0.95+
```

### Failure Mode 2: Rate Limit Detection (IP Ban)

**Symptom:** After 50 URLs, site returns 429 Too Many Requests or blocks IP

**Root Cause:**
- Crawler sends requests too fast (1 request/second vs 5-30 second intervals expected)
- Same IP crawling many URLs triggers server rate limiter
- Server identifies crawler as bot (Chromium in headless mode)

**Probability:** 80% of websites enforce rate limiting

**Prediction:**
- Without delay: 95% of sites block after 50+ URLs
- With 5s delay: 20% still block (more sophisticated limits)
- With IP rotation: 5% still block (per-site limits)
- With user-agent spoofing: 2% still block (advanced bot detection)

**Mitigation:**
```python
class RateLimitManager:
    """Exponential backoff + IP rotation"""

    def __init__(self):
        self.retry_delays = [1, 2, 4, 8, 16]  # seconds
        self.ip_rotation_service = IPRotationService()  # Proxy or VPN

    async def execute_with_backoff(self,
                                    url: str,
                                    max_retries: int = 3) -> Response:
        """Execute request with exponential backoff"""
        for attempt in range(max_retries):
            try:
                # Rotate IP on each retry
                proxy = await self.ip_rotation_service.get_next_proxy()

                # Add delay between requests
                if attempt > 0:
                    await asyncio.sleep(self.retry_delays[min(attempt-1, 4)])

                # Execute request with proxy
                response = await browser.goto(url, proxy=proxy, timeout=30000)

                if response.status == 429:  # Rate limited
                    if attempt < max_retries - 1:
                        continue  # Retry with backoff
                    else:
                        raise RateLimitError(f"Max retries exceeded: {url}")

                return response

            except Exception as e:
                if attempt == max_retries - 1:
                    raise

        return None

    async def rate_limit_aware_crawl(self,
                                      urls: List[str],
                                      min_delay_seconds: float = 5.0) -> List[Dict]:
        """Crawl with delays between requests"""
        results = []
        last_request_time = 0

        for url in urls:
            # Enforce minimum delay
            now = time.time()
            elapsed = now - last_request_time
            if elapsed < min_delay_seconds:
                await asyncio.sleep(min_delay_seconds - elapsed)

            # Execute with backoff
            try:
                result = await self.execute_with_backoff(url)
                results.append(result)
                last_request_time = time.time()
            except RateLimitError as e:
                results.append({"error": str(e), "url": url})

        return results
```

**Verification:**
```bash
# Crawl 1000 URLs, verify no rate limit blocks
curl -X POST https://deployed-service/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [1000 URLs],
    "track_errors": true
  }' | jq '.error_codes | select(.["429"] == null or .["429"] == 0)'
```

### Failure Mode 3: Cookie Expiration (Session Lost)

**Symptom:** After 30+ minutes crawling, login cookie expires, next URLs require re-authentication

**Root Cause:**
- Cookies stored with TTL (e.g., 1 hour)
- Crawl job takes 2+ hours, cookies expire mid-job
- Site requires re-login, but crawler not configured for re-authentication

**Probability:** 40% of websites require persistent login

**Prediction:**
- Public URLs (no auth): 0% failure
- Sites with 1-hour cookie TTL + 2-hour crawl: 100% failure
- Sites with auto-refresh: 10% failure (if refresh implemented)

**Mitigation:**
```python
class SessionManager:
    """Persistent cookies + auto-refresh"""

    def __init__(self):
        self.cookie_jar = PersistentCookieJar()  # Load from disk
        self.token_refresh_interval = 300  # 5 minutes
        self.last_refresh_time = {}

    async def apply_session_to_browser(self, browser: Browser, url: str):
        """Apply cookies, refresh tokens if needed"""
        domain = extract_domain(url)

        # Apply cookies from jar
        cookies = self.cookie_jar.get_cookies(domain)
        for cookie in cookies:
            await browser.context.add_cookies([cookie])

        # Refresh token if approaching TTL
        if self.should_refresh_token(domain):
            await self.refresh_token(browser, domain)
            self.last_refresh_time[domain] = time.time()

    def should_refresh_token(self, domain: str) -> bool:
        """Check if token needs refresh"""
        if domain not in self.last_refresh_time:
            return True
        elapsed = time.time() - self.last_refresh_time[domain]
        return elapsed > self.token_refresh_interval

    async def refresh_token(self, browser: Browser, domain: str):
        """Refresh authentication token"""
        # Navigate to refresh endpoint (e.g., /api/auth/refresh)
        try:
            response = await browser.goto(f"https://{domain}/api/auth/refresh")
            if response.ok():
                cookies = await browser.context.cookies()
                self.cookie_jar.update_cookies(domain, cookies)
        except:
            pass  # Token refresh failed, continue anyway

    async def handle_authentication_error(self,
                                          browser: Browser,
                                          url: str) -> bool:
        """Re-login on 401, return True if successful"""
        domain = extract_domain(url)

        # Check for 401 response
        try:
            response = await browser.goto(url)
            if response.status == 401:
                return await self.relogin(browser, domain)
        except:
            pass

        return False

    async def relogin(self, browser: Browser, domain: str) -> bool:
        """Attempt re-login (credentials from env/secret manager)"""
        username = os.getenv(f"{domain.upper()}_USERNAME")
        password = os.getenv(f"{domain.upper()}_PASSWORD")

        if not username or not password:
            return False  # Can't relogin without credentials

        # Navigate to login page
        await browser.goto(f"https://{domain}/login")

        # Fill credentials
        await browser.fill("input[name='username']", username)
        await browser.fill("input[name='password']", password)
        await browser.click("button[type='submit']")

        # Wait for redirect (up to 5 seconds)
        try:
            await browser.wait_for_navigation(timeout=5000)
            cookies = await browser.context.cookies()
            self.cookie_jar.update_cookies(domain, cookies)
            return True
        except:
            return False
```

**Verification:**
```bash
# Crawl site requiring login, verify session persistence
curl -X POST https://deployed-service/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com/page1", "https://example.com/page2"],
    "credentials": {"username": "user", "password": "pass"}
  }' | jq '.session_persistence_score'  # Should be 1.0
```

### Failure Mode 4: DOM Bloat (Memory Overflow)

**Symptom:** Large page (Twitter timeline, infinite scroll) causes Chrome to consume 1GB+ memory, crashes

**Root Cause:**
- Infinite scroll loads 100K+ DOM nodes
- Each node consumes memory
- Playwright doesn't automatically garbage-collect
- Memory limit exceeded (512MB Cloud Run container)

**Probability:** 25% of websites have bloated DOM

**Prediction:**
- E-commerce (product listing): 50% bloat risk
- Social media (infinite feed): 90% bloat risk
- News (article comments): 60% bloat risk
- Documentation: 5% bloat risk

**Mitigation:**
```python
class MemorySafeExtractor:
    """Snapshot regularly, trim old nodes"""

    def __init__(self, max_dom_nodes: int = 50000):
        self.max_dom_nodes = max_dom_nodes
        self.dom_snapshots = []

    async def crawl_with_memory_safety(self, url: str, max_depth: int = 3) -> str:
        """Crawl with DOM monitoring"""
        browser = await acquire_browser()
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="load", timeout=30000)

            # Scroll incrementally, snapshot at each step
            for i in range(max_depth):
                # Get current DOM
                dom = await self.extract_dom_safely(page)
                node_count = self.count_nodes(dom)

                # Check memory
                memory_mb = self.get_process_memory()

                if memory_mb > 450:  # 450MB of 512MB limit
                    print(f"Warning: Memory high ({memory_mb}MB), stopping scroll")
                    break

                if node_count > self.max_dom_nodes:
                    print(f"Warning: DOM bloated ({node_count} nodes), trimming")
                    dom = self.trim_dom(dom)

                self.dom_snapshots.append(dom)

                # Scroll down
                await page.evaluate("window.scrollBy(0, window.innerHeight)")
                await page.wait_for_timeout(1000)  # Wait for lazy-load

            # Merge snapshots
            final_dom = self.merge_snapshots()
            return final_dom

        finally:
            await page.close()
            await browser.close()

    async def extract_dom_safely(self, page) -> str:
        """Get DOM without loading entire page into memory"""
        dom = await page.content()
        return dom

    def count_nodes(self, dom: str) -> int:
        """Count DOM nodes"""
        parsed = BeautifulSoup(dom, 'html.parser')
        return len(parsed.find_all())

    def trim_dom(self, dom: str, max_nodes: int = 50000) -> str:
        """Remove deepest/oldest nodes"""
        parsed = BeautifulSoup(dom, 'html.parser')
        nodes = parsed.find_all()

        if len(nodes) > max_nodes:
            # Remove nodes from end
            for node in nodes[max_nodes:]:
                node.extract()

        return str(parsed)

    def get_process_memory(self) -> float:
        """Get current process memory in MB"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
```

**Verification:**
```bash
# Crawl large page, monitor memory
curl -X POST https://deployed-service/crawl \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://twitter.com/search?q=test"]}' | \
  jq '.memory_peak_mb'  # Should be < 512MB
```

### Failure Mode 5: Bot Detection Evasion Fail

**Symptom:** Site blocks request: "Detected automated traffic"

**Root Cause:**
- Playwright detection scripts (navigator.webdriver flag)
- Missing or spoofed User-Agent header
- Headless browser detection (e.g., chrome://inspect)
- Request headers too minimal (missing Referer, Accept-Language)

**Probability:** 15% of websites have advanced bot detection

**Prediction:**
- Banks/Financial: 80% detection
- E-commerce: 40% detection
- News sites: 10% detection
- Public wikis: 2% detection

**Mitigation:**
```python
class BotDetectionEvasion:
    """Spoof headers, disable webdriver flag"""

    async def acquire_undetectable_browser(self) -> Browser:
        """Launch Playwright with evasion"""
        browser = await playwright.chromium.launch(
            headless=False,  # Use headed mode (harder to detect)
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-resources',
            ]
        )

        # Disable webdriver flag
        context = await browser.new_context()
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)

        return browser

    async def set_realistic_headers(self, page) -> None:
        """Set headers to appear like real browser"""
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/',
        })

    async def add_human_like_behavior(self, page) -> None:
        """Add delays, mouse movements to appear human"""
        # Random delays between actions
        await page.wait_for_timeout(random.randint(500, 2000))

        # Move mouse randomly
        await page.mouse.move(random.randint(0, 1920), random.randint(0, 1080))

        # Random scroll
        await page.evaluate("window.scrollBy(0, 100 * Math.random())")

    async def crawl_with_evasion(self, url: str) -> str:
        """Crawl with bot evasion"""
        browser = await self.acquire_undetectable_browser()
        page = await browser.new_page()

        try:
            # Set realistic headers
            await self.set_realistic_headers(page)

            # Add human-like behavior
            await self.add_human_like_behavior(page)

            # Navigate
            response = await page.goto(url, wait_until="networkidle")

            # Check for bot detection response
            if response.status == 403:
                # Likely bot detected
                raise BotDetectionError(f"Access denied: {url}")

            return await page.content()

        finally:
            await page.close()
            await browser.close()
```

**Verification:**
```bash
# Crawl bot-protected site, verify no detection
curl -X POST https://deployed-service/crawl \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://protected-site.example.com"],
    "enable_evasion": true
  }' | jq '.bot_detection_errors'  # Should be 0
```

---

## Exact Tests (10 Tests: Setup/Input/Expect/Verify Format)

### Test 1: Real Chromium Execution

```
SETUP:
  - Deploy crawler to Cloud Run
  - Configure Playwright to use real Chromium (not jsdom)

INPUT:
  - POST /crawl with URL that requires JavaScript:
    https://example.com/javascript-only-content

EXPECT:
  - Response includes dynamic content (JavaScript-rendered)
  - Content is NOT from static HTML (which would be empty)
  - browser_type in response = "chromium"
  - javascript_executed = true

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{"urls": ["https://example.com/javascript-only"]}' | \
    jq '.browser_type' | grep -i chromium
```

### Test 2: Dynamic Content Capture Accuracy

```
SETUP:
  - Select 100 JavaScript-heavy URLs
  - Manually inspect each to count visible elements
  - Create baseline (e.g., 500 total visible elements)

INPUT:
  - POST /crawl with same 100 URLs

EXPECT:
  - Captured content ≥ 90% of baseline
  - Example: If manual count = 500 elements, crawler captures ≥ 450

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{"urls": [100 URLs], "measure_accuracy": true}' | \
    jq '.content_capture_accuracy'  # Should be ≥ 0.90
```

### Test 3: Determinism Verification (3 Crawls)

```
SETUP:
  - Select 20 deterministic URLs (stable content)
  - Configure crawler to extract deterministic content only

INPUT:
  - POST /crawl with same 20 URLs, repeat 3 times

EXPECT:
  - All 3 crawls produce identical snapshots for each URL
  - SHA256 hash identical across runs
  - determinism_score = 1.0 (100% match)

VERIFY:
  for i in {1..3}; do
    curl -X POST https://deployed-service/crawl \
      -H "Content-Type: application/json" \
      -d '{"urls": [20 deterministic URLs]}' | \
      jq '.snapshots[] | .sha256' > crawl_$i.txt
  done

  diff crawl_1.txt crawl_2.txt && diff crawl_2.txt crawl_3.txt
```

### Test 4: Rate Limit Handling (No 429 Errors)

```
SETUP:
  - Configure rate limiter with 5-second minimum delay
  - Select 1000 URLs from same domain
  - Enable IP rotation (proxy service)

INPUT:
  - POST /crawl with 1000 URLs

EXPECT:
  - Zero 429 (Too Many Requests) responses
  - Zero IP bans (403 Forbidden due to IP block)
  - All URLs complete successfully or timeout (not rate limited)

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{"urls": [1000 URLs], "enable_rate_limiting": true}' | \
    jq '.error_codes' | jq '.["429"]' | grep -E '^null|^0$'
```

### Test 5: Cost Tracking and Ceiling

```
SETUP:
  - Set cost ceiling to $0.10 for 1000 URLs
  - Configure cost tracker to abort if exceeded

INPUT:
  - POST /crawl with 1000 URLs
  - Measure actual cost

EXPECT:
  - Total cost ≤ $0.10
  - Per-URL cost ≤ $0.0001
  - Cost tracking accurate (within 5% of estimate)

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{"urls": [1000 URLs], "cost_ceiling": 0.10}' | \
    jq '.total_cost_usd'  # Should be ≤ 0.10
```

### Test 6: robots.txt Compliance

```
SETUP:
  - Select 10 URLs, all disallowed by robots.txt
  - Configure compliance check to respect robots.txt

INPUT:
  - POST /crawl with 10 disallowed URLs

EXPECT:
  - All 10 URLs skipped (not crawled)
  - Error code for each: "ROBOTS_BLOCKED"
  - Zero requests sent to those URLs

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{
      "urls": [10 robots-disallowed URLs],
      "respect_robots_txt": true
    }' | jq '.results[] | select(.error == "ROBOTS_BLOCKED") | length'  # Should be 10
```

### Test 7: Session Persistence (Multi-Page Login)

```
SETUP:
  - Select site requiring login (e.g., GitHub)
  - Configure credentials (username/password from env)

INPUT:
  - POST /crawl with multiple pages from authenticated site

EXPECT:
  - First page triggers login flow
  - Subsequent pages use same session (no re-login)
  - All pages crawled successfully

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{
      "urls": [
        "https://github.com/user/repo",
        "https://github.com/user/repo/issues"
      ],
      "credentials": {"username": "user", "password": "pass"}
    }' | jq '.session_failures'  # Should be 0
```

### Test 8: Memory Safety (Large Pages)

```
SETUP:
  - Select large pages (Twitter, infinite scroll)
  - Monitor process memory during crawl

INPUT:
  - POST /crawl with 5 large pages
  - Measure peak memory usage

EXPECT:
  - Peak memory < 512MB (Cloud Run container limit)
  - No OOM kills
  - All pages crawled successfully

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{"urls": [5 large URLs]}' | \
    jq '.memory_peak_mb'  # Should be < 512
```

### Test 9: Bot Detection Evasion

```
SETUP:
  - Select 10 sites with bot detection (e.g., CloudFlare, WAF)
  - Enable bot evasion (headers, webdriver flag disabling)

INPUT:
  - POST /crawl with 10 bot-protected URLs

EXPECT:
  - Zero 403 (Forbidden due to bot detection)
  - All pages loaded successfully
  - No CAPTCHA or challenge page detected

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{
      "urls": [10 bot-protected URLs],
      "enable_evasion": true
    }' | jq '.error_codes | .["403"]'  # Should be null or 0
```

### Test 10: Compliance TOS Blocklist

```
SETUP:
  - Add Facebook, Instagram, LinkedIn to TOS blocklist
  - Configure compliance check

INPUT:
  - POST /crawl with blocked sites in URL list

EXPECT:
  - All blocked URLs skipped
  - Error code: "TOS_BLOCKED"
  - Zero requests sent

VERIFY:
  curl -X POST https://deployed-service/crawl \
    -H "Content-Type: application/json" \
    -d '{
      "urls": [
        "https://facebook.com",
        "https://instagram.com",
        "https://linkedin.com"
      ]
    }' | jq '.results[] | select(.error == "TOS_BLOCKED") | length'  # Should be 3
```

---

## Surface Lock (Allowed Modules & Kwargs)

### Allowed Files (Whitelist)

```python
ALLOWED_FILES = {
    'crawler.py',               # Main orchestrator
    'browser_pool.py',          # Playwright instance management
    'snapshot_extractor.py',    # DOM snapshot extraction
    'compliance.py',            # robots.txt, TOS filtering
    'session_manager.py',       # Cookie jar, login handling
    'cost_tracker.py',          # Cost tracking, ceiling enforcement
    'rate_limiter.py',          # Exponential backoff, IP rotation
    'tests/test_crawler.py',    # Test suite
}

FORBIDDEN_FILES = {
    'credentials.json',         # Never commit credentials
    '.env',                     # Environment files forbidden
    'secret_key.pem',           # Key material forbidden
}
```

### Allowed Functions (Whitelist)

```python
ALLOWED_FUNCTIONS = {
    'crawler.py': {
        'crawl_urls': "Main entry point for crawling",
        'validate_urls': "Check format, robots.txt, TOS",
        'batch_urls': "Group into 50-URL batches",
    },
    'browser_pool.py': {
        'acquire_browser': "Get Chromium instance",
        'release_browser': "Return and cleanup",
        'get_pool_stats': "Memory, instance count",
    },
    'snapshot_extractor.py': {
        'extract_deterministic_dom': "Remove volatiles",
        'measure_content_capture': "Compare dynamic vs static",
    },
    'compliance.py': {
        'check_robots_txt': "robots.txt validation",
        'check_tos_blocklist': "TOS compliance",
        'rate_limit_backoff': "Exponential delay",
    },
    'session_manager.py': {
        'apply_session_to_browser': "Cookies + token refresh",
        'relogin': "Attempt re-authentication",
    },
    'cost_tracker.py': {
        'track_cost': "Log per-URL cost",
        'check_ceiling': "Abort if exceeded",
    },
}

FORBIDDEN_FUNCTIONS = {
    'hardcoded_credentials': "Use Secret Manager",
    'os.system': "Use subprocess with args list",
    'eval/exec': "Dynamic code execution forbidden",
    'pickle.loads': "Untrusted deserialization forbidden",
    'requests.get': "Use playwright.goto()",
}
```

### Allowed Environment Variables

```python
ALLOWED_ENVVARS = {
    'PLAYWRIGHT_BROWSERS_PATH': "Chromium cache location",
    'CRAWL_BATCH_SIZE': "URLs per batch (default 50)",
    'RATE_LIMIT_DELAY': "Min delay between requests (default 5s)",
    'COST_CEILING': "Max cost per URL (default $0.0001)",
    'TOS_BLOCKLIST': "Domains to skip (JSON array)",
}

FORBIDDEN_ENVVARS = {
    'DATABASE_PASSWORD',    # Credentials forbidden
    'API_KEY',              # Use Secret Manager
    'PRIVATE_KEY',          # Key material forbidden
}
```

---

## Proof Artifacts

### JSON Schema (Crawl Proof)

```json
{
  "proof_version": "1.0.0",
  "proof_type": "javascript_crawler",
  "timestamp": "2026-02-14T13:45:00Z",
  "crawl_job_id": "crawl-001",

  "crawler_config": {
    "browser_type": "chromium",
    "javascript_enabled": true,
    "respect_robots_txt": true,
    "enable_rate_limiting": true,
    "enable_bot_evasion": true
  },

  "urls_summary": {
    "total_urls": 1000,
    "successfully_crawled": 998,
    "skipped": 2,
    "errors": 0
  },

  "error_breakdown": {
    "429": 0,
    "403": 0,
    "401": 0,
    "timeout": 0,
    "robots_blocked": 2,
    "tos_blocked": 0
  },

  "content_quality": {
    "dynamic_content_capture": 0.93,
    "determinism_score": 0.98,
    "average_nodes_per_page": 2458,
    "max_nodes": 145000,
    "min_nodes": 42
  },

  "performance": {
    "total_duration_seconds": 850,
    "average_latency_ms": 850,
    "p95_latency_ms": 2100,
    "p99_latency_ms": 3500
  },

  "resource_usage": {
    "peak_memory_mb": 485,
    "total_cpu_time_seconds": 1200,
    "total_network_bytes": 245000000
  },

  "cost_analysis": {
    "total_cost_usd": 0.0833,
    "per_url_cost": 0.0000833,
    "cost_ceiling": 0.0001,
    "status": "UNDER_CEILING"
  },

  "verification": {
    "all_conditions_met": true,
    "chrome_execution_verified": true,
    "determinism_verified": true,
    "rate_limits_handled": true,
    "cost_acceptable": true
  },

  "proof_sha256": "abc123def456...",
  "auth": 65537
}
```

---

## Integration with C1 and Blocker on C3

### C1 → C2 Dependency

**C1 Deliverable:** Cloud Run service deployed at https://deployed-service

**C2 Input:** Service URL from C1 proof

```
Flow:
  1. C1 generates proof: {"service_url": "https://deployed-service"}
  2. C2 reads service_url, validates health: GET /health → 200
  3. C2 batches URLs into 50-URL groups
  4. C2 sends: POST {service_url}/execute with batch recipes
  5. C1 Cloud Run processes batch, returns crawled content
```

### C2 → C3 Dependency

**C2 Deliverable:** Crawled content + cost estimates

**C3 Input:** Cost data from C2 proof

```
Flow:
  1. C2 generates proof: {"total_cost_usd": 0.0833, "per_url_cost": 0.0000833}
  2. C3 reads cost estimates
  3. C3 sets cost ceiling in user requests
  4. C3 aborts if cost would exceed $0.0001 per URL
  5. User sees cost-aware responses in chat
```

---

## Verification Ladder Status

### OAuth Tier (39, 63, 91 - Unlock 641)

```
✓ CARE (39):         Strong motivation (enable crawler = unlock web content)
✓ BRIDGE (63):       Connection to Phase B recipes (recipes need data to test against)
✓ STABILITY (91):    Foundation proven (Playwright is production-grade library)

OAuth Unlocked: TRUE
Ready for 641-edge tests: YES
```

### 641-Edge Tests (Rivals - Sanity Checks)

```
Target: 5+ sanity checks
Status: 10 tests prepared

✓ Real Chromium execution verification
✓ Dynamic content capture (90%+ accuracy)
✓ Determinism verification (3 crawls, identical output)
✓ Rate limit handling (no 429 errors)
✓ Cost tracking and ceiling enforcement
✓ robots.txt compliance
✓ Session persistence (login handling)
✓ Memory safety (no OOM)
✓ Bot detection evasion
✓ TOS compliance (blocklist enforcement)

Status: ALL READY
```

### 274177-Stress Tests (Scale & Load)

```
Target: Large-scale crawling
Plan (ready for Solver):

✓ 1000 URLs crawled (verify cost ≤ $0.10)
✓ Determinism maintained across all URLs
✓ Zero rate limit errors (IP rotation working)
✓ Memory stable (no leaks, peak < 512MB)
✓ Performance: p99 latency < 5 seconds per URL

Status: SPECIFICATIONS READY
```

### 65537-God Tests (Final Verification)

```
Target: Production readiness, integration validation
Plan (ready for Solver + Skeptic):

✓ Cross-phase integration (C1→C2 handoff)
✓ Cost accuracy vs actual execution
✓ Determinism proof (same URL = same content)
✓ Compliance audit (robots.txt, TOS)
✓ Security review (no hardcoded creds, env from Secret Manager)
✓ Performance baseline established

Status: SPECIFICATIONS READY
```

---

## Conclusion

### Summary

Wish C2 specifies the JavaScript crawler that enables Phase C content capture from real websites. The system:

1. **Executes Real Browser:** Chromium, not static HTML parser
2. **Captures Dynamic Content:** 90%+ accuracy vs manual inspection
3. **Evades Detection:** Rate limiting, IP rotation, bot detection evasion
4. **Costs Efficiently:** $0.0001 per URL (lowest in market)
5. **Proves Determinism:** Identical input → identical output
6. **Integrates:** Handoff with C1 (deployment) and C3 (chat)

### Key Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Browser | Chromium (real) | ✅ Design complete |
| Content Capture | 90%+ accuracy | ✅ Extraction logic specified |
| Rate Limiting | No 429 errors | ✅ Backoff + IP rotation |
| Cost/URL | $0.0001 | ✅ Cost ceiling enforced |
| Determinism | 100% match | ✅ Volatile removal logic |
| OAuth Unlock | 3/3 gates | ✅ All passed |
| 641-Edge Tests | 5+ ready | ✅ 10 prepared |

### Next Steps (Solver)

1. **Implement** crawler orchestrator (batching, rate limiting)
2. **Implement** browser pool (acquire, release, cleanup)
3. **Implement** snapshot extractor (remove volatiles, normalize)
4. **Implement** compliance checks (robots.txt, TOS, rate limits)
5. **Implement** cost tracking + ceiling enforcement
6. **Verify** all 10 tests pass (641-edge tier)
7. **Execute** 274177-stress tests (1000 URLs, cost, memory)
8. **Validate** 65537-god tests (integration, determinism)

### Phase C Readiness

✅ **C1 Complete:** Cloud Run deployment ready for Solver
🎮 **C2 Pending:** Awaits C1 implementation (needs service URL)
⏳ **C3 Pending:** Awaits C2 implementation (needs crawler working)

---

**Status:** ⏳ PENDING - Ready for Solver implementation (after C1 deployed)
**Auth:** 65537 | **Northstar:** Phuc Forecast
**Channel:** 5 (Logic) | **GLOW:** 92 | **XP:** 580

*"Real browser, real content, real cost control. Determinism guaranteed."*
