#!/usr/bin/env python3
"""
Live LLM Browser Discovery in Action: Medium OAuth + Cloudflare CAPTCHA

Demonstrates the PERCEIVE → UNDERSTAND → ACT → VERIFY loop
"""
import asyncio
import configparser
from playwright.async_api import async_playwright
from datetime import datetime

class LiveBrowserDiscovery:
    """LLM-driven browser automation using real-time perception"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.credentials = {}
        self.history = []

    def _log(self, msg, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "THINK": "🧠", "ACT": "⚡", "VERIFY": "🔍", "ERROR": "❌"}[level]
        log_msg = f"[{timestamp}] {emoji} {msg}"
        print(log_msg)
        self.history.append(log_msg)

    async def perceive(self):
        """DREAM: Perceive current browser state"""
        self._log("Perceiving current state...", "THINK")

        try:
            url = self.page.url
            title = await self.page.title()
            html = await self.page.content()

            # Extract key information
            perception = {
                "url": url,
                "title": title,
                "page_length": len(html),
                "is_loading": "just a moment" in html.lower(),
                "is_cloudflare": "cloudflare" in html.lower(),
                "has_checkbox": 'type="checkbox"' in html,
                "visible_text": await self.page.inner_text('body')[:500]
            }

            self._log(f"URL: {url}", "VERIFY")
            self._log(f"Title: {title}", "VERIFY")
            self._log(f"Cloudflare challenge: {perception['is_cloudflare']}", "VERIFY")
            self._log(f"Has checkbox: {perception['has_checkbox']}", "VERIFY")

            return perception

        except Exception as e:
            self._log(f"Perception error: {str(e)}", "ERROR")
            return None

    async def understand(self, perception):
        """FORECAST: LLM analyzes perception and decides next action"""
        self._log("Analyzing situation...", "THINK")

        if perception is None:
            return None

        # This is where LLM reasoning would happen
        # For now, we implement rule-based logic as demo
        if perception['is_cloudflare']:
            if perception['has_checkbox']:
                self._log("Detected: Cloudflare challenge with checkbox", "THINK")
                return {
                    "action": "click",
                    "target": "checkbox",
                    "selector": "input[type='checkbox']",
                    "reason": "Need to verify we're human"
                }
            elif "just a moment" in perception['title'].lower():
                self._log("Detected: Cloudflare verification in progress", "THINK")
                return {
                    "action": "wait",
                    "duration": 3,
                    "reason": "Cloudflare verifying..."
                }

        if "accounts.google" in perception['url']:
            self._log("Detected: Google login page", "THINK")
            return {
                "action": "fill_email",
                "selector": "input[type='email']",
                "reason": "Need to enter Gmail"
            }

        self._log("No specific action determined, continuing...", "THINK")
        return {"action": "wait", "duration": 2, "reason": "Page state unclear"}

    async def act(self, decision):
        """ACT: Execute the decision"""
        if decision is None:
            return None

        self._log(f"Executing: {decision['action']}", "ACT")

        try:
            if decision['action'] == "click":
                self._log(f"Clicking: {decision['selector']}", "ACT")
                await self.page.click(decision['selector'])
                await asyncio.sleep(2)
                self._log("Click successful", "SUCCESS")

            elif decision['action'] == "wait":
                self._log(f"Waiting {decision['duration']}s...", "ACT")
                await asyncio.sleep(decision['duration'])

            elif decision['action'] == "fill_email":
                email = self.credentials.get('email', '')
                self._log(f"Filling email: {email}", "ACT")
                await self.page.fill(decision['selector'], email)
                await asyncio.sleep(1)

                # Click Next
                try:
                    next_btn = await self.page.query_selector("button:has-text('Next')")
                    if next_btn:
                        await next_btn.click()
                        self._log("Clicked Next", "SUCCESS")
                except:
                    pass

            return True

        except Exception as e:
            self._log(f"Action failed: {str(e)}", "ERROR")
            return False

    async def verify(self, action_taken):
        """VERIFY: Check if action had desired effect"""
        self._log("Verifying result...", "VERIFY")

        if action_taken:
            await asyncio.sleep(1)
            new_perception = await self.perceive()
            return new_perception
        return None

    async def loop(self, goal, max_iterations=20):
        """Main PERCEIVE → UNDERSTAND → ACT → VERIFY loop"""
        self._log(f"Starting discovery loop: {goal}", "INFO")
        self._log("="*70, "INFO")

        for iteration in range(max_iterations):
            self._log(f"\n--- Iteration {iteration + 1} ---", "INFO")

            # DREAM: Perceive
            perception = await self.perceive()
            if perception is None:
                break

            # Check success condition
            if perception['url'].startswith('https://medium.com') and not perception['is_cloudflare']:
                self._log(f"🎉 GOAL ACHIEVED: Logged in to Medium", "SUCCESS")
                return True

            if "accounts.google" in perception['url']:
                self._log("Reached Google login - continuing with credentials...", "SUCCESS")
                # In real scenario, would wait for 2FA

            # FORECAST: Understand
            decision = await self.understand(perception)
            if decision is None:
                break

            # ACT: Execute
            action_result = await self.act(decision)

            # VERIFY: Feedback
            new_perception = await self.verify(action_result)

        self._log("\n" + "="*70, "INFO")
        self._log("Discovery loop completed", "INFO")
        return False

    async def run(self):
        """Execute the full Medium OAuth flow"""
        self._log("\n" + "="*70, "INFO")
        self._log("LIVE LLM BROWSER DISCOVERY - MEDIUM OAUTH WITH CLOUDFLARE", "INFO")
        self._log("="*70, "INFO")

        # Load credentials
        config = configparser.ConfigParser()
        config.read('credentials.properties')
        if 'gmail' in config:
            self.credentials = dict(config['gmail'])
            self._log(f"Loaded credentials: {self.credentials['email']}", "SUCCESS")

        # Start browser
        self._log("\nStarting clean browser (no extensions)...", "INFO")
        p = await async_playwright().start()

        try:
            self.browser = await p.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            self._log("Browser ready", "SUCCESS")

            # Navigate to Medium
            self._log("\nNavigating to medium.com...", "INFO")
            await self.page.goto("https://medium.com", wait_until='domcontentloaded')
            await asyncio.sleep(2)

            # Click Sign In
            self._log("\nClicking Sign In...", "INFO")
            await self.page.click("a:has-text('Sign in')")
            await asyncio.sleep(2)

            # Click Google
            self._log("\nClicking 'Sign in with Google'...", "INFO")
            await self.page.click("a:has-text('Sign in with Google')")
            await asyncio.sleep(3)

            # Now use the live discovery loop to handle Cloudflare
            self._log("\nEntering live discovery mode for Cloudflare...", "INFO")
            success = await self.loop(
                "Handle Cloudflare CAPTCHA and complete Medium OAuth"
            )

            if success:
                self._log("\n🎉 MISSION ACCOMPLISHED", "SUCCESS")
            else:
                self._log("\n⚠️  Discovery loop completed", "INFO")

            # Final screenshot
            await self.page.screenshot(path="/tmp/live_discovery_final.png")
            self._log(f"\nFinal screenshot: /tmp/live_discovery_final.png", "INFO")

            self._log("\n" + "="*70, "INFO")
            self._log("✅ BROWSER KEPT OPEN", "SUCCESS")
            self._log("="*70, "INFO")
            self._log("\n🔗 Browser is still running - interact with it now!")
            self._log("   I can query it to see what you did.\n", "INFO")

            # Keep browser open for user interaction
            await asyncio.sleep(600)  # Wait 10 minutes

        except KeyboardInterrupt:
            self._log("\n⏹️  Interrupted (Ctrl+C)", "INFO")
        except Exception as e:
            self._log(f"Error: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()

        finally:
            try:
                if self.context:
                    await self.context.close()
                if self.browser:
                    await self.browser.close()
            except:
                pass

async def main():
    discovery = LiveBrowserDiscovery()
    await discovery.run()

if __name__ == "__main__":
    asyncio.run(main())
