# LinkedIn Session Persistence Guide

## Overview

Once you log in to LinkedIn via Google OAuth, your session (cookies, localStorage, etc.) is automatically saved. This means:

✅ **Next time you start the browser, you'll already be logged in**
✅ **No need to go through Google OAuth again**
✅ **Your LinkedIn session persists across browser restarts**

---

## How It Works

### Step 1: First Login
```bash
python3 test_auto_login.py
```

When prompted, enter your Gmail password. The login flow will:
1. Navigate to LinkedIn
2. Click Google Sign-In button
3. Fill in your Gmail credentials
4. Complete 2FA (you approve on phone)
5. **Automatically save your session** ✓

Output:
```
Login Result:
{
  "success": true,
  "status": "logged_in",
  "message": "Successfully logged in to LinkedIn via Google OAuth"
}

✅ LOGIN SUCCESSFUL!

Saving session...
✓ Session saved! You'll be logged in next time automatically
  Session file: artifacts/linkedin_session.json
```

### Step 2: Subsequent Sessions (Already Logged In!)
```bash
python3 test_session_persistence.py load
```

This will:
1. Start the browser
2. **Load your saved session** (cookies automatically restored)
3. Navigate to LinkedIn feed
4. You're already logged in! ✓

---

## Files Involved

### Session Storage
- **Location**: `artifacts/linkedin_session.json`
- **Size**: ~50-100 KB
- **Content**: Cookies, localStorage, sessionStorage, and IndexedDB state
- **Auto-created**: After successful login

### Code Changes
- **Main file**: `solace_browser_server.py`
- **New methods**:
  - `save_session()` - Saves browser context state to JSON file
  - `load_session()` - Restores browser context state from JSON file
  - HTTP endpoints:
    - `POST /api/save-session` - Manually save current session
    - `GET /api/session-status` - Check if session file exists

### Test Scripts
- `test_auto_login.py` - Login + auto-save (recommended first time)
- `test_session_persistence.py save` - Manually save a session
- `test_session_persistence.py load` - Load and test a saved session

---

## Usage Patterns

### Pattern 1: Full Flow (Recommended)
```bash
# First time - login and save
python3 test_auto_login.py

# Subsequent times - automatically logged in
python3 test_session_persistence.py load
```

### Pattern 2: Manual Save/Load
```bash
# Open browser and use manually, then save
python3 test_session_persistence.py save

# Later, resume with saved session
python3 test_session_persistence.py load
```

### Pattern 3: In Your Code
```python
import asyncio
from solace_browser_server import SolaceBrowser

async def main():
    # Browser automatically loads saved session if it exists
    browser = SolaceBrowser(headless=False)
    await browser.start()

    # You're already logged in! ✓
    await browser.navigate("https://www.linkedin.com/feed/")

    # Do stuff...

    # Session is automatically saved on stop()
    await browser.stop()

asyncio.run(main())
```

---

## Clearing Your Session

To log out and clear the saved session:

```bash
rm artifacts/linkedin_session.json
```

Then next time you start, you'll need to login again.

---

## Technical Details

### What Gets Saved?
- **Cookies**: Session tokens, CSRF tokens, preferences
- **localStorage**: Client-side data
- **sessionStorage**: Temporary session data
- **IndexedDB**: LinkedIn's offline data cache

### Security
- ✅ Session file is stored locally on your machine
- ✅ Cookies have expiration dates (LinkedIn refreshes them)
- ⚠️ Keep `artifacts/linkedin_session.json` private (don't commit to git)
- ⚠️ If someone gains access to your machine, they can access the session

### Expiration
- LinkedIn sessions typically expire after 14-30 days of inactivity
- Cookies will be automatically refreshed on next login
- If session expires, you'll need to log in again

---

## API Endpoints

### Save Session (Manual)
```bash
curl -X POST http://localhost:9222/api/save-session
```

Response:
```json
{
  "success": true,
  "session_file": "artifacts/linkedin_session.json",
  "message": "Browser session saved (cookies, localStorage, etc.)"
}
```

### Check Session Status
```bash
curl http://localhost:9222/api/session-status
```

Response:
```json
{
  "session_exists": true,
  "session_file": "artifacts/linkedin_session.json",
  "file_size": 85432,
  "message": "Session file found"
}
```

---

## Troubleshooting

### Session not loading?
```bash
# Check if session file exists
ls -lh artifacts/linkedin_session.json

# If not, run login again
python3 test_auto_login.py
```

### Still getting logged out?
- LinkedIn might have invalidated your session (timeout)
- Clear the session and login again: `rm artifacts/linkedin_session.json`
- Try with a fresh login

### Session file is too old?
- Sessions expire after 14-30 days
- Login again to refresh: `python3 test_auto_login.py`

---

## Summary

🎯 **One-time setup**: Run `test_auto_login.py` once
🔄 **Future sessions**: Browser auto-loads saved session
⚡ **No more OAuth**: Skip the Google popup (unless session expires)
💾 **Persistent state**: Cookies stay across restarts

Enjoy seamless LinkedIn automation! 🚀
