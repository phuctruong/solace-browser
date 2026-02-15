# SOLACE BROWSER - SECURE CREDENTIAL SETUP

**Status**: Phase 2 Critical Fix #1 Complete
**Date**: 2026-02-15
**Auth**: 65537

---

## Overview

Solace Browser now uses **environment variables** for credential management instead of plaintext files. This is a **CRITICAL SECURITY FIX** that:

✅ Prevents credentials from being accidentally committed to git
✅ Keeps credentials in environment memory (not on disk)
✅ Supports cloud deployment (Cloud Run, Docker, etc.)
✅ Enables easy credential rotation
✅ Follows industry best practices (12-Factor App)

---

## Quick Setup (5 Minutes)

### Step 1: Create a .env file

Copy the example file and add your credentials:

```bash
cp .env.example .env
```

Then edit `.env` and add your actual credentials:

```bash
# Your email for Gmail
GMAIL_EMAIL=your-email@gmail.com

# For Gmail: Go to https://myaccount.google.com/apppasswords
# Select "Mail" + "Windows Computer", copy the 16-char password
GMAIL_PASSWORD=xxxx xxxx xxxx xxxx

# Your LinkedIn credentials
LINKEDIN_EMAIL=your-email@linkedin.com
LINKEDIN_PASSWORD=your-password

# (Optional) Google credentials (usually same as Gmail)
GOOGLE_EMAIL=your-email@gmail.com
GOOGLE_PASSWORD=xxxx xxxx xxxx xxxx
```

**IMPORTANT**: `.env` is in `.gitignore` - it will NEVER be committed.

### Step 2: Load environment variables

Before running any scripts:

```bash
# Load .env file into environment
source .env

# Verify credentials are loaded
echo $GMAIL_EMAIL  # Should show your email
```

### Step 3: Test credential loading

```bash
python3 credential_manager.py

# Expected output:
# ✅ Gmail credentials loaded
# ✅ All credentials validated
```

---

## For Each Service

### Gmail Setup

1. **Generate App Password** (required - not your regular password):
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" → "Windows Computer"
   - Copy the 16-character password
   - Add to .env:
     ```
     GMAIL_EMAIL=your-email@gmail.com
     GMAIL_PASSWORD=xxxx xxxx xxxx xxxx
     ```

2. **For Security**: Enable 2-Step Verification first
   - https://myaccount.google.com/security

3. **Test Gmail login**:
   ```bash
   source .env
   python3 haiku_swarm_gmail_correct_login.py
   ```

### LinkedIn Setup

1. **Use your LinkedIn password**:
   - `LINKEDIN_EMAIL`: Your LinkedIn email
   - `LINKEDIN_PASSWORD`: Your LinkedIn password

2. **Test login**:
   ```bash
   source .env
   python3 -c "from credential_manager import CredentialManager; print(CredentialManager.get_credentials('linkedin'))"
   ```

---

## Integration with Scripts

Scripts now automatically load credentials using `CredentialManager`:

```python
from credential_manager import CredentialManager

# Load credentials
creds = CredentialManager.get_credentials('gmail')
email = creds['email']
password = creds['password']

# Error handling included - will show helpful message if env vars missing
```

Updated files:
- `haiku_swarm_gmail_correct_login.py` ✅
- `gmail_production_flow.py` ✅
- Other login scripts (to be updated)

---

## Running in Different Environments

### Local Development

```bash
# Load .env file
source .env

# Run script
python3 my_script.py
```

### Docker Container

```bash
# Build with .env baked in (NOT RECOMMENDED for production)
docker run -e GMAIL_EMAIL="..." -e GMAIL_PASSWORD="..." solace-browser

# Or use docker-compose with env file:
docker-compose up --env-file .env
```

### Cloud Run (Google Cloud)

```bash
# Set secrets in Cloud Run
gcloud run deploy solace-browser \
  --set-env-vars GMAIL_EMAIL=your-email@gmail.com \
  --set-env-vars GMAIL_PASSWORD=your-app-password

# Or use Secret Manager (recommended):
gcloud secrets create gmail-email --data-file=-
gcloud secrets create gmail-password --data-file=-

gcloud run deploy solace-browser \
  --set-env-vars GMAIL_EMAIL=projects/PROJECT_ID/secrets/gmail-email/versions/latest
```

### GitHub Actions CI/CD

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Test with credentials
        env:
          GMAIL_EMAIL: ${{ secrets.GMAIL_EMAIL }}
          GMAIL_PASSWORD: ${{ secrets.GMAIL_PASSWORD }}
        run: |
          python3 credential_manager.py
```

---

## Credential Rotation

**IMPORTANT**: The previous credentials in `credentials.properties` were visible in plaintext. **These credentials should be rotated immediately**:

### For Gmail

1. Go to https://myaccount.google.com/apppasswords
2. Delete any app passwords that might have been compromised
3. Create a NEW app password
4. Update `.env` with the new password
5. Delete the old `credentials.properties` file (already done ✅)

### For LinkedIn

1. Go to https://www.linkedin.com/account/
2. Change password under "Sign in & security"
3. Consider enabling 2-Step Verification
4. Update `.env` with new password

### For GitHub

1. Go to https://github.com/settings/tokens
2. Revoke any personal access tokens
3. Create a new token if needed

---

## Troubleshooting

### Error: "Missing required environment variable: GMAIL_EMAIL"

**Solution**: Load the .env file:
```bash
source .env
# Then run your script
python3 my_script.py
```

### Error: "credentials.properties not found"

**This is expected and GOOD** - we deleted it for security reasons. Use `.env` instead:
```bash
source .env
```

### Credentials not loading in IDE

**IntelliJ IDEA / PyCharm**:
1. Edit Run Configuration
2. Environment variables → paste contents of `.env`:
   ```
   GMAIL_EMAIL=...;GMAIL_PASSWORD=...;LINKEDIN_EMAIL=...
   ```

**VS Code**:
1. Install "Thunder Client" or similar extension
2. Create `.env` file in project root
3. Python extension will auto-load it

---

## Security Checklist

- [ ] `.env` file created with YOUR credentials
- [ ] `.env` is in `.gitignore` (verify: `git status`)
- [ ] Never commit `.env` to git
- [ ] Old `credentials.properties` deleted ✅
- [ ] Old passwords rotated (Gmail, LinkedIn, etc.)
- [ ] Tested credential loading: `python3 credential_manager.py`
- [ ] Verified scripts work with `source .env`

---

## How CredentialManager Works

Under the hood, `credential_manager.py` provides:

```python
class CredentialManager:
    # Load from environment variables
    creds = CredentialManager.get_credentials('gmail')
    # Returns: {'email': 'phuc@example.com', 'password': '...'}

    # Validate all configured services
    CredentialManager.validate_all()  # Returns True/False

    # Get safe debug info (masks passwords)
    info = CredentialManager.get_safe_debug_info()
    # Shows: "GMAIL_EMAIL=p***m"
```

---

## Next Steps

1. **Immediate** (today):
   - [ ] Copy `.env.example` to `.env`
   - [ ] Add your credentials
   - [ ] Test: `source .env && python3 credential_manager.py`
   - [ ] Rotate old passwords (Gmail, LinkedIn)

2. **Short-term** (this week):
   - [ ] Update all scripts to use `CredentialManager`
   - [ ] Test all login flows with new system
   - [ ] Verify `.env` is in `.gitignore`

3. **Long-term** (for production):
   - [ ] Use managed secrets (Cloud Run, AWS Secrets Manager)
   - [ ] Remove `.env` from local machines
   - [ ] Use CI/CD environment variables

---

## References

- 12-Factor App: https://12factor.net/config
- Google App Passwords: https://myaccount.google.com/apppasswords
- Python-dotenv: https://github.com/theskumar/python-dotenv
- Cloud Run Secrets: https://cloud.google.com/run/docs/configuring/secrets

---

**Auth**: 65537 | **Status**: COMPLETE ✅
**Previous Vulnerability**: Plaintext credentials in `credentials.properties` (DELETED)
**Current Status**: Environment variables (SECURE)
