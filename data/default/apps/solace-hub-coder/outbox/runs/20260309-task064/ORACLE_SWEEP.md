Task 064 focused sweep on the touched CLI-agent path:

- Detection remains cached through `shutil.which` with `lru_cache(maxsize=1)`.
- CLI invocation stays argv-based with subprocess timeout and checked exit status; no shell-enabled execution path was introduced in `yinyang_server.py`.
- Cost estimation still uses `Decimal` and returns a fixed-point string via `COST_PER_1M_TOKENS`.
- Auto agent selection now follows the required cheapest-first order: `gemini`, `aider`, `codex`, `claude`.
- Prompt injection now emits `[SKILL: ...]` headers exactly once per skill entry.
- Evidence ids now hash agent output bytes only.
- No generic catch-all exception handlers were found in `yinyang_server.py` or `tests/test_cli_agent_integration.py`.
- The touched production localhost references now flow through `HUB_PORT` and `YINYANG_PORT` rather than direct literals in the edited path.
- Verification witness: `pytest -q tests/test_cli_agent_integration.py` passed with `10 passed`.
