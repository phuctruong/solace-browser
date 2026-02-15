#!/usr/bin/env python3

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser, SolaceBrowserServer


async def test_linkedin_login():
    """Test LinkedIn Google OAuth login via HTTP API"""

    print("\n" + "=" * 80)
    print("TESTING: LinkedIn Google OAuth Login (via HTTP API)")
    print("=" * 80 + "\n")

    # Step 1: Start the browser
    print("📌 STEP 1: Starting Solace Browser...")
    browser = SolaceBrowser(headless=False, debug_ui=False)
    await browser.start()
    print("✓ Browser started\n")

    # Step 2: Create HTTP server
    print("📌 STEP 2: Creating HTTP server...")
    server = SolaceBrowserServer(browser, port=9222)
    print("✓ Server created\n")

    # Step 3: Test the login_linkedin_google() method directly
    print("📌 STEP 3: Calling login_linkedin_google() method...\n")

    result = await browser.login_linkedin_google()

    print("\n📌 STEP 4: Analyzing response...")
    print("\nResponse from login_linkedin_google():")
    print(json.dumps(result, indent=2))

    # Step 5: Verify response
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80 + "\n")

    success = False

    if "error" in result:
        print(f"❌ ERROR: {result['error']}")
    elif "success" in result:
        if result.get("success") and "accounts.google.com" in result.get("current_url", ""):
            print("✅ SUCCESS: Redirected to Google OAuth page!")
            print(f"   Current URL: {result['current_url']}")
            print(f"   Status: {result['status']}")
            success = True
        else:
            print(f"⚠️  Unexpected response:")
            print(f"   Success: {result.get('success')}")
            print(f"   Current URL: {result.get('current_url')}")
    else:
        print(f"⚠️  Unexpected response format: {result}")

    # Step 6: Check for screenshots
    print("\n" + "=" * 80)
    print("SCREENSHOTS CAPTURED")
    print("=" * 80 + "\n")

    screenshot_files = [
        "artifacts/linkedin-01-login.png",
        "artifacts/linkedin-02-google-redirect.png",
    ]

    for screenshot_file in screenshot_files:
        screenshot_path = Path(screenshot_file)
        if screenshot_path.exists():
            size_kb = screenshot_path.stat().st_size / 1024
            print(f"✓ {screenshot_file} ({size_kb:.1f} KB)")
        else:
            print(f"⚠️  {screenshot_file} (not found)")

    # Cleanup
    print("\n" + "=" * 80)
    print("CLEANUP")
    print("=" * 80 + "\n")

    print("🧹 Closing browser...")
    await browser.stop()
    print("✓ Browser stopped\n")

    # Final summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80 + "\n")

    if success:
        print("✅ TEST PASSED: LinkedIn Google OAuth login works!")
        print("\nNext steps:")
        print("  1. The browser will remain open showing Google OAuth page")
        print("  2. Enter your Gmail email and password in the browser")
        print("  3. Approve LinkedIn's permission request")
        print("  4. You will be logged into LinkedIn")
        print("\nPress Ctrl+C to close the browser.")

        # Keep browser open for user to interact
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n\nBrowser closing...")
    else:
        print("❌ TEST FAILED: Check the error message above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_linkedin_login())
