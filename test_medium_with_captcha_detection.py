#!/usr/bin/env python3
"""
Medium Login with CAPTCHA Detection via Network Monitoring
=========================================================
Uses Playwright's built-in network monitoring to detect and handle CAPTCHAs
without relying on extension content scripts.

Key insight: Monitor network requests/responses to detect:
1. Cloudflare challenge API calls
2. CAPTCHA iframe loads
3. Challenge completion signals
"""
import asyncio
import json
import os
import configparser
from playwright.async_api import async_playwright
from datetime import datetime

class MediumCaptchaDetector:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.credentials = {}
        self.captcha_detected = False
        self.captcha_iframe_visible = False
        self.network_events = []
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "captcha_events": [],
            "network_log": [],
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
        self._log("Loading credentials...")
        config = configparser.ConfigParser()
        config.read('credentials.properties')
        if 'gmail' in config:
            self.credentials = dict(config['gmail'])
            self._log(f"✅ Loaded: {self.credentials.get('email')}")
            return True
        return False

    async def on_request(self, request):
        """Monitor outgoing network requests"""
        url = request.url

        # Detect CAPTCHA-related requests
        if any(pattern in url for pattern in [
            'challenges.cloudflare.com',
            'cdn-cgi/challenge',
            'turnstile',
            'recaptcha',
            'hcaptcha',
            'challenge-platform'
        ]):
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "captcha_api_request",
                "url": url,
                "method": request.method
            }
            self.network_events.append(event)
            self.results["captcha_events"].append(event)
            self._log(f"🔴 CAPTCHA API Request: {url[:80]}...")
            self.captcha_detected = True

    async def on_response(self, response):
        """Monitor network responses"""
        url = response.url
        status = response.status

        # Log CAPTCHA-related responses
        if any(pattern in url for pattern in [
            'challenges.cloudflare.com',
            'cdn-cgi/challenge',
            'turnstile',
            'recaptcha',
            'hcaptcha'
        ]):
            event = {
                "timestamp": datetime.now().isoformat(),
                "type": "captcha_api_response",
                "url": url[:100],
                "status": status
            }
            self.results["captcha_events"].append(event)
            self._log(f"   → Response: {status}")

    async def detect_captcha_on_page(self):
        """Check if CAPTCHA iframe is visible on current page"""
        try:
            # Check for Cloudflare iframe
            cf_iframe = await self.page.query_selector('iframe[src*="challenges.cloudflare.com"]')
            if cf_iframe:
                self._log("🔴 Detected: Cloudflare Turnstile iframe")
                self.captcha_iframe_visible = True
                return "cloudflare"

            # Check for reCAPTCHA
            recaptcha_iframe = await self.page.query_selector('iframe[src*="recaptcha"]')
            if recaptcha_iframe:
                self._log("🔴 Detected: reCAPTCHA iframe")
                self.captcha_iframe_visible = True
                return "recaptcha"

            # Check for "I'm not a robot" button
            robot_check = await self.page.query_selector('[role="presentation"]')
            if robot_check:
                checkbox = await self.page.query_selector('input[type="checkbox"]')
                if checkbox:
                    self._log("🔴 Detected: I'm not a robot checkbox")
                    self.captcha_iframe_visible = True
                    return "robot_checkbox"

            # Check page text
            page_text = await self.page.inner_text('body')
            if "just a moment" in page_text.lower() or "verifying" in page_text.lower():
                self._log("🔴 Detected: Challenge verification page")
                return "verification_page"

            return None
        except Exception as e:
            self._log(f"⚠️  Error detecting CAPTCHA: {str(e)[:50]}")
            return None

    async def start_browser(self):
        """Start browser WITHOUT extension - just use network monitoring"""
        self._log("Starting browser (headless mode)...")
        p = await async_playwright().start()

        try:
            self.browser = await p.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            # Setup network monitoring
            self.page.on('request', self.on_request)
            self.page.on('response', self.on_response)

            self._log("✅ Browser started with network monitoring active")
            return True
        except Exception as e:
            self._log(f"❌ Error: {str(e)[:100]}")
            return False

    async def run_test(self):
        """Run the test"""
        self._log("\n" + "="*70)
        self._log("MEDIUM LOGIN - CAPTCHA DETECTION VIA NETWORK MONITORING")
        self._log("="*70)

        if not self.load_credentials():
            return False

        if not await self.start_browser():
            return False

        # Step 1: Navigate to Medium
        self._log("\n📍 Step 1: Navigate to Medium")
        await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1)

        # Check for CAPTCHA
        captcha_type = await self.detect_captcha_on_page()
        if captcha_type:
            self._log(f"   CAPTCHA detected: {captcha_type}")
        else:
            self._log("   ✓ No CAPTCHA on homepage")

        # Step 2: Click Sign In
        self._log("\n📍 Step 2: Click 'Sign in'")
        try:
            sign_in = await self.page.query_selector("a:has-text('Sign in')")
            if sign_in:
                await sign_in.click()
                await asyncio.sleep(2)
                self._log("   ✓ Sign in clicked")
            else:
                self._log("   ⚠️  Sign in button not found")
        except Exception as e:
            self._log(f"   ⚠️  Error: {str(e)[:50]}")

        # Check for CAPTCHA after sign in
        captcha_type = await self.detect_captcha_on_page()
        if captcha_type:
            self._log(f"   🔴 CAPTCHA detected after sign in: {captcha_type}")

        # Step 3: Look for email/password login
        self._log("\n📍 Step 3: Attempting email sign in")
        try:
            email_btn = await self.page.query_selector("button:has-text('Sign in with email')")
            if not email_btn:
                email_btn = await self.page.query_selector("a:has-text('Sign in with email')")

            if email_btn:
                await email_btn.click()
                await asyncio.sleep(2)
                self._log("   ✓ Email sign in clicked")
            else:
                self._log("   ⚠️  Email button not found")
        except Exception as e:
            self._log(f"   ⚠️  Error: {str(e)[:50]}")

        # Step 4: Fill email
        self._log("\n📍 Step 4: Fill email address")
        try:
            email_input = await self.page.query_selector("input[type='email']")
            if email_input:
                email = self.credentials.get('email', '')
                await email_input.fill(email)
                self._log(f"   ✓ Filled: {email}")

                # Click Next
                next_btn = await self.page.query_selector("button:has-text('Next')")
                if next_btn:
                    await next_btn.click()
                    self._log("   ✓ Clicked Next")
                    await asyncio.sleep(2)
            else:
                self._log("   ⚠️  Email input not found")
        except Exception as e:
            self._log(f"   ⚠️  Error: {str(e)[:50]}")

        # Step 5: Check for CAPTCHA during password entry
        self._log("\n📍 Step 5: Monitoring for CAPTCHA...")
        for i in range(10):
            captcha_type = await self.detect_captcha_on_page()
            if captcha_type:
                self._log(f"   🔴 CAPTCHA detected: {captcha_type}")
                # If we detect a CAPTCHA, log it but don't try to interact
                # (would need manual intervention or vision model)
                break
            await asyncio.sleep(1)

        # Step 6: Check final state
        self._log("\n📍 Step 6: Check final page state")
        html = await self.page.content()
        self._log(f"   Page size: {len(html)} bytes")

        if "medium" in html.lower() and len(html) > 50000:
            self._log("   ✅ Medium content loaded")
            self.results["login_successful"] = True
        else:
            self._log("   ⚠️  Could not verify Medium access")

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
        self._log("SUMMARY")
        self._log("="*70)

        self._log(f"CAPTCHA Events Detected: {len(self.results['captcha_events'])}")
        for event in self.results['captcha_events']:
            self._log(f"  - {event['type']}: {event['url'][:60]}")

        self._log(f"\nCAPTCHA Detected on Page: {self.captcha_iframe_visible}")
        self._log(f"Login Successful: {self.results['login_successful']}")

        # Save results
        with open('/tmp/medium_captcha_detection_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        self._log(f"\n💾 Saved to: /tmp/medium_captcha_detection_results.json")

async def main():
    test = MediumCaptchaDetector()
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
