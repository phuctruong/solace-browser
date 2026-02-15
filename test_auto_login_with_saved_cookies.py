#!/usr/bin/env python3

"""
Auto-login with saved cookies + password fallback (non-interactive)
Uses credentials from credentials.properties
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


def read_credentials(section='linkedin'):
    """Read credentials from credentials.properties file"""
    try:
        config = {}
        current_section = None

        with open('credentials.properties') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    config[current_section] = {}
                elif '=' in line and current_section:
                    key, value = line.split('=', 1)
                    config[current_section][key.strip()] = value.strip()

        if section in config:
            return config[section]
        return {}
    except Exception as e:
        print(f"⚠️  Could not read credentials.properties: {e}")
        return {}


async def main():
    print("\n" + "="*80)
    print("AUTO-LOGIN WITH SAVED COOKIES (+ PASSWORD FALLBACK)")
    print("="*80 + "\n")

    # Read credentials
    linkedin_creds = read_credentials('linkedin')
    gmail_creds = read_credentials('gmail')

    linkedin_email = linkedin_creds.get('email', 'phuc.truong@gmail.com')
    linkedin_password = linkedin_creds.get('password', '')

    print(f"Email: {linkedin_email}")
    print(f"Password: {'*' * len(linkedin_password) if linkedin_password else '[not found]'}\n")

    if not linkedin_password:
        print("❌ No LinkedIn password in credentials.properties")
        print("   Please add [linkedin] section with email and password\n")
        return

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

    is_on_login_page = "/uas/login" in current_url or "/login" in current_url
    is_on_feed = "/feed/" in current_url

    print("Step 3: Checking authentication status...")

    # SUCCESS: Already logged in
    if is_on_feed and "login" not in current_url:
        print("✅ ALREADY LOGGED IN with saved cookies!\n")
        await browser.current_page.screenshot(path="artifacts/01-already-logged-in.png")
        result = {
            "success": True,
            "status": "logged_in_with_cookies",
            "message": "Saved cookies were sufficient for login",
            "url": current_url
        }

    # FALLBACK: Need password
    elif is_on_login_page:
        print("⚠️  On login page (saved cookies not sufficient)")
        print("    Attempting password authentication...\n")

        # Check for password field
        print("Step 4: Looking for password field...")
        password_input = await browser.current_page.query_selector(
            "input[type='password']"
        )

        if password_input:
            print("✓ Found password field\n")

            # Enter password
            print("Step 5: Entering LinkedIn password...")
            await password_input.fill(linkedin_password)
            await asyncio.sleep(0.5)
            print(f"✓ Password entered ({len(linkedin_password)} characters)\n")

            # Take screenshot before submit
            await browser.current_page.screenshot(path="artifacts/02-password-entered.png")

            # Find and click submit button
            print("Step 6: Looking for submit button...")
            buttons = await browser.current_page.query_selector_all("button")

            submit_btn = None
            for btn in buttons:
                text = await btn.text_content()
                if text and ("sign in" in text.lower() or "continue" in text.lower()):
                    submit_btn = btn
                    break

            if submit_btn:
                print("✓ Found submit button, clicking...\n")
                await submit_btn.click()
                await asyncio.sleep(3)

                # Check if successful
                current_url = browser.current_page.url
                page_content = await browser.current_page.content()

                print(f"New URL: {current_url}\n")

                # Check for success
                if "/feed/" in current_url and "/login" not in current_url:
                    print("✅ SUCCESS! Logged in!\n")
                    await browser.current_page.screenshot(path="artifacts/03-logged-in-success.png")
                    result = {
                        "success": True,
                        "status": "logged_in",
                        "message": "Successfully authenticated with saved cookies + password",
                        "url": current_url
                    }

                # Check for 2FA
                elif "challenge" in current_url or "verify" in current_url.lower():
                    print("⚠️  2FA Required - waiting for phone approval...\n")
                    await browser.current_page.screenshot(path="artifacts/04-2fa-required.png")

                    # Wait for 2FA
                    print("Waiting up to 60 seconds for 2FA approval...\n")
                    for i in range(60):
                        await asyncio.sleep(1)
                        current_url = browser.current_page.url

                        if i % 10 == 0:
                            print(f"  {i}s: Waiting for 2FA approval...")

                        # Check if 2FA completed
                        if "/feed/" in current_url and "/challenge" not in current_url:
                            print("\n✅ 2FA APPROVED! Logged in!\n")
                            await browser.current_page.screenshot(path="artifacts/05-2fa-approved.png")
                            result = {
                                "success": True,
                                "status": "logged_in_after_2fa",
                                "message": "Successfully authenticated after 2FA approval",
                                "url": current_url
                            }
                            break
                    else:
                        print("\n⚠️  2FA timeout - approve on phone and refresh manually\n")
                        result = {
                            "success": True,
                            "status": "waiting_for_2fa",
                            "message": "2FA approval pending",
                            "url": current_url
                        }

                # Check for recovery page
                elif "recovery" in current_url.lower():
                    print("⚠️  Recovery info page detected - skipping...\n")
                    result = {
                        "success": True,
                        "status": "recovery_page",
                        "message": "On recovery page, manual approval needed",
                        "url": current_url
                    }

                else:
                    print(f"⚠️  Unexpected state: {current_url}\n")
                    result = {
                        "success": True,
                        "status": "uncertain",
                        "message": "Password submitted, verify manually",
                        "url": current_url
                    }

            else:
                print("❌ Could not find submit button\n")
                result = {
                    "success": False,
                    "error": "Submit button not found"
                }
        else:
            print("❌ Could not find password field\n")
            result = {
                "success": False,
                "error": "Password field not found"
            }

    else:
        print(f"⚠️  Unknown state: {current_url}\n")
        result = {
            "success": False,
            "error": f"Unknown page state"
        }

    # Print results
    print("="*80)
    print("RESULT")
    print("="*80)
    print(json.dumps(result, indent=2))
    print()

    # Keep browser open for verification
    print("Keeping browser open for 15 seconds for verification...")
    print("Check the browser to see current state\n")

    await asyncio.sleep(15)

    # Save updated session before closing
    print("Saving updated session...")
    save_result = await browser.save_session()
    if save_result.get('success'):
        print(f"✓ Session saved: {save_result['session_file']}\n")

    await browser.stop()
    print("✓ Test complete!\n")


if __name__ == "__main__":
    asyncio.run(main())
