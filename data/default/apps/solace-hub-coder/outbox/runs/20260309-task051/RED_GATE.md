# RED Gate

## Command
```bash
pytest -q tests/test_domain_detection.py
```

## Expected failing assertions proven before the patch
- `assert status == 200` failed for `GET /api/v1/apps/by-domain?domain=web.whatsapp.com` because the route returned `404`.
- `assert status == 401` failed for unauthenticated domain lookup because the route returned `404`.
- `assert status == 200` failed for `GET /api/v1/user/tier` because the route returned `404`.
- `assert status == 201` failed for `POST /api/v1/apps/custom/create` because the route returned `404`.
- `assert status == 403` failed for `POST /api/v1/apps/sync` because the route returned `404`.
- `sidepanel.html` did not exist, causing `FileNotFoundError`.

## Witness
- `8 failed in 0.65s`
