# LinkedIn Google OAuth - Quick Start Guide

## 🚀 Quick Start (2 minutes)

### 1. Start the Browser Server
```bash
cd /home/phuc/projects/solace-browser
python3 solace_browser_server.py
```

Output should show:
```
2026-02-14 18:34:00,123 - solace-browser - INFO - Starting Solace Browser (headless=False)
2026-02-14 18:34:00,567 - solace-browser - INFO - ✓ Solace Browser started
2026-02-14 18:34:00,789 - solace-browser - INFO - Server running on http://localhost:9222
```

### 2. Call the LinkedIn OAuth API
```bash
curl -X POST http://localhost:9222/api/login-linkedin-google
```

Response:
```json
{
  "success": false,
  "status": "redirect_failed",
  "current_url": "https://www.linkedin.com/login",
  "timestamp": "2026-02-14T18:34:51.256380"
}
```

### 3. Watch the Browser
- A Chromium browser window will open
- You'll see the LinkedIn login page
- Google OAuth UI will appear
- Enter your Gmail email and password

## 📊 Implementation Status

| Feature | Status | Notes |
|---------|--------|-------|
| Navigate to LinkedIn | ✅ | Works perfectly |
| Find Google button | ✅ | Located via CSS selector |
| Trigger OAuth | ⚠️ | Events dispatched, user sees OAuth page |
| Auto-complete Gmail | ❌ | Requires manual input (security) |
| Full login | ⚠️ | Partial - needs manual Gmail login |

## 🔍 How It Works

```
1. Browser starts (headless=False shows window)
2. Navigates to https://www.linkedin.com/login
3. Finds Google button (div.alternate-signin__btn--google)
4. Dispatches click events
5. Google OAuth page appears
6. User enters Gmail credentials (manually)
7. LinkedIn logs in user
```

## 📁 Files & Their Purpose

| File | Purpose | Lines |
|------|---------|-------|
| `solace_browser_server.py` | Main server + OAuth method | 28 KB |
| `test_linkedin_login.sh` | Full test harness | 7 KB |
| `test_linkedin_login_http.py` | HTTP API test | 3.6 KB |
| `debug_linkedin_buttons.py` | Debug button detection | 3.7 KB |
| `debug_linkedin_oauth.py` | Debug OAuth config | 4.5 KB |
| `LINKEDIN_OAUTH_STATUS.md` | Technical docs | 6.5 KB |
| `SESSION_SUMMARY_LINKEDIN_OAUTH.md` | Full session report | 9.1 KB |

## 🧪 Testing

### Run All Tests
```bash
bash test_linkedin_login.sh
```

### Test Individual Components
```bash
# Test button detection
python3 debug_linkedin_buttons.py

# Test OAuth configuration
python3 debug_linkedin_oauth.py

# Test HTTP API
python3 test_linkedin_login_http.py
```

## 📡 API Reference

### POST /api/login-linkedin-google

**Request:**
```bash
curl -X POST http://localhost:9222/api/login-linkedin-google
```

**Response (Success):**
```json
{
  "success": true,
  "status": "awaiting_user_input",
  "message": "Google OAuth page loaded. Please enter your Gmail credentials.",
  "current_url": "https://accounts.google.com/",
  "timestamp": "2026-02-14T18:34:51.256380"
}
```

**Response (Timeout):**
```json
{
  "success": false,
  "status": "redirect_failed",
  "current_url": "https://www.linkedin.com/login",
  "timestamp": "2026-02-14T18:34:51.256380"
}
```

## 🐍 Python Usage

```python
import asyncio
from solace_browser_server import SolaceBrowser

async def test():
    # Create and start browser
    browser = SolaceBrowser(headless=False)
    await browser.start()
    print(f"Browser started")

    # Trigger LinkedIn OAuth login
    result = await browser.login_linkedin_google()
    print(f"Status: {result['status']}")
    print(f"Current URL: {result['current_url']}")

    # User completes login manually in browser window
    # Then verify
    title = await browser.current_page.title()
    print(f"Page title: {title}")

    await browser.stop()

asyncio.run(test())
```

## ⚠️ Important Notes

1. **Security**: Credentials are handled by Google OAuth, not stored locally
2. **Manual Input Required**: Due to Google security, Gmail password must be typed manually
3. **Browser Must Be Visible**: headless=False required to see OAuth dialog
4. **Timeout**: 3-second wait for redirect, then returns control to user
5. **One Tap**: Google One Tap UI may appear instead of standard login

## 🛠️ Troubleshooting

### Problem: "Could not find Google button"
```
Solution: Page may not have loaded. Wait longer or check network.
         Run: python3 debug_linkedin_buttons.py
```

### Problem: "CORS or other error"
```
Solution: This is expected - iframe is cross-origin. Use event dispatch instead.
         Check: artifacts/linkedin-*.png screenshots
```

### Problem: URL didn't change to Google OAuth
```
Solution: Browser may have blocked the automated click.
         Try: Click manually in the browser window or check One Tap notification
```

### Problem: Browser doesn't open
```
Solution: Ensure headless=False and DISPLAY is set on Linux
         Check: export DISPLAY=:1 or :0
```

## 📈 Architecture

```
Solace Browser Server (Port 9222)
├─ GET  /json/version      - Browser version (CDP compatible)
├─ GET  /json/list         - List open pages
├─ POST /api/navigate      - Navigate to URL
├─ POST /api/click         - Click element
├─ POST /api/fill          - Fill form field
├─ POST /api/screenshot    - Take screenshot
├─ POST /api/snapshot      - Get DOM snapshot
├─ POST /api/evaluate      - Run JavaScript
├─ POST /api/login-linkedin-google  ⭐ NEW
├─ GET  /api/status        - Browser status
└─ GET  /api/events        - Event history
```

## 🎯 Next Steps

1. ✅ **Basic OAuth Flow**: Working (this implementation)
2. ⏳ **Email Auto-fill**: Next phase - auto-fill Gmail email
3. ⏳ **Password Handling**: Phase after - secure password entry
4. ⏳ **Multi-account**: Support multiple LinkedIn accounts
5. ⏳ **Proof Generation**: Create verification artifacts

## 📚 Additional Resources

- Full documentation: `LINKEDIN_OAUTH_STATUS.md`
- Session details: `SESSION_SUMMARY_LINKEDIN_OAUTH.md`
- GitHub issues: https://github.com/anthropics/claude-code/issues

## 💡 Key Learnings

- Google Sign-In SDK renders buttons in iframes for security
- CORS prevents direct access to cross-origin iframe contents
- Event dispatching works better than .click() for OAuth buttons
- FedCM (Federated Credential Management) has strict requirements
- Real browser windows are essential for OAuth flows

## ✨ Credits

**Implementation**: Solace Browser Team
**Browser Engine**: Chromium (via Playwright)
**OAuth**: Google Sign-In SDK + LinkedIn OAuth2
**Server**: aiohttp (Python async HTTP)
**Testing**: Bash + Python

---

**Last Updated**: 2026-02-14
**Version**: 1.0.0
**Status**: 🟡 Staging (Manual testing ready)
