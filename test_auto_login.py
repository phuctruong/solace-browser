#!/usr/bin/env python3

"""
Test auto-login to LinkedIn via Google OAuth
Automatically fills Gmail credentials and completes login
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_auto_login():
    """Test auto-login with Gmail credentials"""

    print("\n" + "=" * 80)
    print("LINKEDIN AUTO-LOGIN TEST (via Google OAuth)")
    print("=" * 80 + "\n")

    # Gmail credentials (using default from credentials.properties)
    gmail_email = "phuc.truong@gmail.com"
    gmail_password = input("Enter your Gmail password: ").strip()

    if not gmail_password:
        print("❌ Password required")
        return

    print(f"\nLogging in with: {gmail_email}\n")

    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("Calling auto-login...")
    result = await browser.login_linkedin_google_auto(gmail_email, gmail_password)

    print("\nLogin Result:")
    print(json.dumps(result, indent=2))

    if result.get('success'):
        print("\n✅ LOGIN SUCCESSFUL!")

        # Save the session so you stay logged in next time
        print("\nSaving session...")
        save_result = await browser.save_session()
        if save_result.get('success'):
            print("✓ Session saved! You'll be logged in next time automatically")
            print(f"  Session file: {save_result['session_file']}")
        else:
            print(f"⚠️  Could not save session: {save_result.get('error')}")
    else:
        print(f"\n❌ Login failed: {result.get('error')}")

    print("\nKeeping browser open (30 seconds)...")
    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("Closed by user")

    await browser.stop()
    print("\n✓ Done\n")


if __name__ == "__main__":
    asyncio.run(test_auto_login())
