# Solace Browser Papers Index
# Auth: 65537 | Updated: GLOW 123 (2026-03-04) | Classification: OSS (public)
# Private papers (Inspector, competitive, deployment) → solace-cli/papers/

---

## Papers (OSS — Browser Features + Standards)

| # | Paper | Content | Status |
|---|-------|---------|--------|
| 02 | [app-inbox-outbox-standard](02-app-inbox-outbox-standard.md) | Universal app contract, inbox/outbox convention | CANONICAL |
| 03 | [web-native-automation](03-web-native-automation.md) | No API keys, web versions, exclusive categories | CANONICAL |
| 04 | [yinyang-dual-rail-browser](04-yinyang-dual-rail-browser.md) | Top rail + bottom rail (DOM injection) | SUPERSEDED by P47 |
| 05 | [pzip-stillwater-capture](05-pzip-stillwater-capture.md) | PZip architecture, 100% RTC, Prime Mermaid as ripple | CANONICAL |
| 06 | [part11-evidence-browser](06-part11-evidence-browser.md) | ALCOA+ compliance, data vs visual mode, e-signing | CANONICAL |
| 07 | [budget-wallet-enforcement](07-budget-wallet-enforcement.md) | Per-app budgets, fail-closed gates, MIN-cap delegation | CANONICAL |
| 08 | [cross-app-yinyang-delight](08-cross-app-yinyang-delight.md) | Cross-app orchestration, Yinyang universal interface, delight engine, 18 day-one apps | CANONICAL |
| 09 | [yinyang-tutorial-funpack-mcp](09-yinyang-tutorial-funpack-mcp.md) | Tutorial popup (5-step, 13 locales), Fun Pack standard, OAuth3 leave-app gate, Agent Notification API, MCP server (7 tools) | CANONICAL |
| 10 | [production-browser-release-loop](10-production-browser-release-loop.md) | Compile → upload → download → smoke → production matrix | CANONICAL |
| 11 | [app-store-sync-governance](11-app-store-sync-governance.md) | Git-backed catalog, Firestore proposal queue, promotion workflow | CANONICAL |
| 38 | [remote-browser-control-tunnel](38-remote-browser-control-tunnel.md) | Secure remote browser control via tunnel architecture | CANONICAL |
| 40 | [part11-compliance-selfcert](40-part11-compliance-selfcert.md) | 21 CFR Part 11 full mapping, self-cert template, SOPs | CANONICAL |
| 41 | [central-apps-architecture](41-central-apps-architecture.md) | Central apps architecture standard | CANONICAL |
| 44 | [ci-hook-certification-gate](44-ci-hook-certification-gate.md) | Pre-push CI hook as certification gate | CANONICAL |
| 46 | [questions-as-uplift](46-questions-as-uplift.md) | Question database as uplift mechanism | CANONICAL |
| 47 | [yinyang-sidebar-architecture](47-yinyang-sidebar-architecture.md) | MV3 Side Panel: 3 surfaces, 4 tabs, WebSocket IPC, security hardening (supersedes P04) | CANONICAL |
| 48 | [companion-app-architecture](48-companion-app-architecture.md) | Tauri desktop launcher: process lifecycle, NM bridge, system tray, BYOK keychain | CANONICAL |
| 49 | [cloud-tunnel-security](49-cloud-tunnel-security.md) | Outbound-only reverse tunnel, ECDH device key, scope gating, audit trail | CANONICAL |
| 50 | [uplift-tier-system](50-uplift-tier-system.md) | Free (6 uplifts, BYOK) vs Paid (25+ uplifts, managed) brain split | CANONICAL |

---

## Diagrams (OSS)

| # | Diagram | Content |
|---|---------|---------|
| 01 | [browser-startup-sequence](../diagrams/01-browser-startup-sequence.md) | 3-step boot (server + Playwright + webservice) |
| 02 | [cron-scheduler-patterns](../diagrams/02-cron-scheduler-patterns.md) | Cron job canonical patterns |
| 03 | [first-install-ux-flow](../diagrams/03-first-install-ux-flow.md) | 4-step onboarding flow |
| 04 | [tunnel-architecture](../diagrams/04-tunnel-architecture.md) | Secure remote browser control |
| 05 | [alcoa-evidence-chain](../diagrams/05-alcoa-evidence-chain.md) | FDA Part 11 evidence architecture |
| 23 | [three-surface-architecture](../src/diagrams/23-three-surface-architecture.md) | Companion + Sidebar + API: 3 surfaces, port map, before/after |
| 24 | [sidebar-tab-flow](../src/diagrams/24-sidebar-tab-flow.md) | Tab state machine, app detection sequence, run flow |
| 25 | [ipc-native-messaging](../src/diagrams/25-ipc-native-messaging.md) | Token bootstrap, security boundaries, process lifecycle |

---

## Private Papers (→ solace-cli/papers/)

Moved for trade secret protection. See solace-cli/papers/00-index.md.

| Was | Now at | Why |
|-----|--------|-----|
| 01-competitive-landscape | solace-cli/papers/23 | Competitive intel = private |
| 12-deployment-surface-mapping | solace-cli/papers/27 | Deployment strategy = private |
| 39-marketing-asset-pipeline | solace-cli/papers/39 | GTM strategy = private |
| 42-solace-inspector | solace-cli/papers/42 | **TRADE SECRET** |
| 43-webservices-northstar-abcd | solace-cli/papers/43 | Internal protocol = private |
| 45-launch-blessing-47-personas | solace-cli/papers/45 | Personas system = private |
| sop-01, sop-02 | solace-cli/papers/sop-* | Internal SOPs = private |

---

## Forbidden Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Moving private papers back to this repo | Competitive intel and trade secrets must stay in solace-cli/papers/ |
| Adding papers without updating the index table | Orphan papers become invisible and unmaintainable |
| Numbering gaps without a "Moved to" entry | Creates confusion about whether papers were deleted or relocated |

## Invariants (All Browser Papers)

1. LLM called ONCE at preview, never during execution
2. Evidence captured at event time, never retroactively
3. Fail-closed: any gate failure = BLOCKED
4. OAuth3 scoped delegation on every request
5. Local-first: computation in browser, cloud = sync only
6. No vendor API keys: web versions of all services
