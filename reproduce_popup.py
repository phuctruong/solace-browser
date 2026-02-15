#!/usr/bin/env python3

"""
Reproduce the popup from before
Run the exact same code that triggered it
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def main():
    print("\n" + "=" * 80)
    print("REPRODUCING GOOGLE OAUTH POPUP")
    print("=" * 80 + "\n")

    print("Starting browser...\n")
    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("Calling login_linkedin_google()...\n")
    result = await browser.login_linkedin_google()

    print("Result:")
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 80)
    print("Did you see the Google popup?")
    print("=" * 80 + "\n")

    if result.get('popup_opened') or 'popup' in result.get('status', '').lower():
        print("✅ Popup detected by code!")
    else:
        print("⚠️  Code didn't detect popup")
        print("     But you might still see one - check all windows!\n")

    print("Keeping browser open for 60 seconds...")
    print("(You can interact with the popup if you see it)\n")
    print("Press Ctrl+C to close early\n")

    try:
        for i in range(60):
            await asyncio.sleep(1)
            if i % 10 == 0 and i > 0:
                current_url = browser.current_page.url
                print(f"{i}s: Main page at {current_url}")
    except KeyboardInterrupt:
        print("\n✓ Closed by user")

    await browser.stop()
    print("\n✓ Done\n")


if __name__ == "__main__":
    asyncio.run(main())
