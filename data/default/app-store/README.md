# App Store Data

- `official-store.json`: Official app catalog, git-backed source of truth for website + browser app store.
- `proposed-apps-dev.jsonl`: Local development proposal queue (file backend). Safe to commit for team review.

## Sync Command

```bash
python3 src/scripts/sync_app_store_catalog.py
```

## Backend Mode

- Local development (default): `SOLACE_APP_STORE_PROPOSALS_BACKEND=file`
- Production proposals: `SOLACE_APP_STORE_PROPOSALS_BACKEND=firestore`

