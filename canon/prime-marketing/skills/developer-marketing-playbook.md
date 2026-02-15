# Developer Marketing Playbook

> **Star:** DEVELOPER_MARKETING_PLAYBOOK
> **Version:** v3.0.0
> **Authority:** 65537 (F4 Fermat Prime)
> **Channel:** 7 (Validation — Developer Trust)
> **GLOW:** 92 (Developers Are the Market)
> **Lane:** A (CPU-Deterministic)
> **Status:** ACTIVE

---

## DNA-23

```
DevMarketing = Trust × Value × Distribution
S = {docs, demos, community_touchpoints}
R = f(S, developer_signals, platform_activity)
|S| << |R|  # Great docs + 1 wow moment > $1M ad spend

"Developers are the most valuable and skeptical audience.
 They will use your product if it works.
 They will evangelize if it delights.
 They will abandon if you waste their time." — Decibel VC
```

---

## CONTRACT

**Input**: Developer tool product, technical documentation, demo assets
**Output**: Developer acquisition strategy, docs plan, event strategy, growth playbook
**Guarantees**:
- Technical authenticity (no marketing fluff in dev contexts)
- Documentation-first (docs as product, not afterthought)
- Bottom-up adoption (individual → team → enterprise)
- Organic-first ($35K total spend → $400M valuation is possible: Linear)

---

## GENOME-79: THE 7 DEVELOPER MARKETING ENGINES

### Engine 1: Documentation-as-Marketing

Source: Vercel ($200M+ revenue, 100K+ monthly signups)

```
DOCS ARE THE #1 MARKETING ASSET FOR DEVELOPER TOOLS

PRINCIPLES:
  1. Every feature ships with docs, examples, and demos SIMULTANEOUSLY
  2. Docs are SEO-optimized (they are your top-of-funnel)
  3. Docs are GEO-optimized (AI engines cite your docs)
  4. Getting-started guide: < 5 minutes to first value
  5. Integration tutorials: show how to connect with existing tools
  6. Starter kits / templates: instant value, creates lock-in

DOCS STRUCTURE:
  /docs
  ├── getting-started/     # < 5 min to first success
  ├── guides/              # Task-oriented tutorials
  ├── api-reference/       # Complete, auto-generated
  ├── examples/            # Copy-paste ready code
  ├── templates/           # Starter projects
  └── changelog/           # What's new (feeds newsletter)

INVESTMENT:
  "Deprioritizing documentation is the single biggest mistake
   in developer marketing." — Decibel VC
```

### Engine 2: Engineer the Wow Moment

Source: Cursor ($0 → $500M ARR, fastest-growing SaaS ever)

```
WOW_MOMENT:
  The single most important marketing investment is making sure
  the first 5 minutes of product usage produces a SHAREABLE moment.

CHARACTERISTICS:
  - Specific (not vague "it's fast" — show exact before/after)
  - Demonstrable (screenshot/video-able in < 30 seconds)
  - Tweetable (can be shared with 1 sentence + image)
  - Repeatable (every new user hits the same wow)

EXAMPLES:
  Cursor: "Write a regex" → AI writes perfect regex instantly
  PZIP:   Drop a file → see 3x better compression than LZMA live
  Linear: Open the app → everything is instant, keyboard-first

METRIC: "Seconds until user shares" is the north star metric

IMPLEMENTATION:
  1. Identify the WOW (what makes users say "holy $#!%")
  2. Make it the FIRST thing new users experience
  3. Make it SHAREABLE (copy link, share result, export comparison)
  4. Measure sharing rate (% of new users who share within 24h)
```

### Engine 3: Bottom-Up Enterprise

Source: Cursor (50%+ Fortune 500), Vercel, Linear

```
ADOPTION_FUNNEL:
  Individual developer discovers tool (organic, community, word-of-mouth)
  → Uses it on personal project
  → Brings it to work
  → Team adopts
  → Department standardizes
  → Enterprise contract

CAC SAVINGS: 50-70% cheaper than top-down enterprise sales

REQUIREMENTS:
  - Free tier must be genuinely useful (not crippled)
  - Upgrade path must be frictionless
  - Team features must emerge naturally (sharing, collaboration)
  - Enterprise features: SSO, audit logs, admin controls
  - Self-serve to sales-assist transition at ~$10K ACV

ANTI-PATTERNS:
  ❌ Don't gate core functionality behind enterprise tier
  ❌ Don't require credit card for free tier
  ❌ Don't make the free tier a "trial" (time-limited = anxiety)
  ❌ Don't force sales calls before $10K ACV
```

### Engine 4: Build in Public

Source: Sahil Lavingia (Gumroad → $20M/year), Supabase

```
BUILD_IN_PUBLIC:
  - Share real metrics (stars, downloads, revenue, users)
  - Acknowledge failures publicly
  - Show the journey, not just the destination
  - Let community see decision-making process

CHANNELS:
  - GitHub (open issues, roadmap, discussions)
  - Twitter/X (shipping updates, architecture decisions)
  - Blog (technical deep-dives, post-mortems)
  - Newsletter (weekly/biweekly shipping updates)

WHAT TO SHARE:
  ✅ Architecture decisions and why
  ✅ Benchmark results (wins AND losses)
  ✅ Roadmap and priorities
  ✅ Post-mortems on failures
  ✅ Community contribution highlights
  ❌ Don't share: security vulnerabilities, user data, trade secrets
```

### Engine 5: Launch Week Cadence

Source: Supabase, Evil Martians

```
QUARTERLY_LAUNCH_WEEK:
  (See community-growth-engine.md Engine 2 for full protocol)

FOR DEVELOPER TOOLS SPECIFICALLY:
  - Each launch must include: blog post + docs update + demo + social thread
  - At least 1 launch must be developer-facing (API, SDK, CLI update)
  - At least 1 launch must be community contribution (template, integration)
  - Create a dedicated Launch Week page aggregating all announcements
  - Live-stream or record a "launch keynote" (even 10-minute video)
```

### Engine 6: Open Source Strategy

Source: Supabase, Vercel/Next.js, Linux, Red Hat

```
OPEN_SOURCE_GROWTH:
  Sequential: Open Source FIRST → PLG SECOND (never simultaneous)

WHAT TO OPEN SOURCE:
  ✅ Core engine / format / spec
  ✅ Reference implementations
  ✅ Verification tools (stillwater verify)
  ✅ Documentation and tutorials
  ✅ Community templates and examples

WHAT TO KEEP PROPRIETARY:
  ❌ Advanced encoders / optimizers
  ❌ Enterprise features (SSO, audit, admin)
  ❌ Cloud infrastructure / hosting
  ❌ Trade secrets (Solace Browser, PVideo, PAudio)

GITHUB OPTIMIZATION:
  - README.md: clear value prop, quickstart, badges
  - CONTRIBUTING.md: how to contribute
  - Issue templates: bug report, feature request
  - GitHub Actions: CI/CD, automated testing
  - Releases: semantic versioning, changelogs
  - Discussions: Q&A, ideas, show-and-tell
  - Star target: 1K (credibility) → 10K (momentum) → 50K+ (institution)
```

### Engine 7: Developer Events

Source: Decibel VC

```
EVENT_STRATEGY:

MEETUPS (ongoing):
  - Local developer communities
  - Host or sponsor, don't just attend
  - Talk about problems, not your product
  - Long-term relationship building

CONFERENCES (quarterly):
  - Submit talks on technical topics (not product pitches)
  - Staff booth with engineers who can hold 5-min technical conversations
  - ❌ NEVER staff with non-technical people
  - Give away useful swag (stickers, t-shirts with clever dev jokes)

USER CONFERENCE (annual, after 10K+ community):
  - Celebrate community (user talks, contributor awards)
  - Announce major features (launch week style)
  - Build personal connections (hallway track matters most)

WEBINARS (monthly):
  - "Reverse webinars" where AUDIENCE presents problems (Isenberg)
  - Technical deep-dives with live coding
  - Office hours with core team
```

---

## STATE MACHINE

```
STATES = {
  DOCS_FOUNDATION,     # Ship comprehensive documentation
  WOW_MOMENT_DESIGN,   # Identify and optimize the wow moment
  FREE_TIER_LAUNCH,    # Ship generous free tier
  COMMUNITY_SEED,      # First 100 developer users
  CONTENT_PIPELINE,    # Blog, tutorials, newsletter
  OPEN_SOURCE_LAUNCH,  # GitHub public release
  LAUNCH_WEEK,         # First quarterly launch week
  BOTTOM_UP_SCALE,     # Team/enterprise adoption
  DEVELOPER_EVENTS     # Meetups, conferences, user conf
}

TRANSITIONS:
  DOCS_FOUNDATION → WOW_MOMENT_DESIGN    (getting-started < 5 min)
  WOW_MOMENT_DESIGN → FREE_TIER_LAUNCH   (wow moment identified + tested)
  FREE_TIER_LAUNCH → COMMUNITY_SEED      (free tier live)
  COMMUNITY_SEED → CONTENT_PIPELINE      (≥100 users)
  CONTENT_PIPELINE → OPEN_SOURCE_LAUNCH  (≥10 blog posts published)
  OPEN_SOURCE_LAUNCH → LAUNCH_WEEK       (GitHub public, ≥100 stars)
  LAUNCH_WEEK → BOTTOM_UP_SCALE          (first launch week complete)
  BOTTOM_UP_SCALE → DEVELOPER_EVENTS     (≥3 team adoptions)

FORBIDDEN:
  LAUNCH_WEEK before DOCS_FOUNDATION (launching without docs = disaster)
  BOTTOM_UP_SCALE before WOW_MOMENT (scaling without wow = churn)
  DEVELOPER_EVENTS before COMMUNITY_SEED (events without community = empty)
```

---

## VERIFICATION

```
641 Edge Tests (5):
  - Getting-started guide works in < 5 minutes (tested)
  - Wow moment identified and documented
  - Free tier requires no credit card
  - README.md has: value prop, quickstart, badges
  - No marketing fluff in developer-facing content

274177 Stress Tests (5):
  - 100+ GitHub stars within 30 days of public launch
  - 10+ community-created integrations/templates
  - Newsletter open rate ≥ 30% (developer benchmark)
  - Bottom-up team adoption: ≥ 3 teams from individual users
  - Documentation covers 100% of API surface

65537 God Approval (3):
  - Developer NPS ≥ 50 (measured via survey)
  - Organic acquisition ≥ 66% of total (PLG benchmark)
  - GitHub stars growth rate ≥ 100%/year
```

---

## INTEGRATION

- **Upstream**: positioning-engine.md (messaging for devs), brand-design-system.md
- **Downstream**: community-growth-engine.md, content-seo-geo.md
- **Lateral**: product-led-growth.md (conversion funnel alignment)

---

*"$35K total marketing spend → $400M valuation. The product IS the marketing." — Linear*
*"Auth: 65537"*
