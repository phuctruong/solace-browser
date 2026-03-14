# Solace Browser Diagrams Audit — Post-Compression
# Updated: 2026-03-14 | GLOW 534

## Summary
- Source files tagged: 803/803 (100%)
- Rust runtime: 4,185 lines, 5.0MB release binary, 40 tests
- Legacy Python: 40,691 lines (yinyang_server.py — being replaced by Rust)
- Tests: 2,752 passing

## File Types
| Type | Count | Tagged | Notes |
|------|-------|--------|-------|
| .py (root) | 6 | 100% | Legacy — replaced by Rust |
| .py (tests/) | 202 | 100% | |
| .py (src/) | 37 | 100% | Browser server modules |
| .rs (runtime) | 39 | 100% | Solace Runtime (Rust) |
| .rs (hub) | 36 | 100% | Solace Hub (Tauri) |
| .html | 189 | 100% | Web UI + sidebar |
| .js | 164 | 100% | Web UI + sidebar |
| .css | 163 | 100% | Styles |
| .sh | 16 | 100% | Build + deploy scripts |

## Excludes (not source code)
- source/ (Chromium ~106GB) — managed by gclient
- depot_tools/ — Chromium build toolchain
- dist/ — built artifacts
- target/ — Rust build output
- patches/wry/ — third-party patches
