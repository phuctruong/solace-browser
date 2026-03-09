# PATCH_DIFF

## Files changed
- Dockerfile.cloud-twin
- cloudbuild-twin.yaml
- requirements.txt
- scripts/deploy-cloud-twin.sh
- scripts/start-cloud-twin.sh
- tests/test_cloud_twin_docker.py
- yinyang_server.py

## Summary
- Added the cloud twin Docker image and Cloud Build config.
- Added the Xvfb startup script for head-hidden browser execution.
- Updated the deploy script to build and deploy the new twin image.
- Added cloud twin CLI parsing, runtime mode helpers, health payload metadata, and Chrome launch support.
- Added seven cloud twin tests covering the new container artifacts and server mode wiring.

## Diffstat
```
 requirements.txt             |   1 +
 scripts/deploy-cloud-twin.sh |  10 ++--
 yinyang_server.py            | 107 +++++++++++++++++++++++++++++++++++++------
 3 files changed, 100 insertions(+), 18 deletions(-)
```
