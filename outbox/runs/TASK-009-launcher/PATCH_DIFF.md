# PATCH DIFF — TASK-009-launcher

- Added `scripts/launch-yinyang.sh` to start `yinyang-server.py` on port `8888`, persist a PID in `$HOME/.solace/yinyang.pid`, and wait up to 5 seconds for `/health`.
- Added `scripts/stop-yinyang.sh` to stop the tracked process with `TERM`, wait 3 seconds, then force-stop if needed, and remove the PID file.
- Added `scripts/yinyang.service` as a user unit that runs the launcher from `%h/.local/lib/solace/` and restarts on failure.
- Added `scripts/install.sh` to create `$HOME/.solace/`, copy launcher assets into `$HOME/.local/lib/solace/`, install the user unit into `$HOME/.config/systemd/user/`, persist the repo root, and enable the unit.
- Updated `README.md` quick-start so the launcher install path is the default local-first flow.

## Files Changed

- `scripts/launch-yinyang.sh`
- `scripts/stop-yinyang.sh`
- `scripts/yinyang.service`
- `scripts/install.sh`
- `README.md`

## Key Behaviors

- `launch-yinyang.sh` is idempotent: a healthy server on `8888` returns success without spawning a duplicate process.
- `launch-yinyang.sh` fails loudly when the child exits before health goes green and points to `$HOME/.solace/yinyang.log`.
- `install.sh` records the repository root in `$HOME/.solace/repo-root` so the installed launcher can still find `yinyang-server.py`.
- `yinyang.service` uses `%h` so the unit remains user-local and does not require root.
