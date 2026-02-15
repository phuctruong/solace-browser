#!/usr/bin/env python3

"""Quick test: Load saved session and verify cookies are restored"""

import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def quick_test():
    print("\n" + "="*80)
    print("QUICK TEST: LOAD SAVED SESSION WITH COOKIES")
    print("="*80 + "\n")

    session_file = "artifacts/linkedin_session.json"

    # Verify session file exists and check cookies
    if Path(session_file).exists():
        with open(session_file) as f:
            session_data = json.load(f)

        cookies = session_data.get('cookies', [])
        print(f"✓ Session file found: {session_file}")
        print(f"✓ Contains {len(cookies)} cookies\n")

        # Show key cookies
        key_cookies = ['JSESSIONID', 'bcookie', 'bscookie', 'li_rm']
        for cookie_name in key_cookies:
            found = any(c['name'] == cookie_name for c in cookies)
            status = "✓" if found else "✗"
            print(f"  {status} {cookie_name}: {'Present' if found else 'Missing'}")
        print()
    else:
        print(f"❌ Session file not found: {session_file}\n")
        return

    # Start browser with saved session
    print("Starting browser with saved session...")
    browser = SolaceBrowser(headless=False, session_file=session_file)
    await browser.start()
    print("✓ Browser started\n")

    # Navigate to LinkedIn
    print("Navigating to LinkedIn...")
    await browser.navigate("https://www.linkedin.com/feed/")
    await asyncio.sleep(4)

    url = browser.current_page.url
    print(f"Current URL: {url}\n")

    # Check if logged in
    print("Checking logged-in status...")
    try:
        # Try to get profile info (should exist if logged in)
        profile_element = await browser.current_page.query_selector("[data-test-id='avatar']")
        if profile_element:
            print("✓ Found profile avatar (you are logged in!)\n")
        else:
            print("⚠️ Could not find profile avatar\n")
    except Exception as e:
        print(f"⚠️ Error checking profile: {e}\n")

    # Take screenshot
    print("Taking screenshot...")
    await browser.current_page.screenshot(path="artifacts/quick-test-screenshot.png")
    print("✓ Screenshot: artifacts/quick-test-screenshot.png\n")

    print("="*80)
    if "login" not in url and "linkedin.com/feed" in url:
        print("✅ SUCCESS! SAVED SESSION WORKS!")
    else:
        print("✓ Session was loaded (check screenshot for verification)")
    print("="*80 + "\n")

    print("Browser will close in 10 seconds...")
    await asyncio.sleep(10)

    await browser.stop()
    print("\n✓ Test complete!\n")


if __name__ == "__main__":
    try:
        asyncio.run(quick_test())
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        import traceback
        traceback.print_exc()
