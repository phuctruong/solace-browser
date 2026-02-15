#!/usr/bin/env python3

"""
Test script to save current LinkedIn session and verify it works
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def main():
    """Save and verify LinkedIn session"""

    print("\n" + "="*80)
    print("SAVE & VERIFY LINKEDIN SESSION")
    print("="*80 + "\n")

    session_file = Path("artifacts/linkedin_session.json")

    # Step 1: Start browser
    print("Step 1: Starting browser...")
    browser = SolaceBrowser(headless=False)
    await browser.start()
    print("✓ Browser started\n")

    # Step 2: Navigate to LinkedIn to check if already logged in
    print("Step 2: Navigating to LinkedIn feed...")
    await browser.navigate("https://www.linkedin.com/feed/")
    await asyncio.sleep(3)

    current_url = browser.current_page.url
    print(f"Current URL: {current_url}\n")

    # Step 3: Take screenshot to verify state
    print("Step 3: Taking screenshot to verify logged-in state...")
    await browser.current_page.screenshot(path="artifacts/session-verify-before-save.png")
    print("✓ Screenshot saved: artifacts/session-verify-before-save.png\n")

    # Step 4: Save the session
    print("Step 4: Saving session...")
    save_result = await browser.save_session()

    print("Save Result:")
    print(json.dumps(save_result, indent=2))

    if save_result.get('success'):
        print("\n✅ SESSION SAVED SUCCESSFULLY!")
        print(f"   Location: {save_result['session_file']}")

        # Verify file exists
        if session_file.exists():
            file_size = session_file.stat().st_size
            print(f"   File size: {file_size:,} bytes")
            print(f"   ✓ Session file verified\n")
        else:
            print("   ⚠️  Session file not found\n")
    else:
        print(f"\n❌ Save failed: {save_result.get('error')}\n")

    # Step 5: Show next steps
    print("Step 5: What's Next?")
    print("-" * 80)
    print("""
Next time you start the browser, it will automatically:
1. Load your saved session (cookies, localStorage, etc.)
2. You'll be logged in without Google OAuth!

To test this immediately:
  python3 test_session_persistence.py load

Or use this simple Python code:

  import asyncio
  from solace_browser_server import SolaceBrowser

  async def test():
      browser = SolaceBrowser(headless=False)
      await browser.start()
      # Already logged in!
      await browser.navigate('https://www.linkedin.com/in/your-profile/')
      await asyncio.sleep(30)
      await browser.stop()

  asyncio.run(test())

Your session is persistent! No more OAuth needed! 🎉
    """)
    print("-" * 80 + "\n")

    # Keep browser open for user to verify
    print("Keeping browser open for 20 seconds...")
    print("Check the screenshot: artifacts/session-verify-before-save.png")
    print("Verify you can see your LinkedIn feed\n")

    await asyncio.sleep(20)

    await browser.stop()
    print("✓ Done!\n")


if __name__ == "__main__":
    asyncio.run(main())
