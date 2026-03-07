# Paper 48: Companion App Architecture — Tauri Desktop Launcher
# DNA: `companion(launch, manage, monitor, tunnel) = front_door(desktop) + sidebar(browser)`
# Forbidden: `ELECTRON_BLOAT | AUTO_RUN_WITHOUT_CONSENT | INBOUND_PORTS | PLAINTEXT_KEYS`
**Date:** 2026-03-07 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser
**Cross-ref:** Paper 47 (sidebar), Paper 49 (tunnel), Paper 50 (uplift-tier)

---

## 1. The Problem

Today, launching Solace Browser requires: install Python, install Playwright, run CLI command, navigate to localhost. That's a developer workflow, not a user workflow.

## 2. The Solution: Companion App Opens First

A lightweight Tauri desktop app (~20MB) is the first thing the user sees. It manages the Python backend, browser sessions, and system tray presence.

### User Flow

```
1. Double-click "Solace" on desktop
2. Companion app opens (600x800)
3. First-run wizard (3 screens, ~30s)
4. Click "Launch Browser"
5. Chromium opens with Yinyang sidebar
6. Companion app moves to system tray
```

## 3. Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Shell | Tauri (Rust + web frontend) | ~20MB binary, native menus, system tray |
| Frontend | HTML/CSS/JS (reuse sidebar design tokens) | Same tech as sidebar |
| Backend mgmt | Rust process supervisor | Spawn/monitor/restart Python |
| Keychain | tauri-plugin-stronghold | OS keychain for tokens and BYOK keys |

### Why Not Electron

Tauri: ~20MB, fast, native menus. Electron: ~150MB, memory hog. Since we control the tech stack and the frontend is simple HTML/CSS/JS, Tauri wins.

## 4. What the Companion App Shows

### Main Screen
- Server status (running/stopped)
- Active sessions (headed/headless) with toggle
- Recent activity (runs, costs, evidence links)
- Today's stats (runs, cost, time saved)
- Quick actions (Launch Browser, App Store, Schedules, Settings)

### Session Management
- Multiple simultaneous sessions (headed and headless)
- Head on/off toggle per session (~2-5s switch via storage_state)
- Per-session: URL, active app, progress, cost, OAuth3 scopes
- Resource cap: max background sessions (default 3)

### OAuth3 Dashboard
- Active scopes with TTL remaining
- Revocation controls
- Evidence chain stats
- Consent log export

## 5. Process Lifecycle

```
Tauri starts
  -> Spawns Python backend via Command
  -> Writes port to ~/.solace/port.lock
  -> Generates SOLACE_SESSION_SECRET
  -> Installs Native Messaging host manifest
  -> Health checks every 30s

On Python crash:
  -> Retry 3x with backoff (1s, 2s, 4s)
  -> Surface error in system tray

On Tauri quit:
  -> SIGTERM to Python child
  -> Wait 3s, then SIGKILL
  -> Delete port.lock
```

### Port Fallback
8888 -> 8889 -> 8890 (write chosen port to port.lock)

### Zombie Protection
- Python `atexit` + signal handlers close all Playwright contexts
- Tauri checks `~/.solace/server.pid` on launch (kill stale processes)
- Watchdog: 3 consecutive health check failures -> restart

## 6. First-Run Wizard

| Screen | Content |
|--------|---------|
| 1: Welcome | Yinyang logo + "Welcome to Solace Browser" |
| 2: LLM Setup | BYOK (paste key) vs Managed ($8/mo) vs Skip |
| 3: Launch | "Where do you start? [Gmail] [LinkedIn] [Slack]" -> Launch Browser |

### BYOK Key Storage
- macOS: Keychain via stronghold
- Windows: Credential Store via keyring crate (HKCU, no UAC)
- Linux: Secret Service (libsecret)
- Path: `solace/byok/{provider}`
- NEVER in SQLite or config files

## 7. System Tray / Menu Bar

```
[Yinyang icon]
  Status: 2 sessions active
  --------
  Session 1: Gmail (headed)
  Session 2: LinkedIn (headless) -- running...
  --------
  Launch New Session
  Open Companion App
  --------
  Today: 6 runs, $0.31, 45m saved
  --------
  Settings
  Quit Solace
```

## 8. Native Messaging Bridge

Tauri installs a Native Messaging host manifest (`com.solaceagi.bridge.json`) that points to a bundled binary. This is the ONLY secure IPC path between Tauri and the MV3 extension.

```
Extension loads -> chrome.runtime.connectNative("com.solaceagi.bridge")
  -> NM host returns {port: 8888, token: "...", tokenGeneration: 1}
  -> Extension stores in chrome.storage.session
```

### Windows NM Registration
- Per-user: `HKCU\Software\Google\Chrome\NativeMessagingHosts\`
- Also Edge: `HKCU\Software\Microsoft\Edge\NativeMessagingHosts\`
- NO UAC required

## 9. Python Distribution

| Strategy | Size | Cold Start | Platform |
|----------|------|-----------|----------|
| PyInstaller --onedir | ~40MB | <2s | All |
| PyInstaller --onefile | ~40MB | 3-8s | All (worse) |
| Nuitka | ~35MB | <1.5s | All (better perf) |

**Decision:** PyInstaller --onedir for v1. Total: Tauri (~20MB) + Python sidecar (~40MB) = ~60MB.

## 10. Pricing Impact

The companion app is FREE for all tiers, like the sidebar. It's the delivery vehicle.

| Component | Free | Starter ($8) | Pro ($28) |
|-----------|------|-------------|-----------|
| Companion App | Full | Full | Full |
| Sessions | 1 headed | 3 simultaneous | Unlimited |
| Headless | No | Yes (1) | Unlimited |
| Cloud Tunnel | No | No | Yes |

## 11. head-hidden Mode

Background sessions use `head-hidden` instead of true headless (keeps extension APIs working):

| Platform | Mechanism |
|----------|-----------|
| Linux | `--window-position=-32000,-32000` or Xvfb |
| macOS | LSUIElement: true (suppress Dock icon) |
| Windows | `--window-position=-32000,-32000` + SW_HIDE |

CPU overhead: ~15% vs true headless (acceptable for background automation).

## 12. Local Persistence

| Data | Store |
|------|-------|
| Schedules | SQLite (`~/.solace/solace.db`) |
| Evidence chain | SQLite (append-only, hash-chained) |
| Session state | In-memory (rebuilt on restart) |
| Preferences | `~/.solace/config.json` |
| Auth tokens | OS keychain |
| Port lock | `~/.solace/port.lock` |

---

## Interaction Patterns

| Actor | Action | Companion Response |
|-------|--------|-------------------|
| User double-clicks Solace | Tauri launches | Show main screen, spawn Python backend |
| User clicks Launch Browser | Spawn Chromium with extension | Move to system tray |
| Session crashes | Health check fails | Restart Python, notify via tray |
| User toggles headless | Kill context, relaunch | "Switching mode..." (2-5s) |
| User quits | SIGTERM chain | Clean shutdown, delete port.lock |

---

*Paper 48 | Auth: 65537 | Companion App = Front Door*
