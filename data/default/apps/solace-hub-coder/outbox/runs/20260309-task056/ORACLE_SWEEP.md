# ORACLE Sweep

## Spec coverage
- Prime Wiki storage root and URL-hash bucketing implemented in `yinyang_server.py:576` and `yinyang_server.py:822`.
- Structural extraction implemented in `yinyang_server.py:613`, `yinyang_server.py:698`, `yinyang_server.py:716`, and `yinyang_server.py:759`.
- Snapshot POST route implemented in `yinyang_server.py:2709` and handler in `yinyang_server.py:3043`.
- Snapshot metadata/content GET routes implemented in `yinyang_server.py:2487`, `yinyang_server.py:2490`, `yinyang_server.py:3110`, and `yinyang_server.py:3117`.
- Diff route implemented in `yinyang_server.py:2483`, `yinyang_server.py:904`, and `yinyang_server.py:3133`.
- Stats route implemented in `yinyang_server.py:2485`, `yinyang_server.py:931`, and `yinyang_server.py:3149`.
- Async cloud push implemented in `yinyang_server.py:959` and `yinyang_server.py:1005`.

## Test sweep
- Compression round-trip: `tests/test_prime_wiki_snapshots.py:91`
- SHA-256 integrity: `tests/test_prime_wiki_snapshots.py:121`
- Title/headings extraction: `tests/test_prime_wiki_snapshots.py:141`
- CTA extraction: `tests/test_prime_wiki_snapshots.py:160`
- Diff behavior: `tests/test_prime_wiki_snapshots.py:180`
- Stats aggregation: `tests/test_prime_wiki_snapshots.py:215`
- Async sync non-blocking: `tests/test_prime_wiki_snapshots.py:241`
- Local storage layout: `tests/test_prime_wiki_snapshots.py:264`
