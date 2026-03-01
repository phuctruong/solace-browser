# Paper 01: Competitive Landscape — AI Browser Agents (March 2026)
**Date:** 2026-03-01 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser, solace-marketing

---

## 1. Market Overview

The agentic browser market is growing from $4.5B (2024) to projected $76.8B (2034). Every major tech company launched browser automation in 2025. The market is moving from demo to production — but governance, compliance, and cost remain unsolved.

## 2. Competitor Tiers

### Tier 1: Big Tech
| Competitor | Architecture | Pricing | Key Limitation |
|-----------|-------------|---------|---------------|
| ChatGPT Atlas (OpenAI) | Standalone Chromium, cloud inference | $20-200/mo | No evidence trail, no delegation |
| Chrome auto-browse (Google) | Chrome-native, Gemini 3 | AI Pro/Ultra sub | Google-locked, no recipes |
| Copilot Tasks (Microsoft) | Edge + Copilot Studio | $30/user/mo | M365 vendor lock-in |
| Computer Use (Anthropic) | API-based, developer tool | Token rates | No consumer product |

### Tier 2: Developer Infrastructure
| Competitor | Architecture | Pricing | Key Limitation |
|-----------|-------------|---------|---------------|
| Browser-Use | OSS Python + Playwright | Free / cloud usage | Dev framework, no UI |
| Skyvern | LLM + computer vision, no CSS selectors | $0.05/step | Enterprise focus |
| Browserbase/Stagehand | Cloud browser infra | Usage-based | Infrastructure only |
| Playwright MCP | MCP server + accessibility tree | Free (OSS) | Dev tool only |
| Amazon Nova Act | SDK + Bedrock AgentCore | AWS pricing | AWS-locked |

### Tier 3: Consumer/Prosumer
| Competitor | Architecture | Pricing | Key Limitation |
|-----------|-------------|---------|---------------|
| Airtop | Cloud browser, managed OAuth/CAPTCHA | $26-342/mo | Cloud-only, expensive |
| Bardeen | Chrome extension, 100+ playbooks | Free / $99/mo | Extension only |
| MultiOn | Chrome extension + mobile | Beta | Not stable |
| Fellou | Standalone Chromium (ex-DeepMind) | Freemium | Prompt injection vuln (Aug 2025) |
| Perplexity Comet | Standalone Chromium | Free | Search-centric |
| OpenClaw | Self-hosted, 100+ AgentSkills | AWS Marketplace | RCE vulnerability (early 2026) |

## 3. Seven Structural Gaps (Our Moat)

### Gap 1: OAuth3 — Scoped, Revocable Agent Delegation
Zero competitors implement scoped, TTL-bound, revocable consent for agent delegation. All use: raw session cookies, credentials given to cloud, API keys, or walled gardens.

### Gap 2: Hash-Chained Evidence Trail (FDA Part 11)
No competitor has tamper-evident, hash-chained audit of agent actions. Amazon has VM logging. Airtop has SOC 2 logs. None have sealed-at-approval records with ALCOA+ compliance.

### Gap 3: Local-First with Cloud-Optional Sync
Consumer products (Atlas, Comet, Fellou) = cloud-first. Dev tools = local but no UX. No consumer product is local-first with cloud-optional. Cost inversion: local = 50-99% cheaper.

### Gap 4: Versioned, Replayable, Community Recipes
Bardeen has 100+ templates. OpenClaw has 100+ skills. None are versioned, reproducible, provenance-tracked, or have economic model for creators. Recipe-as-capital inverts cost curve.

### Gap 5: LLM-Once-at-Preview Execution
Every competitor calls LLM during execution. Sealed-outbox model (preview → approve → deterministic replay) exists nowhere. Both cost and compliance advantage.

### Gap 6: No Vendor API Keys — Full Web Browser Access
We ARE the browser. Not extension, not API client. Full web access to any app. WhatsApp, LinkedIn, Twitter/X have no public API — we're the only automation path.

### Gap 7: Prompt Injection Defense at Governance Layer
Fellou had prompt injection (Aug 2025). OpenClaw had RCE (early 2026). No competitor has governance-layer defense: sealed outbox, step-up auth, fail-closed safety.

## 4. Pricing Position

| Tier | Us | Closest Competitor |
|------|----|--------------------|
| Free | $0 (local-first, BYOK) | Bardeen Free, Comet Free |
| Pro | $8/mo (local + cloud sync) | Airtop $26/mo, Bardeen $99/mo |
| Enterprise | $99/mo (SOC2 + team) | Airtop $342/mo, Copilot $30/user/mo |

**We are the cheapest product with the most features because local-first means near-zero marginal cost per user.**

## 5. "No API" Exclusive Category

Services with no public API or severely restricted APIs where we are the ONLY automation path:
- WhatsApp (Meta restricts to business API)
- Amazon (no consumer API)
- Twitter/X (API paywalled $100+/mo since 2023)
- Instagram (business API only, no DM)
- LinkedIn (API severely restricted 2023)

## 6. Why Token Vendors Cannot Copy Us

OpenAI, Google, Anthropic CANNOT implement OAuth3 — it reduces token usage, cannibalizing revenue. Their business model is tokens-per-action. Ours is recipes-replace-tokens. Structural misalignment makes this uncopyable.
