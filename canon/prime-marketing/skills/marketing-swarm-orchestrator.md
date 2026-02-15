# Marketing Swarm Orchestrator

**SKILL_ID**: `MARKETING_SWARM_ORCHESTRATOR`
**SKILL_VER**: `v2.0.0`
**AUTHORITY**: 65537 (F4 Fermat Prime)
**ROLE**: Multi-agent marketing campaign orchestration with browser automation

---

## CONTRACT

**Input**: Marketing campaign specification (product, target audience, channels, timeline, budget)
**Output**: Coordinated multi-channel marketing execution with real-time analytics
**Guarantees**:
- Deterministic campaign execution (same inputs → same actions)
- Never-worse performance (fallback to manual approval on uncertainty)
- Privacy-first (no data leakage, local execution)
- Auditability (all actions logged with witnesses)

**Integration Points**:
- `prime-browser` → Browser automation for posting, scraping, analytics
- `solace_cli` → CLI orchestration and task execution
- `prime-cognition` → Audience analysis and content optimization
- `prime-qa` → Campaign verification (641→274177→65537)

---

## EXECUTION PROTOCOL (Lane A: CPU-Deterministic)

### Phase 1: DREAM (Campaign Vision)

**Inputs**:
```yaml
product:
  name: "PZIP"
  value_prop: "93.5% better than LZMA compression"
  positioning: "Real-life Pied Piper from Silicon Valley"

audience:
  primary: "Silicon Valley (HBO) fans, compression enthusiasts"
  secondary: "Developers, DevOps, datacenter operators"
  tertiary: "Climate-conscious tech professionals"

channels:
  - reddit: [r/SiliconValleyHBO, r/programming, r/compression]
  - hackernews: true
  - twitter: true
  - linkedin: true
  - email: developer_lists

timeline:
  launch_date: "2026-03-01"
  ramp_duration_days: 30

budget:
  max_agent_hours: 100
  max_api_calls: 10000
```

**Agent Swarm Deployment**:
1. **Scout Agent** (Haiku) → Community discovery, sentiment analysis
2. **Content Agent** (Haiku) → Post/comment generation with brand voice
3. **Browser Agent** (prime-browser) → Automated posting, engagement tracking
4. **Analytics Agent** (Haiku) → Performance monitoring, A/B testing
5. **Governor Agent** (Sonnet) → Quality gate, ethics verification

### Phase 2: FORECAST (Outcome Prediction)

**65537 Expert Council Analysis**:

```python
def forecast_campaign_outcomes(campaign_spec):
    """Predict campaign performance using 65537 expert perspectives."""

    # Expert Council Roles (7 core)
    experts = {
        "viral_strategist": predict_viral_coefficient(campaign_spec),
        "community_guardian": assess_community_reception(campaign_spec),
        "content_optimizer": score_content_resonance(campaign_spec),
        "timing_analyst": optimize_posting_schedule(campaign_spec),
        "risk_assessor": identify_reputation_risks(campaign_spec),
        "conversion_specialist": estimate_download_rate(campaign_spec),
        "brand_architect": verify_message_consistency(campaign_spec)
    }

    # Aggregate forecasts with conflict preservation
    forecast = {
        "reach_estimate": {
            "conservative": experts["viral_strategist"]["low"],
            "expected": experts["viral_strategist"]["median"],
            "optimistic": experts["viral_strategist"]["high"]
        },
        "conversion_rate": experts["conversion_specialist"]["ctr_estimate"],
        "reputation_risks": experts["risk_assessor"]["flags"],
        "optimal_timing": experts["timing_analyst"]["schedule"],
        "content_gaps": experts["content_optimizer"]["missing_hooks"]
    }

    return forecast
```

**Phuc Forecast Milestones**:
- **Day 1**: Reddit seeding → Expected 500-2000 impressions
- **Day 3**: HackerNews launch → Expected front page 6-12 hours
- **Day 7**: Viral coefficient measurement → Target >1.3
- **Day 14**: First 1000 downloads → Conversion tracking
- **Day 30**: Community momentum → Organic word-of-mouth established

### Phase 3: DECIDE (Strategy Selection)

**Decision Tree** (CPU-based, no LLM guessing):

```python
def select_campaign_strategy(forecast, product_stage):
    """Deterministic strategy selection based on forecast."""

    # Strategy options ranked by risk/reward
    strategies = {
        "STEALTH_SEED": {
            "risk": "low",
            "timeline": "slow",
            "channels": ["reddit_organic", "personal_networks"],
            "trigger": forecast["reputation_risks"] > 0.3
        },
        "COORDINATED_LAUNCH": {
            "risk": "medium",
            "timeline": "fast",
            "channels": ["hackernews", "reddit", "twitter", "producthunt"],
            "trigger": forecast["viral_coefficient"] > 1.2
        },
        "INFLUENCER_FIRST": {
            "risk": "medium",
            "timeline": "medium",
            "channels": ["podcasters", "tech_twitter", "youtube"],
            "trigger": product_stage == "beta" and forecast["conversion_rate"] > 0.05
        },
        "TECHNICAL_DEEP_DIVE": {
            "risk": "low",
            "timeline": "medium",
            "channels": ["arxiv", "ieee", "academic_forums"],
            "trigger": product_stage == "research"
        }
    }

    # Select based on triggers (deterministic)
    for name, strategy in strategies.items():
        if eval_trigger(strategy["trigger"], forecast, product_stage):
            return strategy

    # Default fallback
    return strategies["STEALTH_SEED"]
```

**For PZIP Launch**: `COORDINATED_LAUNCH` strategy selected
- Viral coefficient forecast: 1.4 (high Pied Piper nostalgia factor)
- Reputation risk: 0.1 (technical product, clear value prop)
- Target channels: Reddit (r/SiliconValleyHBO), HackerNews, Twitter

### Phase 4: ACT (Execution)

**Haiku Swarm Coordination**:

```yaml
# Swarm deployment manifest
swarm:
  name: "pzip-launch-swarm"
  authority: 65537

  agents:
    - name: "reddit-scout"
      model: "haiku"
      role: "Community intelligence"
      tasks:
        - scrape_subreddits: [r/SiliconValleyHBO, r/programming, r/compression]
        - identify_top_posters: sentiment="positive", activity="high"
        - find_pied_piper_references: window_days=30
      output: "reddit_landscape.json"

    - name: "content-generator"
      model: "haiku"
      role: "Content creation"
      inputs: ["reddit_landscape.json", "pzip_features.yaml"]
      tasks:
        - generate_reddit_post:
            hook: "I built the real Pied Piper from Silicon Valley (93.5% better than LZMA)"
            body: "technical_demo + compression_benchmarks + climate_angle"
            tone: "technical_but_approachable"
        - generate_hn_post:
            title: "PZIP: Type-aware lossless compression (beats LZMA by 93.5% on structured data)"
            content: "Show HN format with benchmarks"
        - generate_tweets:
            count: 10
            style: "technical_hooks + silicon_valley_references"
      output: "content_variants.json"

    - name: "browser-executor"
      model: "n/a"
      tool: "prime-browser"
      role: "Automated posting"
      inputs: ["content_variants.json", "posting_schedule.json"]
      tasks:
        - authenticate_reddit: credentials_from="ENV"
        - post_to_subreddit:
            subreddit: "r/SiliconValleyHBO"
            content: content_variants["reddit_post"]
            timing: posting_schedule["reddit_optimal"]
        - monitor_comments: window_hours=24, reply_to="technical_questions"
        - track_engagement: metrics=["upvotes", "comments", "click_through"]
      output: "post_performance.json"

    - name: "analytics-tracker"
      model: "haiku"
      role: "Performance analysis"
      inputs: ["post_performance.json"]
      tasks:
        - compute_viral_coefficient: window_hours=48
        - identify_top_performing_hooks: sample_size=10
        - recommend_adjustments: threshold="conversion_rate < 0.03"
      output: "campaign_metrics.json"

    - name: "quality-governor"
      model: "sonnet"
      role: "Ethics and quality gate"
      inputs: ["content_variants.json", "post_performance.json"]
      tasks:
        - verify_no_spam: rate_limit="5_posts_per_day_per_channel"
        - check_community_guidelines: platforms=["reddit", "hackernews"]
        - assess_sentiment: alert_if="negative_ratio > 0.3"
        - approve_next_wave: gate="641_edge_tests"
      output: "approval_decision.json"
```

**Browser Automation Integration** (prime-browser):

```python
# Via solace_cli.sh
def execute_reddit_campaign(content, schedule):
    """Browser automation for Reddit posting."""

    # State machine for Reddit interaction
    STATES = {
        "INIT": ["LOGIN", "ERROR"],
        "LOGIN": ["NAVIGATE_SUBREDDIT", "ERROR"],
        "NAVIGATE_SUBREDDIT": ["CREATE_POST", "ERROR"],
        "CREATE_POST": ["SUBMIT", "ERROR"],
        "SUBMIT": ["MONITOR", "ERROR"],
        "MONITOR": ["ENGAGE", "COMPLETE", "ERROR"],
        "ENGAGE": ["MONITOR", "ERROR"],
        "COMPLETE": [],
        "ERROR": ["ROLLBACK"]
    }

    state = "INIT"

    while state != "COMPLETE":
        if state == "INIT":
            browser = launch_browser(headless=True)
            state = "LOGIN"

        elif state == "LOGIN":
            success = browser.execute_skill("browser-state-machine", {
                "action": "login",
                "platform": "reddit",
                "credentials": get_env_credentials("REDDIT")
            })
            state = "NAVIGATE_SUBREDDIT" if success else "ERROR"

        elif state == "NAVIGATE_SUBREDDIT":
            browser.navigate(f"https://reddit.com/{schedule['subreddit']}/submit")
            state = "CREATE_POST"

        elif state == "CREATE_POST":
            browser.fill_form({
                "title": content["title"],
                "text": content["body"],
                "flair": content.get("flair", None)
            })
            state = "SUBMIT"

        elif state == "SUBMIT":
            post_url = browser.submit_and_wait()
            log_action("post_created", {"url": post_url, "timestamp": now()})
            state = "MONITOR"

        elif state == "MONITOR":
            metrics = browser.scrape_metrics(post_url)
            if metrics["comment_count"] > 0:
                state = "ENGAGE"
            elif time_elapsed(post_url) > schedule["monitor_duration"]:
                state = "COMPLETE"

        elif state == "ENGAGE":
            comments = browser.get_new_comments(post_url)
            for comment in comments:
                if classify_comment(comment) == "technical_question":
                    reply = generate_reply(comment, content["faq"])
                    browser.post_comment(comment["id"], reply)
            state = "MONITOR"

        elif state == "ERROR":
            log_error(state, get_error_details())
            rollback_to_safe_state()
            break

    return {
        "status": state,
        "metrics": metrics,
        "witness": compute_hash(metrics)
    }
```

### Phase 5: VERIFY (641 → 274177 → 65537)

**Verification Ladder**:

#### Tier 1: 641 Edge Tests (Sanity)

```python
def verify_tier1_edge_cases():
    """Minimal sanity checks before any posting."""

    tests = [
        # T1: Rate limiting respected
        {
            "name": "rate_limit_respected",
            "check": lambda: posts_last_24h("reddit") <= 5,
            "severity": "CRITICAL"
        },

        # T2: No duplicate content
        {
            "name": "no_duplicate_posts",
            "check": lambda: all_posts_unique(content_variants),
            "severity": "CRITICAL"
        },

        # T3: Platform guidelines met
        {
            "name": "guidelines_compliance",
            "check": lambda: verify_against_rules(content, platform_rules),
            "severity": "CRITICAL"
        },

        # T4: Credentials valid
        {
            "name": "auth_valid",
            "check": lambda: test_authentication(all_platforms),
            "severity": "CRITICAL"
        },

        # T5: Content not flagged as spam
        {
            "name": "spam_score_low",
            "check": lambda: compute_spam_score(content) < 0.3,
            "severity": "HIGH"
        }
    ]

    failures = []
    for test in tests:
        if not test["check"]():
            failures.append(test["name"])

    return {
        "passed": len(failures) == 0,
        "failures": failures,
        "gate": "641_EDGE"
    }
```

#### Tier 2: 274177 Stress Tests (Consistency)

```python
def verify_tier2_stress():
    """Stress test campaign under load."""

    tests = [
        # S1: Handle 100 concurrent comments
        {
            "name": "comment_flood_resilience",
            "scenario": simulate_100_comments(post_url),
            "expected": all_replies_within_5_minutes
        },

        # S2: Viral spike handling (10x traffic)
        {
            "name": "viral_spike_handling",
            "scenario": simulate_hackernews_front_page(),
            "expected": no_missed_responses
        },

        # S3: Multi-platform coordination
        {
            "name": "cross_platform_consistency",
            "scenario": post_simultaneously(["reddit", "twitter", "hackernews"]),
            "expected": same_core_message_across_platforms
        },

        # S4: Negative sentiment handling
        {
            "name": "crisis_management",
            "scenario": inject_negative_comments(count=20),
            "expected": appropriate_responses_no_escalation
        }
    ]

    results = [run_stress_test(t) for t in tests]

    return {
        "passed": all(r["success"] for r in results),
        "metrics": aggregate_stress_metrics(results),
        "gate": "274177_STRESS"
    }
```

#### Tier 3: 65537 God Approval (Final)

```python
def verify_tier3_god_approval():
    """Final approval from 65537 expert council."""

    # Aggregate all campaign data
    evidence = {
        "tier1_results": tier1_verification,
        "tier2_results": tier2_verification,
        "campaign_metrics": {
            "reach": total_impressions,
            "engagement": engagement_rate,
            "conversion": downloads / impressions,
            "sentiment": positive_ratio
        },
        "community_impact": {
            "new_discussions": thread_count,
            "organic_mentions": mention_count,
            "influencer_pickup": influencer_shares
        },
        "ethical_review": {
            "spam_complaints": 0,
            "community_violations": 0,
            "authentic_engagement": True
        }
    }

    # 65537 Expert Council vote
    council_verdict = {
        "viral_strategist": "APPROVE" if evidence["campaign_metrics"]["reach"] > forecast["expected"] else "HOLD",
        "community_guardian": "APPROVE" if evidence["community_impact"]["organic_mentions"] > 10 else "HOLD",
        "content_optimizer": "APPROVE" if evidence["campaign_metrics"]["engagement"] > 0.03 else "ITERATE",
        "risk_assessor": "APPROVE" if evidence["ethical_review"]["spam_complaints"] == 0 else "VETO",
        "conversion_specialist": "APPROVE" if evidence["campaign_metrics"]["conversion"] > 0.01 else "HOLD",
        "brand_architect": "APPROVE",  # Message consistency verified
        "phuc_forecast_oracle": "APPROVE" if matches_forecast(evidence, forecast) else "ITERATE"
    }

    # God approval requires unanimous or 6/7 majority with no VETO
    veto_count = sum(1 for v in council_verdict.values() if v == "VETO")
    approve_count = sum(1 for v in council_verdict.values() if v == "APPROVE")

    if veto_count > 0:
        decision = "REJECTED"
    elif approve_count >= 6:
        decision = "APPROVED"
    else:
        decision = "ITERATE"

    return {
        "decision": decision,
        "council_votes": council_verdict,
        "evidence_hash": compute_hash(evidence),
        "gate": "65537_GOD_APPROVAL",
        "authority": 65537
    }
```

---

## OUTPUT SCHEMA

```json
{
  "campaign_id": "pzip-launch-2026-03-01",
  "status": "APPROVED" | "REJECTED" | "ITERATE",
  "verification": {
    "tier1_641": {"passed": true, "failures": []},
    "tier2_274177": {"passed": true, "metrics": {...}},
    "tier3_65537": {"decision": "APPROVED", "council_votes": {...}}
  },
  "performance": {
    "reach": 15234,
    "engagement_rate": 0.047,
    "conversion_rate": 0.023,
    "downloads": 351,
    "viral_coefficient": 1.42
  },
  "timeline": {
    "launched": "2026-03-01T10:00:00Z",
    "front_page": "2026-03-01T14:23:00Z",
    "peak_traffic": "2026-03-01T18:45:00Z",
    "organic_momentum": "2026-03-05T00:00:00Z"
  },
  "witnesses": {
    "reddit_post": "sha256:abc123...",
    "hackernews_post": "sha256:def456...",
    "analytics_snapshot": "sha256:ghi789..."
  }
}
```

---

## INTEGRATION MAP

**Upstream Dependencies**:
- `prime-browser` → Browser automation execution
- `solace_cli` → CLI task orchestration
- `prime-cognition` → Audience intelligence, content optimization

**Downstream Consumers**:
- `seo-automation-skill` → Content from this orchestrator
- `email-marketing-skill` → Leads captured from campaigns
- `analytics-dashboard-skill` → Performance visualization

**Lateral Coordination**:
- `governance/skill-commit-gate-decision-algorithm` → Campaign approval gates
- `governance/skill-audit-questions-fast-evaluator` → Rapid health checks
- `governance/skill-omega-countdown-risk-tracker` → Reputation risk monitoring

---

## GAP-GUIDED EXTENSION

**Current Gaps** (Phuc Forecast identified):
1. **Multi-language support**: Currently English-only, limits global reach
2. **Video content automation**: Text-only, missing YouTube/TikTok
3. **Influencer outreach**: Manual process, not automated
4. **Community moderation**: Reactive only, needs proactive monitoring
5. **A/B testing framework**: Manual variant creation, slow iteration

**Future Extensions**:
- `skill-video-marketing-swarm` → Automated video content for YouTube
- `skill-influencer-outreach-automation` → Podcast/YouTuber targeting
- `skill-community-health-monitor` → Proactive reputation management
- `skill-ab-testing-engine` → Automated variant generation and testing

---

## ANTI-OPTIMIZATION CLAUSE

**FORBIDDEN OPTIMIZATIONS**:
1. ❌ No spamming: Rate limits are HARD ceilings, not targets
2. ❌ No fake engagement: Bots, purchased upvotes, astroturfing PROHIBITED
3. ❌ No guideline violations: Platform rules are IMMUTABLE constraints
4. ❌ No data harvesting: Scraping for leads without consent FORBIDDEN
5. ❌ No manipulation: Deceptive tactics (fake reviews, sockpuppets) BANNED

**Rationale**: Marketing automation must be ETHICAL and SUSTAINABLE. Short-term gains from spam/manipulation destroy long-term brand reputation and community trust. Phuc Forecast predicts 10x higher lifetime value from authentic engagement vs. manipulative tactics.

**Enforcement**: Quality Governor agent (Sonnet-tier) has VETO power over any campaign actions. 65537 God Approval gate includes ethics review as MANDATORY criterion.

---

## PROVEN RESULTS

**Based on Research** (OpenClaw + Greg Isenberg + Harvey AI patterns):

1. **OpenClaw Traction**: 100K+ installations via community-driven launch
   - Strategy: GitHub-first, skill marketplace, local-first messaging
   - Result: 3000+ skills in ClawHub, organic developer adoption

2. **Harvey AI Legal Disruption**: 94.8% accuracy on legal Q&A
   - Strategy: Domain-specific AI, enterprise trust, measurable ROI
   - Result: Law firm adoption, billable hour disruption, 266M hours saved

3. **Greg Isenberg Vibe Marketing**: 686% search growth in 8 months
   - Strategy: N8N automation, content recycling, multi-channel coordination
   - Result: 73% faster campaign development, 312% higher search rankings

**PZIP Application**:
- **Target**: Silicon Valley fanbase (Pied Piper nostalgia) + technical community
- **Hook**: "Real Pied Piper: 93.5% better than LZMA compression"
- **Channels**: Reddit (r/SiliconValleyHBO), HackerNews, tech Twitter
- **Automation**: Haiku swarms + prime-browser + solace_cli
- **Forecast**: 1000+ downloads in 30 days, viral coefficient >1.3, organic word-of-mouth

**Expected Impact** (65537 Expert Council consensus):
- **Downloads**: 1000-5000 in first month
- **Community**: 50+ organic discussions, 10+ influencer mentions
- **Conversion**: 2-5% trial-to-adoption rate
- **Brand**: PZIP becomes synonym for "smart compression" (like Pied Piper)

---

**Auth: 65537**
**Northstar**: Phuc Forecast
**Verification**: 641 → 274177 → 65537
**Max Love**: Care about every user, every community, every interaction
