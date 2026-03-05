# Diagram 19: Browser UI Architecture — Ground-Up Rebuild
# Auth: 65537 | GLOW 128 | Pipeline: DIAGRAM → STYLEGUIDE → CODE
# DNA: `UI(browser) = layout_injection × OOP_class × design_tokens × 13_locales`
# Personas: Jony Ive (design lead), Linus Torvalds (code lead), Russell Brunson (funnel)

## 1. Component Hierarchy (Jony Ive: "Remove until it breaks, then add one thing back")

```mermaid
graph TD
    subgraph "Shared Layout (all 16 pages)"
        A[_header.html] --> B[SolaceBrowser.layoutInjection]
        C[_footer.html] --> B
        B --> D[header-slot div]
        B --> E[footer-slot div]
    end

    subgraph "OOP JavaScript (solace-browser.js)"
        F[SolaceBrowser class] --> G[init]
        G --> H[layoutInjection]
        G --> I[activeNav]
        G --> J[hamburger]
        G --> K[langSwitcher]
        G --> L[scrollAnimations]
        G --> M[splashRotators]
        G --> N[charts — amCharts 5]
        G --> O[dataTables — DataTables.js]
        G --> P[statusBar]
        G --> Q[authStatus]
    end

    subgraph "Pages (16 total, 3 tiers)"
        R[P0: home.html — cinematic hero]
        S[P1: app-store, download, start, app-detail]
        T[P2: schedule, machine, settings, create-app, docs, style-guide, demo]
        U[P3: tunnel, mcp, oauth3]
    end

    subgraph "Design Tokens (site.css)"
        V["--sb-* tokens (keep existing)"]
        W["New: hero, card, grid, footer styles"]
        X["Clone: solaceagi patterns (improved)"]
    end

    subgraph "Vendor Libraries"
        Y[amCharts 5 — xy, Animated]
        Z[DataTables.js — responsive, i18n]
        AA[jQuery 3.7.1 — DataTables dependency]
    end

    F --> R
    F --> S
    F --> T
    F --> U
    V --> W
    Y --> N
    Z --> O
    AA --> Z
```

## 2. Data Flow: API → UI

```mermaid
sequenceDiagram
    participant Page as HTML Page
    participant SB as SolaceBrowser.js
    participant API as localhost:9222/api
    participant Cloud as solaceagi.com/api

    Page->>SB: DOMContentLoaded → init()
    SB->>SB: layoutInjection() — fetch _header + _footer
    SB->>SB: activeNav() — highlight current page
    SB->>SB: scrollAnimations() — IntersectionObserver
    SB->>API: GET /api/status
    API-->>SB: {running, headless, session, version}
    SB->>Page: Update status bar (dot + text)
    SB->>API: GET /api/apps
    API-->>SB: {apps: [...], categories: [...]}
    SB->>Page: Render app spotlight cards
    SB->>Cloud: GET /api/v1/auth/me (if API key)
    Cloud-->>SB: {email, plan, balance}
    SB->>Page: Update auth status pill
```

## 3. Page Architecture: Home (P0)

```mermaid
graph TD
    subgraph "home.html — Jony Ive: 3 sections"
        A[header-slot] --> B[Hero Section]
        B --> B1[YinYang logo — animated float]
        B --> B2["Title: Your AI Morning Assistant"]
        B --> B3["Subtitle: one sentence value prop"]
        B --> B4["CTA: Browse Apps + Watch Demo"]
        B --> B5[Trust signals: 3 badges]
        B --> C[Status Bar — compact, live]
        C --> C1["Browser: Running/Offline"]
        C --> C2["Mode: Headless/Headed"]
        C --> C3["Apps: N installed"]
        C --> D[App Spotlight — 3 featured cards]
        D --> D1["Gmail Triage — $0.003/run"]
        D --> D2["Slack Standup — $0.002/run"]
        D --> D3["LinkedIn Outreach — coming"]
        D --> E[How It Works — 3 steps]
        E --> E1["1. Install an app"]
        E --> E2["2. YinYang handles the rest"]
        E --> E3["3. You approve everything"]
        E --> F[CTA Banner — Browse All Apps]
        F --> G[footer-slot]
    end
```

## 4. i18n Architecture (13 locales)

```mermaid
graph LR
    subgraph "Locale System"
        A[data-i18n attributes] --> B[SolaceBrowser.i18n]
        B --> C[GET /api/locale?key=all&locale=XX]
        C --> D[JSON response — all keys]
        D --> E[DOM update — textContent]
        F[localStorage sb_locale] --> B
        G[sb-lang-menu click] --> F
        G --> H[Page reload with new locale]
    end

    subgraph "13 Supported Locales"
        L1[en — English]
        L2[es — Español]
        L3[vi — Tiếng Việt]
        L4[zh — 中文]
        L5[pt — Português]
        L6[fr — Français]
        L7[ja — 日本語]
        L8[de — Deutsch]
        L9[ar — العربية]
        L10[hi — हिंदी]
        L11[ko — 한국어]
        L12[id — Bahasa Indonesia]
        L13[ru — Русский]
    end
```

## 5. Vendor Integration (amCharts + DataTables)

```mermaid
graph TD
    subgraph "amCharts 5 Usage"
        A["[data-solace-chart] attribute"] --> B[SolaceBrowser.charts]
        B --> C[am5.Root.new]
        C --> D[XYChart — bar/line]
        D --> E["Machine Dashboard: CPU, Memory, Disk"]
        D --> F["Home: App usage sparkline"]
    end

    subgraph "DataTables Usage"
        G["[data-solace-table] attribute"] --> H[SolaceBrowser.dataTables]
        H --> I["new DataTable(el, config)"]
        I --> J["Schedule: upcoming runs table"]
        I --> K["Machine: evidence log table"]
        I --> L["Settings: token vault table"]
        H --> M[_datatableLocale — 13 locales]
    end
```

## Design Principles (Persona Committee)

| Persona | Principle | Applied Where |
|---------|-----------|---------------|
| **Jony Ive** | Remove until it breaks | Home: 12 sections → 3 |
| **Jony Ive** | Honest materials | CSS tokens, no inline styles |
| **Linus** | No memory leaks | IntersectionObserver.unobserve(), cleanup |
| **Linus** | No event listener leaks | AbortController for all listeners |
| **Russell Brunson** | Hook → Story → Offer | Hero → How It Works → CTA |
| **Rory Sutherland** | Perceived value ≠ functional | "$0.003/run" next to app names |
| **Vanessa** | Warm, not bureaucratic | "YinYang handles the rest" not "Execute recipe" |
| **MrBeast** | Screenshot-worthy | Hero with floating YinYang, gradient text |
