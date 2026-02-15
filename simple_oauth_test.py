#!/usr/bin/env python3

"""
Simple test to trigger LinkedIn Google OAuth
Watch for popup window to appear
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def main():
    print("\n" + "=" * 80)
    print("LINKEDIN GOOGLE OAUTH - SIMPLE TEST")
    print("=" * 80 + "\n")

    print("Starting browser (headless=False so you can see it)...\n")
    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("✓ Browser started\n")
    print("Navigating to LinkedIn login...\n")

    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)

    print("✓ LinkedIn login page loaded\n")
    print("=" * 80)
    print("NOW LOOK AT THE BROWSER WINDOW!")
    print("=" * 80 + "\n")

    print("Finding Google button...")
    container = await browser.current_page.query_selector("div.alternate-signin__btn--google")

    if container:
        print("✓ Google button found\n")

        print("CLICKING GOOGLE BUTTON...")
        print("(Watch for a Google OAuth popup window)\n")

        # Try simple click
        try:
            await container.click()
            print("✓ Click command sent\n")
        except Exception as e:
            print(f"✗ Click failed: {e}\n")

        print("Waiting 5 seconds for popup to appear...\n")

        for i in range(5):
            await asyncio.sleep(1)
            print(f"  {i+1}s...")

        print("\n" + "=" * 80)
        print("Did you see a Google popup window?")
        print("=" * 80 + "\n")

        url = browser.current_page.url
        print(f"Main page URL: {url}\n")

        if "google" in url.lower():
            print("✅ Page shows Google - OAuth worked!")
        else:
            print("⚠️  Main page still at LinkedIn")
            print("   Check if a popup window appeared (might be behind main window)\n")

        print("Keeping browser open for 30 seconds...")
        print("(You can interact with popup if it appeared)\n")

        try:
            for i in range(30):
                await asyncio.sleep(1)
                if i % 10 == 0 and i > 0:
                    print(f"  {i}s elapsed...")
        except KeyboardInterrupt:
            print("\nClosed by user")

    else:
        print("✗ Google button not found")

    await browser.stop()
    print("\n✓ Browser closed\n")


if __name__ == "__main__":
    asyncio.run(main())
