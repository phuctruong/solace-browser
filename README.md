# Solace Browser

> Custom Thorium fork with integrated Solace automation
> **Auth**: 65537 | **Status**: Phase 1 - Initialization
> **Version**: 0.1.0-alpha

---

## Vision

Solace Browser is a custom fork of Thorium (optimized Chromium) with built-in Solace automation features:
- ✅ Episode recording (Phase B integration)
- ✅ Reference resolution (semantic + structural selectors)
- ✅ Automated posting (fill forms, click, type)
- ✅ Cryptographic proofs (verification)
- ✅ CLI bridge (bash integration)

No extension needed. Native browser automation.

---

## Quick Start

### Phase 1: Setup (Current)
```bash
cd ~/projects/solace-browser

# Initialize project
./scripts/init-thorium.sh

# Verify compilation
./scripts/build.sh --verify
```

### Phase 2-6: Development
See `ROADMAP.md` for detailed phases.

---

## Architecture

```
Solace Browser (Custom Thorium)
├── Thorium base (optimized Chromium)
├── Solace modules
│   ├─ episode-recorder.cc
│   ├─ reference-resolver.cc
│   ├─ action-executor.cc
│   ├─ proof-generator.cc
│   └─ ipc-bridge.cc
└── CLI interface
    └─ solace-browser command
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

