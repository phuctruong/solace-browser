# Solace Browser

Custom Chromium browser fork with native AI sidebar (Yinyang) + desktop app (Solace Hub).

## Architecture

Three surfaces:
1. **Yinyang** — native C++ sidebar (4 tabs: Now/Runs/Chat/More), follows user on every page
2. **Solace Hub** — Tauri desktop app (~20MB), system tray, OAuth3 dashboard, scheduler
3. **Yinyang Server** — Python backend at `localhost:8888`, serves both surfaces

## Quick Start

```bash
chmod +x scripts/*.sh && ./scripts/install.sh
./scripts/start-hub.sh
curl http://127.0.0.1:8888/api/status
# Then open Solace Browser after Hub is healthy
```

Solace Hub starts first. It launches Yinyang Server on `localhost:8888`, verifies the runtime, and then controls the Browser lifecycle.

## Browser Modes

The Browser now has two explicit modes:

1. `local dev`
   Uses the real Chromium build tree from `source/src/out/Solace/`.
   Hub should resolve `solace-wrapper` first, then `solace`.
2. `production bundle`
   Uses the downloadable Browser bundle layout (`solace-browser-release/solace`) that is meant to be uploaded to GCS and installed by humans.

Override mode explicitly when needed:

```bash
SOLACE_BROWSER_MODE=local-dev ./scripts/start-hub.sh
SOLACE_BROWSER_MODE=production-bundle ./scripts/start-hub.sh
```

## Human Smoke Path

1. Install the local scripts and service assets:
   `chmod +x scripts/*.sh && ./scripts/install.sh`
2. Start Solace Hub:
   `./scripts/start-hub.sh`
3. Verify Yinyang Server health separately from the Browser:
   `curl http://127.0.0.1:8888/api/status`
4. Launch the Browser and confirm the native Yinyang sidebar attaches.
5. Optionally verify agent control through `webservices` or `MCP` once the sidebar is live.

## Distribution

```bash
bash scripts/build-linux-release.sh
bash scripts/build-deb.sh
```

- `scripts/build-linux-release.sh` assembles `dist/solace-browser-release/` and `dist/solace-browser-chromium-linux-x86_64.tar.gz`.
- `scripts/build-deb.sh` reads the repo `VERSION`, reuses the portable release root, and builds `dist/solace-browser_<version>_amd64.deb`.
- The portable release root includes the real Chromium runtime, Solace Hub, Yinyang Server, and runtime assets.
- Local dev browser input: `source/src/out/Solace/solace-wrapper` or `source/src/out/Solace/solace`.
- Production browser bundle contract: extracted `solace-browser-release/solace`.
- `dpkg-deb` must be installed before running the packager.

## Manual Development

```bash
# Preferred: start Solace Hub first. It spawns Yinyang Server on 8888.
scripts/start-hub.sh

# Verify Yinyang Server on 8888
curl http://127.0.0.1:8888/api/status

# Low-level server debugging only (not the default onboarding path)
python3 yinyang-server.py

# Run tests
pytest tests/ -q
```

## Chromium Build

```bash
# Prerequisites (Ubuntu 22.04+)
export PATH="depot_tools:$PATH"
cd source/src
sudo python3 build/install-build-deps.py --no-arm --no-prompt

# Configure
gn gen out/Solace --args='is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true proprietary_codecs=false'

# Build (takes several hours on first run)
autoninja -C out/Solace solace

# Run
./out/Solace/solace
```

Or use the script: `scripts/build-chromium.sh`

## Key Rules

- Port **8888 ONLY**
- Use the name **Solace Hub**
- No Chromium extensions / MV3 — sidebar is native C++ WebUI
- Bearer auth required for mutating endpoints (POST/DELETE)

## Apps

36 apps in `data/default/apps/` — detected per-URL, executed via recipes.

## Tests

533 tests across 3 files:
- `tests/test_yinyang_instructions.py` — 330 API tests (109 test classes)
- `tests/test_solace_hub.py` — 181 structural tests
- `tests/test_mcp_server.py` — 22 MCP protocol tests

## License

Source-available under [FSL](https://fsl.software/) — converts to OSS after 4 years.
Chromium source code is licensed under the Chromium BSD license.
