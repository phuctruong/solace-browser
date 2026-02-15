#!/usr/bin/env python3

"""
Compare Apple OAuth vs Google OAuth
If Apple works, why doesn't Google?
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_apple_oauth():
    """Test Sign in with Apple"""

    print("\n" + "=" * 80)
    print("TESTING: Sign in with Apple (should work)")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("Navigate to LinkedIn login...")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)

    print("Find Apple button...")
    apple_button = await browser.current_page.query_selector("button:has-text('Sign in with Apple')")

    if apple_button:
        print("✓ Apple button found\n")
        print("Clicking Apple button...")

        await apple_button.click()
        print("✓ Clicked\n")

        await asyncio.sleep(3)

        url = browser.current_page.url
        print(f"URL after click: {url}")

        if "apple" in url.lower() or "appleid" in url.lower():
            print("✅ APPLE OAUTH WORKS - Redirected to Apple OAuth!")
        else:
            print("⚠️  Apple button was clicked but no OAuth redirect")

        await browser.current_page.screenshot(path="artifacts/apple-oauth-test.png")
    else:
        print("✗ Apple button not found")

    await browser.stop()


async def test_google_oauth_improved():
    """Test Google OAuth with better wait and monitoring"""

    print("\n" + "=" * 80)
    print("TESTING: Sign in with Google (improved version)")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("Navigate to LinkedIn login...")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)

    print("Find Google button container...")
    google_container = await browser.current_page.query_selector("div.alternate-signin__btn--google")

    if google_container:
        print("✓ Google button container found\n")

        # Try to click like we click Apple
        print("Method 1: Direct click on container (like Apple)...")
        try:
            await google_container.click()
            print("✓ Clicked\n")
        except Exception as e:
            print(f"✗ Click failed: {e}\n")

        # Wait much longer for redirect
        print("Waiting for OAuth redirect (10 seconds)...")
        for i in range(10):
            await asyncio.sleep(1)
            current_url = browser.current_page.url
            print(f"  {i+1}s: {current_url}")

            if "google" in current_url.lower() or "oauth" in current_url.lower():
                print(f"\n✅ GOOGLE OAUTH WORKS - Redirected to: {current_url}")
                break
        else:
            print(f"\n⚠️  No redirect after 10 seconds. Current URL: {current_url}")

        await browser.current_page.screenshot(path="artifacts/google-oauth-improved.png")
    else:
        print("✗ Google button container not found")

    await browser.stop()


async def test_google_via_iframe():
    """Test clicking the Google button via iframe"""

    print("\n" + "=" * 80)
    print("TESTING: Google OAuth via iframe button")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("Navigate to LinkedIn login...")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)

    print("Find Google iframe...")
    google_iframe = await browser.current_page.query_selector("iframe[title='Sign in with Google Button']")

    if google_iframe:
        print("✓ Google iframe found\n")

        print("Method 1: Click on iframe element...")
        try:
            await google_iframe.click()
            print("✓ Clicked iframe\n")

            print("Waiting for OAuth redirect (10 seconds)...")
            for i in range(10):
                await asyncio.sleep(1)
                current_url = browser.current_page.url
                print(f"  {i+1}s: {current_url}")

                if "google" in current_url.lower() or "oauth" in current_url.lower():
                    print(f"\n✅ GOOGLE OAUTH WORKS via iframe click!")
                    break
            else:
                print(f"\n⚠️  No redirect. Current URL: {current_url}")
        except Exception as e:
            print(f"✗ Click failed: {e}\n")

        await browser.current_page.screenshot(path="artifacts/google-oauth-iframe.png")
    else:
        print("✗ Google iframe not found")

    await browser.stop()


async def main():
    print("=" * 80)
    print("APPLE vs GOOGLE OAUTH COMPARISON")
    print("=" * 80)

    # Test Apple first to see if it actually works
    await test_apple_oauth()

    # Test Google with improved waiting
    await test_google_oauth_improved()

    # Test Google via iframe
    await test_google_via_iframe()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
If Apple OAuth worked but Google didn't, possible reasons:
1. Apple uses different OAuth flow (might be simpler)
2. Google OAuth takes longer to redirect
3. Google has additional security checks
4. The iframe vs container click matters
5. We need to wait longer and monitor URL changes
""")


if __name__ == "__main__":
    asyncio.run(main())
