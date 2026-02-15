#!/usr/bin/env python3
"""
Medium Login Discovery - Proper OAuth2 Flow
============================================
Strategy: Go to Medium login page and actually login
(Don't try to access homepage - go through login flow first)
"""
import asyncio
import json
import configparser
from playwright.async_api import async_playwright
from datetime import datetime

class MediumLoginDiscovery:
    def __init__(self, credentials_file='credentials.properties'):
        self.browser = None
        self.context = None
        self.page = None
        self.credentials = {}
        self.credentials_file = credentials_file
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "method": "headed_login_with_email",
            "steps": [],
            "success": False,
            "cf_clearance_obtained": False,
            "screenshots": []
        }

    def load_credentials(self):
        """Load Medium credentials from properties file"""
        print(f"\n🔐 Loading credentials from {self.credentials_file}")
        config = configparser.ConfigParser()
        config.read(self.credentials_file)

        # Use Gmail as Medium login (Gmail OAuth is available)
        if 'gmail' in config:
            self.credentials = dict(config['gmail'])
            print(f"✅ Credentials loaded")
            print(f"   Email: {self.credentials.get('email', 'unknown')}")
            return True
        else:
            print("❌ Credentials not found")
            return False

    async def start(self):
        """Start headed browser"""
        print("\n🖥️  Starting HEADED browser...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        print("✅ Headed browser started\n")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def screenshot(self, step_num: int, title: str):
        """Take screenshot"""
        path = f"/tmp/medium_login_step{step_num:02d}_{title.replace(' ', '_').lower()}.png"
        await self.page.screenshot(path=path)
        print(f"   📸 {path}")
        self.results["screenshots"].append(path)

    async def step_1_navigate_to_medium_login(self):
        """Step 1: Go to Medium and find login"""
        print("=" * 70)
        print("STEP 1: Navigate to Medium and Find Login")
        print("=" * 70)

        print("\n🌐 Navigate to medium.com...")
        try:
            await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
            print("✅ Page loaded")
            await self.screenshot(1, "homepage")

            # Look for sign in link
            print("\n🔍 Looking for 'Sign in' link...")
            sign_in_selectors = [
                "a:has-text('Sign in')",
                "button:has-text('Sign in')",
                "[data-testid*='sign'][data-testid*='in']",
                "a[href*='signin']",
            ]

            for selector in sign_in_selectors:
                try:
                    elem = await self.page.query_selector(selector)
                    if elem:
                        print(f"   ✅ Found: {selector}")
                        await elem.click()
                        print("   ✓ Clicked")
                        await asyncio.sleep(2)
                        self.results["steps"].append({
                            "step": 1,
                            "action": "navigate_and_click_signin",
                            "success": True
                        })
                        return True
                except:
                    pass

            print("   ⚠️  Sign in link not found - might already be on login page")
            return True

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.results["steps"].append({
                "step": 1,
                "success": False,
                "error": str(e)
            })
            return False

    async def step_2_click_google_signin(self):
        """Step 2: Click 'Sign in with Google' button"""
        print("\n" + "=" * 70)
        print("STEP 2: Click 'Sign in with Google' (Gmail OAuth)")
        print("=" * 70)

        print("\n🔍 Looking for 'Sign in with Google' button...")
        await self.screenshot(2, "signin_modal")

        # Click the "Sign in with Google" button
        google_button_selectors = [
            "button:has-text('Google')",
            "button:has-text('Sign in with Google')",
            "a:has-text('Google')",
            "[data-provider='google']",
        ]

        button_clicked = False
        for selector in google_button_selectors:
            try:
                elem = await self.page.query_selector(selector)
                if elem:
                    print(f"   ✅ Found: {selector}")
                    await elem.click()
                    print("   ✓ Clicked 'Sign in with Google'")
                    await asyncio.sleep(3)
                    button_clicked = True
                    break
            except Exception as e:
                print(f"   ⚠️  Error: {str(e)[:50]}")

        if not button_clicked:
            print("   ⚠️  'Sign in with Google' button not found")
            self.results["steps"].append({
                "step": 2,
                "success": False,
                "note": "Sign in with Google button not found"
            })
            return False

        self.results["steps"].append({
            "step": 2,
            "action": "click_google_signin",
            "success": True
        })
        return True

    async def step_3_handle_google_oauth(self):
        """Step 3: Google OAuth - Email, Password, and 2FA"""
        print("\n" + "=" * 70)
        print("STEP 3: Google OAuth - Email & Password & 2FA")
        print("=" * 70)

        print("\n⏳ Waiting for Google login page...")
        await asyncio.sleep(3)
        await self.screenshot(3, "google_login")

        # Step 3a: Enter email
        print("\n🔍 Looking for email input...")
        try:
            email_input = await self.page.query_selector("input[type='email']")
            if email_input:
                email = self.credentials.get('email', '')
                print(f"   ✅ Found email input")
                print(f"   → Entering: {email}")
                await email_input.fill(email)
                print("   ✓ Email entered")

                # Click Next
                next_btn = await self.page.query_selector("button:has-text('Next')")
                if next_btn:
                    await next_btn.click()
                    print("   ✓ Clicked Next")
                    await asyncio.sleep(2)
        except Exception as e:
            print(f"   ⚠️  Error: {str(e)[:50]}")

        await self.screenshot(3, "google_password_page")

        # Step 3b: Enter password
        print("\n🔍 Looking for password input...")
        try:
            password_input = await self.page.query_selector("input[type='password']")
            if password_input:
                password = self.credentials.get('password', '')
                print(f"   ✅ Found password input")
                print(f"   → Entering password...")
                await password_input.fill(password)
                print("   ✓ Password entered")

                # Click Next
                next_btn = await self.page.query_selector("button:has-text('Next')")
                if next_btn:
                    await next_btn.click()
                    print("   ✓ Clicked Next")
                    await asyncio.sleep(3)
        except Exception as e:
            print(f"   ⚠️  Error: {str(e)[:50]}")

        await self.screenshot(3, "google_after_password")

        # Step 3c: Handle 2FA
        print("\n🔍 Checking for 2FA requirement...")
        html = await self.page.content()

        if "2-step" in html.lower() or "approve" in html.lower():
            print("   ⚠️  2FA required - Google Authenticator app approval needed")
            print("   ⏳ WAITING for you to approve in Gmail app...")
            print("   (Check your phone/Gmail app and approve the login)")

            # Wait up to 30 seconds for user to approve
            for i in range(30):
                await asyncio.sleep(1)
                html = await self.page.content()

                # Check if we got past 2FA
                if "2-step" not in html.lower() and len(html) > 30000:
                    print(f"   ✅ 2FA approved! (after {i}s)")
                    self.results["steps"].append({
                        "step": 3,
                        "action": "google_oauth",
                        "success": True,
                        "2fa_handled": True,
                        "wait_time": i
                    })
                    await self.screenshot(3, "after_2fa_approved")
                    return True

                if i % 10 == 0 and i > 0:
                    print(f"   ... still waiting ({i}s)")

            print("   ⚠️  Timeout waiting for 2FA")
            self.results["steps"].append({
                "step": 3,
                "action": "google_oauth",
                "success": False,
                "note": "2FA timeout"
            })
            return False
        else:
            print("   ✅ No 2FA required - proceeding")
            self.results["steps"].append({
                "step": 3,
                "action": "google_oauth",
                "success": True,
                "2fa_handled": False
            })
            return True

    async def step_4_verify_login(self):
        """Step 4: Verify we're logged in"""
        print("\n" + "=" * 70)
        print("STEP 4: Verify Login Success")
        print("=" * 70)

        await self.screenshot(4, "after_login")

        html = await self.page.content()

        # Check for content indicators
        indicators = [
            ("Home feed", "feed" in html.lower() or "home" in html.lower()),
            ("Articles", "<article" in html),
            ("Medium UI", "medium" in html.lower()),
            ("User profile", "profile" in html.lower()),
        ]

        print("\n🔍 Checking for Medium content...")
        found = 0
        for name, result in indicators:
            if result:
                print(f"   ✅ {name}")
                found += 1
            else:
                print(f"   ❌ {name}")

        if found >= 2:
            print(f"\n✅ Login successful! ({found}/4 indicators)")
            self.results["steps"].append({
                "step": 4,
                "action": "verify_login",
                "success": True,
                "indicators_found": found
            })
            return True
        else:
            print(f"\n⚠️  Unclear login status ({found}/4 indicators)")
            self.results["steps"].append({
                "step": 4,
                "action": "verify_login",
                "success": False,
                "indicators_found": found
            })
            return False

    async def step_5_get_cookies(self):
        """Step 5: Get session cookies"""
        print("\n" + "=" * 70)
        print("STEP 5: Extract Session Cookies")
        print("=" * 70)

        try:
            cookies = await self.context.cookies()
            print(f"\n📊 Total cookies: {len(cookies)}")

            # Save all cookies
            with open('/tmp/medium_login_cookies.json', 'w') as f:
                json.dump(cookies, f, indent=2)

            print("💾 Saved to: /tmp/medium_login_cookies.json")

            # Check for important cookies
            important_cookies = {}
            for c in cookies:
                if any(x in c['name'].lower() for x in ['auth', 'session', 'cf', 'medium']):
                    important_cookies[c['name']] = c['value'][:50] + "..."

            if important_cookies:
                print("\n🔑 Important cookies found:")
                for name, value in important_cookies.items():
                    print(f"   • {name}: {value}")
                    if 'cf_clearance' in name:
                        self.results["cf_clearance_obtained"] = True

            self.results["steps"].append({
                "step": 5,
                "action": "get_cookies",
                "success": True,
                "total_cookies": len(cookies)
            })
            return True

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            self.results["steps"].append({
                "step": 5,
                "action": "get_cookies",
                "success": False,
                "error": str(e)
            })
            return False

    async def run_discovery(self):
        """Run complete discovery"""
        print("\n" + "█" * 70)
        print("MEDIUM LOGIN DISCOVERY")
        print("Go through actual login flow (not just homepage access)")
        print("█" * 70)

        try:
            if not await self.step_1_navigate_to_medium_login():
                return

            if not await self.step_2_click_google_signin():
                return

            if not await self.step_3_handle_google_oauth():
                return

            if await self.step_4_verify_login():
                self.results["success"] = True

            await self.step_5_get_cookies()

        finally:
            with open('/tmp/medium_login_discovery_results.json', 'w') as f:
                json.dump(self.results, f, indent=2)

            print("\n" + "=" * 70)
            print("DISCOVERY COMPLETE")
            print("=" * 70)
            print(f"\n📊 Summary:")
            print(f"   Steps completed: {len(self.results['steps'])}")
            print(f"   Success: {self.results['success']}")
            print(f"   CF_Clearance: {self.results['cf_clearance_obtained']}")
            print(f"   Screenshots: {len(self.results['screenshots'])}")

async def main():
    discovery = MediumLoginDiscovery()

    if not discovery.load_credentials():
        return

    await discovery.start()

    try:
        await discovery.run_discovery()
    finally:
        await discovery.stop()

if __name__ == "__main__":
    asyncio.run(main())
