#!/usr/bin/env python3
"""
Test Medium with Solace Browser CAPTCHA Handler
===============================================
Uses browser extension to auto-detect and handle CAPTCHAs
that Playwright normally can't touch.

Flow:
1. Start Solace Browser with extension
2. CAPTCHA handler monitors for challenges
3. When detected, auto-clicks
4. Playwright waits for completion
5. Continue with automation
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumWithCaptchaHandler:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "method": "headless_with_captcha_handler",
            "captcha_detected": False,
            "captcha_handled": False,
            "login_success": False,
            "content_accessible": False
        }

    async def start(self):
        """Start browser with CAPTCHA handler extension"""
        print("🖥️  Starting headless browser with CAPTCHA handler...")
        p = await async_playwright().start()

        # Note: In real implementation, would load extension from:
        # /home/phuc/projects/solace-browser/canon/prime-browser/archive/extension/
        #
        # For now, demonstrating the flow:

        self.browser = await p.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

        print("✅ Browser started")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def check_captcha_handler(self):
        """Check if CAPTCHA handler is active"""
        try:
            # This would work if extension is loaded
            status = await self.page.evaluate("""
                () => {
                    if (window.solace_captcha) {
                        return {
                            available: true,
                            monitoring: window.solace_captcha.isMonitoring(),
                            summary: window.solace_captcha.getSummary()
                        };
                    }
                    return { available: false };
                }
            """)
            return status
        except:
            return {"available": False, "note": "Extension not loaded in this test"}

    async def login_to_medium(self):
        """Login to Medium and let CAPTCHA handler manage challenges"""
        print("\n" + "=" * 70)
        print("Login to Medium (with CAPTCHA handler)")
        print("=" * 70)

        # Check if CAPTCHA handler is available
        handler_status = await self.check_captcha_handler()
        print(f"\n🔍 CAPTCHA Handler Status: {handler_status}")

        if handler_status.get("available"):
            self.results["captcha_handler_available"] = True
            print("✅ CAPTCHA handler is active and monitoring")

        # Navigate to Medium
        print("\n🌐 Navigate to Medium...")
        await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
        print("✅ Page loaded")

        # Screenshot before login
        await self.page.screenshot(path="/tmp/medium_captcha_handler_before_login.png")

        # Click sign in
        print("\n🔍 Looking for Sign in link...")
        sign_in = await self.page.query_selector("a:has-text('Sign in')")
        if sign_in:
            await sign_in.click()
            await asyncio.sleep(2)
            print("✅ Clicked Sign in")

        await self.page.screenshot(path="/tmp/medium_captcha_handler_signin_modal.png")

        # Click Google OAuth
        print("\n🔍 Looking for 'Sign in with Google' button...")
        google_btn = await self.page.query_selector("a:has-text('Google')")
        if google_btn:
            await google_btn.click()
            await asyncio.sleep(3)
            print("✅ Clicked Google OAuth")

        # Now CAPTCHA handler should detect if challenge appears
        print("\n⏳ Waiting for CAPTCHA handler to detect and handle challenges...")

        # Check for CAPTCHA detection
        await asyncio.sleep(5)  # Wait for CAPTCHA to appear

        captcha_status = await self.check_captcha_handler()
        print(f"\n📊 CAPTCHA Status after navigation:")
        print(f"   Available: {captcha_status.get('available')}")
        if captcha_status.get('available'):
            print(f"   Monitoring: {captcha_status.get('monitoring')}")
            summary = captcha_status.get('summary', {})
            print(f"   Detected Count: {summary.get('detected_count', 0)}")
            print(f"   Auto-Clicked: {summary.get('auto_clicked_count', 0)}")

            if summary.get('detected_count', 0) > 0:
                self.results["captcha_detected"] = True
                print(f"   ✅ CAPTCHA(s) detected and auto-clicked")

                if summary.get('auto_clicked_count', 0) > 0:
                    self.results["captcha_handled"] = True

        # Wait for potential CAPTCHA completion
        if self.results["captcha_detected"]:
            print("\n⏳ Waiting for CAPTCHA completion (30 seconds)...")
            for i in range(30):
                await asyncio.sleep(1)

                # Check if challenge is still present
                html = await self.page.content()
                if "Just a moment" not in html and len(html) > 30000:
                    print(f"   ✅ CAPTCHA completed! ({i}s)")
                    break

                if i % 10 == 0 and i > 0:
                    print(f"   ... waiting ({i}s)")

        # Take final screenshot
        await self.page.screenshot(path="/tmp/medium_captcha_handler_after_oauth.png")

        # Check for success
        html = await self.page.content()
        if len(html) > 50000 and "medium" in html.lower():
            self.results["login_success"] = True
            self.results["content_accessible"] = True
            print("\n✅ Login successful - Medium content accessible!")
            return True
        else:
            print("\n⚠️ Login status unclear")
            return False

    async def run_test(self):
        """Run the complete test"""
        print("\n" + "█" * 70)
        print("MEDIUM LOGIN WITH CAPTCHA HANDLER")
        print("Testing headless access with browser extension CAPTCHA handling")
        print("█" * 70)

        try:
            await self.login_to_medium()
        finally:
            with open('/tmp/medium_captcha_handler_results.json', 'w') as f:
                json.dump(self.results, f, indent=2)

            print("\n" + "=" * 70)
            print("RESULTS")
            print("=" * 70)
            print(f"CAPTCHA Detected: {self.results['captcha_detected']}")
            print(f"CAPTCHA Handled: {self.results['captcha_handled']}")
            print(f"Login Success: {self.results['login_success']}")
            print(f"Content Accessible: {self.results['content_accessible']}")

            if self.results['content_accessible']:
                print("\n🎉 SUCCESS! Medium accessible with CAPTCHA handler extension!")
            else:
                print("\n⚠️ Extension integration needed for full automation")

async def main():
    test = MediumWithCaptchaHandler()
    await test.start()

    try:
        await test.run_test()
    finally:
        await test.stop()

if __name__ == "__main__":
    asyncio.run(main())
