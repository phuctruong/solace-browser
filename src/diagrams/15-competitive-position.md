# Diagram 15: Competitive Position — Feature Matrix
**Date:** 2026-03-01 | **Auth:** 65537
**Cross-ref:** Paper 01 (Competitive Landscape)

---

## Feature Matrix vs Key Competitors

```mermaid
graph TD
    subgraph "Solace Browser (8 structural advantages)"
        S1["AI IS the browser\n(not extension, not API)"]
        S2["Zero vendor API keys\n(full web access)"]
        S3["Local-first\n(cost → $0 at scale)"]
        S4["LLM once at preview\n(50-99% cheaper)"]
        S5["OAuth3 delegation\n(scoped, revocable)"]
        S6["Hash-chained evidence\n(Part 11 / regulated)"]
        S7["Versioned recipes\n(deterministic replay)"]
        S8["Prompt injection defense\n(sealed outbox)"]
    end

    S1 --- S2 --- S3 --- S4
    S5 --- S6 --- S7 --- S8

    style S1 fill:#2d7a2d,color:#fff
    style S2 fill:#2d7a2d,color:#fff
    style S3 fill:#2d7a2d,color:#fff
    style S4 fill:#2d7a2d,color:#fff
    style S5 fill:#222,color:#fff
    style S6 fill:#7a2d7a,color:#fff
    style S7 fill:#7a5a00,color:#fff
    style S8 fill:#222,color:#fff
```

## Competitor Comparison

| Capability | Us | Atlas | Chrome | Copilot | Airtop | Bardeen | OpenClaw |
|-----------|-----|-------|--------|---------|--------|---------|----------|
| Full browser (not ext) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ |
| No API keys needed | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ |
| Local-first | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| LLM once (preview) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| OAuth3 delegation | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Hash-chained evidence | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Recipe marketplace | ✓ | ✗ | ✗ | ✗ | ✗ | partial | partial |
| Prompt injection defense | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ (RCE vuln) |
| Self-host | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| BYOK (bring own key) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| Part 11 compliance | ✓ | ✗ | ✗ | ✗ | SOC2 only | ✗ | ✗ |
| Price | $8/mo | $20-200 | AI sub | $30/user | $26-342 | $99/mo | AWS |

## Why Token Vendors Cannot Copy

```mermaid
graph LR
    THEM["Token Vendors\n(OpenAI, Google, Anthropic)"] -->|"Revenue = tokens/action"| CONFLICT
    CONFLICT["OAuth3 reduces tokens\n= cannibalizes revenue"] -->|"Cannot implement"| MOAT["Our moat"]

    US["Solace"] -->|"Revenue = membership"| ALIGNED
    ALIGNED["Recipes replace tokens\n= cost curve inverts"] -->|"Naturally implements"| MOAT

    style THEM fill:#FF6B6B,color:#fff
    style US fill:#2d7a2d,color:#fff
    style MOAT fill:#7a5a00,color:#fff
    style CONFLICT fill:#FF6B6B,color:#fff
    style ALIGNED fill:#2d7a2d,color:#fff
```

## No-API Exclusive Category

Services with no public API where we're the ONLY automation path:
- WhatsApp (web.whatsapp.com)
- Amazon (amazon.com)
- Twitter/X ($100+/mo API paywall)
- Instagram (business API only)
- LinkedIn (severely restricted 2023)

## Invariants

1. Eight advantages are mutually reinforcing (each strengthens others)
2. Token vendors cannot copy (kills their revenue model)
3. Extension vendors cannot copy (limited browser access)
4. Cloud vendors cannot copy (local-first economics)
5. $8/mo is cheapest product with most features (local-first = near-zero marginal cost)
