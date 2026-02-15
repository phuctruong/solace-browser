# Testing the Saved Session (Cookies)

## Summary

Your LinkedIn cookies have been saved to: `artifacts/linkedin_session.json`

The file contains:
- ✅ JSESSIONID - Main session cookie
- ✅ bcookie - Browser cookie
- ✅ bscookie - Browser security cookie
- ✅ li_rm - LinkedIn auth token
- ✅ lidc - LinkedIn data center routing
- ✅ Plus 20+ other authentication cookies and localStorage data

## Test 1: Quick Session Load Test

Run this to verify the saved session works:

```bash
python3 quick_test_session.py
```

**What it does:**
1. Loads the saved session file
2. Shows which cookies are present
3. Starts a browser with those cookies
4. Navigates to LinkedIn feed
5. Checks if you're logged in
6. Takes a screenshot

**Expected output:**
```
✓ Session file found: artifacts/linkedin_session.json
✓ Contains 28 cookies

  ✓ JSESSIONID: Present
  ✓ bcookie: Present
  ✓ bscookie: Present
  ✓ li_rm: Present

Starting browser with saved session...
✓ Browser started

Navigating to LinkedIn...
Current URL: https://www.linkedin.com/feed/

Checking logged-in status...
✓ Found profile avatar (you are logged in!)

Taking screenshot...
✓ Screenshot: artifacts/quick-test-screenshot.png

================================================================================
✅ SUCCESS! SAVED SESSION WORKS!
================================================================================
```

## Test 2: Full Session Persistence Test

This tests the complete cycle (login → save → reload):

```bash
python3 test_full_session_flow.py
```

**What it does:**
1. Starts a fresh browser
2. Auto-logs in via Google OAuth
3. Saves the session
4. Closes the browser
5. **Starts a NEW browser with the saved session**
6. Navigates to LinkedIn
7. Verifies you're still logged in

**Expected result:** You're logged in without needing to go through Google OAuth again!

## How It Works Under The Hood

### Session File Contents
```json
{
  "cookies": [
    {"name": "JSESSIONID", "value": "ajax:..."},
    {"name": "bcookie", "value": "v=2&..."},
    ...
  ],
  "origins": [...]
}
```

### When Browser Starts
1. Playwright reads the session file
2. Restores all cookies to the browser
3. Browser now has the authenticated state
4. No need to login again!

### Why It Works
- LinkedIn uses **cookie-based sessions**
- Your authentication is stored in cookies
- When you close/reopen the browser, cookies are gone (normally)
- But we **saved the cookies to a file**
- On restart, we **restore those cookies**
- So you're instantly logged in!

## Security Notes

✅ **Safe to use locally**
- Session file is stored on your machine only
- Not shared anywhere

⚠️ **Keep it private**
- Don't commit to git (it's in .gitignore)
- Don't share with others
- Contains authentication tokens

⚠️ **Sessions expire**
- LinkedIn sessions expire after 14-30 days
- Cookies might be invalidated
- If that happens, just login again

## Troubleshooting

### "Session file not found"
```bash
# Check if file exists
ls -lh artifacts/linkedin_session.json

# If not, run the full flow first
python3 test_full_session_flow.py
```

### "Still need to login"
- Session might have expired
- Try running the full test: `python3 test_full_session_flow.py`
- Or just delete old session: `rm artifacts/linkedin_session.json && python3 test_full_session_flow.py`

### "Browser won't start"
- Make sure Playwright is installed: `pip install playwright`
- Make sure Chromium is installed: `playwright install`

## Next Steps

1. **Test it now:**
   ```bash
   python3 quick_test_session.py
   ```

2. **Or run full test:**
   ```bash
   python3 test_full_session_flow.py
   ```

3. **Check the screenshot:**
   - `artifacts/quick-test-screenshot.png` (if using quick test)
   - `artifacts/phase2-reloaded-with-session.png` (if using full test)

4. **Use in your own code:**
   ```python
   import asyncio
   from solace_browser_server import SolaceBrowser

   async def main():
       # Loads saved session automatically!
       browser = SolaceBrowser(headless=False)
       await browser.start()

       # You're logged in!
       await browser.navigate("https://www.linkedin.com/feed/")

       # Do stuff...

       await browser.stop()

   asyncio.run(main())
   ```

That's it! Session persistence is ready to use. 🚀
