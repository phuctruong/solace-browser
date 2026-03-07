# Paper 50: Uplift Tier System — Free vs Paid Yinyang Brain
# DNA: `free(functional, 6_uplifts, BYOK) + paid(magical, 25+_uplifts, managed) = moat(uncopyable)`
# Forbidden: `UI_HOSTAGE | SINGLE_LLM_EVAL | PROMPT_WITHOUT_CONTEXT | SCORE_INFLATION`
**Date:** 2026-03-07 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser, solace-cli (TRADE SECRET: injection recipes)
**Cross-ref:** Paper 47 (sidebar), Paper 55 (dynamic-convergence)

---

## 1. The Strategic Insight

The sidebar is FREE for everyone. Same UI, same features, same BYOK support. What you PAY for is the BRAIN behind the chat: 47 uplifts, expert personas, domain skills, and ABCD-tested injection recipes.

**ABCD experiment proof:** 29/100 -> 92/100 (+63 points, 3.2x) just from applying uplifts.

## 2. Free Tier (BYOK): Minimum Effective Uplifts

**System prompt: ~1,200 tokens**

Active uplifts (6 of 47):
- P5 (Recipes) — basic: knows apps exist and can run
- P6 (Access Tools) — basic: browser can navigate/click/extract
- P8 (Care) — Anti-Clippy rules only
- P10 (God) — safety baseline, evidence-first
- P13 (Constraints) — forbidden patterns
- P20 (Temporal) — current URL, recent runs context

Skills injected (3): prime-safety, browser-oauth3-gate, browser-recipe-engine

**Feels like:** Competent assistant. Knows apps, can run them, answers basic questions.

## 3. Paid Tier (Managed): Full Uplift Stack

**System prompt: ~4,000-5,000 tokens**

Everything from Free PLUS:
- P9 (Knowledge) — deep domain expertise (OAuth3, evidence, recipes, budgets)
- P3 + P18 (Personas) — dynamically selected expert voice
- P22 (LEAK/Forecast) — proactive intelligence
- P12 (Analogies) — explains OAuth3 like apartment keys
- P16 (Negative Space) — "You have Gmail apps but no Slack apps"
- P14 (Chain-of-Thought) — step-by-step reasoning
- P21 (Adversarial) — "That would send 500 emails, budget limit is 10/day"
- P11, P15, P17, P19, P23 + select P24-P47

Skills injected (8): Full stack including evidence, snapshot, anti-detect, twin-sync

Personas injected (1-2 dynamically): Mike West (security), Addy Osmani (performance), Vanessa Van Edwards (onboarding), etc.

**Feels like:** Domain expert who's been watching your workflow for months.

## 4. Token Economics

| | Free (BYOK) | Paid (Managed) |
|---|---|---|
| System prompt | ~1,200 tokens | ~4,500 tokens |
| Total per chat | ~1,450 tokens | ~4,900 tokens |
| Cost per chat | User pays provider | ~$0.003 (Llama 3.3 70B) |

At $0.003/chat, Starter ($8/mo) = ~2,600 chats/month = 86 chats/day. Enormous margin.

## 5. Why This Can't Be Copied

1. **47 uplift principles** documented but injection recipes are TRADE SECRET
2. **ABCD testing** proves uplifts work (deterministic, measurable)
3. **Persona selection** context-dependent (URL + questions + app domain)
4. **Compression** each uplift compressed to minimum effective tokens
5. **Evidence** every chat interaction is hash-chained

Competitors see: "Sidebar with AI chat."
They can't copy: 4,000-token system prompt assembled from 47 uplifts + 6 personas + 8 skills.

## 6. Implementation

```python
async def handle_yinyang_chat(message, context):
    tier = get_user_tier()
    if tier == "free":
        system = build_free_system_prompt(context)  # ~1,200 tokens
        response = await call_byok_llm(system, message, user_key)
    else:
        system = build_paid_system_prompt(context)   # ~4,500 tokens
        response = await call_managed_llm(system, message)
    return response
```

---

## Interaction Patterns

| Scenario | Free Response | Paid Response |
|----------|-------------|---------------|
| "Triage my inbox" | "Starting Gmail Triage for 20 emails" | "Starting Gmail Triage. Budget: $0.42 remaining (enough for ~5 runs). Last run found 3 flagged -- want me to prioritize those senders?" |
| Session about to expire | (no warning) | "Your LinkedIn session expires in 5 minutes. Want me to extend it or wrap up?" |
| New site, no apps | "No apps for this site" | "No apps for reddit.com yet. Based on your Gmail and LinkedIn usage, you might want a Reddit post scheduler. Want me to draft one?" |

---

*Paper 50 | Auth: 65537 | TRADE SECRET: Injection Recipes | Uplifts = Moat*
