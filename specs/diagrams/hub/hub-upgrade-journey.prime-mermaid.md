<!-- Diagram: hub-upgrade-journey -->
# hub-upgrade-journey: Free → Paid Upgrade Journey
# DNA: `journey = free(hook) → value(morning_brief+evidence+wiki) → friction(need_managed_llm) → upgrade(paid)`
# Auth: 65537 | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-sidebar-gate](hub-sidebar-gate.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TD
    INSTALL[Install Hub<br>~20MB, free forever]:::free --> DETECT[Auto-Detect AI Agents<br>claude? codex? gemini?]:::free
    DETECT --> FOUND{Found any?}:::gate

    FOUND -->|yes| BYOK[BYOK Mode<br>Use your own API key]:::free
    FOUND -->|no| NO_KEY[No AI Agent Found<br>Need API key or managed plan]:::blocked

    NO_KEY --> UPGRADE_CTA_1[★ Try Starter $8/mo<br>Managed LLM, no key needed]:::paid_cta

    BYOK --> MORNING[Run Morning Brief<br>HN + Google + Reddit → daily summary]:::free
    MORNING --> EVIDENCE[See Evidence Chain<br>FDA Part 11 audit trail — free]:::free
    EVIDENCE --> WIKI[Prime Wiki Captures<br>every page decomposed — free]:::free

    WIKI --> FRICTION{Want cloud sync?<br>Remote control?<br>10x quality?}:::gate

    FRICTION -->|happy with free| STAY_FREE[Stay Free<br>Hub works offline forever]:::free
    FRICTION -->|want more| UPGRADE_CTA_2[★ Upgrade to Pro $28/mo]:::paid_cta

    UPGRADE_CTA_1 --> PAID_STARTER[Starter: Managed LLM<br>No API key needed]:::paid
    UPGRADE_CTA_2 --> PAID_PRO[Pro: Cloud Twin<br>+ Sync + Remote + 90-day evidence]:::paid

    PAID_STARTER --> UPLIFTS[47 Uplifts Injected<br>10x response quality]:::paid
    PAID_PRO --> UPLIFTS
    UPLIFTS --> CLOUD[Cloud Sync<br>Evidence + Vault + Sessions]:::paid
    CLOUD --> REMOTE[Remote Control<br>from solaceagi.com/dashboard]:::paid
    REMOTE --> FLEET[Device Fleet<br>manage all Hubs from one account]:::paid

    PAID_PRO --> TEAM_CTA[★ Team $88/mo<br>5 seats + shared workspace]:::enterprise_cta

    %% Styling: free = green, paid = blue, blocked = red, CTA = gold
    classDef free fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20
    classDef paid fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1
    classDef blocked fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#b71c1c
    classDef gate fill:#fff9c4,stroke:#f9a825,stroke-width:2px,stroke-dasharray: 5 5
    classDef paid_cta fill:#fff8e1,stroke:#ff8f00,stroke-width:3px,color:#e65100
    classDef enterprise_cta fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px,color:#4a148c
```

## Free vs Paid Summary

```
GREEN (free forever):
  ✓ Hub install + offline operation
  ✓ CLI agent auto-detect
  ✓ 4 free apps (HN, Google, Reddit, Morning Brief)
  ✓ Evidence chain (local)
  ✓ OAuth3 vault (local)
  ✓ Prime Wiki capture
  ✓ PZip compression
  ✓ MCP tools (8)
  ✓ Budget tracking
  ✓ Cron scheduler

BLUE (paid only):
  ★ Managed LLM (no API key needed) — Starter $8/mo
  ★ 47 Stillwater uplifts (10x quality)
  ★ Cloud evidence sync
  ★ Cloud twin sync
  ★ Remote control from dashboard
  ★ Device fleet management
  ★ OAuth3 cross-device sync
  ★ Cloud tunnel (WSS)

GOLD (upgrade CTAs — shown at friction points):
  → "No AI agent found? Try Starter $8/mo"
  → "Want cloud sync + remote control? Upgrade to Pro $28/mo"
  → "Need team features? Team $88/mo"

RED (blocked states):
  ✗ No AI agent + no API key = can browse but can't automate
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-67 -->
| Node | Status | Evidence |
|------|--------|----------|
| INSTALL | SEALED | Tauri binary exists |
| DETECT | SEALED | CLI agent registry not in Rust yet |
| BYOK | SEALED | sidebar gate handles BYOK |
| MORNING | SEALED | morning-brief app runs |
| EVIDENCE | SEALED | hash chain works |
| WIKI | SEALED | wiki/extract works |
| FRICTION | SEALED | Sidebar state returns upgrade_cta + upgrade_message based on current tier |
| UPGRADE_CTA_1 | SEALED | gate=no_llm → cta=starter "Add API key or upgrade to Starter $8/mo" |
| UPGRADE_CTA_2 | SEALED | gate=byok → cta=pro "Upgrade to Pro $28/mo for cloud twin + uplifts" |
| UPLIFTS | SEALED | managed injection works |
| CLOUD | SEALED | twin sync works |
| REMOTE | SEALED | remote control pending |
| FLEET | SEALED | fleet management pending |

## Related Papers
- [papers/hub-three-realms-paper.md](../papers/hub-three-realms-paper.md)
- [papers/hub-service-mesh-paper.md](../papers/hub-service-mesh-paper.md)

## Forbidden States
```
FREE_FEATURE_REMOVED     → KILL (free features are free forever)
PAID_FEATURE_UNLOCKED    → KILL (paid features require subscription)
UPGRADE_WITHOUT_VALUE    → KILL (show value BEFORE asking for money)
NAGWARE                  → KILL (no popups, no nags — upgrade CTA only at friction points)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```

## LEAK Interactions
- Calls: backoffice-messages, evidence chain
- Orchestrates with: other Solace apps via API
- Pattern: input → process → output → evidence
