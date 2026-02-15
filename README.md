# Solace Browser

> Self-Improving Web Automation Agent with PrimeWiki Knowledge Capture
> **Auth**: 65537 | **Status**: 🎯 PRODUCTION
> **Version**: 2.0 (Persistent Server + Recipe System)

---

## Vision

Solace Browser is a **self-improving web crawler** that:
- ✅ **Browses websites** 20x faster (optimized persistent server)
- ✅ **Saves recipes** (externalized LLM reasoning for instant replay)
- ✅ **Builds PrimeWiki** (knowledge graphs with evidence + portals)
- ✅ **Updates skills** constantly as it learns
- ✅ **Documents itself** (commits knowledge automatically)

**Not just automation - it's a learning system that gets smarter with every interaction.**

---

## Quick Start

### Start the Browser Server

```bash
cd ~/projects/solace-browser

# Start persistent server (stays running)
python persistent_browser_server.py

# Server available at: http://localhost:9222
# Browser stays open - connect/disconnect anytime
```

### Use via HTTP API

```bash
# Navigate to LinkedIn
curl -X POST http://localhost:9222/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://linkedin.com/in/me/"}'

# Get cleaned HTML (best for LLM)
curl http://localhost:9222/html-clean | jq -r '.html'

# Click a button
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button:has-text(\"Save\")"}'

# Fill a form field
curl -X POST http://localhost:9222/fill \
  -d '{"selector": "#email", "text": "user@example.com"}'

# Save session (avoid re-login)
curl -X POST http://localhost:9222/save-session
```

### Execute Saved Recipes

```bash
# Run LinkedIn profile optimization
python replay_recipe.py recipes/linkedin-profile-optimization-10-10.recipe.json

# Result: 10/10 profile in ~5 minutes (vs hours of manual work)
```

---

## Architecture

```
solace-browser/
├── persistent_browser_server.py    # HTTP server (20x faster, stays alive)
├── enhanced_browser_interactions.py # ARIA + PageObserver + NetworkMonitor
├── browser_interactions.py          # ARIA tree extraction via CDP
│
├── recipes/                         # Externalized LLM reasoning
│   └── linkedin-profile-optimization-10-10.recipe.json
│
├── primewiki/                       # Knowledge graphs with evidence
│   └── linkedin-profile-optimization.primemermaid.md
│
├── canon/prime-browser/skills/      # Self-updating skills
│   └── web-automation-expert.skill.md
│
└── artifacts/                       # Sessions, screenshots, proofs
    ├── linkedin_session.json
    └── screenshots/
```

---

## Integration with Stillwater OS

Solace Browser depends on:
- `~/projects/stillwater/canon/prime-browser/` (Phase B recipes)
- `~/projects/stillwater/solace_cli/` (CLI wrappers)

Can import and use:
- Phase B snapshot canonicalization
- Phase B episode-to-recipe compiler
- Prime Browser skills
- Verification ladder (641→274177→65537)

---

## Development Phases

| Phase | What | Timeline |
|-------|------|----------|
| 1 | Fork + Setup | Week 1 |
| 2 | Episode Recording | Weeks 2-3 |
| 3 | Reference Resolution | Week 4 |
| 4 | Automated Posting | Week 5 |
| 5 | Proof Generation | Week 6 |
| 6 | CLI Bridge | Week 7 |

See `ROADMAP.md` for details.

---

## License

Solace Browser is built on Thorium, which is built on Chromium.
- Chromium: BSD 3-Clause License
- Thorium: Modifications under same BSD license
- Solace: Modifications under Stillwater OS license (65537 authority)

---

## Contributors

- 65537 Experts (Phuc Forecast methodology)
- Claude Code agents (implementation)

---

**Status**: 🟢 Phase 1 - Ready to initialize

