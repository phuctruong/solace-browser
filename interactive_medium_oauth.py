#!/usr/bin/env python3
"""
Interactive Medium OAuth Flow - Browser Stays Open
Navigate to the challenge and keep browser open for you to interact
"""
import asyncio
import configparser
from playwright.async_api import async_playwright
from datetime import datetime

class InteractiveMediumOAuth:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    async def run(self):
        """Navigate to Medium OAuth and wait for user interaction"""
        self._log("\n" + "="*70)
        self._log("INTERACTIVE MEDIUM OAUTH - BROWSER STAYS OPEN")
        self._log("="*70)

        # Load credentials
        config = configparser.ConfigParser()
        config.read('credentials.properties')
        credentials = dict(config['gmail']) if 'gmail' in config else {}
        self._log(f"\n✅ Credentials loaded: {credentials.get('email', 'N/A')}")

        # Start browser
        self._log("\n🚀 Starting browser...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self._log("✅ Browser started\n")

        try:
            # Step 1: Medium homepage
            self._log("📍 Step 1: Navigate to medium.com")
            await self.page.goto("https://medium.com", wait_until='domcontentloaded')
            await asyncio.sleep(1)
            self._log(f"   ✓ URL: {self.page.url}\n")

            # Step 2: Click Sign In
            self._log("📍 Step 2: Click 'Sign in'")
            await self.page.click("a:has-text('Sign in')")
            await asyncio.sleep(2)
            self._log(f"   ✓ Modal opened\n")

            # Step 3: Click Google
            self._log("📍 Step 3: Click 'Sign in with Google'")
            await self.page.click("a:has-text('Sign in with Google')")
            await asyncio.sleep(3)
            self._log(f"   ✓ Redirected\n")

            # Check current state
            url = self.page.url
            title = await self.page.title()
            html = await self.page.content()

            self._log("📊 CURRENT STATE:")
            self._log(f"   URL: {url}")
            self._log(f"   Title: {title}")
            self._log(f"   Page size: {len(html)} bytes")

            # Detect what's on screen
            detection = await self.page.evaluate("""
            () => ({
                has_verify_text: document.body.innerText.includes('Verify you are human'),
                has_checkbox: !!document.querySelector('input[type="checkbox"]'),
                has_just_moment: document.body.innerText.toLowerCase().includes('just a moment'),
                page_text_sample: document.body.innerText.substring(0, 300)
            })
            """)

            self._log("\n🔍 DETECTION:")
            self._log(f"   'Verify you are human' text: {detection['has_verify_text']}")
            self._log(f"   Checkbox element: {detection['has_checkbox']}")
            self._log(f"   'Just a moment' text: {detection['has_just_moment']}")

            # Screenshot
            await self.page.screenshot(path="/tmp/interactive_medium_current.png")
            self._log(f"\n📸 Screenshot saved: /tmp/interactive_medium_current.png")

            # Now wait for user interaction
            self._log("\n" + "="*70)
            self._log("🔗 BROWSER IS OPEN - WAITING FOR YOUR INTERACTION")
            self._log("="*70)
            self._log("\n✨ You can now:")
            self._log("   1. Click the 'I'm not a robot' checkbox in the browser")
            self._log("   2. Complete any other interactions")
            self._log("   3. I will detect what changed")
            self._log("\n⏳ Waiting... (Press Ctrl+C to stop)\n")

            # Wait for user to interact
            for i in range(600):  # 10 minutes
                await asyncio.sleep(1)
                if i % 30 == 0:
                    self._log(f"   {i}s elapsed...")

        except KeyboardInterrupt:
            self._log("\n\n⏹️  Stopped by user")
        except Exception as e:
            self._log(f"\n\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()

        finally:
            # Ask if user wants to keep browser open
            self._log("\n\n" + "="*70)
            response = input("Close browser? (y/n): ")
            if response.lower() == 'y':
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
                self._log("✅ Browser closed")
            else:
                self._log("✅ Browser kept open")

async def main():
    test = InteractiveMediumOAuth()
    await test.run()

if __name__ == "__main__":
    asyncio.run(main())
