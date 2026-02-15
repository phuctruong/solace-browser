#!/usr/bin/env python3

"""
LINKEDIN LOGIN - CONTINUE WITH GOOGLE BUTTON
Clicks the "Continue with Google" button and uses Gmail OAuth
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
    """Login to LinkedIn using 'Continue with Google' button"""

    print("=" * 80)
    print("LINKEDIN - CONTINUE WITH GOOGLE")
    print("=" * 80)
    print("")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # Step 1: Navigate to LinkedIn login
        print("STEP 1: 📄 Opening LinkedIn login page...")
        await page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
        await asyncio.sleep(2)

        print("✓ Page loaded")
        await page.screenshot(path="artifacts/linkedin-01-login-page.png")

        # Step 2: Find and click "Continue with Google" button
        print("")
        print("STEP 2: 🔍 Finding 'Continue with Google' button...")

        # Wait for page to be fully loaded
        await page.wait_for_load_state('networkidle')

        # Find the button by text
        continue_google = None

        # Try different selectors
        selectors = [
            "button:has-text('Continue with Google')",
            "a:has-text('Continue with Google')",
            "[aria-label*='Continue with Google']",
        ]

        for selector in selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    continue_google = element
                    print(f"✓ Found with selector: {selector}")
                    break
            except:
                pass

        if not continue_google:
            # Manual search - look for button with "Continue" and "Google"
            buttons = await page.query_selector_all("button")
            for btn in buttons:
                text = await btn.text_content()
                if text and 'continue' in text.lower() and 'google' in text.lower():
                    continue_google = btn
                    print(f"✓ Found button: {text.strip()}")
                    break

        if not continue_google:
            print("❌ Could not find button")
            print("")
            print("Available buttons:")
            buttons = await page.query_selector_all("button")
            for i, btn in enumerate(buttons[:5]):
                text = await btn.text_content()
                print(f"  {i+1}. {text.strip() if text else '(empty)'}")
            return False

        # Step 3: Click the button
        print("")
        print("STEP 3: ✋ Clicking 'Continue with Google'...")
        await continue_google.click()
        print("✓ Button clicked!")

        await asyncio.sleep(3)
        await page.screenshot(path="artifacts/linkedin-02-google-page.png")
        print(f"Current URL: {page.url}")

        # Step 4: Google login page
        print("")
        print("STEP 4: 🔐 Google OAuth page loading...")
        print("")
        print("━" * 80)
        print("✅ BROWSER IS READY FOR YOUR GMAIL LOGIN")
        print("━" * 80)
        print("")
        print("The browser window is now showing Google's login page.")
        print("")
        print("NEXT STEPS:")
        print("  1. Enter your Gmail email address")
        print("  2. Click 'Next'")
        print("  3. Enter your Gmail password")
        print("  4. Click 'Next'")
        print("  5. Grant LinkedIn permission (if prompted)")
        print("  6. LinkedIn will load your feed")
        print("")
        print("Screenshots will be saved automatically to artifacts/")
        print("")
        print("Press Ctrl+C when you're done...")
        print("")

        # Keep browser open and monitor for completion
        try:
            # Check periodically if we've successfully logged in
            for i in range(300):  # 5 minutes
                await asyncio.sleep(1)

                # Check if we're back at LinkedIn
                current_url = page.url
                if 'linkedin.com' in current_url and 'login' not in current_url:
                    print("")
                    print("✅ Login successful! Redirected to LinkedIn")
                    break

        except KeyboardInterrupt:
            print("\n")

        # Final screenshot
        await asyncio.sleep(1)
        final_url = page.url
        print(f"Final URL: {final_url}")

        await page.screenshot(path="artifacts/linkedin-03-final.png")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        await page.screenshot(path="artifacts/linkedin-error.png")
        return False

    finally:
        print("")
        print("Closing browser...")
        await browser.close()
        await playwright.stop()


async def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "LINKEDIN - GOOGLE OAUTH LOGIN".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print("")

    success = await linkedin_google_oauth()

    print("")
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    if success:
        print("✅ OAuth flow completed successfully!")
    else:
        print("⚠️  Check the screenshots for what happened")

    print("")
    print("Screenshots saved:")
    print("  - linkedin-01-login-page.png")
    print("  - linkedin-02-google-page.png")
    print("  - linkedin-03-final.png")
    print("")


if __name__ == '__main__':
    asyncio.run(main())
