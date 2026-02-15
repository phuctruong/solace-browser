#!/usr/bin/env python3
"""
SOLACE BROWSER - VISUAL MODE (Real Window)
Shows actual Chromium browser on screen
"""

import asyncio
import sys
import os
from pathlib import Path

# Ensure DISPLAY is set for X11
if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':1'

print("=" * 80)
print("SOLACE BROWSER - VISUAL MODE (Real Chromium Window)")
print("=" * 80)
print(f"Display: {os.environ.get('DISPLAY')}")
print("")

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed")
    sys.exit(1)


async def main():
    print("Starting Chromium browser window...")
    print("A browser window should appear on your desktop")
    print("")

    playwright = await async_playwright().start()

    try:
        # Launch browser in VISUAL mode (not headless)
        browser = await playwright.chromium.launch(
            headless=False,  # Show window!
            args=[
                '--disable-blink-features=AutomationControlled',
            ]
        )

        print("✓ Chromium started")
        print("")

        # Create a page
        context = await browser.new_context()
        page = await context.new_page()

        print("Opening pages in sequence...")
        print("")

        # Navigate to Example.com
        print("1️⃣  Loading: https://example.com")
        await page.goto("https://example.com", wait_until='domcontentloaded')
        await page.screenshot(path="artifacts/visual-example.png")
        title1 = await page.title()
        print(f"   ✓ Loaded: {title1}")
        await asyncio.sleep(3)

        # Navigate to Wikipedia
        print("")
        print("2️⃣  Loading: https://en.wikipedia.org/wiki/Browser")
        await page.goto("https://en.wikipedia.org/wiki/Browser", wait_until='domcontentloaded')
        await page.screenshot(path="artifacts/visual-wikipedia.png")
        title2 = await page.title()
        print(f"   ✓ Loaded: {title2}")
        await asyncio.sleep(3)

        # Navigate to GitHub
        print("")
        print("3️⃣  Loading: https://github.com")
        await page.goto("https://github.com", wait_until='domcontentloaded')
        await page.screenshot(path="artifacts/visual-github.png")
        title3 = await page.title()
        print(f"   ✓ Loaded: {title3}")
        await asyncio.sleep(3)

        # Navigate to Python.org
        print("")
        print("4️⃣  Loading: https://python.org")
        await page.goto("https://python.org", wait_until='domcontentloaded')
        await page.screenshot(path="artifacts/visual-python.png")
        title4 = await page.title()
        print(f"   ✓ Loaded: {title4}")
        await asyncio.sleep(3)

        print("")
        print("=" * 80)
        print("✅ BROWSER DEMONSTRATION COMPLETE")
        print("=" * 80)
        print("")
        print("You should have seen 4 different websites load in the browser window:")
        print("  1. Example.com (simple page)")
        print("  2. Wikipedia (complex page with content)")
        print("  3. GitHub (dynamic site)")
        print("  4. Python.org (web application)")
        print("")
        print("Screenshots saved to artifacts/:")
        print("  - visual-example.png")
        print("  - visual-wikipedia.png")
        print("  - visual-github.png")
        print("  - visual-python.png")
        print("")
        print("Press Ctrl+C to close browser window...")

        # Keep window open until Ctrl+C
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass

        await browser.close()
        print("")
        print("✓ Browser closed")

    finally:
        await playwright.stop()


if __name__ == '__main__':
    asyncio.run(main())
