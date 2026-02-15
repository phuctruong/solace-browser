#!/usr/bin/env python3
"""
Test Medium with Session Cookie + CAPTCHA Click
================================================
Goal: Reuse Gmail session, navigate to Medium, click "I'm not a robot" button
Test if this allows headless access on next attempt
"""
import asyncio
import json
import os
from playwright.async_api import async_playwright
from datetime import datetime

class MediumCaptchaTest:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "success": False,
            "cf_clearance_obtained": False,
            "captcha_clicked": False
        }

    async def start(self):
        """Start headed browser"""
        print("🖥️  Starting HEADED browser...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)  # HEADED - visible
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        print("✅ Browser started in HEADED mode\n")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def navigate_medium(self):
        """Navigate to Medium homepage"""
        print("=" * 70)
        print("STEP 1: Navigate to Medium")
        print("=" * 70)

        print("\n📱 Navigating to medium.com...")
        try:
            await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
            print("✅ Page loaded")
            self.results["steps"].append({"step": 1, "action": "navigate", "success": True})
            return True
        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            self.results["steps"].append({"step": 1, "action": "navigate", "success": False, "error": str(e)[:100]})
            return False

    async def check_for_captcha(self):
        """Check for CAPTCHA button and click it"""
        print("\n" + "=" * 70)
        print("STEP 2: Look for CAPTCHA/Human Verification")
        print("=" * 70)

        await asyncio.sleep(2)

        try:
            # Take screenshot to see what we're dealing with
            screenshot_path = "/tmp/medium_before_captcha.png"
            await self.page.screenshot(path=screenshot_path)
            print(f"\n📸 Screenshot: {screenshot_path}")

            # Look for various CAPTCHA button patterns
            captcha_selectors = [
                "input[type='checkbox']",  # "I'm not a robot"
                "iframe[src*='recaptcha']",  # reCAPTCHA frame
                "iframe[src*='cloudflare']",  # Cloudflare challenge frame
                "button:has-text('Verify')",  # Generic verify button
                "button:has-text('I am human')",  # Human verification button
                "button:has-text('Continue')",  # Continue button
                "[data-testid*='captcha']",  # Test id
                "[role='button']:has-text('not')",  # "I'm not a robot"
                "div.cf-turnstile",  # Cloudflare Turnstile container
            ]

            print("\n🔍 Searching for CAPTCHA button...")

            for selector in captcha_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        print(f"  ✓ Found: {selector} ({len(elements)} element(s))")

                        # Try to interact with it
                        if len(elements) > 0:
                            elem = elements[0]
                            print(f"    → Attempting to click...")

                            try:
                                # Wait for element to be visible
                                await self.page.wait_for_selector(selector, timeout=3000)
                                await elem.click()
                                print(f"    ✅ Clicked!")
                                self.results["captcha_clicked"] = True
                                self.results["steps"].append({
                                    "step": 2,
                                    "action": "click_captcha",
                                    "selector": selector,
                                    "success": True
                                })
                                return True
                            except Exception as click_err:
                                print(f"    ⚠️  Click failed: {str(click_err)[:50]}")

                except Exception as e:
                    pass

            print("\n⚠️  No obvious CAPTCHA button found")
            print("   Checking page content...")

            # Get page content to analyze
            html = await self.page.content()
            if "challenge" in html.lower():
                print("   ✓ Challenge content detected")
            if "turnstile" in html.lower():
                print("   ✓ Turnstile detected")
            if "not a robot" in html.lower():
                print("   ✓ 'Not a robot' text detected")

            # Try generic iframe click (sometimes CAPTCHA is in iframe)
            try:
                iframes = await self.page.query_selector_all("iframe")
                print(f"\n   Found {len(iframes)} iframes - checking for interactive elements...")

                for i, iframe in enumerate(iframes[:3]):
                    try:
                        # Try to access iframe content
                        frame = await iframe.content_frame()
                        if frame:
                            print(f"     → Iframe {i}: accessible")
                            # Look for clickable elements in iframe
                            buttons = await frame.query_selector_all("button, input[type='checkbox']")
                            if buttons:
                                print(f"       ✓ Found {len(buttons)} buttons in iframe")
                                await buttons[0].click()
                                print(f"       ✅ Clicked button in iframe!")
                                self.results["captcha_clicked"] = True
                                return True
                    except:
                        pass

            except Exception as e:
                print(f"   ⚠️  Iframe check error: {str(e)[:50]}")

            self.results["steps"].append({
                "step": 2,
                "action": "find_captcha",
                "success": False,
                "note": "No CAPTCHA button found - page may have loaded or challenge completed"
            })
            return False

        except Exception as e:
            print(f"❌ Error during CAPTCHA check: {str(e)[:100]}")
            self.results["steps"].append({
                "step": 2,
                "action": "check_captcha",
                "success": False,
                "error": str(e)[:100]
            })
            return False

    async def verify_access(self):
        """Verify if we got access to Medium content"""
        print("\n" + "=" * 70)
        print("STEP 3: Verify Access to Medium Content")
        print("=" * 70)

        await asyncio.sleep(3)

        try:
            # Take final screenshot
            screenshot_path = "/tmp/medium_after_captcha.png"
            await self.page.screenshot(path=screenshot_path)
            print(f"\n📸 Screenshot: {screenshot_path}")

            # Check for Medium content
            html = await self.page.content()

            success_indicators = [
                ("'Inbox'", "inbox" in html.lower()),
                ("'Stories'", "stories" in html.lower()),
                ("'Trending'", "trending" in html.lower()),
                ("Article elements", "article" in html.lower()),
                ("Medium UI", "medium" in html.lower())
            ]

            print("\n🔍 Checking for Medium content...")
            content_found = 0
            for indicator_name, found in success_indicators:
                if found:
                    print(f"  ✓ {indicator_name}")
                    content_found += 1
                else:
                    print(f"  ✗ {indicator_name}")

            # Check if challenge page still present
            if "Just a moment" in html:
                print("\n⚠️  Still on Cloudflare challenge page")
                self.results["steps"].append({
                    "step": 3,
                    "action": "verify",
                    "success": False,
                    "note": "Still on challenge page"
                })
                return False

            if content_found >= 2:
                print("\n✅ Medium content loaded!")
                self.results["steps"].append({
                    "step": 3,
                    "action": "verify",
                    "success": True,
                    "indicators_found": content_found
                })
                self.results["success"] = True
                return True
            else:
                print("\n⚠️  Uncertain - mixed results")
                self.results["steps"].append({
                    "step": 3,
                    "action": "verify",
                    "success": False,
                    "note": "Content unclear"
                })
                return False

        except Exception as e:
            print(f"❌ Error during verification: {str(e)[:100]}")
            self.results["steps"].append({
                "step": 3,
                "action": "verify",
                "success": False,
                "error": str(e)[:100]
            })
            return False

    async def check_cookies(self):
        """Check what cookies we have"""
        print("\n" + "=" * 70)
        print("STEP 4: Check for cf_clearance Cookie")
        print("=" * 70)

        try:
            cookies = await self.context.cookies()
            print(f"\n📊 Total cookies: {len(cookies)}")

            cf_cookies = [c for c in cookies if 'cf' in c['name'].lower()]
            print(f"   Cloudflare cookies: {len(cf_cookies)}")

            for c in cf_cookies:
                print(f"   • {c['name']}: {c['value'][:30]}...")
                if c['name'] == 'cf_clearance':
                    self.results["cf_clearance_obtained"] = True
                    print(f"     ✅ CF_CLEARANCE FOUND!")

            # Save all cookies
            with open('/tmp/medium_cookies_after_captcha.json', 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"\n✅ Cookies saved: /tmp/medium_cookies_after_captcha.json")

        except Exception as e:
            print(f"❌ Error checking cookies: {str(e)[:100]}")

    async def run_test(self):
        """Run the complete test"""
        print("\n" + "█" * 70)
        print("MEDIUM + CLOUDFLARE CAPTCHA TEST")
        print("Test: Can we click CAPTCHA and get cf_clearance cookie?")
        print("█" * 70)

        try:
            # Step 1: Navigate
            if not await self.navigate_medium():
                print("\n❌ Failed to navigate")
                return

            # Step 2: Find and click CAPTCHA
            await self.check_for_captcha()

            # Step 3: Verify access
            await self.verify_access()

            # Step 4: Check cookies
            await self.check_cookies()

        finally:
            # Save results
            with open('/tmp/medium_captcha_test_results.json', 'w') as f:
                json.dump(self.results, f, indent=2)

            print("\n" + "=" * 70)
            print("✅ TEST COMPLETE")
            print("=" * 70)
            print(f"\n📊 Results saved: /tmp/medium_captcha_test_results.json")
            print(f"\n📈 Summary:")
            print(f"   Navigation: {self.results['steps'][0]['success'] if self.results['steps'] else '?'}")
            print(f"   CAPTCHA Found: {self.results['captcha_clicked']}")
            print(f"   CF_Clearance: {self.results['cf_clearance_obtained']}")
            print(f"   Overall Success: {self.results['success']}")

async def main():
    tester = MediumCaptchaTest()
    await tester.start()

    try:
        await tester.run_test()
    finally:
        await tester.stop()

if __name__ == "__main__":
    asyncio.run(main())
