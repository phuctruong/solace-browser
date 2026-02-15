#!/usr/bin/env python3

"""
Interactive Browser Session - OpenClaw Style
The LLM (me) can see the page, reason, and decide actions in real-time
"""

import asyncio
import json
import logging
from pathlib import Path
from playwright.async_api import async_playwright
from dataclasses import asdict

from browser_interactions import format_aria_tree, get_dom_snapshot
from enhanced_browser_interactions import (
    AriaRefMapper,
    PageObserver,
    NetworkMonitor,
    get_llm_snapshot
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('interactive')


class InteractiveBrowser:
    """Interactive browser that exposes page state for LLM analysis"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.ref_mapper = None
        self.observer = None
        self.network = None

    async def start(self, headless=False, session_file="artifacts/linkedin_session.json"):
        """Start browser with optional session"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        context_options = {}
        if Path(session_file).exists():
            context_options['storage_state'] = session_file
            logger.info(f"Loaded session: {session_file}")

        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

        # Setup monitoring
        self.observer = PageObserver(self.page)
        self.network = NetworkMonitor(self.page)

        logger.info("✅ Browser ready")
        return self.page

    async def goto(self, url):
        """Navigate to URL"""
        logger.info(f"→ Navigating to: {url}")
        await self.page.goto(url, wait_until='networkidle')
        await asyncio.sleep(1)
        logger.info(f"✅ Loaded: {self.page.url}")

    async def see(self):
        """
        SEE the current page state (like OpenClaw does)
        Returns structured snapshot for LLM analysis
        """
        logger.info("👁️  Getting page snapshot...")

        # Get ARIA tree
        aria_tree = await format_aria_tree(self.page, limit=500)
        dom_tree = await get_dom_snapshot(self.page, limit=800)

        # Build ref mapper
        self.ref_mapper = AriaRefMapper()
        await self.ref_mapper.build_map(self.page, [asdict(node) for node in aria_tree])

        # Get comprehensive snapshot
        snapshot = await get_llm_snapshot(
            self.page,
            [asdict(node) for node in aria_tree],
            dom_tree,
            self.observer,
            self.network
        )

        logger.info(f"✅ Snapshot ready: {len(aria_tree)} ARIA nodes, {len(dom_tree)} DOM nodes")

        return snapshot

    async def show_interactive_elements(self, snapshot):
        """Show what interactive elements are visible"""
        print("\n" + "="*80)
        print("🔍 INTERACTIVE ELEMENTS ON PAGE")
        print("="*80)

        buttons = []
        textboxes = []
        links = []

        for node in snapshot['aria']:
            role = (node.get('role') or '').lower()
            name = (node.get('name') or '').lower()
            ref = node.get('ref')

            if role == 'button':
                buttons.append(f"{ref:6s} | {name}")
            elif role == 'textbox':
                textboxes.append(f"{ref:6s} | {name}")
            elif role == 'link' and name:  # Only links with names
                links.append(f"{ref:6s} | {name}")

        if buttons:
            print(f"\n📌 BUTTONS ({len(buttons)}):")
            for b in buttons[:20]:  # Show first 20
                print(f"  {b}")

        if textboxes:
            print(f"\n📝 TEXTBOXES ({len(textboxes)}):")
            for t in textboxes[:10]:  # Show first 10
                print(f"  {t}")

        if links:
            print(f"\n🔗 LINKS ({len(links)}):")
            for l in links[:10]:  # Show first 10
                print(f"  {l}")

        print("\n" + "="*80)

    async def click(self, selector):
        """Click element by CSS selector"""
        logger.info(f"🖱️  Clicking: {selector}")
        await self.page.click(selector)
        await asyncio.sleep(1)
        logger.info("✅ Clicked")

    async def fill(self, selector, text):
        """Fill text into field"""
        logger.info(f"⌨️  Filling: {selector}")
        await self.page.fill(selector, text)
        await asyncio.sleep(0.5)
        logger.info("✅ Filled")

    async def screenshot(self, path="screenshot.png"):
        """Take screenshot"""
        await self.page.screenshot(path=path)
        logger.info(f"📸 Screenshot: {path}")

    async def wait(self, seconds=2):
        """Wait and observe"""
        logger.info(f"⏳ Waiting {seconds}s...")
        await asyncio.sleep(seconds)

    async def save_session(self, path="artifacts/linkedin_session.json"):
        """Save session"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        await self.context.storage_state(path=path)
        logger.info(f"💾 Session saved: {path}")

    async def stop(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
            logger.info("🛑 Browser closed")


# Interactive REPL-style usage
async def interactive_session():
    """
    Interactive session - LLM can see and react
    """
    browser = InteractiveBrowser()
    await browser.start(headless=False)

    print("\n" + "="*80)
    print("🎮 INTERACTIVE BROWSER SESSION")
    print("="*80)
    print("\nI can now:")
    print("  1. See the page (get ARIA snapshot)")
    print("  2. Reason about what to do")
    print("  3. Execute actions")
    print("  4. See results")
    print("  5. Decide next step")
    print("\n" + "="*80)

    # Navigate to LinkedIn
    await browser.goto("https://www.linkedin.com/in/phuctruong/")

    # SEE the page
    snapshot = await browser.see()

    # SHOW what I see
    await browser.show_interactive_elements(snapshot)

    print("\n📊 PAGE STATE:")
    print(f"  URL: {snapshot['url']}")
    print(f"  Title: {snapshot['title']}")
    print(f"  ARIA nodes: {snapshot['stats']['ariaNodes']}")
    print(f"  Console messages: {snapshot['stats']['consoleMessages']}")
    print(f"  Has errors: {snapshot['hasErrors']}")

    # Now return the browser and snapshot for interactive use
    return browser, snapshot


if __name__ == "__main__":
    # Run interactive session
    browser, snapshot = asyncio.run(interactive_session())

    # Browser is now ready for interactive commands
    # You can save the browser object and call:
    # - await browser.see() - to get current page state
    # - await browser.click(selector) - to click
    # - await browser.fill(selector, text) - to type
    # - etc.
