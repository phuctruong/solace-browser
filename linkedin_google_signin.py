#!/usr/bin/env python3

"""
LINKEDIN LOGIN VIA GOOGLE OAUTH BUTTON
Clicks the "Sign in with Google" button and uses Gmail OAuth flow
"""

import asyncio
import os
import sys

# Set display
if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':1'

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed")
    sys.exit(1)


async def linkedin_google_oauth():
    """Login to LinkedIn using the "Sign in with Google" button"""

    print("=" * 80)
    print("LINKEDIN - GOOGLE OAUTH BUTTON FLOW")
    print("=" * 80)
    print("")
    print("This will:")
    print("  1. Navigate to LinkedIn login page")
    print("  2. Click the 'Sign in with Google' button")
    print("  3. Redirect to Google OAuth")
    print("  4. You will enter your Gmail credentials")
    print("")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # Step 1: Navigate to LinkedIn login
        print("STEP 1: Opening LinkedIn login page...")
        await page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
        await asyncio.sleep(2)

        print("✓ Loaded LinkedIn login page")
        await page.screenshot(path="artifacts/01-linkedin-login-page.png")

        # Step 2: Find and click "Sign in with Google" button
        print("")
        print("STEP 2: Looking for 'Sign in with Google' button...")

        # Wait for page elements to load
        await page.wait_for_load_state('networkidle')

        # Look for the Google sign-in button
        # LinkedIn typically has this with various possible selectors
        google_button = None

        # Try different possible selectors for Google button
        selectors = [
            "button:has-text('Google')",
            "a:has-text('Google')",
            "[aria-label*='Google']",
            "button[data-test-signin-google-button]",
            ".artdeco-button:has-text('Google')",
        ]

        print("Searching for Google sign-in button...")

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    google_button = element
                    print(f"✓ Found button with selector: {selector}")
                    break
            except:
                pass

        if not google_button:
            # Manual search through all buttons
            buttons = await page.query_selector_all("button")
            for btn in buttons:
                text = await btn.text_content()
                if text and 'google' in text.lower():
                    google_button = btn
                    print(f"✓ Found button with text: {text.strip()}")
                    break

        if not google_button:
            print("❌ Could not find 'Sign in with Google' button")
            print("")
            print("Available buttons on page:")
            buttons = await page.query_selector_all("button")
            for i, btn in enumerate(buttons[:10]):  # Show first 10
                text = await btn.text_content()
                print(f"  {i+1}. {text.strip() if text else '(empty)'}")

            await page.screenshot(path="artifacts/01-linkedin-buttons.png")
            return False

        # Step 3: Click the Google button
        print("")
        print("STEP 3: Clicking 'Sign in with Google' button...")
        await google_button.click()
        print("✓ Clicked button")

        await asyncio.sleep(3)
        await page.screenshot(path="artifacts/02-google-redirect.png")

        # Step 4: Google OAuth page should appear
        print("")
        print("STEP 4: Google OAuth page loading...")
        print(f"Current URL: {page.url}")

        # Wait for Google page to load
        await page.wait_for_load_state('domcontentloaded')
        await asyncio.sleep(2)

        print("")
        print("=" * 80)
        print("✅ READY FOR GMAIL LOGIN")
        print("=" * 80)
        print("")
        print("The browser is now on Google's OAuth login page.")
        print("You can now:")
        print("  1. Enter your Gmail email")
        print("  2. Enter your Gmail password")
        print("  3. Approve LinkedIn access")
        print("")
        print("The browser window is open and waiting for your input.")
        print("Screenshots will be saved automatically.")
        print("")

        # Keep browser open for user to interact
        print("Press Ctrl+C when done...")

        try:
            # Wait indefinitely for user interaction
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nClosing browser...")

        # Final screenshot
        await page.screenshot(path="artifacts/03-final-result.png")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        await page.screenshot(path="artifacts/error.png")
        return False

    finally:
        await browser.close()
        await playwright.stop()


async def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "LINKEDIN - SIGN IN WITH GOOGLE".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print("")

    success = await linkedin_google_oauth()

    print("")
    print("=" * 80)
    print("SCREENSHOTS")
    print("=" * 80)
    print("Saved to artifacts/:")
    print("  - 01-linkedin-login-page.png (initial page)")
    print("  - 02-google-redirect.png (Google OAuth page)")
    print("  - 03-final-result.png (after login)")
    print("")


if __name__ == '__main__':
    asyncio.run(main())
