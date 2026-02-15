#!/usr/bin/env python3

"""
Test session persistence: Save and restore LinkedIn login
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_save_session():
    """Save the current browser session (cookies, localStorage)"""

    print("\n" + "="*80)
    print("SAVE SESSION - Persist LinkedIn Login")
    print("="*80 + "\n")

    print("Step 1: Starting browser...")
    browser = SolaceBrowser(headless=False)
    await browser.start()
    print("✓ Browser started\n")

    # Just navigate to LinkedIn to show current state
    print("Step 2: Navigating to LinkedIn...")
    await browser.navigate("https://www.linkedin.com/feed/")
    await asyncio.sleep(2)

    # Save the session
    print("\nStep 3: Saving session...")
    save_result = await browser.save_session()
    print(json.dumps(save_result, indent=2))

    if save_result.get('success'):
        print("\n✓ SESSION SAVED!")
        print(f"  Location: {save_result['session_file']}")
        print("  This file contains: cookies, localStorage, etc.")
        print("\n  Next time you start the browser, it will automatically")
        print("  load this session and you'll be logged in!")
    else:
        print(f"\n❌ Save failed: {save_result.get('error')}")

    # Keep browser open briefly
    print("\nKeeping browser open for 5 seconds...")
    await asyncio.sleep(5)

    await browser.stop()
    print("\n✓ Done\n")


async def test_load_session():
    """Load a previously saved session"""

    print("\n" + "="*80)
    print("LOAD SESSION - Resume LinkedIn Login")
    print("="*80 + "\n")

    session_file = "artifacts/linkedin_session.json"

    if not Path(session_file).exists():
        print(f"❌ No saved session found at: {session_file}")
        print("   Please run test_save_session.py first\n")
        return

    print(f"✓ Found saved session at: {session_file}\n")

    print("Step 1: Starting browser (will load saved session)...")
    browser = SolaceBrowser(headless=False, session_file=session_file)
    await browser.start()
    print("✓ Browser started with saved session\n")

    # Navigate to LinkedIn
    print("Step 2: Navigating to LinkedIn feed...")
    await browser.navigate("https://www.linkedin.com/feed/")
    await asyncio.sleep(3)

    current_url = browser.current_page.url
    print(f"Current URL: {current_url}")

    if "linkedin.com/feed" in current_url:
        print("\n✓ YOU'RE STILL LOGGED IN!")
        print("  The saved session (cookies) were automatically restored")
    else:
        print("\n⚠️  Not yet on feed page, but session was loaded")

    # Keep browser open for verification
    print("\nKeeping browser open for 10 seconds...")
    print("Check if you're logged in and can see your feed!\n")

    await asyncio.sleep(10)

    await browser.stop()
    print("\n✓ Done\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "save":
            asyncio.run(test_save_session())
        elif sys.argv[1] == "load":
            asyncio.run(test_load_session())
        else:
            print("Usage: python3 test_session_persistence.py [save|load]")
    else:
        print("""
Session Persistence Test

Usage:
  python3 test_session_persistence.py save
    -> Save current LinkedIn login to file

  python3 test_session_persistence.py load
    -> Load saved session and resume logged-in state

To use:
  1. First run: python3 test_session_persistence.py save
  2. Close the browser
  3. Then run: python3 test_session_persistence.py load
  4. You should still be logged in!
        """)
