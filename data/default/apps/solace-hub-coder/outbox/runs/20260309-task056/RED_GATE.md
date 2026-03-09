# RED Gate

## Guardrails checked
- No usage of port `9222` was introduced.
- No LLM-backed extraction was introduced; extraction is CPU-structural only.
- No synchronous cloud push was introduced; sync is queued on a daemon thread.
- No `except Exception` blocks were added.
- `GET /api/v1/prime-wiki/snapshot/{id}` omits `content_gzip_b64`.

## Negative-risk notes
- The repository already contains unrelated working tree changes outside this task; this patch stays scoped to `yinyang_server.py` and `tests/test_prime_wiki_snapshots.py`.
