# Solace Browser Papers Index
**Updated:** 2026-03-03 | **Auth:** 65537

## Papers

| # | Paper | Content | Status |
|---|-------|---------|--------|
| 01 | competitive-landscape | 19 competitors analyzed, 7 structural gaps, pricing | CANONICAL |
| 02 | app-inbox-outbox-standard | Universal app contract, inbox/outbox convention | CANONICAL |
| 03 | web-native-automation | No API keys, web versions, exclusive categories | CANONICAL |
| 04 | yinyang-dual-rail-browser | Top rail (status) + bottom rail (chat), Anti-Clippy laws | CANONICAL |
| 05 | pzip-stillwater-capture | PZip architecture, 100% RTC, Prime Mermaid as ripple | CANONICAL |
| 06 | part11-evidence-browser | ALCOA+ compliance, data vs visual mode, e-signing | CANONICAL |
| 07 | budget-wallet-enforcement | Per-app budgets, fail-closed gates, MIN-cap delegation | CANONICAL |
| 08 | cross-app-yinyang-delight | Cross-app orchestration, Yinyang universal interface, delight engine, 18 day-one apps | CANONICAL |
| 09 | yinyang-tutorial-funpack-mcp | Tutorial popup (5-step, 13 locales), Fun Pack standard, OAuth3 leave-app gate, Agent Notification API, MCP server (7 tools), YinYang Chat (OpenRouter) | CANONICAL |
| 10 | production-browser-release-loop | Compile -> upload -> download -> head-on smoke -> production API matrix, timed release loop, default bundle policy | CANONICAL |
| 11 | app-store-sync-governance | Git-backed official catalog, Firestore proposal queue, local file backend for dev, promotion workflow | CANONICAL |
| 12 | solaceagi-deployment-surface-mapping | Domain mapping + trigger source verification, repo/service ownership matrix, website -> GCS download-link contract | CANONICAL |

## Cross-References

| This Paper | solaceagi Papers | solace-cli Papers/Diagrams |
|-----------|-----------------|---------------------------|
| 01 competitive-landscape | solace-marketing/STRATEGY.md | Paper 09 (SW5.0 Triangle) |
| 02 app-inbox-outbox | papers/13-agent-inbox-outbox.md | Diagram 07 (Sync Bus) |
| 03 web-native-automation | papers/01-solace-browser-white-paper.md | Paper 07 (Three Realms) |
| 04 yinyang-dual-rail | papers/22+25 (Yinyang proposal+spec) | Diagram 13 (Yinyang FSM) |
| 05 pzip-stillwater | papers/14+20 (PZip+PrimeWiki) | Paper 12 (Prime Vision), Diagram 11 (PM Snapshot) |
| 06 part11-evidence | papers/07+11 (Part 11) | Diagram 03 (Evidence Bundling) |
| 07 budget-wallet | papers/04+19 (Wallet+Preview) | Paper 14 (Phase 4 Dispatch), Diagram 10 (Core Flow) |
| 08 cross-app-delight | papers/13 (Inbox/Outbox), 22+25 (Yinyang) | Paper 04 (Triple-Twin warm tokens), Diagrams 16-18 |
| 09 tutorial-funpack-mcp | papers/22+25 (Yinyang), 04+19 (Wallet) | Paper 04 (Triple-Twin), Diagram 13 (Yinyang FSM) |
| 10 production-browser-release-loop | solaceagi download + API deployment docs | Diagram 19 (Browser Release Loop) |
| 11 app-store-sync-governance | app-store release + community submission process | Diagram 20 (App Store Sync Governance) |
| 12 deployment-surface-mapping | Cloud Run domain + trigger ownership | Diagram 21 (Deployment Surface Mapping) |

## Invariants (All Papers)

1. LLM called ONCE at preview, never during execution
2. Evidence captured at event time, never retroactively
3. Fail-closed: any gate failure = BLOCKED, never degrade
4. OAuth3 scoped delegation: Bearer sw_sk_ on every request
5. Local-first: all computation runs in browser, cloud = sync only
6. Zero CRUD in browser UI: read-only display + VS Code + Yinyang
7. File = single source of truth, browser watches for changes
8. No vendor API keys: web versions of all services
