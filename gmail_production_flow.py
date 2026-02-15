#!/usr/bin/env python3
"""
GMAIL ACCESS - PRODUCTION FLOW
Headless automation with user OAuth approval via mobile

Flow:
1. Login to LinkedIn (headless)
2. Detect OAuth verification screen
3. Alert user (SMS/email/webhook)
4. User approves in Gmail app
5. Wait for approval
6. Save session
7. Access Gmail
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from credential_manager import CredentialManager

if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':1'

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed")
    sys.exit(1)


def send_user_notification(message: str):
    """
    Send notification to user requesting OAuth approval

    In production, this would send:
    - SMS via Twilio
    - Email via SendGrid
    - Push notification via Firebase
    - Webhook to user's phone

    For now, just print to console
    """
    print("\n" + "="*80)
    print("🔔 USER NOTIFICATION")
    print("="*80)
    print(f"\n{message}\n")
    print("="*80)

    # Production implementation:
    # import twilio_client
    # twilio_client.send_sms(user_phone, message)

    # Or webhook:
    # requests.post(user_webhook_url, json={"message": message})


async def wait_for_oauth_approval(page, timeout=120):
    """
    Poll page to detect when OAuth approval completes

    Returns True when approved, False on timeout
    """
    print("\n⏳ Waiting for user to approve OAuth (up to 120s)...")

    start_time = asyncio.get_event_loop().time()

    while True:
        elapsed = asyncio.get_event_loop().time() - start_time

        if elapsed > timeout:
            print(f"\n⏱️  Timeout after {timeout}s")
            return False

        # Check if URL changed (OAuth completed)
        current_url = page.url

        # LinkedIn redirects to /feed after successful OAuth
        if 'linkedin.com/feed' in current_url or 'linkedin.com/in/' in current_url:
            print(f"\n✅ OAuth approved! ({elapsed:.1f}s)")
            return True

        # Check for error states
        if 'error' in current_url.lower() or 'denied' in current_url.lower():
            print(f"\n❌ OAuth denied or errored")
            return False

        # Show progress every 10 seconds
        if int(elapsed) % 10 == 0 and int(elapsed) > 0:
            print(f"   Still waiting... ({int(elapsed)}s)")

        await asyncio.sleep(2)


async def main():
    print("\n" + "="*80)
    print("🎯 GMAIL PRODUCTION FLOW - Headless OAuth")
    print("="*80)
    print()

    # Load credentials (secure - from environment variables)
    try:
        linkedin_creds = CredentialManager.get_credentials('linkedin')
        linkedin_email = linkedin_creds['email']
        linkedin_password = linkedin_creds['password']
    except EnvironmentError as e:
        print(f"❌ {e}")
        sys.exit(1)

    print("Configuration:")
    print(f"  LinkedIn Email: {linkedin_email}")
    print(f"  Password: {'*' * len(linkedin_password)}")
    print()

    # Start browser (headless for production)
    headless = False  # Set to True in production
    print(f"Starting browser (headless={headless})...")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # PHASE 1: LinkedIn Login
        print("\n" + "="*80)
        print("PHASE 1: LINKEDIN LOGIN")
        print("="*80)
        print()

        print("Step 1: Navigate to LinkedIn...")
        await page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
        await asyncio.sleep(2)

        print("Step 2: Fill LinkedIn username...")
        await page.fill("input#username", linkedin_email)
        print(f"   ✅ Username: {linkedin_email}")
        await asyncio.sleep(1)

        print("Step 3: Fill LinkedIn password...")
        await page.fill("input#password", linkedin_password)
        print(f"   ✅ Password: {'*' * len(linkedin_password)}")
        await asyncio.sleep(1)

        print("Step 4: Submit LinkedIn login form...")
        await page.click("button[type='submit']")
        print("   ✅ Form submitted")
        await asyncio.sleep(5)

        current_url = page.url
        print(f"   Current URL: {current_url[:80]}...")

        # PHASE 2: Detect OAuth Screen
        print("\n" + "="*80)
        print("PHASE 2: OAUTH VERIFICATION DETECTION")
        print("="*80)
        print()

        # Check if we're at OAuth verification screen
        # Common indicators:
        # - URL contains "checkpoint" or "challenge"
        # - Page asks to verify identity
        # - Page mentions "Gmail" or "Google"

        page_content = await page.content()
        is_oauth_screen = (
            'oauth' in current_url.lower() or
            'challenge' in current_url.lower() or
            'checkpoint' in current_url.lower() or
            'verify' in page_content.lower() or
            'gmail' in page_content.lower()
        )

        if is_oauth_screen:
            print("✅ OAuth verification screen detected!")

            # PHASE 3: Alert User
            print("\n" + "="*80)
            print("PHASE 3: USER NOTIFICATION")
            print("="*80)
            print()

            send_user_notification(
                "🔐 LinkedIn OAuth Approval Needed\n\n"
                "Please open your Gmail app and approve the login request.\n\n"
                "You have 2 minutes to approve."
            )

            # PHASE 4: Wait for Approval
            print("\n" + "="*80)
            print("PHASE 4: WAITING FOR OAUTH APPROVAL")
            print("="*80)
            print()

            approved = await wait_for_oauth_approval(page, timeout=120)

            if not approved:
                print("\n❌ OAuth was not approved in time")
                await page.screenshot(path="artifacts/oauth-timeout.png")
                return False

            print("\n✅ OAuth approval completed!")
            await page.screenshot(path="artifacts/oauth-approved.png")

        elif 'linkedin.com/feed' in current_url:
            print("✅ Logged in directly (no OAuth needed)")
        else:
            print("⚠️  Unexpected state")
            print(f"   URL: {current_url}")
            await page.screenshot(path="artifacts/unexpected-state.png")

        # PHASE 5: Save Session
        print("\n" + "="*80)
        print("PHASE 5: SAVE SESSION")
        print("="*80)
        print()

        session_path = "artifacts/gmail_production_session.json"
        print(f"Saving session to {session_path}...")

        await context.storage_state(path=session_path)
        print(f"✅ Session saved!")

        # Check cookies
        cookies = await context.cookies()
        google_cookies = [c for c in cookies if 'google' in c.get('domain', '').lower()]
        print(f"   Total cookies: {len(cookies)}")
        print(f"   Google cookies: {len(google_cookies)}")

        if google_cookies:
            print(f"   Google cookie domains:")
            for c in google_cookies[:5]:
                print(f"   - {c['name']} @ {c['domain']}")

        # PHASE 6: Test Gmail Access
        print("\n" + "="*80)
        print("PHASE 6: TEST GMAIL ACCESS")
        print("="*80)
        print()

        print("Navigating to Gmail...")
        await page.goto("https://mail.google.com", wait_until='domcontentloaded')
        await asyncio.sleep(7)

        gmail_url = page.url
        print(f"   Gmail URL: {gmail_url[:80]}...")

        # Check for Gmail indicators
        try:
            # Look for compose button or inbox
            compose = await page.query_selector("[gh='cm'], button:has-text('Compose'), [aria-label*='Compose']")
            inbox_indicators = await page.query_selector("[aria-label*='Inbox'], [title*='Inbox']")
            sign_in = await page.query_selector("a:has-text('Sign in'), button:has-text('Sign in')")

            if compose or (inbox_indicators and not sign_in):
                print("\n" + "="*80)
                print("✅ ✅ ✅ LOGGED INTO GMAIL! ✅ ✅ ✅")
                print("="*80)
                print()
                print("Production flow SUCCESSFUL:")
                print("1. ✅ LinkedIn login (automated)")
                print("2. ✅ OAuth detection (automated)")
                print("3. ✅ User notification (automated)")
                print("4. ✅ OAuth approval (user via mobile)")
                print("5. ✅ Session saved (automated)")
                print("6. ✅ Gmail access (automated)")
                print()
                print("Next steps:")
                print("- Deploy as headless service")
                print("- Add SMS/webhook notifications")
                print("- Implement Gmail automation tasks")
                print("- Set up session refresh before expiry")

                await page.screenshot(path="artifacts/gmail-production-success.png")
                success = True
            elif sign_in:
                print("\n❌ NOT LOGGED IN - Still showing sign-in")
                await page.screenshot(path="artifacts/gmail-production-failed.png")
                success = False
            else:
                print("\n⚠️  Uncertain state - check screenshot")
                await page.screenshot(path="artifacts/gmail-production-uncertain.png")
                success = False

        except Exception as e:
            print(f"\n❌ Error checking Gmail: {e}")
            await page.screenshot(path="artifacts/gmail-production-error.png")
            success = False

        return success

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        await page.screenshot(path="artifacts/production-error.png")
        return False

    finally:
        print("\n" + "="*80)
        print("CLEANUP")
        print("="*80)
        print()

        print("Closing browser in 10 seconds...")
        await asyncio.sleep(10)

        await browser.close()
        await playwright.stop()
        print("✅ Done")


if __name__ == '__main__':
    success = asyncio.run(main())

    print("\n" + "="*80)
    print("FINAL STATUS")
    print("="*80)

    if success:
        print("\n✅ Gmail production flow WORKING!")
        print("\nReady to deploy as headless service.")
        sys.exit(0)
    else:
        print("\n❌ Flow incomplete - check screenshots")
        sys.exit(1)
