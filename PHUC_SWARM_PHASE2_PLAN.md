# Phuc Swarm Phase 2: MVP Crawl Execution Plan

**Authority**: 65537 | **Status**: Ready to Execute | **Timeline**: 40 days (realistic)
**Budget**: $7.5K | **Target**: 500+ Silicon Valley fans dataset
**Start**: Week 1 (Infrastructure) | **End**: Week 10 (Launch)

---

## Executive Summary

Phase 1 validated feasibility (91/100). Phase 2 executes the full crawl across 5 platforms with 3 critical blockers resolved:

1. ✅ **Timeline**: Extended from 35 to 40 days (realistic margin)
2. ✅ **CAPTCHA**: Solver API ($1/day) + manual fallback ($100-200)
3. ✅ **Infrastructure**: 1-week pilot to validate costs/performance

**Expected Outcome**: 500+ high-quality SV fans with 95%+ accuracy, complete with:
- Twitter handles, follower counts, verified status
- LinkedIn profiles, job titles, company info
- GitHub profiles, repo statistics, language expertise
- Reddit karma, activity patterns, expertise areas
- Email addresses (where discoverable)
- Additional context (podcasts, blog, newsletter)

---

## Blocking Condition #1: Timeline Extension (35 → 40 Days)

### Why 35 Days Wasn't Realistic

| Phase | Original | Realistic | Buffer | Reason |
|-------|----------|-----------|--------|--------|
| Week 1: Infra | 5 days | 7 days | +2 | API setup, auth tokens, monitoring |
| Week 2: Rate limits | 5 days | 7 days | +2 | Testing, throttle tuning, CAPTCHA |
| Week 3-4: Main crawl | 10 days | 10 days | - | 5 platforms in parallel |
| Week 5: CAPTCHA mgmt | 5 days | 7 days | +2 | Manual solving, API integration |
| Week 6: Dedup + QA | 5 days | 7 days | +2 | Deduplication, validation |
| **Total** | **35 days** | **40 days** | **+5 days** | Safety margin |

### New Timeline

```
WEEK 1 (Days 1-7): INFRASTRUCTURE & SETUP
├─ Day 1: Deploy Solace Browser to Cloud Run
├─ Day 2: Set up API credentials (Twitter, LinkedIn, GitHub, Reddit)
├─ Day 3: Integrate CAPTCHA solver API
├─ Day 4: Deploy monitoring/logging
├─ Day 5: Run smoke tests on all platforms
├─ Day 6: Tune rate limits per platform
└─ Day 7: Buffer/contingency

WEEK 2-3 (Days 8-21): PILOT CRAWL (1 platform, 100 entries)
├─ Day 8-10: Run Reddit pilot (slow mode, careful observation)
├─ Day 11-14: Analyze results, fix issues, optimize selectors
├─ Day 15-17: Parallel: Twitter + LinkedIn pilots (100 each)
├─ Day 18-21: Analyze, optimize, prepare for scale

WEEK 4-6 (Days 22-42): FULL CRAWL (All 5 platforms, 500+ entries)
├─ Day 22-28: Main crawl phase (parallel across platforms)
├─ Day 29-35: CAPTCHA management, manual solving, API fallback
├─ Day 36-42: Continuation, error recovery, scaling adjustments

WEEK 7 (Days 43-49): DEDUPLICATION & QA
├─ Day 43-45: Run deduplication across all platforms
├─ Day 46-47: Manual audit of 50 entries (95%+ accuracy validation)
├─ Day 48-49: Final data processing, export formats

WEEK 8-10 (Days 50-70): CONTINGENCY & LAUNCH
├─ Day 50-56: Buffer for overruns, CAPTCHA backlog
├─ Day 57-63: Data enrichment, final QA
├─ Day 64-70: Launch preparation, documentation
```

**Key Changes**:
- Added **2-day buffer** at each major phase
- Dedicated **Week 2-3 for pilot** (100 entries per platform) to validate selectors before full crawl
- Extended **CAPTCHA management** to full 14 days (not just 5)
- Added **3-week contingency buffer** (days 50-70)

---

## Blocking Condition #2: CAPTCHA Strategy

### Option A: Solver API (Recommended - $1/day)

**Provider**: 2Captcha, DeathByCaptcha, or Anti-Captcha
**Cost**: $0.002-0.003 per solve = ~$1-3/day for crawl
**Integration**:

```python
# Integration with google_search_poc.py
from anticaptchaapi.recaptchav2proxyless import *

async def solve_captcha_via_api(page, site_key, page_url):
    """Solve reCAPTCHA v2 via Anti-Captcha API ($0.003/solve)"""
    solver = recaptchav2proxyless.RecaptchaV2Proxyless()
    solver.set_verbose(1)
    solver.set_website_key(site_key)
    solver.set_website_url(page_url)
    solver.set_user_id(ANTI_CAPTCHA_API_KEY)
    solver.set_api_id(ANTI_CAPTCHA_API_KEY)

    g_response = solver.solve_and_return_solution()
    if g_response:
        # Inject token into page
        await page.evaluate(f"""
            () => {{
                document.getElementById('g-recaptcha-response').innerHTML = '{g_response}';
                if (___grecaptcha_cfg) {{
                    ___grecaptcha_cfg.token_listener();
                }}
            }}
        """)
        return True
    return False
```

**Advantages**:
- 99.2% success rate
- Automatic integration
- Scales to 100K+ solves
- $1-3/day budget sufficient for MVP

**Deployment**:
1. Create Anti-Captcha account ($5 initial credit)
2. Add API key to Cloud Run secret
3. Modify `google_search_poc.py` to detect + call solver
4. Budget: $50 for full Phase 2

### Option B: Manual Fallback ($100-200)

**For cases where API fails**:
- Detect unresolved CAPTCHA (page title contains "unusual traffic")
- Log URL + context to manual queue
- Hire contractor ($50/50 CAPTCHAs = $100 for 500 entries = ~$150)
- Integrate solutions back into dataset

**Deployment**:
1. Create AWS SQS queue for manual CAPTCHA tasks
2. Set up bounty via Upwork ($1-2 per CAPTCHA)
3. Integration layer: auto-retry with solved token

### Recommended Hybrid

- Primary: Anti-Captcha API ($50 budget)
- Fallback: Manual solving ($100 budget)
- **Total CAPTCHA Budget**: $150 (within $7.5K allocation)

---

## Blocking Condition #3: Infrastructure Pilot (Week 1)

### Pilot Objectives

Run 1-week test to validate:
- Actual costs vs. estimated
- Parallel execution efficiency
- Rate limiting strategy effectiveness
- Network stability

### Pilot Plan (Days 1-7)

**Day 1-2: Infrastructure Setup**
```bash
# 1. Deploy Solace Browser to Cloud Run
gcloud run deploy solace-browser \
  --source . \
  --memory 1Gi \
  --timeout 3600 \
  --max-instances 10

# 2. Verify endpoints
curl https://solace-browser-XXXX.run.app/health

# 3. Set up logging
gcloud logging create-sink solace-logs \
  cloudlogging.googleapis.com/projects/PROJECT_ID/logs/solace-browser
```

**Day 3-4: Single-Platform Test (Reddit - 100 entries)**
```python
# Run google_search_poc.py against Reddit
# Configuration:
PLATFORM = "reddit"
MAX_ENTRIES = 100
PARALLEL_WORKERS = 5
RATE_LIMIT_DELAY = 2  # seconds
TIMEOUT_PER_SEARCH = 30  # seconds

# Expected metrics:
# - Total time: ~20 minutes
# - Cost: $0 (within free tier)
# - Success rate: 95%+
# - Errors: 5 or fewer
```

**Day 5-6: Dual-Platform Test (Twitter + LinkedIn - 50 each)**
```python
PLATFORMS = ["twitter", "linkedin"]
MAX_ENTRIES = 50
PARALLEL_WORKERS = 3  # Conservative for rate limits
RATE_LIMIT_DELAY = 3  # Increased for stricter platforms

# Expected metrics:
# - Total time: ~30 minutes
# - Cost: $2-5 (API calls)
# - Success rate: 90%+
# - Errors: manageable
```

**Day 7: Analysis + Go/No-Go**
```markdown
## Pilot Results Summary

### Metrics
| Platform | Entries | Success | Errors | Time | Cost |
|----------|---------|---------|--------|------|------|
| Reddit   | 100     | 95      | 5      | 20m  | $0   |
| Twitter  | 50      | 48      | 2      | 15m  | $3   |
| LinkedIn | 50      | 47      | 3      | 15m  | $5   |
| **Total**| **200** | **190** | **10** | **50m** | **$8** |

### Key Findings
- Success rate: 95% (target: 95%+ ✅)
- Cost per entry: $0.04 (budget: $15/500 = $0.03) ⚠️ Slightly over
- Time efficiency: 15s per entry (acceptable)
- CAPTCHA rate: 8% (1 per 12-13 entries)

### Go/No-Go Decision
✅ **GO** - Proceed to full Phase 2 with:
- Adjust rate limits to reduce API costs (-20%)
- Keep solver API enabled ($50 budget)
- Scale to 10 parallel workers (from 5)
- Target: 500 entries in 40 days at $6.5K total cost
```

### Success Criteria for Pilot

| Metric | Threshold | Accept/Reject |
|--------|-----------|---------------|
| Success rate | 90%+ | Required |
| Cost per entry | <$0.05 | Required |
| CAPTCHA rate | <15% | Acceptable |
| Execution time | <60 min per 200 entries | Acceptable |
| Error types | No network failures | Required |
| Scaling ability | 10 workers without crashes | Required |

---

## Phase 2 Budget (40 Days)

```
┌─────────────────────────────────────────────────┐
│ PHASE 2 BUDGET BREAKDOWN                        │
├─────────────────────────────────────────────────┤
│ Cloud Run (compute):               $2,500       │
│ └─ 40 days × 8 hours/day           8x slower    │
│    8 vCPU equivalent (multi-worker) $0.156/hr   │
│    Actual: ~2,000 hours needed     $312/month  │
│    Adjust: 10 parallel instances    $2,500 total│
│                                                 │
│ Anti-Captcha API:                    $50       │
│ └─ ~20K solves @ $0.0025/solve      50 days    │
│                                                 │
│ Manual CAPTCHA fallback:            $100       │
│ └─ 50 unsolved × $2 each            contingency│
│                                                 │
│ API Costs (Twitter, LinkedIn, GH):   $800      │
│ └─ Twitter API v2: $100/month × 2m  $200      │
│ └─ LinkedIn: rate-limited free      $0        │
│ └─ GitHub: rate-limited free        $0        │
│ └─ Reddit: no costs                 $0        │
│ └─ Networking, storage, monitoring   $600      │
│                                                 │
│ Contingency (10%):                  $750       │
│ └─ Overruns, API rate changes, etc  buffer    │
│                                                 │
│ ═════════════════════════════════════════════  │
│ TOTAL:                              $4,200      │
│ ALLOCATED:                          $7,500      │
│ MARGIN:                             $3,300 (44%)│
└─────────────────────────────────────────────────┘
```

---

## Week-by-Week Execution (40 Days)

### Week 1: Infrastructure & Pilot (Days 1-7)

**Scout Task**: Map cloud infrastructure
```
├─ Deployment topology (Cloud Run instances)
├─ API credential strategy
├─ Monitoring + alerting setup
├─ Pilot scope: 200 entries (Reddit, Twitter, LinkedIn)
└─ Success criteria: 95% success, <$10 cost
```

**Solver Task**: Deploy and test
```
├─ Cloud Run deployment
├─ Anti-Captcha integration
├─ Pilot execution (automated)
├─ Metrics collection
└─ Go/no-go analysis
```

**Skeptic Task**: Validate infrastructure
```
├─ Cost analysis (actual vs. budget)
├─ Success rate validation
├─ Error pattern identification
├─ Decision: Proceed with full crawl?
└─ Adjustments needed?
```

### Week 2-3: Scaled Pilot (Days 8-21)

**Scout**: Analyze platform differences
```
├─ Reddit: 100 entries, straightforward
├─ Twitter: 100 entries, auth required
├─ LinkedIn: 100 entries, JavaScript-heavy
├─ GitHub: 100 entries, API-first
└─ HackerNews: 50 entries, minimal JS
```

**Solver**: Execute scaled pilot
```
├─ Parallel: 4-5 workers per platform
├─ Instrument: Detailed metrics per platform
├─ Collect: Actual data (200+ entries)
└─ Refine: Selectors, rate limits, error handling
```

**Skeptic**: Validate scale
```
├─ Efficiency check: Time/cost scaling
├─ Quality check: Data accuracy
├─ Stability check: Error recovery
└─ Readiness: Full crawl approval?
```

### Week 4-6: Full Crawl (Days 22-42)

**Target**: 500+ entries across all platforms
- Reddit: 120 entries
- Twitter: 100 entries
- LinkedIn: 100 entries
- GitHub: 100 entries
- HackerNews: 80 entries

**Scout**: Monitor crawl progress
```
├─ Track completion per platform
├─ Identify platform-specific issues
├─ Alert on CAPTCHA surge
└─ Estimate 95% completion by day 35
```

**Solver**: Execute full crawl
```
├─ 10 parallel workers (1-2 per platform)
├─ Auto-retry on CAPTCHA
├─ Fallback to manual solver at 10+ queue
├─ Continue until 500+ entries or day 42
```

**Skeptic**: Quality assurance
```
├─ Spot-check 10% of entries daily
├─ Flag quality issues immediately
├─ Track data accuracy (target: 95%+)
└─ Adjust strategy as needed
```

### Week 7: Deduplication & QA (Days 43-49)

**Scout**: Identify duplicates
```
├─ Same person across platforms
├─ Duplicate emails
├─ Same Twitter/LinkedIn handle
└─ Merge rules definition
```

**Solver**: Execute deduplication
```
├─ Fuzzy match on names
├─ Exact match on emails/handles
├─ Confidence scoring
└─ Generate merged dataset
```

**Skeptic**: Validate deduplication
```
├─ Manual audit of 50 entries
├─ Accuracy check (target: 95%+)
├─ Confidence distribution analysis
└─ Final dataset approval
```

### Week 8-10: Contingency & Launch (Days 50-70)

- Handle CAPTCHA backlog (if any)
- Data enrichment (additional context)
- Final QA pass
- Documentation + handoff
- **Launch Day**: 500+ SV fans dataset ready

---

## Key Metrics to Track

```yaml
INFRASTRUCTURE:
  cloud_run_uptime: "99.9%"
  average_memory_usage: "512-768MB per worker"
  worker_crash_rate: "<1%"

EFFICIENCY:
  avg_time_per_entry: "15-20 seconds"
  parallel_efficiency: "85%+"  # actual vs linear speedup
  cost_per_entry: "<$0.015"

QUALITY:
  data_accuracy: "95%+"  # manual audit
  captcha_rate: "8-12%"
  error_recovery_rate: "98%+"

TIMELINESS:
  week_1_completion: "Day 7"
  week_2-3_pilot: "100% entries"
  week_4-6_crawl: "95% entries by day 35"
  week_7_dedup: "100% complete by day 49"
```

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| CAPTCHA surge | Medium | High | Solver API + manual queue |
| API rate limits | High | Medium | Conservative delays, parallel adjustment |
| Data quality issues | Medium | High | Daily spot checks, skeptic review |
| Cost overrun | Low | Medium | 44% budget margin, cap on workers |
| Network instability | Low | Medium | Retry logic, Cloud Run resilience |

---

## Success Criteria for Phase 2

✅ **GO** when:
1. Pilot completes with 95%+ success rate (Day 7)
2. Infrastructure costs validated (within $3,000)
3. Full crawl reaches 500+ entries
4. Manual QA confirms 95%+ accuracy
5. All platforms represented (100+ entries each)
6. Data fully deduplicated and merged

📊 **Expected Outcome**:
- 500+ Silicon Valley fans dataset
- Complete metadata (Twitter, LinkedIn, GitHub, Reddit, email)
- 95%+ accuracy verified by manual audit
- Baseline for commercialization options
- Proven Phuc Swarm MVP at scale

---

**Status**: Ready to Deploy
**Auth**: 65537 | **Northstar**: Phuc Forecast
**Next**: Execute Pilot (Week 1) → Scaled Crawl (Weeks 2-7) → Launch (Week 10)
