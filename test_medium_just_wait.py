#!/usr/bin/env python3
"""
Test Medium - Just Wait Strategy
=================================
Theory: In headed mode, Cloudflare might auto-complete the challenge
        if it detects human presence (visible browser).

Strategy: Don't try to click - just WAIT for Cloudflare to complete
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumJustWaitTest:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "page_loaded": False,
            "challenge_completed": False,
            "content_found": False,
            "cf_clearance_obtained": False,
            "wait_time": 0,
            "success": False
        }

    async def start(self):
        """Start headed browser"""
        print("🖥️  Starting HEADED browser...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        print("✅ Browser started\n")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def run_test(self):
        """Navigate to Medium and just wait"""
        print("=" * 70)
        print("MEDIUM - JUST WAIT STRATEGY")
        print("Let Cloudflare auto-complete when it detects visible browser")
        print("=" * 70)

        print("\n🌐 Navigate to medium.com...")
        try:
            response = await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
            print(f"✅ Page loaded (status: {response.status})")
            self.results["page_loaded"] = True
        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            self.results["page_loaded"] = False
            return

        # Take initial screenshot
        await self.page.screenshot(path="/tmp/medium_wait_initial.png")
        print("📸 Initial screenshot: /tmp/medium_wait_initial.png")

        print("\n⏳ Waiting for Cloudflare to complete challenge...")
        print("   (Monitoring page content every 2 seconds)\n")

        # Wait up to 60 seconds for challenge to complete
        max_wait = 60
        wait_interval = 2

        for elapsed in range(0, max_wait, wait_interval):
            # Get current page content
            html = await self.page.content()
            content_size = len(html)

            # Check for success indicators
            has_challenge = "Just a moment" in html or "challenge" in html.lower()
            has_content = content_size > 50000  # Real Medium has lots of content
            has_articles = "<article" in html or "medium" in html.lower()

            status = f"{elapsed}s"
            if has_challenge:
                status += " [challenge] "
            else:
                status += " [no challenge] "

            status += f"({content_size} bytes)"

            print(f"   {status}")

            # Check if challenge completed
            if not has_challenge and has_content:
                print(f"\n✅ Challenge completed!")
                print(f"   Time taken: {elapsed} seconds")
                print(f"   Content size: {content_size} bytes")
                self.results["challenge_completed"] = True
                self.results["wait_time"] = elapsed
                break

            await asyncio.sleep(wait_interval)

        # Take final screenshot
        await self.page.screenshot(path="/tmp/medium_wait_final.png")
        print("\n📸 Final screenshot: /tmp/medium_wait_final.png")

        # Check final state
        html = await self.page.content()

        if "Just a moment" not in html and len(html) > 50000:
            print("\n✅ Medium content is accessible!")
            self.results["content_found"] = True

            # Check for cookies
            cookies = await self.context.cookies()
            print(f"\n📊 Cookies obtained: {len(cookies)}")

            cf_cookie = [c for c in cookies if c['name'] == 'cf_clearance']
            if cf_cookie:
                print(f"   ✅ cf_clearance cookie found!")
                self.results["cf_clearance_obtained"] = True

                # Save cookies
                with open('/tmp/medium_cookies_just_wait.json', 'w') as f:
                    json.dump(cookies, f, indent=2)
                print(f"   💾 Cookies saved to /tmp/medium_cookies_just_wait.json")

                self.results["success"] = True

        else:
            print("\n⚠️  Challenge still present or content not loaded")
            if "Just a moment" in html:
                print("   'Just a moment' page still visible")
            else:
                print(f"   Content size: {len(html)} bytes (expected > 50000)")

        # Save results
        with open('/tmp/medium_just_wait_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Page Loaded: {self.results['page_loaded']}")
        print(f"Challenge Completed: {self.results['challenge_completed']}")
        print(f"Content Found: {self.results['content_found']}")
        print(f"CF_Clearance: {self.results['cf_clearance_obtained']}")
        print(f"Wait Time: {self.results['wait_time']}s")
        print(f"SUCCESS: {self.results['success']}")

async def main():
    tester = MediumJustWaitTest()
    await tester.start()

    try:
        await tester.run_test()
    finally:
        await tester.stop()

if __name__ == "__main__":
    asyncio.run(main())
