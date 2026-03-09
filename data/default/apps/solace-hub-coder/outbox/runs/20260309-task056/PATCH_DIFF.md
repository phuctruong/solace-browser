# Task 056 Patch Diff

## Changed files
- `yinyang_server.py:131` adds Prime Wiki constants, storage root, snapshot types, and cloud push config.
- `yinyang_server.py:613` adds CPU-structural extraction helpers for metadata, title, headings, and CTAs.
- `yinyang_server.py:791` adds snapshot record creation, gzip/base64 compression, local storage, diff, stats, and async cloud push helpers.
- `yinyang_server.py:2483` wires GET routes for snapshot detail, lazy content fetch, diff, and stats.
- `yinyang_server.py:2709` wires POST `/api/v1/prime-wiki/snapshot`.
- `yinyang_server.py:3043` adds the request handlers for snapshot create/detail/content/diff/stats.
- `tests/test_prime_wiki_snapshots.py:1` adds 8 focused tests for compression, hashing, extraction, diffing, stats, async sync, and local storage layout.

## Behavioral delta
- Captures snapshots as gzip-compressed, base64-encoded records stored under `~/.solace/prime-wiki/<url_hash[:16]>`.
- Computes SHA-256 over uncompressed HTML and returns snapshot metadata without exposing content on the metadata route.
- Extracts `title`, `headings`, `ctas`, and `metadata` using BeautifulSoup when available, otherwise regex fallback.
- Returns structural diffs and aggregate local stats.
- Pushes snapshots to the Prime Wiki cloud API only on `pro`+ tiers using `threading.Thread(daemon=True)`.
