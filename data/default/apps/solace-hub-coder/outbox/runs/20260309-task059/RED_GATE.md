# RED Gate

- NORTHSTAR metric advanced: `Local-First` and `Evidence by Default`.
- Initial gate failed before the fix because the original `tests/test_community_recipes.py` used a live HTTP socket in this sandbox and crashed during `build_server(...)` with `PermissionError: [Errno 1] Operation not permitted`.
- That failure blocked proof of the real feature gap: Task 059 install/fork/create flows updated only the community index and did not persist recipe JSON files into local recipe storage.
- The test harness was rewritten to the repo's existing direct-handler pattern so the feature could be verified without broadening capabilities.
