TASK: Test the coding app pipeline
PHASE: 0 (Setup verification)
TEMPORAL: No Chromium source compiled yet. Testing prompt composition only.

ACCEPTANCE CRITERIA:
1. Prompt composes correctly with all inbox files
2. All uplifts present in composed prompt
3. Claude CLI spawns and returns output
4. Diff parser extracts diffs from output
5. Path validator checks against allowed-paths.yaml
