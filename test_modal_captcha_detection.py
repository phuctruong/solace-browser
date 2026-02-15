#!/usr/bin/env python3
"""
Test the new Modal + CAPTCHA Detection in Solace Browser
Shows the LLM exactly what's blocking the flow
"""
import asyncio
import json
import configparser
from playwright.async_api import async_playwright
from datetime import datetime

class ModalCaptchaTest:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None

    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

    async def perceive_with_detection(self, description=""):
        """
        Use BOTH html-clean AND detect-modals to give LLM full picture
        """
        if description:
            self._log(f"\n🧠 {description}")

        self._log("  Step 1: Get page structure (HTML)...")
        html = await self.page.content()

        self._log("  Step 2: Explicitly detect modals/CAPTCHAs...")
        detection = await self.page.evaluate("""
        () => {
            const detections = {
                cloudflare_challenge: document.body.innerText.includes('Verify you are human'),
                cloudflare_turnstile: !!document.querySelector('iframe[src*="challenges.cloudflare.com"]'),
                cloudflare_verifying: document.body.innerText.toLowerCase().includes('just a moment'),
                checkbox_visible: !!document.querySelector('input[type="checkbox"]'),
                page_text_sample: document.body.innerText.substring(0, 300)
            };
            return detections;
        }
        """)

        title = await self.page.title()
        url = self.page.url

        self._log(f"\n  📊 Perception Report:")
        self._log(f"     URL: {url}")
        self._log(f"     Title: {title}")
        self._log(f"     Page size: {len(html)} bytes")
        self._log(f"     Cloudflare Challenge Text: {detection['cloudflare_challenge']}")
        self._log(f"     Cloudflare Turnstile iframe: {detection['cloudflare_turnstile']}")
        self._log(f"     'Just a moment' text: {detection['cloudflare_verifying']}")
        self._log(f"     Checkbox element visible: {detection['checkbox_visible']}")

        return {
            "url": url,
            "title": title,
            "html_size": len(html),
            "detection": detection,
            "page_text_sample": detection['page_text_sample']
        }

    async def run(self):
        """Run the test"""
        self._log("\n" + "="*70)
        self._log("SOLACE BROWSER: Modal + CAPTCHA Detection Test")
        self._log("="*70)

        # Load credentials
        config = configparser.ConfigParser()
        config.read('credentials.properties')
        credentials = dict(config['gmail']) if 'gmail' in config else {}
        self._log(f"\n✅ Credentials: {credentials.get('email', 'N/A')}")

        # Start browser
        self._log("\n🚀 Starting browser...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        self._log("✅ Browser ready\n")

        try:
            # Step 1: Navigate to Medium
            self._log("STEP 1: Navigate to medium.com")
            await self.page.goto("https://medium.com", wait_until='domcontentloaded')
            await asyncio.sleep(1)
            perception1 = await self.perceive_with_detection("Perceive: Medium homepage")

            # Step 2: Click Sign In
            self._log("\n\nSTEP 2: Click 'Sign in'")
            await self.page.click("a:has-text('Sign in')")
            await asyncio.sleep(2)
            perception2 = await self.perceive_with_detection("Perceive: After clicking Sign in")

            # Step 3: Click Google
            self._log("\n\nSTEP 3: Click 'Sign in with Google'")
            try:
                await self.page.click("a:has-text('Sign in with Google')")
                await asyncio.sleep(3)
            except Exception as e:
                self._log(f"  ⚠️  Click timeout: {str(e)[:50]}")

            perception3 = await self.perceive_with_detection(
                "Perceive: After clicking Google (CAPTCHA should be here)"
            )

            # Key question: Can we see the Cloudflare challenge?
            self._log("\n\n" + "="*70)
            self._log("🔍 CRITICAL ANALYSIS")
            self._log("="*70)

            if perception3['detection']['cloudflare_challenge']:
                self._log("\n✅ LLM CAN SEE: Cloudflare 'Verify you are human' text")
                self._log("   → This means the modal is visible in the page content")

            if perception3['detection']['cloudflare_turnstile']:
                self._log("\n✅ LLM CAN SEE: Cloudflare Turnstile iframe")
                self._log("   → This means we detected the iframe element")

            if perception3['detection']['checkbox_visible']:
                self._log("\n✅ LLM CAN SEE: Checkbox element on page")
                self._log("   → The input[type='checkbox'] is in the DOM")

            if perception3['detection']['cloudflare_verifying']:
                self._log("\n✅ LLM CAN SEE: 'Just a moment...' text")
                self._log("   → Cloudflare is performing verification")

            # Page text sample
            if "verify" in perception3['page_text_sample'].lower():
                self._log("\n✅ LLM CAN UNDERSTAND: Verification language in page text")
                self._log(f"   Sample: {perception3['page_text_sample'][:200]}")

            # What should happen next
            self._log("\n\n" + "="*70)
            self._log("💡 NEXT ACTIONS FOR LLM")
            self._log("="*70)

            if perception3['detection']['cloudflare_challenge']:
                self._log("\n1. ✅ LLM detected the challenge")
                self._log("2. ✅ LLM should try to click the checkbox")
                self._log("3. ✅ LLM should wait for verification")
                self._log("4. ✅ LLM should verify success and continue")

                # Try to click the checkbox
                self._log("\n\n🔴 ATTEMPTING TO CLICK CHECKBOX...")
                try:
                    # Try multiple selector strategies
                    selectors = [
                        'input[type="checkbox"]',
                        '.cf-turnstile input[type="checkbox"]',
                        'input[aria-label*="not a robot"]'
                    ]

                    clicked = False
                    for selector in selectors:
                        try:
                            elem = await self.page.query_selector(selector)
                            if elem:
                                self._log(f"   Found element with: {selector}")
                                await elem.click()
                                self._log(f"   ✅ Clicked!")
                                clicked = True
                                await asyncio.sleep(2)
                                break
                        except:
                            pass

                    if not clicked:
                        self._log("   ❌ Could not click checkbox (may be in iframe/shadow DOM)")
                        self._log("   ℹ️  Waiting for manual click...")

                    # Wait a bit
                    for i in range(10):
                        await asyncio.sleep(1)
                        perception_current = await self.perceive_with_detection(f"Wait {i}s...")
                        new_title = await self.page.title()

                        # Check if we got past the challenge
                        if "just a moment" not in new_title.lower():
                            self._log(f"\n✅ Challenge page title changed!")
                            break

                except Exception as e:
                    self._log(f"   ❌ Error: {str(e)[:100]}")

            # Final state
            self._log("\n\n" + "="*70)
            self._log("📊 FINAL STATE")
            self._log("="*70)

            final_perception = await self.perceive_with_detection("Final state")
            await self.page.screenshot(path="/tmp/modal_captcha_test_final.png")
            self._log(f"\n📸 Final screenshot: /tmp/modal_captcha_test_final.png")

            self._log("\n\n" + "="*70)
            self._log("✅ BROWSER KEPT OPEN FOR LIVE INTERACTION")
            self._log("="*70)
            self._log("\n🔗 Browser is still running - you can interact with it!")
            self._log("   The page is waiting for your input.")
            self._log("   I can query the browser to see what you did.\n")

            # Keep browser open - don't close it!
            await asyncio.sleep(300)  # Wait 5 minutes for user interaction

        except KeyboardInterrupt:
            self._log("\n\n⏹️  Interrupted by user (Ctrl+C)")
        except Exception as e:
            self._log(f"\n\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            # Only close if explicitly interrupted
            try:
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
            except:
                pass

async def main():
    test = ModalCaptchaTest()
    await test.run()

if __name__ == "__main__":
    asyncio.run(main())
