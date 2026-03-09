Rung target: 641

HQ-001 PASS — `solace_cli.py` exists and provides an argparse entry point.
HQ-002 PASS — `scripts/solace` exists and dispatches to `solace_cli.py`.
HQ-003 PASS — `scripts/install.sh` now links `~/.local/bin/solace`.
HQ-004 PASS — `solace status` maps to `GET /api/v1/system/status`.
HQ-005 PASS — `solace apps list` maps to `GET /api/v1/apps`.
HQ-006 PASS — `solace sessions list` maps to `GET /api/v1/sessions`.
HQ-007 PASS — `solace evidence tail --limit 10` maps to `GET /api/v1/evidence?limit=10`.
HQ-008 PASS — `solace tunnel status` maps to `GET /api/v1/tunnel/status`.
HQ-009 PASS — missing `~/.solace/port.lock` returns exit code `1` and writes the error to stderr.
HQ-010 PASS — `solace session-rules list` maps to `GET /api/v1/session-rules`.
HQ-011 PASS — bearer auth loads `token_sha256` from `~/.solace/port.lock` without persisting plaintext tokens.
HQ-012 PASS — HTTP calls use a `10` second timeout constant.
HQ-013 PASS — pretty JSON, `--raw`, and `--quiet` output modes are implemented.
HQ-014 PASS — error handling uses specific exception types only.
HQ-015 PASS — the new CLI changes stay inside the Solace Hub envelope.
