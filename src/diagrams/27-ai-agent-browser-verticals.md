# Diagram 27: AI-Agent Browser — Vertical Market Architecture
# DNA: `browser(one) → verticals(sales, email, content, enterprise) → replaces(5+ tools)`
# Paper: 47 (Sections 20-21) | Auth: 65537

```mermaid
flowchart LR
    subgraph BROWSER["Solace Browser — AI-Agent Platform"]
        direction TB
        SIDEBAR[Yinyang Sidebar]
        CDP[CDP 4-Plane Control]
        RECIPES[Recipe Engine]
        EVIDENCE[Evidence Chain]
        OAUTH3[OAuth3 Consent]
        TWIN[Cloud Twin]
        SIDEBAR --> CDP
        SIDEBAR --> RECIPES
        SIDEBAR --> EVIDENCE
        SIDEBAR --> OAUTH3
        CDP --> TWIN
    end

    subgraph SALES["Sales AI (S1-S10)"]
        direction TB
        S_LI[LinkedIn Autopilot]
        S_CRM[CRM Auto-Fill]
        S_PREP[Meeting Prep]
        S_CAD[Multi-Channel Cadence]
        S_INTEL[Territory Intelligence]
    end

    subgraph EMAIL["Email AI (M1-M6)"]
        direction TB
        M_CTX[Context-Aware Reply]
        M_FU[Multi-Channel Follow-Up]
        M_TRIAGE[Inbox Zero Autopilot]
        M_TMPL[Template Recipes]
    end

    subgraph CONTENT["Content/PR AI (C1-C7)"]
        direction TB
        C_PUB[Write→Publish→Promote]
        C_SEO[SEO Research+Create]
        C_PR[PR Outreach Autopilot]
        C_CAL[Content Calendar]
        C_MON[Competitive Monitor]
    end

    subgraph ENTERPRISE["Enterprise (E1-E6)"]
        direction TB
        E_BAT[BAT Automation]
        E_CMP[Data Comparison]
        E_CUT[Cutover Runbook]
        E_GXP[GxP Validation]
        E_DEV[Deviation Tracking]
        E_SIGN[Business eSign-Off]
    end

    BROWSER --> SALES
    BROWSER --> EMAIL
    BROWSER --> CONTENT
    BROWSER --> ENTERPRISE

    subgraph REPLACES["Tools Replaced"]
        direction TB
        R1["Copilot for Sales $50/mo"]
        R2["Gong $100/mo"]
        R3["Shortwave $25/mo"]
        R4["Jasper $49/mo"]
        R5["SAP Consultants $400/hr"]
    end

    SALES -.->|replaces| R1
    SALES -.->|replaces| R2
    EMAIL -.->|replaces| R3
    CONTENT -.->|replaces| R4
    ENTERPRISE -.->|replaces| R5

    style BROWSER fill:#1a1a2e,stroke:#6C5CE7,color:#fff
    style SALES fill:#0f3460,stroke:#00b894,color:#fff
    style EMAIL fill:#0f3460,stroke:#fdcb6e,color:#fff
    style CONTENT fill:#0f3460,stroke:#e17055,color:#fff
    style ENTERPRISE fill:#0f3460,stroke:#74b9ff,color:#fff
    style REPLACES fill:#2d2d2d,stroke:#d63031,color:#fff
```

## Key Insight
One browser, four verticals, replacing $200-500/mo of point solutions with $28/mo (Pro).
The moat: every vertical shares the same evidence chain, recipe engine, and OAuth3 consent.
Point solutions can't replicate this because they only see one channel.
