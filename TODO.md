# TODO — Solace Browser
# Updated: 2026-03-01 | Auth: 65537
# Agent: Antigravity / Gemini 2.5 Pro
# Tests: 4,768 passed | Modules: 22+
# Run: pytest tests/ -v

---

## P0 — Critical (DONE)

### T1: Playwright browser auto-installer ✅
- DONE: `scripts/install_browsers.py` — platform-aware Playwright browser download
- CLI: --browser, --check, --dry-run, --install-deps, --timeout
- 61 tests in tests/test_install_browsers.py

### T2: Settings hot-reload ✅
- DONE: `src/settings_manager.py` — background polling (5s), callback-based, thread-safe
- register/unregister callbacks, force reload, daemon thread with clean shutdown
- 32 tests in tests/test_settings_manager.py

### T3: Personality customization ✅
- DONE: `src/yinyang/personality.py` — 5 personalities (Professional/Friendly/Playful/Minimal/Custom)
- Content filtering by personality tags, tone parameters for each module
- 37 tests in tests/test_personality.py

### T4: macOS binary build ✅
- DONE: `solace-browser-macos.spec` + `scripts/build-mac.sh` rewrite
- Universal binary (x86_64+arm64), ad-hoc codesign, GCS upload, SHA-256
- 30 tests in tests/test_macos_build.py

---

## P1 — Important (Do After P0)

### T5: Cloudflare tunnel integration
- `src/tunnel_client.py` — real Cloudflare tunnel (replace fake URL placeholder)
- Use `cloudflared` binary to create tunnel to local server
- Expose local Solace Browser instance at `*.trycloudflare.com`
- Auto-detect if `cloudflared` is installed, provide install instructions if not
- Test: mock cloudflared subprocess, verify URL extraction from stdout

### T6: Recipe versioning
- `src/recipes/versioning.py` — track recipe versions with semantic versioning
- Each recipe gets a `version` field in its JSON
- On update: bump minor version, keep previous version in `~/.solace/recipes/history/`
- Rollback support: `solace recipe rollback <name> <version>`
- Test: create recipe v1.0 → update → verify v1.1 exists + v1.0 in history

### T7: Offline mode improvements
- `src/offline_manager.py` — graceful degradation when no internet
- Cache last-known-good recipes locally
- Queue outbox items for later sync
- Show "offline" indicator in top rail (new state color: orange)
- Test: mock network failure → verify cached recipes still work

### T8: Evidence export
- `src/audit/export.py` — export evidence chains to PDF/JSON/CSV
- PDF: formatted report with hash chain verification
- JSON: raw evidence bundle (compatible with external audit tools)
- CSV: flattened for spreadsheet analysis
- Test: create 5 evidence entries → export to each format → verify content

---

## P2 — Nice to Have

### T9: Voice command integration
- Wire `src/voice/` module to Yinyang for voice-triggered actions
- "Hey Solace, run gmail compose" → trigger recipe
- Test: mock audio input → verify intent classification

### T10: Browser extension mode
- Package core functionality as Chrome extension (Manifest V3)
- Subset: top rail, budget display, recipe trigger
- No full automation (extension sandbox limits)

---

## Rules for Agent

1. Read `AGENTS.md` first — build commands, coding rules, architecture
2. Run `pytest tests/ -v` after EVERY change — must stay at 4,608+ passed, 0 failures
3. All new modules go in `src/` with matching `tests/test_<module>.py`
4. NEVER `except Exception: pass` — Fallback Ban is ABSOLUTE
5. Evidence captured at event time, never retroactively
6. All Playwright interactions go through 4-plane architecture (capture/control/execute/evidence)
7. Git commits need descriptive messages (no GLOW hook on this repo)
