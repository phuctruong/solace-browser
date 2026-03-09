**Done**
- Added the launcher flow in `scripts/launch-yinyang.sh:1`, `scripts/stop-yinyang.sh:1`, `scripts/install.sh:1`, and `scripts/yinyang.service:1`.
- Updated quick-start docs in `README.md:12`.
- Wrote the required handoff artifacts in `outbox/runs/TASK-009-launcher/PATCH_DIFF.md:1`, `outbox/runs/TASK-009-launcher/GREEN_GATE.md:1`, and `outbox/runs/TASK-009-launcher/EVIDENCE.json:1`.

**Validation**
- `bash -n` passes for all three shell scripts.
- Temp-home harness passes: install twice, launch twice, stop twice, with the installed launcher proving it calls `yinyang-server.py` using the persisted repo root.
- Real-path launch against the actual entrypoint fails loudly and correctly under this sandbox because localhost socket bind is blocked; the launcher now surfaces that cleanly via `$HOME/.solace/yinyang.log`.
- `systemd-analyze verify` is sandbox-blocked here, but the unit fields are valid and the install path is user-local with `/bin/sh` as the executable.
- Banned-term sweep over touched files and outbox artifacts passes.

If you want, I can next give you a one-command host-side smoke test to run outside the sandbox.