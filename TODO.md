# TODO — Solace Browser
# Updated: 2026-03-01 | Auth: 65537
# Agent: Antigravity / Gemini 2.5 Pro
# Tests: 4,608 passed | Modules: 18+
# Run: pytest tests/ -v

---

## P0 — Critical (Do First)

### T1: Playwright browser auto-installer
- Create `scripts/install_browsers.py` that downloads Playwright browsers
- Detect platform (Linux/macOS/Windows) and install correct binaries
- Show progress bar during download (~1.8GB)
- After install, verify with `playwright install --check`
- This is needed because PyInstaller binary (267MB) cannot bundle browsers
- Test: mock subprocess calls, verify platform detection logic

### T2: Settings hot-reload
- `src/settings_manager.py` — watch `~/.solace/settings.json` for changes
- Use `watchdog` or polling (every 5s) to detect file modifications
- Emit `settings_changed` event to all active modules
- Modules that need hot-reload: budget_gates (limits), auth_proxy (tokens), delight_engine (content)
- Test: write settings file → verify modules pick up changes within 10s

### T3: Personality customization
- `src/yinyang/personality.py` — user-selectable personality for Yinyang responses
- Personalities: Professional, Friendly, Playful, Minimal, Custom
- Stored in `~/.solace/settings.json` under `personality` key
- Affects: delight_engine content selection, support_bridge tone, warm_token style
- Default: Friendly
- Test: set personality → verify delight pool filters by personality tag

### T4: macOS binary build
- Create `solace-browser-macos.spec` for PyInstaller on macOS
- Handle macOS-specific: code signing (ad-hoc), universal binary (x86_64 + arm64)
- Update `scripts/build_binary.sh` to detect platform
- Upload to GCS: `gs://solace-downloads/solace-browser/v1.0.0/solace-browser-macos-universal`
- Test: spec file generates without errors (CI can't actually build macOS on Linux)

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
