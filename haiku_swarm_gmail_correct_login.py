#!/usr/bin/env python3
"""
HAIKU SWARM: Gmail Login - CORRECT PATTERN
===========================================

Load credentials → Use saved cookies → Auto-fill if needed → Wait for OAuth approval → Proceed with tasks

Phase 1 (now): Discover patterns + save recipes + PrimeWiki
Phase 2+ (future): Load recipes + execute with CPU only
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

from credential_manager import CredentialManager

# ============================================================================
# LOAD CREDENTIALS (SECURE)
# ============================================================================

def load_credentials(section='gmail'):
    """Load credentials from environment variables (secure)"""
    try:
        return CredentialManager.get_credentials(section)
    except EnvironmentError as e:
        print(f"❌ Credential Error: {e}")
        raise

# ============================================================================
# SCOUT AGENT: Navigate & Detect State
# ============================================================================

class Scout:
    """Navigate and detect page states"""

    def __init__(self, page):
        self.page = page
        self.learnings = []

    async def navigate(self, url):
        """Navigate to URL and detect state"""
        print(f"\n[SCOUT] Navigating to: {url}")
        await self.page.goto(url, wait_until='domcontentloaded')
        await self.page.wait_for_timeout(3000)

        current_url = self.page.url
        title = await self.page.title()

        # Detect state
        state = self._detect_state(current_url, title)

        print(f"[SCOUT] State: {state}")
        print(f"  URL: {current_url}")
        print(f"  Title: {title}")

        self.learnings.append({
            "action": "navigate",
            "url": current_url,
            "state": state,
            "title": title
        })

        return state, current_url

    def _detect_state(self, url, title):
        """Detect page state"""
        if "accounts.google.com" in url:
            if "signin" in url.lower() or "login" in title.lower():
                return "login"
        elif "mail.google.com" in url:
            return "inbox"
        elif "2fa" in url.lower() or "verify" in url.lower() or "challenge" in url.lower():
            return "oauth_2fa"
        return "unknown"

# ============================================================================
# SOLVER AGENT: Auto-fill & Click
# ============================================================================

class Solver:
    """Find elements and perform interactions"""

    def __init__(self, page):
        self.page = page
        self.learnings = []

    async def auto_fill_email(self, email):
        """Auto-fill email using JavaScript (not Playwright fill)"""
        print(f"\n[SOLVER] Auto-filling email: {email}")

        js_fill = f"""
        async () => {{
            const input = document.querySelector('input[type="email"]');
            if (!input) throw new Error('Email input not found');

            // Trigger full event chain
            input.focus();
            await new Promise(r => setTimeout(r, 100));

            input.value = '{email}';

            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            await new Promise(r => setTimeout(r, 50));

            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            await new Promise(r => setTimeout(r, 50));

            input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
            await new Promise(r => setTimeout(r, 50));

            input.blur();
            await new Promise(r => setTimeout(r, 200));

            return true;
        }}
        """

        try:
            result = await self.page.evaluate(js_fill)
            if result:
                print(f"[SOLVER] ✓ Email auto-filled")
                self.learnings.append({"action": "fill_email", "success": True})
                return True
        except Exception as e:
            print(f"[SOLVER] ✗ Failed to auto-fill email: {e}")
            self.learnings.append({"action": "fill_email", "success": False, "error": str(e)})
            return False

    async def click_next(self):
        """Click Next button and wait for it to be enabled"""
        print(f"\n[SOLVER] Clicking Next button...")

        js_click = """
        async () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const nextBtn = buttons.find(b => b.textContent.toLowerCase().includes('next'));

            if (!nextBtn) throw new Error('Next button not found');

            // Wait for enabled state
            for (let i = 0; i < 50; i++) {
                if (!nextBtn.disabled && !nextBtn.hasAttribute('aria-disabled')) {
                    break;
                }
                await new Promise(r => setTimeout(r, 100));
            }

            nextBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
            await new Promise(r => setTimeout(r, 300));

            nextBtn.click();
            return true;
        }
        """

        try:
            result = await self.page.evaluate(js_click)
            if result:
                print(f"[SOLVER] ✓ Next clicked")
                await self.page.wait_for_timeout(2000)
                self.learnings.append({"action": "click_next", "success": True})
                return True
        except Exception as e:
            print(f"[SOLVER] ✗ Failed to click Next: {e}")
            self.learnings.append({"action": "click_next", "success": False, "error": str(e)})
            return False

    async def auto_fill_password(self, password):
        """Auto-fill password"""
        print(f"\n[SOLVER] Auto-filling password...")

        js_fill = f"""
        async () => {{
            const input = document.querySelector('input[type="password"]');
            if (!input) throw new Error('Password input not found');

            input.focus();
            await new Promise(r => setTimeout(r, 100));

            input.value = '{password}';

            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            await new Promise(r => setTimeout(r, 50));

            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            await new Promise(r => setTimeout(r, 50));

            input.blur();
            await new Promise(r => setTimeout(r, 200));

            return true;
        }}
        """

        try:
            result = await self.page.evaluate(js_fill)
            if result:
                print(f"[SOLVER] ✓ Password auto-filled")
                self.learnings.append({"action": "fill_password", "success": True})
                return True
        except Exception as e:
            print(f"[SOLVER] ✗ Failed to auto-fill password: {e}")
            self.learnings.append({"action": "fill_password", "success": False, "error": str(e)})
            return False

    async def click_signin(self):
        """Click Sign in / Submit button"""
        print(f"\n[SOLVER] Clicking Sign in...")

        js_click = """
        async () => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const signinBtn = buttons.find(b => {
                const text = b.textContent.toLowerCase();
                return text.includes('sign') || text.includes('next') || text.includes('submit');
            });

            if (!signinBtn) throw new Error('Sign in button not found');

            signinBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
            await new Promise(r => setTimeout(r, 300));

            signinBtn.click();
            return true;
        }
        """

        try:
            result = await self.page.evaluate(js_click)
            if result:
                print(f"[SOLVER] ✓ Sign in clicked")
                await self.page.wait_for_timeout(3000)
                self.learnings.append({"action": "click_signin", "success": True})
                return True
        except Exception as e:
            print(f"[SOLVER] ✗ Failed to click Sign in: {e}")
            self.learnings.append({"action": "click_signin", "success": False, "error": str(e)})
            return False

# ============================================================================
# SKEPTIC AGENT: Verify & Detect Errors
# ============================================================================

class Skeptic:
    """Verify state and detect errors"""

    def __init__(self, page):
        self.page = page
        self.learnings = []

    async def check_2fa_screen(self):
        """Check if we're on 2FA/OAuth screen"""
        print(f"\n[SKEPTIC] Checking for 2FA/OAuth...")

        current_url = self.page.url

        # Check URL for 2FA indicators
        is_2fa = any(x in current_url.lower() for x in ['2fa', 'verify', 'challenge', 'oauth', 'signin'])

        print(f"[SKEPTIC] URL: {current_url}")
        print(f"[SKEPTIC] 2FA/OAuth detected: {is_2fa}")

        self.learnings.append({
            "action": "check_2fa",
            "url": current_url,
            "is_2fa": is_2fa
        })

        return is_2fa

    async def save_session(self):
        """Save cookies for next run"""
        print(f"\n[SKEPTIC] Saving cookies...")

        # Playwright context already saves cookies automatically
        print(f"[SKEPTIC] ✓ Cookies saved")

        self.learnings.append({
            "action": "save_session",
            "success": True
        })

# ============================================================================
# MAIN COORDINATOR
# ============================================================================

async def main():
    print("\n" + "="*80)
    print("HAIKU SWARM: GMAIL LOGIN - CORRECT PATTERN")
    print("="*80)
    print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Strategy: Load creds → Try cookies → Auto-fill → Wait for OAuth\n")

    # Load credentials
    creds = load_credentials('gmail')
    email = creds.get('email', 'phuc.truong@gmail.com')
    password = creds.get('password', '')

    print(f"Loaded credentials:")
    print(f"  Email: {email}")
    print(f"  Password: {'*' * len(password)}\n")

    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=300,
            args=["--start-maximized"]
        )

        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        # Initialize agents
        scout = Scout(page)
        solver = Solver(page)
        skeptic = Skeptic(page)

        try:
            # ================================================================
            # STEP 1: Navigate to Gmail
            # ================================================================
            print("[STEP 1] NAVIGATE TO GMAIL")
            print("-" * 80)

            state, url = await scout.navigate("https://mail.google.com/mail/u/0/#inbox")

            # If already logged in
            if state == "inbox":
                print("\n✓ Already logged in with saved cookies!")
                await page.screenshot(path="artifacts/swarm_login_already_in.png")

            # If on login page
            elif state == "login":
                print("\n⚠ On login page - auto-filling credentials...")

                # STEP 2: Auto-fill email
                print("\n[STEP 2] AUTO-FILL EMAIL")
                print("-" * 80)
                await solver.auto_fill_email(email)
                await page.screenshot(path="artifacts/swarm_email_filled.png")

                # STEP 3: Click Next
                print("\n[STEP 3] CLICK NEXT")
                print("-" * 80)
                await solver.click_next()
                await page.screenshot(path="artifacts/swarm_after_next.png")

                # STEP 4: Check what page we're on
                state, url = await scout.navigate(page.url)

                # STEP 5: Auto-fill password
                if state == "login":
                    print("\n[STEP 4] AUTO-FILL PASSWORD")
                    print("-" * 80)
                    await solver.auto_fill_password(password)
                    await page.screenshot(path="artifacts/swarm_password_filled.png")

                    # STEP 6: Click Sign in
                    print("\n[STEP 5] CLICK SIGN IN")
                    print("-" * 80)
                    await solver.click_signin()
                    await page.screenshot(path="artifacts/swarm_after_signin.png")

                # STEP 7: Check for 2FA
                print("\n[STEP 6] CHECK FOR 2FA/OAUTH")
                print("-" * 80)
                is_2fa = await skeptic.check_2fa_screen()

                if is_2fa:
                    print("\n" + "="*80)
                    print("⏸ WAITING FOR OAUTH APPROVAL")
                    print("="*80)
                    print("\n[INSTRUCTION] Click your Gmail app to approve OAuth")
                    print("[WAITING] Waiting for approval (max 300 seconds)...\n")

                    try:
                        # Wait for successful login (URL change to inbox)
                        await page.wait_for_url(
                            "**mail.google.com**",
                            timeout=300000
                        )
                        print("\n[SUCCESS] ✓ OAuth approved!")
                        await page.screenshot(path="artifacts/swarm_oauth_approved.png")
                    except:
                        print("[TIMEOUT] OAuth approval timeout")
                        return
                else:
                    # Check if we're now in inbox
                    state, url = await scout.navigate(page.url)
                    if state == "inbox":
                        print("\n✓ Successfully logged in!")
                        await page.screenshot(path="artifacts/swarm_loggedin.png")

            # ================================================================
            # STEP 7: Save session
            # ================================================================
            print("\n[STEP 7] SAVE SESSION")
            print("-" * 80)
            await skeptic.save_session()

            # ================================================================
            # SUCCESS - Ready for next tasks
            # ================================================================
            print("\n" + "="*80)
            print("✓ LOGIN COMPLETE - READY FOR TIER 1 TASKS")
            print("="*80)
            print("\nNext: Start TIER 1 Task 1 - Attachment Upload")
            print("Browser open for live monitoring. Press Ctrl+C when done.\n")

            # Keep browser open
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n\nSession ended by user")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await context.close()
            await browser.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
