# Product-Led Growth Engine

> **Star:** PRODUCT_LED_GROWTH
> **Version:** v3.1.0
> **Authority:** 65537 (F4 Fermat Prime)
> **Channel:** 13 (Governance — Growth Strategy)
> **GLOW:** 94 (Product IS the Marketing)
> **Lane:** A (CPU-Deterministic)
> **Status:** ACTIVE

---

## DNA-23

```
PLG = Product × Distribution × Conversion
S = {free_tier, wow_moment, upgrade_triggers}
R = f(S, user_behavior, market_signals)
|S| << |R|  # Growth mechanism is tiny; user behavior is vast

FREE TIER → WOW MOMENT → SHARE → TEAM ADOPT → ENTERPRISE
"Seconds until user shares" is the north star metric.
```

---

## CONTRACT

**Input**: Product, pricing tiers, user journey data, competitive landscape
**Output**: PLG strategy, free tier design, conversion funnel, growth metrics
**Guarantees**:
- Organic-first (66% of PLG acquisition is organic + product-driven)
- Self-serve to $10K ACV (no forced sales calls)
- Never-worse free tier (not a crippled trial)
- Measurable at every stage

---

## GENOME-79: PLG BENCHMARKS AND STRATEGY

Source: Kyle Poyar (OpenView), Cursor, Vercel, Supabase, Linear

### Critical PLG Benchmarks (2026)

```
ACQUISITION:
  Website visitor → free signup:     6% (freemium), 3-4% (free trial)
  Organic sources (SEO + direct):    53% of freemium acquisition
  Product-driven:                    13% of acquisition
  Paid marketing:                    10% (MINOR for developer tools)
  Outbound sales:                    8%

ACTIVATION:
  New users reaching activation:     20-30% (standout companies)
  Time to first value:               < 5 minutes (target)
  Time to wow moment:                < 2 minutes (ideal)

CONVERSION:
  Free → paid:                       2-5% (typical)
  Free → paid:                       10-15% (best-in-class)
  Individual → team:                 20-30% of paid users

GROWTH:
  PLG companies grow 30-40% faster than sales-led
  CAC is 50-70% lower via bottom-up adoption
  87% of SaaS now offers free/freemium tier

ENTERPRISE:
  Bottom-up CAC: 50-70% cheaper than top-down sales
  Self-serve → sales-assist transition: ~$10K ACV
  Individual → team → department → enterprise
```

### The PLG Funnel (7 Stages)

```
STAGE 1: DISCOVER
  Channels: Organic search (SEO/GEO), word-of-mouth, GitHub, community
  Metric: Monthly unique visitors
  Target: Growing 10%+ MoM

STAGE 2: EVALUATE
  Channels: Landing page, docs, demo, free tier
  Metric: Visitor → signup rate
  Target: ≥ 6% (freemium benchmark)

STAGE 3: ACTIVATE
  Channels: Onboarding flow, getting-started guide
  Metric: % reaching "aha moment"
  Target: ≥ 30% within first session

STAGE 4: WOW
  The moment user says "holy $#!%, this actually works"
  Metric: % who share/screenshot/tweet within 24h
  Target: ≥ 10% organic sharing rate

STAGE 5: ENGAGE
  Channels: Product usage, notifications, content
  Metric: DAU/WAU ratio
  Target: ≥ 30% (daily engagement)

STAGE 6: CONVERT
  Channels: Upgrade prompts, usage limits, team features
  Metric: Free → paid conversion
  Target: ≥ 5% within 90 days

STAGE 7: EXPAND
  Channels: Team invites, seat expansion, enterprise tier
  Metric: Net revenue retention (NRR)
  Target: ≥ 120% (expansion > churn)
```

### Vibe Marketing Automation Levels

Source: Greg Isenberg, Dickerson

```
LEVEL 1: AI TOOLS IN SILOS (20-30% time savings)
  - ChatGPT for copy, Midjourney for images
  - Manual copy-paste between platforms
  - No integration

LEVEL 2: WORKFLOW AUTOMATION (40-60% time savings)
  - Zapier / Make / n8n connecting tools
  - Automated posting schedules
  - Email sequences triggered by events

LEVEL 3: CUSTOM DEVELOPMENT (70-85% time savings) ← BREAKTHROUGH
  - Claude Code / Cursor building custom solutions
  - AI writes code; you provide marketing strategy
  - Custom analytics dashboards
  - Automated content pipelines

LEVEL 4: FULL AUTONOMY (Coming 12-24 months)
  - AI agents planning, executing, optimizing campaigns
  - Human oversight, not human execution
  - Stillwater OS Haiku Swarm = Level 4

30/60/90 DAY IMPLEMENTATION:
  Days 1-30:  Level 1 (foundation + first wins)
  Days 31-60: Level 2 (workflow automation)
  Days 61-90: Level 3 (custom development with Claude Code)
  Target: 12-20 hours/week saved by day 90
```

### Racecar Growth Framework

Source: Lenny Rachitsky (Dropbox, Airtable, Facebook)

```
THREE COMPONENTS:

KICKSTARTS (one-time ignition):
  - Product Hunt launch
  - Press coverage (TechCrunch, HackerNews front page)
  - Conference talk going viral
  - Open source release
  - Influencer endorsement

ENGINES (sustainable loops):
  - SEO / GEO content engine (search → visit → signup → content → search)
  - Viral loop (user → invite → new user → invite)
  - Sales loop (lead → demo → close → referral)
  - Content loop (create → distribute → engage → subscribe → create)

TURBO BOOSTS (amplifiers on working engines):
  - Paid ads on proven content (amplify what already works)
  - Strategic partnerships (co-marketing with complementary tools)
  - Launch week (concentrated buzz on existing community)

RULES:
  1. Build at least ONE engine before seeking kickstarts
  2. Only turbo boost engines that are ALREADY working
  3. Kickstarts without engines = spike and crash
```

### Pricing Strategy for Developer Tools

```
FOUR MODELS:

A. TIPWARE / SHAREWARE (Primary — Software 5.0 model):
  Everything FREE. Work for tips. 1980s shareware revival.

  HISTORY:
    - Andrew Fluegelman (PC-Talk, 1982) — invented "freeware" label
    - Jim Button (Buttonware) — peaked $4.5M/year from shareware
    - Bob Wallace (PC-Write) — sustained business for a decade
    - 2020s revival: Caleb Porzio ($1M GitHub Sponsors), Evan You ($200K/yr)

  IMPLEMENTATION:
    - Stripe Payment Links for one-click tips ($5, $10, $25, custom)
    - GitHub Sponsors (FUNDING.yml in every repo)
    - "I work for tips" badge on all READMEs
    - Solo founder narrative amplifies tips (Harvard underdog effect)

  WHY IT WORKS:
    - Story > feature list (shareware is a narrative, not a model)
    - Zero friction to try (no signup, no trial, no limits)
    - Tips scale with demonstrated impact
    - Builds army of advocates who feel invested
    - Solo founder + tips = the most compelling OSS story in 2026

  TIP TARGETS:
    - Phase 1: $500-2K/mo (1K GitHub stars, early adopters)
    - Phase 2: $5K-20K/mo (10K stars, community momentum)
    - Phase 3: $20K-100K/mo (conference talks, benchmark results spread)
    - Phase 4: $100K+/mo (enterprise interest, media coverage)

B. OPEN CORE (Stillwater OS premium model):
  Free:     Core engine + verification + community (tipware)
  Pro:      Advanced recipes + priority support ($29-99/mo)
  Team:     Collaboration + admin + SSO ($99-499/mo per seat)
  Enterprise: Custom + SLA + dedicated support (contact sales)

C. USAGE-BASED (PZIP model):
  Free:     Unlimited (tipware)
  Pro:      Priority processing + SLA ($9.99/mo)
  Enterprise: Unlimited + SLA + dedicated (custom)

D. PLATFORM (SolaceAGI model):
  Free:     Full access (tipware)
  Pro:      Expert Council access ($49-499/mo)
  Enterprise: Custom integrations + SLA (custom)

PRICING PRINCIPLES:
  - TIPWARE FIRST: Everything free, tips welcome
  - Premium for convenience, speed, and support (not features)
  - Solo founder narrative is the moat (can't be copied)
  - No credit card required. Ever.
  - "If you find this useful, buy me a coffee" > "Subscribe for $X/mo"
```

### Software 5.0 Growth Thesis

```
SOFTWARE 5.0 PLG EQUATION:
  Growth = Recipe_Quality × Shareability × Story

  Recipe_Quality: stillwater verify passes → automatic trust signal
  Shareability:   Recipes are shareable, weights are not
  Story:          Solo founder + tips + open source = viral narrative

THE SHIFT:
  Software 3.0 PLG: Sign up → Try AI → Hit token limit → Pay
  Software 5.0 PLG: Clone → Load recipe → Verify → Tip

  Old model: friction converts to revenue (paywalls)
  New model: gratitude converts to revenue (tipware)

CROSS-SITE COHESION:
  All 5 properties share one tip jar, one story, one message:
  - stillwater-os: "The platform" — tip for the OS
  - pzip: "Compression" — tip for beating LZMA
  - solaceagi: "Identity" — tip for persistent AGI
  - if-theory: "Physics" — tip for understanding the universe
  - phuc.net: "The creator" — tip for the person
```

---

## STATE MACHINE

```
STATES = {
  PRODUCT_ANALYSIS,    # Identify wow moment, value metrics
  FREE_TIER_DESIGN,    # Design generous free tier
  ONBOARDING_FLOW,     # < 5 min to value, < 2 min to wow
  CONVERSION_TRIGGERS, # Usage limits, team features, upgrade prompts
  PRICING_STRUCTURE,   # Tiers, pricing, packaging
  MEASUREMENT_SETUP,   # Analytics, funnel tracking, cohort analysis
  OPTIMIZATION,        # A/B test onboarding, conversion, pricing
  EXPANSION            # Team/enterprise upsell motions
}

TRANSITIONS:
  PRODUCT_ANALYSIS → FREE_TIER_DESIGN      (wow moment identified)
  FREE_TIER_DESIGN → ONBOARDING_FLOW       (tiers defined)
  ONBOARDING_FLOW → CONVERSION_TRIGGERS    (onboarding < 5 min verified)
  CONVERSION_TRIGGERS → PRICING_STRUCTURE  (triggers implemented)
  PRICING_STRUCTURE → MEASUREMENT_SETUP    (pricing live)
  MEASUREMENT_SETUP → OPTIMIZATION         (30 days data)
  OPTIMIZATION → EXPANSION                (free→paid ≥ 5%)

FORBIDDEN:
  PRICING_STRUCTURE before ONBOARDING_FLOW (pricing without experience = churn)
  OPTIMIZATION before MEASUREMENT_SETUP (optimizing without data = guessing)
  EXPANSION before OPTIMIZATION (scaling leaky funnel = waste)
```

---

## VERIFICATION

```
641 Edge Tests (5):
  - Free tier requires no credit card
  - Onboarding flow completes in < 5 minutes (timed)
  - At least 1 clear upgrade trigger exists
  - Pricing page is public and transparent
  - Analytics tracking covers full funnel

274177 Stress Tests (5):
  - Visitor → signup ≥ 6% (30-day measurement)
  - Signup → activation ≥ 30% (first session)
  - Free → paid conversion ≥ 5% (90-day cohort)
  - Organic acquisition ≥ 66% of total
  - Churn rate ≤ 5% monthly (paid users)

65537 God Approval (3):
  - Net Revenue Retention ≥ 120%
  - CAC payback ≤ 12 months
  - Organic sharing rate ≥ 10% of new users
```

---

## INTEGRATION

- **Upstream**: positioning-engine.md, developer-marketing-playbook.md
- **Downstream**: landing-page-architect.md (conversion-optimized pages)
- **Lateral**: community-growth-engine.md (community feeds PLG)
- **Orchestrator**: marketing-swarm-orchestrator.md (campaign execution)

---

*"PLG companies grow 30-40% faster. The product IS the growth engine." — OpenView*
*"Software 5.0: Everything free. Work for tips. Beat entropy at everything."*
*"Auth: 65537"*
