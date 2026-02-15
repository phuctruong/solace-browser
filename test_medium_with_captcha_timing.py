#!/usr/bin/env python3
"""
Test Medium with Proper CAPTCHA Timing
======================================
Strategy: Wait for "I'm not a robot" button to be CLICKABLE, then click
Key: Don't click immediately - wait for the button to be ready
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumCaptchaTimingTest:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "captcha_detected": False,
            "captcha_clicked": False,
            "challenge_passed": False,
            "content_loaded": False,
            "cf_clearance_obtained": False,
            "success": False,
            "steps": []
        }

    async def start(self):
        """Start headed browser"""
        print("🖥️  Starting HEADED browser...")
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

    async def navigate_medium(self):
        """Navigate to Medium"""
        print("=" * 70)
        print("STEP 1: Navigate to Medium")
        print("=" * 70)

        print("\n🌐 Going to medium.com...")
        try:
            await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
            print("✅ Page loaded")
            self.results["steps"].append({"step": 1, "action": "navigate", "success": True})
            return True
        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            self.results["steps"].append({"step": 1, "action": "navigate", "success": False})
            return False

    async def find_and_click_captcha(self):
        """Find the 'I'm not a robot' button and click it with proper timing"""
        print("\n" + "=" * 70)
        print("STEP 2: Find and Click 'I'm Not a Robot' Button")
        print("=" * 70)

        print("\n⏳ Waiting for CAPTCHA to appear...")

        try:
            # Wait up to 10 seconds for the checkbox to appear
            print("   Waiting for 'I'm not a robot' checkbox...")

            # The reCAPTCHA checkbox selector
            checkbox_selector = "iframe[title*='reCAPTCHA']"

            # Wait for the iframe to appear
            try:
                await self.page.wait_for_selector(checkbox_selector, timeout=10000)
                print("   ✅ reCAPTCHA iframe detected")
                self.results["captcha_detected"] = True
            except:
                print("   ⏳ Trying alternative selectors...")

                # Try alternative selectors
                alt_selectors = [
                    "iframe[src*='recaptcha']",
                    "[data-testid*='captcha']",
                    "input[type='checkbox']",
                    "div.g-recaptcha",
                ]

                found = False
                for selector in alt_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        if elements:
                            print(f"   ✅ Found: {selector}")
                            self.results["captcha_detected"] = True
                            found = True
                            break
                    except:
                        pass

                if not found:
                    # Maybe the page loaded without captcha?
                    html = await self.page.content()
                    if "Just a moment" in html:
                        print("   ⚠️  'Just a moment' page detected - challenge might be ongoing")
                    else:
                        print("   ℹ️  No obvious CAPTCHA detected - page might have loaded")
                    self.results["steps"].append({
                        "step": 2,
                        "action": "find_captcha",
                        "success": False,
                        "note": "CAPTCHA not found"
                    })
                    return False

            # Now wait for the clickable element within the iframe
            print("\n   ⏳ Waiting for CAPTCHA to be clickable (this can take a moment)...")

            # Try to find and click the checkbox
            await asyncio.sleep(2)  # Initial wait for page to settle

            # Method 1: Try clicking reCAPTCHA checkbox directly
            try:
                print("   → Attempting to click checkbox...")

                # Look for the actual clickable area
                recaptcha_selectors = [
                    ".recaptcha-checkbox-border",
                    ".goog-inline-block.recaptcha-checkbox",
                    "div.g-recaptcha-bubble-div",
                    "[role='presentation'] input",
                ]

                for selector in recaptcha_selectors:
                    try:
                        elem = await self.page.query_selector(selector)
                        if elem:
                            await elem.click(timeout=5000)
                            print(f"   ✅ Clicked: {selector}")
                            self.results["captcha_clicked"] = True
                            break
                    except:
                        pass

                if not self.results["captcha_clicked"]:
                    # Try clicking on the iframe itself
                    iframe = await self.page.query_selector("iframe[title*='reCAPTCHA']")
                    if iframe:
                        print("   → Clicking reCAPTCHA iframe...")
                        await iframe.click(timeout=5000)
                        print("   ✅ Clicked iframe")
                        self.results["captcha_clicked"] = True

            except Exception as e:
                print(f"   ⚠️  Click error: {str(e)[:80]}")

            # If we haven't clicked yet, try using keyboard
            if not self.results["captcha_clicked"]:
                print("   → Trying keyboard interaction...")
                try:
                    await self.page.press("Tab")
                    await self.page.press("Space")
                    print("   ✅ Used keyboard to interact")
                    self.results["captcha_clicked"] = True
                except:
                    pass

            # Wait for challenge to complete
            if self.results["captcha_clicked"]:
                print("\n   ⏳ Waiting for challenge to complete (20 seconds)...")

                for i in range(20):
                    html = await self.page.content()

                    # Check if challenge passed
                    if "Just a moment" not in html and len(html) > 50000:
                        print(f"   ✅ Challenge passed! (after {i}s)")
                        self.results["challenge_passed"] = True
                        break

                    await asyncio.sleep(1)
                    if i % 5 == 0 and i > 0:
                        print(f"      ... still waiting ({i}s)")

            self.results["steps"].append({
                "step": 2,
                "action": "click_captcha",
                "success": self.results["captcha_clicked"],
                "challenge_passed": self.results["challenge_passed"]
            })

            return self.results["challenge_passed"]

        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            self.results["steps"].append({
                "step": 2,
                "action": "click_captcha",
                "success": False,
                "error": str(e)[:100]
            })
            return False

    async def verify_access(self):
        """Verify we can access Medium content"""
        print("\n" + "=" * 70)
        print("STEP 3: Verify Access to Medium Content")
        print("=" * 70)

        print("\n🔍 Checking for Medium content...")

        try:
            html = await self.page.content()

            # Take screenshot
            await self.page.screenshot(path="/tmp/medium_captcha_success.png")
            print("📸 Screenshot: /tmp/medium_captcha_success.png")

            # Check for content indicators
            indicators = [
                ("Articles", "article" in html),
                ("Stories", "stories" in html.lower()),
                ("Medium UI", "medium" in html.lower()),
                ("Navigation", "<nav" in html),
            ]

            found = 0
            for name, result in indicators:
                if result:
                    print(f"   ✅ {name} found")
                    found += 1
                else:
                    print(f"   ❌ {name} not found")

            if found >= 2:
                print(f"\n✅ Medium content accessible!")
                self.results["content_loaded"] = True
                return True
            else:
                print(f"\n⚠️  Limited content (only {found}/4 indicators)")
                return False

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

    async def check_cookies(self):
        """Check for cf_clearance cookie"""
        print("\n" + "=" * 70)
        print("STEP 4: Check for cf_clearance Cookie")
        print("=" * 70)

        try:
            cookies = await self.context.cookies()
            print(f"\n📊 Total cookies: {len(cookies)}")

            cf_cookie = [c for c in cookies if c['name'] == 'cf_clearance']
            if cf_cookie:
                c = cf_cookie[0]
                print(f"\n✅ CF_CLEARANCE FOUND!")
                print(f"   Value: {c['value'][:50]}...")
                print(f"   Expires: {c['expires']}")
                self.results["cf_clearance_obtained"] = True

                # Save cookies for future use
                with open('/tmp/medium_cookies_with_captcha_success.json', 'w') as f:
                    json.dump(cookies, f, indent=2)
                print(f"\n💾 Cookies saved: /tmp/medium_cookies_with_captcha_success.json")

                return True
            else:
                print("\n⚠️  cf_clearance not found")
                return False

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

    async def run_test(self):
        """Run complete test"""
        print("\n" + "█" * 70)
        print("MEDIUM CAPTCHA TEST - PROPER TIMING")
        print("Testing: Wait → Click → Verify")
        print("█" * 70)

        try:
            if not await self.navigate_medium():
                return

            if await self.find_and_click_captcha():
                await self.verify_access()
                await self.check_cookies()

                if self.results["content_loaded"] and self.results["cf_clearance_obtained"]:
                    self.results["success"] = True

        finally:
            with open('/tmp/medium_captcha_timing_results.json', 'w') as f:
                json.dump(self.results, f, indent=2)

            print("\n" + "=" * 70)
            print("TEST COMPLETE")
            print("=" * 70)
            print(f"\n📊 Summary:")
            print(f"   CAPTCHA Detected: {self.results['captcha_detected']}")
            print(f"   CAPTCHA Clicked: {self.results['captcha_clicked']}")
            print(f"   Challenge Passed: {self.results['challenge_passed']}")
            print(f"   Content Loaded: {self.results['content_loaded']}")
            print(f"   CF_Clearance: {self.results['cf_clearance_obtained']}")
            print(f"   OVERALL SUCCESS: {self.results['success']}")

async def main():
    tester = MediumCaptchaTimingTest()
    await tester.start()

    try:
        await tester.run_test()
    finally:
        await tester.stop()

if __name__ == "__main__":
    asyncio.run(main())
