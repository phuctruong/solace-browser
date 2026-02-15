#!/usr/bin/env python3
"""
Medium Login via Gmail OAuth - CAPTCHA Trigger Test
===================================================
Follows the specific path:
1. Navigate to medium.com homepage
2. Click Google sign-in button (from homepage, NOT from modal)
3. Complete Gmail OAuth flow
4. Monitor for and detect Cloudflare CAPTCHA
"""
import asyncio
import json
import os
import configparser
from playwright.async_api import async_playwright
from datetime import datetime

class MediumGmailOAuthTest:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.credentials = {}
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "captcha_detected": False,
            "captcha_type": None,
            "login_successful": False,
            "log": []
        }

    def _log(self, msg):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        self.results["log"].append(log_msg)

    def load_credentials(self):
        """Load credentials"""
        self._log("Loading Gmail credentials...")
        config = configparser.ConfigParser()
        config.read('credentials.properties')
        if 'gmail' in config:
            self.credentials = dict(config['gmail'])
            self._log(f"✅ Loaded: {self.credentials.get('email')}")
            return True
        return False

    async def start_browser(self):
        """Start browser"""
        self._log("Starting browser...")
        p = await async_playwright().start()

        try:
            self.browser = await p.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            self._log("✅ Browser started")
            return True
        except Exception as e:
            self._log(f"❌ Error: {str(e)[:100]}")
            return False

    async def detect_captcha(self):
        """Detect if CAPTCHA is present"""
        try:
            page_text = await self.page.inner_text('body')
            url = self.page.url

            # Check for Cloudflare challenge indicators
            if "just a moment" in page_text.lower():
                self._log("🔴 DETECTED: Cloudflare 'Just a moment' challenge")
                self.results["captcha_detected"] = True
                self.results["captcha_type"] = "cloudflare_challenge"
                return True

            if "verifying you are human" in page_text.lower():
                self._log("🔴 DETECTED: 'Verifying you are human' message")
                self.results["captcha_detected"] = True
                self.results["captcha_type"] = "verification"
                return True

            # Check for CAPTCHA iframe
            cf_iframe = await self.page.query_selector('iframe[src*="challenges.cloudflare.com"]')
            if cf_iframe:
                self._log("🔴 DETECTED: Cloudflare Turnstile iframe")
                self.results["captcha_detected"] = True
                self.results["captcha_type"] = "turnstile_iframe"
                return True

            # Check for "I'm not a robot" button
            robot_btn = await self.page.query_selector('input[type="checkbox"]')
            if robot_btn and "robot" in page_text.lower():
                self._log("🔴 DETECTED: 'I'm not a robot' checkbox")
                self.results["captcha_detected"] = True
                self.results["captcha_type"] = "robot_checkbox"
                return True

            return False
        except Exception as e:
            self._log(f"⚠️  Error detecting CAPTCHA: {str(e)[:50]}")
            return False

    async def take_screenshot(self, name):
        """Take screenshot"""
        path = f"/tmp/medium_gmail_oauth_{name}_{datetime.now().strftime('%H%M%S')}.png"
        await self.page.screenshot(path=path)
        self._log(f"📸 Screenshot: {path}")
        return path

    async def run_test(self):
        """Run the test"""
        self._log("\n" + "="*70)
        self._log("MEDIUM LOGIN VIA GMAIL OAUTH - CAPTCHA TEST")
        self._log("="*70)

        if not self.load_credentials():
            return False

        if not await self.start_browser():
            return False

        # Step 1: Navigate to Medium homepage
        self._log("\n📍 Step 1: Navigate to medium.com")
        await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(2)
        await self.take_screenshot("01_homepage")

        # Check for CAPTCHA on homepage
        if await self.detect_captcha():
            self._log("   ⚠️  CAPTCHA on homepage (unexpected)")

        # Step 2: Look for Google sign-in button on homepage
        self._log("\n📍 Step 2: Find Google sign-in button on homepage")
        try:
            # Try different selectors for Google button
            google_btn = None

            # Try button with Google text
            google_btn = await self.page.query_selector("button:has-text('Google')")
            if not google_btn:
                google_btn = await self.page.query_selector("a:has-text('Google')")
            if not google_btn:
                google_btn = await self.page.query_selector("[role='button']:has-text('Google')")

            if google_btn:
                self._log("   ✓ Found Google button")
                await self.take_screenshot("02_before_google_click")
                await google_btn.click()
                self._log("   ✓ Clicked Google button")
                await asyncio.sleep(3)
                await self.take_screenshot("03_after_google_click")
            else:
                # Look for any button/link that might be Google OAuth
                all_buttons = await self.page.query_selector_all("button, a")
                self._log(f"   ⚠️  No 'Google' button found. Available buttons: {len(all_buttons)}")
                for btn in all_buttons[:5]:
                    text = await btn.inner_text()
                    if text.strip():
                        self._log(f"      - {text[:50]}")
        except Exception as e:
            self._log(f"   ❌ Error: {str(e)[:50]}")

        # Step 3: Monitor for CAPTCHA
        self._log("\n📍 Step 3: Monitoring for CAPTCHA during OAuth...")
        for i in range(20):
            if await self.detect_captcha():
                self._log(f"   CAPTCHA found at {i}s")
                await self.take_screenshot("04_captcha_detected")
                break

            await asyncio.sleep(1)

        # Step 4: Fill Gmail credentials if still on Google page
        self._log("\n📍 Step 4: Filling Gmail credentials")
        url = self.page.url
        self._log(f"   Current URL: {url}")

        if "accounts.google.com" in url:
            try:
                # Fill email
                email_input = await self.page.query_selector("input[type='email']")
                if email_input:
                    email = self.credentials.get('email', '')
                    await email_input.fill(email)
                    self._log(f"   ✓ Filled email: {email}")

                    # Click Next
                    next_btn = await self.page.query_selector("button:has-text('Next')")
                    if next_btn:
                        await next_btn.click()
                        self._log("   ✓ Clicked Next")
                        await asyncio.sleep(3)
                        await self.take_screenshot("05_after_email_next")
            except Exception as e:
                self._log(f"   ⚠️  Error filling email: {str(e)[:50]}")

        # Step 5: Check for password page
        self._log("\n📍 Step 5: Filling password")
        url = self.page.url
        if "accounts.google.com" in url:
            try:
                password_input = await self.page.query_selector("input[type='password']")
                if password_input:
                    password = self.credentials.get('password', '')
                    await password_input.fill(password)
                    self._log(f"   ✓ Filled password")

                    next_btn = await self.page.query_selector("button:has-text('Next')")
                    if next_btn:
                        await next_btn.click()
                        self._log("   ✓ Clicked Next")
                        await asyncio.sleep(5)
                        await self.take_screenshot("06_after_password")
            except Exception as e:
                self._log(f"   ⚠️  Error filling password: {str(e)[:50]}")

        # Step 6: Wait for 2FA or completion
        self._log("\n📍 Step 6: Waiting for 2FA approval or page completion...")
        self._log("   (Check your Gmail app for 2FA prompt)")
        for i in range(30):
            # Check if CAPTCHA appears
            if await self.detect_captcha():
                await self.take_screenshot("07_captcha_in_oauth_flow")
                break

            # Check if we're past Google (redirected to Medium)
            url = self.page.url
            if "medium.com" in url and "accounts.google.com" not in url:
                self._log(f"   ✓ Redirected to Medium: {url}")
                self.results["login_successful"] = True
                await self.take_screenshot("08_medium_after_oauth")
                break

            await asyncio.sleep(1)
            if i % 5 == 0:
                self._log(f"   Waiting... ({i}s)")

        # Final state
        self._log("\n📍 Step 7: Final state check")
        html = await self.page.content()
        url = self.page.url

        self._log(f"   Final URL: {url}")
        self._log(f"   Page size: {len(html)} bytes")

        if "medium" in html.lower() and len(html) > 50000:
            self._log("   ✅ Medium content detected")
            self.results["login_successful"] = True

        if self.results["captcha_detected"]:
            self._log(f"   🔴 CAPTCHA was detected: {self.results['captcha_type']}")

        return True

    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def print_summary(self):
        """Print summary"""
        self._log("\n" + "="*70)
        self._log("TEST RESULTS")
        self._log("="*70)
        self._log(f"CAPTCHA Detected: {self.results['captcha_detected']}")
        if self.results['captcha_detected']:
            self._log(f"   Type: {self.results['captcha_type']}")
        self._log(f"Login Successful: {self.results['login_successful']}")

        # Save results
        with open('/tmp/medium_gmail_oauth_test.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        self._log(f"\n💾 Saved to: /tmp/medium_gmail_oauth_test.json")

async def main():
    test = MediumGmailOAuthTest()
    try:
        await test.run_test()
        test.print_summary()
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await test.close()

if __name__ == "__main__":
    asyncio.run(main())
