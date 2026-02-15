# 📣 Prime Browser: Campaign Resources

> **Status:** 🎮 OPERATIONAL
> **Target:** Phase 7 Multi-Platform Orchestration

---

## 1. PLATFORM ADAPTERS

Solace Browser provides native adapters for the following high-value platforms:

| Platform | Difficulty | Strategy |
|----------|------------|----------|
| **Reddit** | Medium | High Jitter + Karma Warming |
| **Hacker News** | High | Show HN + Immediate Verification |
| **Twitter/X** | Low | Multi-variant A/B Testing |
| **LinkedIn** | Medium | Proof-backed Professional Content |

---

## 2. JITTER & TIMING (PHASE 7)

To bypass bot detection, the `CampaignOrchestrator` applies **Prime-Number Jitter**:
*   **Small Jitter:** 3s, 5s, 7s (between clicks)
*   **Medium Jitter:** 13s, 17s, 23s (between fields)
*   **Large Jitter:** 39s, 63s, 91s (between posts)

*Formula:* `delay = base_delay + (prime_seed % max_jitter)`

---

## 3. ENGAGEMENT TRACKING (LEK)

We track **GLOW (Impact × Reusability × Alignment × Longevity) / Cost**:
*   **Impact:** Upvotes/Karma/Impressions
*   **Reusability:** Recipe success rate across accounts
*   **Alignment:** Click-through rate (CTR) to Northstar targets
*   **Longevity:** Time before post deletion/account flag

---

## 4. TEMPLATE ENGINE

Use the Phase 7 substitution syntax for dynamic posting:
```handlebars
"Check out {{project_name}} at {{url}}. It uses {{tech_stack}} to beat entropy!"
```

---

## 5. PROOF REPOSITORIES

Every campaign execution generates a signed artifact in:
`/home/phuc/projects/solace-browser/proofs/campaign_<id>/`

Verification Command:
`./solace-browser-cli.sh verify-campaign --id <id>`

*"Marketing is the breath of the project. Don't choke it."*
*"Auth: 65537"*
