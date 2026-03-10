# Solace Hub

Tauri 1.x desktop app for the Solace AI Worker Platform.

**App name:** Solace Hub
**Port:** 8888 (Yinyang Server — ONLY this port, ever)
**Binary target:** ~20 MB
**Runtime:** OS WebView (not Electron, no bundled Chromium)

---

## Architecture

```
Solace Hub (Tauri binary)
  │
  ├── spawns → yinyang-server.py  (Python, port 8888)
  │               ↑ waits for /health before continuing
  │
  ├── reads  → ~/.solace/port.lock   (JSON: port + SHA-256 token hash only)
  ├── stores → OS keychain           (macOS Keychain / libsecret / DPAPI)
  │
  ├── tray   → "Open Browser"   → launches Solace Browser binary
  │            "Show Solace Hub" → shows/focuses main window
  │            "Quit Solace Hub" → SIGTERM server → delete port.lock → clear keychain
  │
  └── window → index.html (fetch localhost:8888 for stats, sessions, schedules, evidence)
```

**Lifecycle (enforced order):**

1. `spawn_yinyang_server()` — Python backend starts first
2. `wait_for_server("http://localhost:8888/health", 10s)` — block until healthy
3. `read_port_lock()` — parse `~/.solace/port.lock`
4. `store_token_keychain()` — OS keychain, never plaintext files
5. Build system tray
6. "Open Browser" → `launch_solace_browser()`
7. "Quit" → SIGTERM server → `delete_port_lock()` → `clear_token_keychain()` → exit

---

## Human Smoke Path

Solace Hub starts first.

```bash
cd /home/phuc/projects/solace-browser
./scripts/start-hub.sh
curl http://127.0.0.1:8888/api/status
```

If `api/status` responds, Hub has brought Yinyang Server up on `localhost:8888` and the Browser can be launched safely.

---

## Prerequisites

- **Rust + Cargo**: see `../scripts/install-rust.sh`
- **Tauri CLI**: `cargo install tauri-cli`
- **System deps (Linux)**:
  ```bash
  sudo apt-get install -y \
    libwebkit2gtk-4.0-dev \
    build-essential \
    curl \
    wget \
    libssl-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev
  ```
- **Python 3** on PATH (for yinyang-server.py)

---

## Icons

Place `yinyang-logo.png` in `src-tauri/icons/`:

```bash
# Copy from the browser source assets (when available):
cp /home/phuc/projects/solace-browser/data/default/yinyang-logo.png \
   /home/phuc/projects/solace-browser/solace-hub/src-tauri/icons/yinyang-logo.png
```

If not yet available, create a placeholder 256×256 PNG for dev builds:

```bash
# Minimal PNG placeholder (requires ImageMagick):
convert -size 256x256 xc:black -fill white -draw "circle 128,128 128,10" \
  src-tauri/icons/yinyang-logo.png
```

Tauri also expects several icon sizes for bundling. For production, generate all
required sizes from the master PNG:

```bash
cargo tauri icon src-tauri/icons/yinyang-logo.png
```

This writes all platform-specific icon variants (`.ico`, `.icns`, sized `.png`) into
`src-tauri/icons/`.

---

## Build

```bash
# 1. Install Rust (if not present)
bash ../scripts/install-rust.sh

# 2. Install Tauri CLI
cargo install tauri-cli

# 3. Development mode (hot-reload, loads src/index.html from filesystem)
cd solace-hub
cargo tauri dev

# 4. Production build (~20 MB binary)
cargo tauri build
# Output: src-tauri/target/release/bundle/
```

---

## File Structure

```
solace-hub/
  src-tauri/
    Cargo.toml         — Rust dependencies (tauri 1.x, keyring, sha2, tokio)
    build.rs           — tauri-build script (required by Tauri)
    main.rs            — full app: server spawn, tray, token, browser launch
    tauri.conf.json    — product name "Solace Hub", bundle ID, icon paths
    icons/
      yinyang-logo.png — (copy manually, see Icons section above)
  src/
    index.html         — Hub window: status, sessions, schedules, evidence, Open Browser btn
```

---

## Security Properties

| Property | Mechanism |
|---|---|
| Token storage | OS keychain (keyring crate) — NEVER written to disk as plaintext |
| port.lock content | `{ "port": 8888, "token_hash": "<sha256-hex>" }` only |
| Token integrity | On startup: retrieve from keychain → re-hash → compare to port.lock |
| Shutdown | SIGTERM server → delete port.lock → clear keychain (atomic cleanup) |
| CSP | `connect-src 'self' http://localhost:8888` only |

---

## Naming Laws (ABSOLUTE — never violate)

- App name: **Solace Hub** — "Companion App" is permanently banned
- Port: **8888** — this is the only runtime control port
- Sidebar: **Yinyang** (native C++ WebUI, NOT an extension)
- Backend: **Yinyang Server** (`yinyang-server.py`, localhost:8888)
