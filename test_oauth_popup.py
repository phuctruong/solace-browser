#!/usr/bin/env python3

"""
Test Google OAuth popup detection and monitoring
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_oauth_popup():
    """Test OAuth popup detection"""

    print("\n" + "=" * 80)
    print("GOOGLE OAUTH POPUP TEST")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("Step 1: Navigate to LinkedIn login\n")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)

    print("Step 2: Trigger Google OAuth login\n")
    result = await browser.login_linkedin_google()

    print(f"Login Result:")
    print(json.dumps(result, indent=2))

    print(f"\n✓ Status: {result.get('status')}")
    print(f"✓ Message: {result.get('message')}")

    if result.get('popup_opened'):
        print(f"\n🎉 POPUP DETECTED!")
        print(f"   URL: {result.get('current_url')}")
        print(f"\n   👉 You can now enter your Gmail credentials in the popup window")
        print(f"   👉 The OAuth flow will continue automatically")

        # Wait for user to complete login
        print(f"\nWaiting for you to complete Gmail login (max 5 minutes)...")
        print(f"Press Ctrl+C when done, or wait for automatic redirect\n")

        try:
            # Keep browser open
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n✓ User completed login")

    else:
        print(f"\n⚠️  No popup detected")
        print(f"   Check if a popup window appeared on your screen")
        print(f"   If you see it, please complete the Gmail login")

    # Check final state
    print("\nFinal page info:")
    final_url = browser.current_page.url
    print(f"  Main page URL: {final_url}")

    await browser.stop()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_oauth_popup())
