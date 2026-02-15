#!/usr/bin/env python3

"""
Test LinkedIn full flow: Google OAuth login + Profile update
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_full_flow():
    """Test complete LinkedIn flow: login + profile update"""

    print("\n" + "="*80)
    print("LINKEDIN FULL FLOW TEST: Login + Profile Update")
    print("="*80 + "\n")

    # Gmail credentials (using default from credentials.properties)
    gmail_email = "phuc.truong@gmail.com"
    gmail_password = "Late2eat!!"

    print(f"Step 1: Starting browser (headless=False)...")
    browser = SolaceBrowser(headless=False)
    await browser.start()
    print("✓ Browser started\n")

    # Step 2: Auto-login
    print("Step 2: Auto-login to LinkedIn via Google OAuth...")
    print(f"  Email: {gmail_email}")
    print(f"  Password: {'*' * len(gmail_password)}")
    print("\n  If you see a Google OAuth popup, enter your credentials when prompted.")
    print("  If you see a recovery page, I'll try to skip it automatically.\n")

    login_result = await browser.login_linkedin_google_auto(gmail_email, gmail_password)

    print("\nLogin Result:")
    print(json.dumps(login_result, indent=2))

    if not login_result.get('success'):
        print(f"\n❌ Login failed: {login_result.get('error', 'Unknown error')}")
        await browser.stop()
        return

    print("\n✓ Login successful!")

    # Step 3: Wait a bit for page to fully load
    print("\nStep 3: Waiting for page to fully load...")
    await asyncio.sleep(3)

    # Step 4: Update profile
    print("\nStep 4: Updating LinkedIn profile...")
    profile_result = await browser.update_linkedin_profile()

    print("\nProfile Update Result:")
    print(json.dumps(profile_result, indent=2))

    if profile_result.get('success'):
        print("\n✓ PROFILE UPDATE SUCCESSFUL!")
    else:
        print(f"\n⚠️  Profile update had issues: {profile_result.get('error', 'Unknown error')}")

    # Step 5: Keep browser open for verification
    print("\n" + "="*80)
    print("Browser will stay open for 30 seconds for verification")
    print("Check the LinkedIn profile to see if changes were applied!")
    print("="*80 + "\n")

    try:
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\nClosed by user")

    await browser.stop()
    print("\n✓ Done\n")


if __name__ == "__main__":
    asyncio.run(test_full_flow())
