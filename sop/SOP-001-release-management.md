# SOP-001: Release Management

| Field | Value |
|-------|-------|
| **SOP ID** | SOP-001 |
| **Title** | Solace Browser Release Management |
| **Version** | 1.0 |
| **Effective Date** | 2026-03-01 |
| **Author** | Phuc Truong (Dragon Rider, Authority 65537) |
| **Reviewed By** | Saint Solace (AI System) |
| **Classification** | Internal — Part 11 Architected |
| **Revision History** | See Section 8 |

---

## 1. Purpose

This SOP defines the standard procedure for releasing new versions of the Solace Browser software. It ensures every release is:
- **Tested** (automated test suite, 4,556+ tests)
- **Signed** (SHA-256 hash of binary)
- **Documented** (release notes, changelog)
- **Traceable** (git SHA, build timestamp, evidence chain)
- **Reproducible** (build from tagged commit produces identical binary)

## 2. Scope

Applies to all releases of:
- Solace Browser (desktop binary via PyInstaller)
- Solace Browser Server (Python package)
- Solace Browser Docker image (Cloud Run deployment)

## 3. Responsibilities

| Role | Responsibility |
|------|---------------|
| **Release Manager** | Coordinates release, verifies checklist, signs off |
| **QA Engineer** | Runs test suite, performs harsh QA, documents results |
| **DevOps** | Builds binary, uploads to distribution, updates CDN |
| **Legal/Compliance** | Reviews release notes for regulatory claims |

## 4. Pre-Release Checklist

### 4.1 Code Freeze
- [ ] All feature branches merged to `main`
- [ ] No open P0/P1 bugs
- [ ] All tests pass (`pytest tests/ -v` — 0 failures required)
- [ ] Test count documented (must be >= previous release)

### 4.2 Security Review
- [ ] No known CVEs in dependencies
- [ ] OAuth3 token handling reviewed
- [ ] Evidence chain integrity verified
- [ ] No secrets in codebase (`git secrets --scan`)

### 4.3 Documentation
- [ ] CHANGELOG.md updated with version entry
- [ ] Release notes drafted
- [ ] Migration guide (if breaking changes)
- [ ] API documentation updated (if endpoints changed)

## 5. Release Procedure

### 5.1 Tag and Build

```bash
# 1. Tag the release
git tag -a v{VERSION} -m "Release v{VERSION}"
git push origin v{VERSION}

# 2. Build binary
cd /home/phuc/projects/solace-browser
pyinstaller solace-browser.spec --noconfirm

# 3. Generate SHA-256 hash
sha256sum dist/solace-browser > dist/solace-browser.sha256
```

### 5.2 Sign and Verify

```bash
# 4. Record build metadata
cat > dist/BUILD_INFO.json << EOF
{
    "version": "{VERSION}",
    "git_sha": "$(git rev-parse HEAD)",
    "build_timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "python_version": "$(python --version)",
    "pyinstaller_version": "$(pyinstaller --version)",
    "platform": "$(uname -m)-$(uname -s)",
    "tests_passed": {TEST_COUNT},
    "tests_failed": 0,
    "builder": "$(whoami)@$(hostname)"
}
EOF

# 5. Verify binary starts
./dist/solace-browser --version
./dist/solace-browser --help
```

### 5.3 Upload to Distribution

```bash
# 6. Upload to GCS
VERSION={VERSION}
gcloud storage cp dist/solace-browser gs://solace-downloads/browser/v${VERSION}/solace-browser-linux-amd64
gcloud storage cp dist/solace-browser.sha256 gs://solace-downloads/browser/v${VERSION}/solace-browser-linux-amd64.sha256
gcloud storage cp dist/BUILD_INFO.json gs://solace-downloads/browser/v${VERSION}/BUILD_INFO.json

# 7. Update latest symlink
gcloud storage cp dist/solace-browser gs://solace-downloads/browser/latest/solace-browser-linux-amd64

# 8. Set public read
gcloud storage objects update gs://solace-downloads/browser/v${VERSION}/* --add-acl-grant=entity=allUsers,role=READER
```

### 5.4 Post-Release Verification

```bash
# 9. Download and verify
curl -O https://storage.googleapis.com/solace-downloads/browser/v${VERSION}/solace-browser-linux-amd64
curl -O https://storage.googleapis.com/solace-downloads/browser/v${VERSION}/solace-browser-linux-amd64.sha256
sha256sum -c solace-browser-linux-amd64.sha256

# 10. Smoke test
chmod +x solace-browser-linux-amd64
./solace-browser-linux-amd64 --version
```

## 6. Rollback Procedure

If a critical issue is discovered post-release:

1. Do NOT delete the existing release (evidence preservation)
2. Update `latest` symlink to previous known-good version
3. Create hotfix branch from tagged release
4. Follow full release procedure for hotfix version
5. Document rollback in incident report

## 7. Records

All release records are maintained in:
- Git tags (immutable, timestamped)
- `dist/BUILD_INFO.json` (uploaded with each release)
- `CHANGELOG.md` (version history)
- GCS bucket `gs://solace-downloads/browser/` (all versions preserved)

## 8. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-01 | Phuc Truong | Initial release |
