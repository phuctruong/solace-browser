#!/usr/bin/env python3
"""
Start Solace Browser in VISUAL mode (not headless)
Shows actual browser window with rendering
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser, SolaceBrowserServer

async def main():
    print("=" * 70)
    print("SOLACE BROWSER - VISUAL MODE")
    print("=" * 70)
    print("")
    print("Starting real Chromium browser window...")
    print("You should see a browser window open on your desktop")
    print("")

    # Create browser in VISUAL mode (not headless)
    browser = SolaceBrowser(headless=False, debug_ui=False)

    try:
        page_id = await browser.start()
        print(f"✓ Browser started (page_id={page_id})")
        print("")

        # Create and start server
        server = SolaceBrowserServer(browser, port=9222)
        print("✓ Server started on http://localhost:9222")
        print("")

        print("Navigate with:")
        print("  bash solace-browser-cli-v3.sh navigate demo 'https://example.com'")
        print("")

        # Navigate to example.com to show something
        print("Loading example.com...")
        result = await browser.navigate("https://example.com")
        print(f"✓ {result}")
        print("")

        # Keep browser open
        print("Browser is running. Press Ctrl+C to stop.")
        print("")
        await asyncio.Event().wait()

    except KeyboardInterrupt:
        print("\nShutting down...")
        await browser.stop()
        print("✓ Browser closed")

if __name__ == '__main__':
    asyncio.run(main())
