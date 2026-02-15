#!/usr/bin/env python3

"""
Test loading a saved LinkedIn session (cookies, localStorage, etc.)
This should load your existing artifacts/linkedin_session.json file
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_load_session():
    """Load saved session and verify logged-in state"""

    print("\n" + "="*80)
    print("TEST LOAD SAVED SESSION")
    print("="*80 + "\n")

    session_file = "artifacts/linkedin_session.json"

    # Check if session file exists
    if not Path(session_file).exists():
        print(f"❌ Session file not found: {session_file}\n")
        return

    print(f"✓ Found session file: {session_file}")
    print(f"  Size: {Path(session_file).stat().st_size:,} bytes\n")

    # Start browser with saved session
    print("Step 1: Starting browser with SAVED SESSION...")
    browser = SolaceBrowser(headless=False, session_file=session_file)
    await browser.start()
    print("✓ Browser started (session automatically loaded)\n")

    # Navigate to LinkedIn feed
    print("Step 2: Navigating to LinkedIn feed...")
    result = await browser.navigate("https://www.linkedin.com/feed/")
    await asyncio.sleep(3)

    current_url = browser.current_page.url
    print(f"Current URL: {current_url}\n")

    # Take screenshot
    print("Step 3: Taking screenshot...")
    await browser.current_page.screenshot(path="artifacts/test-loaded-session.png")
    print("✓ Screenshot saved: artifacts/test-loaded-session.png\n")

    # Check page content
    print("Step 4: Checking if logged in...")
    page_content = await browser.current_page.content()

    # Check for logged-in indicators
    logged_in_indicators = [
        "Add a comment",  # Feed interaction
        "/feed",          # In URL
        "Home",           # Navigation
        "Your recent searches",  # Feed feature
        "My network",     # Feed feature
    ]

    is_logged_in = any(indicator in page_content for indicator in logged_in_indicators) and "login" not in current_url

    print(f"URL contains /feed: {'linkedin.com/feed' in current_url}")
    print(f"Not at login page: {'login' not in current_url}")
    print(f"Found logged-in indicators: {is_logged_in}\n")

    if is_logged_in or "linkedin.com/feed" in current_url:
        print("="*80)
        print("✅ SUCCESS! LOADED SESSION WORKS!")
        print("="*80)
        print(f"\n✓ You are LOGGED IN using the saved cookies!")
        print(f"✓ No Google OAuth needed!")
        print(f"✓ URL: {current_url}\n")
    else:
        print("="*80)
        print("⚠️  UNCERTAIN STATUS")
        print("="*80)
        print(f"\n⚠️  Could not confirm logged-in status")
        print(f"✓ But session WAS loaded from file")
        print(f"✓ URL: {current_url}\n")
        print("Check the screenshot: artifacts/test-loaded-session.png\n")

    # Keep open for user to verify
    print("Keeping browser open for 20 seconds for manual verification...")
    print("Check if you can see:")
    print("  • Your feed")
    print("  • Your profile info")
    print("  • Any logged-in features\n")

    await asyncio.sleep(20)

    print("Step 5: Closing browser (session will be saved again)...")
    await browser.stop()
    print("✓ Done!\n")


if __name__ == "__main__":
    asyncio.run(test_load_session())
