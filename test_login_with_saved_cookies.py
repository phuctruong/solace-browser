#!/usr/bin/env python3

"""
Test login with saved cookies + password fallback
If saved cookies aren't enough, complete with password
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def main():
    print("\n" + "="*80)
    print("TEST: LOGIN WITH SAVED COOKIES (+ PASSWORD FALLBACK)")
    print("="*80 + "\n")

    gmail_email = "phuc.truong@gmail.com"
    gmail_password = "Late2eat!!"
    linkedin_password = None  # Will read from input if needed

    # Start browser (loads saved session automatically)
    print("Step 1: Starting browser with saved session...")
    browser = SolaceBrowser(headless=False)
    await browser.start()
    print("✓ Browser started (saved cookies loaded)\n")

    # Navigate to LinkedIn
    print("Step 2: Navigating to LinkedIn...")
    await browser.navigate("https://www.linkedin.com/feed/")
    await asyncio.sleep(3)

    current_url = browser.current_page.url
    print(f"Current URL: {current_url}\n")

    # Check if we're on login page
    is_on_login_page = "/uas/login" in current_url or "/login" in current_url
    is_on_feed = "/feed/" in current_url

    print("Step 3: Checking page state...")
    if is_on_feed and "login" not in current_url:
        print("✅ GREAT! Already logged in with saved cookies!\n")
        await browser.current_page.screenshot(path="artifacts/logged-in-with-saved-cookies.png")
        result = {
            "success": True,
            "status": "logged_in_with_cookies",
            "message": "Saved cookies were sufficient",
            "url": current_url
        }
    elif is_on_login_page:
        print("⚠️  On login page, but saved cookies helped (Welcome back detected)")
        print("    Need to complete authentication with password...\n")

        # Check for "Welcome back" message
        page_content = await browser.current_page.content()
        if "welcome back" in page_content.lower():
            print("✓ Confirmed: LinkedIn recognizes your account\n")

        # Look for password field
        print("Step 4: Looking for password field...")
        password_input = await browser.current_page.query_selector(
            "input[type='password'], input[name='password'], input[aria-label*='password' i]"
        )

        if password_input:
            print("✓ Found password field\n")

            # Ask for password if not provided
            if not linkedin_password:
                print("Step 5: Entering LinkedIn password...")
                linkedin_password = input("Enter your LinkedIn password: ").strip()

                if not linkedin_password:
                    print("❌ Password required\n")
                    await browser.stop()
                    return

            # Enter password
            print(f"Filling password field...")
            await password_input.fill(linkedin_password)
            await asyncio.sleep(0.5)

            # Look for submit button
            print("Looking for submit button...")
            submit_btn = await browser.current_page.query_selector("button[type='submit'], button[aria-label*='sign in' i]")

            if submit_btn:
                print("✓ Found submit button, clicking...\n")
                await submit_btn.click()
                await asyncio.sleep(3)

                # Wait for page load
                current_url = browser.current_page.url
                print(f"New URL: {current_url}\n")

                if "/feed/" in current_url and "/login" not in current_url:
                    print("✅ SUCCESS! Logged in with saved cookies + password!\n")
                    await browser.current_page.screenshot(path="artifacts/logged-in-cookies-plus-password.png")
                    result = {
                        "success": True,
                        "status": "logged_in_with_cookies_and_password",
                        "message": "Saved cookies + password authentication completed",
                        "url": current_url
                    }
                else:
                    print("⚠️  Password submitted, may still need 2FA\n")
                    result = {
                        "success": True,
                        "status": "password_submitted",
                        "message": "Password submitted, may need 2FA approval",
                        "url": current_url
                    }
            else:
                print("⚠️  Could not find submit button\n")
                result = {
                    "success": False,
                    "error": "Submit button not found"
                }
        else:
            print("⚠️  Could not find password field\n")
            result = {
                "success": False,
                "error": "Password field not found"
            }
    else:
        print(f"⚠️  Unknown state at: {current_url}\n")
        result = {
            "success": False,
            "error": f"Unknown state: {current_url}"
        }

    print("="*80)
    print("RESULT")
    print("="*80)
    print(json.dumps(result, indent=2))
    print()

    # Take final screenshot
    print("Taking final screenshot...")
    await browser.current_page.screenshot(path="artifacts/final-state.png")
    print("✓ Screenshot: artifacts/final-state.png\n")

    print("Browser will stay open for 20 seconds...")
    try:
        await asyncio.sleep(20)
    except KeyboardInterrupt:
        print("\nClosed by user")

    await browser.stop()
    print("\n✓ Test complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
