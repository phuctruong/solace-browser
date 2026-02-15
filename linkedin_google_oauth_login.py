#!/usr/bin/env python3

"""
LINKEDIN LOGIN WITH GOOGLE OAUTH
Uses Gmail credentials to sign into LinkedIn via Google
"""

import asyncio
import os
import sys
import configparser
from pathlib import Path

# Set display
if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':1'

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed")
    sys.exit(1)


async def login_linkedin_with_google():
    """Login to LinkedIn using Google OAuth with Gmail credentials"""

    # Load credentials
    config = configparser.ConfigParser()
    config.read('credentials.properties')

    gmail_email = config.get('gmail', 'email')
    gmail_password = config.get('gmail', 'password')

    if not gmail_email or gmail_email == 'your-email@gmail.com':
        print("ERROR: Gmail credentials not configured")
        return False

    print("=" * 80)
    print("LINKEDIN LOGIN WITH GOOGLE OAUTH")
    print("=" * 80)
    print(f"Using Gmail: {gmail_email}")
    print("")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # Step 1: Navigate to LinkedIn
        print("1️⃣  Navigate to LinkedIn...")
        await page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
        await asyncio.sleep(2)

        print("   Taking screenshot of login page...")
        await page.screenshot(path="artifacts/linkedin-step1-login-page.png")

        # Step 2: Click "Sign in with Google" button
        print("")
        print("2️⃣  Looking for 'Sign in with Google' button...")

        # Wait for page to load and find Google button
        google_buttons = await page.query_selector_all("button")
        google_button_found = False

        for btn in google_buttons:
            text = await btn.text_content()
            if text and 'google' in text.lower():
                print(f"   Found: {text}")
                await btn.click()
                google_button_found = True
                break

        if not google_button_found:
            # Try clicking by aria-label
            google_btn = await page.query_selector('[aria-label*="Google"], [aria-label*="google"]')
            if google_btn:
                print("   Found Google button (aria-label)")
                await google_btn.click()
                google_button_found = True

        if not google_button_found:
            # Try finding link
            links = await page.query_selector_all("a")
            for link in links:
                text = await link.text_content()
                if text and 'google' in text.lower():
                    print(f"   Found Google link: {text}")
                    await link.click()
                    google_button_found = True
                    break

        if google_button_found:
            print("   ✓ Clicked Google button")
        else:
            print("   ⚠️  Could not find Google button, attempting direct method...")

        await asyncio.sleep(3)

        # Step 3: Google login page
        print("")
        print("3️⃣  Google login page should appear...")
        print(f"   Current URL: {page.url}")

        await page.screenshot(path="artifacts/linkedin-step2-google-login.png")

        # Step 4: Enter Gmail email
        print("")
        print("4️⃣  Entering Gmail email...")

        email_inputs = await page.query_selector_all("input[type='email']")
        if email_inputs:
            print(f"   Found {len(email_inputs)} email input(s)")
            await email_inputs[0].fill(gmail_email)
            print(f"   ✓ Entered: {gmail_email}")
            await asyncio.sleep(1)

            # Click Next
            print("   Clicking Next...")
            next_buttons = await page.query_selector_all("button")
            for btn in next_buttons:
                text = await btn.text_content()
                if text and 'Next' in text:
                    await btn.click()
                    print("   ✓ Clicked Next")
                    break

        await asyncio.sleep(3)
        await page.screenshot(path="artifacts/linkedin-step3-email-entered.png")

        # Step 5: Enter password
        print("")
        print("5️⃣  Entering Gmail password...")

        password_inputs = await page.query_selector_all("input[type='password']")
        if password_inputs:
            print(f"   Found {len(password_inputs)} password input(s)")
            await password_inputs[0].fill(gmail_password)
            print(f"   ✓ Entered password (hidden)")
            await asyncio.sleep(1)

            # Click Next or Sign in
            print("   Clicking Sign in...")
            buttons = await page.query_selector_all("button")
            for btn in buttons:
                text = await btn.text_content()
                if text and ('Next' in text or 'Sign' in text):
                    await btn.click()
                    print("   ✓ Clicked Sign in")
                    break

        await asyncio.sleep(5)
        await page.screenshot(path="artifacts/linkedin-step4-password-entered.png")

        # Step 6: Check for consent screen
        print("")
        print("6️⃣  Checking for permission consent screen...")

        allow_buttons = await page.query_selector_all("button")
        for btn in allow_buttons:
            text = await btn.text_content()
            if text and ('Allow' in text or 'Continue' in text or 'Agree' in text):
                print(f"   Found: {text}")
                await btn.click()
                print("   ✓ Clicked to allow permissions")
                await asyncio.sleep(2)
                break

        await asyncio.sleep(5)
        await page.screenshot(path="artifacts/linkedin-step5-consent.png")

        # Step 7: Check if logged in
        print("")
        print("7️⃣  Checking login status...")
        print(f"   Current URL: {page.url}")

        # Wait for redirect and load
        await page.wait_for_load_state('domcontentloaded')
        await asyncio.sleep(2)

        final_url = page.url
        print(f"   Final URL: {final_url}")

        # Determine success
        success = False
        if 'feed' in final_url or 'home' in final_url or 'linkedin.com' in final_url:
            if 'login' not in final_url:
                success = True

        if success:
            print("")
            print("✅ ✅ ✅ LINKEDIN LOGIN SUCCESSFUL! ✅ ✅ ✅")
            print("")
            await page.screenshot(path="artifacts/linkedin-success.png")
        else:
            print("")
            print("⚠️  Login status unclear. Checking page content...")

            # Try to find user menu or profile
            profile_menu = await page.query_selector('[data-test-id="profile-dropdown"]')
            if profile_menu:
                print("✅ Found profile menu - likely logged in")
                success = True
            else:
                print("❌ Could not verify login")

            await page.screenshot(path="artifacts/linkedin-final.png")

        # Get page title
        title = await page.title()
        print(f"   Page title: {title}")

        # Take final screenshot showing what's on screen
        print("")
        print("📸 Taking final screenshots...")
        await page.screenshot(path="artifacts/linkedin-final-full.png")

        # Get HTML content
        html = await page.content()
        print(f"   Page content length: {len(html)} bytes")

        return success

    except Exception as e:
        print(f"❌ Error: {e}")
        await page.screenshot(path="artifacts/linkedin-error.png")
        return False

    finally:
        await browser.close()
        await playwright.stop()


async def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "LINKEDIN LOGIN WITH GOOGLE OAUTH - LIVE DEMONSTRATION".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    print("")

    success = await login_linkedin_with_google()

    print("")
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)

    if success:
        print("✅ LOGIN SUCCESSFUL")
    else:
        print("⚠️  LOGIN STATUS UNCLEAR - Check screenshots below")

    print("")
    print("Screenshots saved to artifacts/:")
    print("  - linkedin-step1-login-page.png (initial page)")
    print("  - linkedin-step2-google-login.png (Google redirect)")
    print("  - linkedin-step3-email-entered.png (after email)")
    print("  - linkedin-step4-password-entered.png (after password)")
    print("  - linkedin-step5-consent.png (permission screen)")
    print("  - linkedin-final.png (result page)")
    print("  - linkedin-final-full.png (full page screenshot)")
    print("")
    print("=" * 80)


if __name__ == '__main__':
    asyncio.run(main())
