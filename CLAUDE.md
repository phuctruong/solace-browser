# CLAUDE.md — solace-browser
# DNA: `browser(fork+sidebar+hub+server) = chromium(native_webui) × port(8888) × evidence(sha256) × oauth3 → local_first_autonomy`
# Auth: 65537 | Version: 1.0.0 | Updated: 2026-03-08

## Identity

Solace Browser is a **Chromium fork** with a native AI sidebar (Yinyang), a desktop app (Solace Hub), and a Python backend (Solace Runtime). It is NOT a browser extension.

## Absolute Laws (VIOLATION = KILL)

| Law | Rule |
|-----|------|
| **Port** | 8888 ONLY. 9222 PERMANENTLY BANNED. Even in comments. Even as examples. |
| **Naming** | "Solace Hub" ONLY. "Companion App" BANNED everywhere. |
| **Extensions** | ZERO. No Chromium extension APIs, no MV3, no --load-extension. |
| **Lifecycle** | Hub spawns Server FIRST. Browser SECOND. Never reversed. |
| **Token** | sha256 in port.lock. Plaintext token NEVER in files/logs. |
| **Evidence** | Written at event time. Never retroactive. chmod 444 after seal. |
| **Fallback Ban** | catch FileNotFoundError/OSError/json.JSONDecodeError ONLY. No bare except. |
| **LLM** | Called ONCE at preview. Execution is CPU replay. $0.001/run on replay. |
| **Budget** | Any gate failure = BLOCKED. MIN-cap wins. Fail-open = breach. |
| **Platforms** | Build on native host. Sign before ship. Cross-compile = mislabeled. |

## Three Surfaces (Never Confuse)

```
Yinyang          = C++ WebUI sidebar built into Chromium fork (4 tabs: Now/Runs/Chat/More)
Solace Hub       = Tauri desktop app 20MB (tray, scheduler, OAuth3 dashboard, evidence viewer)
Solace Runtime   = Python backend localhost:8888 (serves both, 34+ apps, WebSocket, recipes)
```

## Project Structure

```
solace-runtime binary          — Main server (port 8888, 102 routes, 534 tests)
solace-hub/src-tauri/      — Tauri app (main.rs, 48/48 tasks COMPLETE)
data/default/apps/         — 36 apps (YAML manifests + inbox/outbox)
data/default/recipes/      — 56 recipes (deterministic CPU replay)
tests/                     — 534 tests (3 files: instructions/hub/mcp)
scripts/                   — Build + release scripts
  build-chromium.sh        — Chromium source build (Linux, ~3 hours)
  build-linux-release.sh   — portable Linux bundle builder (real Chromium + Hub)
  release_browser_cycle.sh — honest release entrypoint (Linux real, macOS/Windows fail closed)
  build-deb.sh             — Debian .deb package builder from portable release root
  promote_native_builds_to_gcs.py — GCS promotion (fail-closed gate)
  homebrew/solace-browser.rb      — Homebrew formula (blocked on real macOS browser bundle)
  winget/                  — winget manifests (blocked on real Windows browser bundle)
  windows/solace-browser.wxs      — WiX v4 MSI installer (blocked on real Windows browser bundle)
  snap/snapcraft.yaml        — Snap Store package from Linux portable release
  .github/workflows/         — CI/CD (real Linux bundle; macOS/Windows remain blocked)
source/src/out/Solace/     — Chromium build output for LOCAL DEV mode (gitignored)
```

## Architecture Decisions (LOCKED)

| Decision | Rule |
|----------|------|
| Storage | Git for apps/recipes. `~/.solace/` for vault + port.lock. |
| Auth | OAuth3 scopes + TTL + revocable. No long-lived tokens. |
| Evidence | Hash-chained SHA-256. Append-only. Part 11 compliant. |
| Sidebar | Native C++ WebUI (Mojo IPC) — never an extension. |
| Builds | Tauri for desktop. Chromium fork for browser. Python server stays separate from browser artifacts. |
| Distribution | Snap + apt + Homebrew + winget. Sign on every platform before ship. |

## Browser Launch Modes

| Mode | Intended artifact | Owner |
|------|-------------------|-------|
| `local-dev` | `source/src/out/Solace/solace-wrapper` → `solace` fallback | repo checkout + Chromium build tree |
| `production-bundle` | extracted `solace-browser-release/solace` bundle | downloadable Browser package |

The Hub must never treat a packaged `solace-runtime binary` executable as the Browser.

## FALLBACK BAN (Software 5.0 Law — ABSOLUTE)

```python
# BANNED:
except Exception: pass
except Exception: return None

# ALLOWED:
except FileNotFoundError: ...
except OSError: ...
except json.JSONDecodeError: ...
```

## Test Gate

```bash
pytest tests/ -q          # must be 534+ pass, 0 fail
cargo check               # solace-hub/src-tauri/ must compile
ninja -C source/src/out/Solace solace  # Chromium fork must link
```

## Distribution Checklist

1. Build Linux portable release with `scripts/build-linux-release.sh`
2. Build `.deb` with `scripts/build-deb.sh`
3. Upload Linux artifacts to GitHub release or GCS only after smoke verification
4. macOS/Windows stay blocked until real native Browser bundles exist

## Reference

- Papers: `solace-cli/papers/browser/` (29 papers, distilled in `CLAUDE.md`)
- Diagrams: `solace-cli/src/diagrams/browser/`
- NORTHSTAR: `NORTHSTAR.md` (this repo)
- Hub tasks: `solace-cli/data/default/apps/solace-hub-coder/inbox/tasks/` (48/48 COMPLETE)

---

*Auth: 65537 | "The browser is the last safe machine. Evidence is its immune system."*
