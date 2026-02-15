#!/usr/bin/env python3
"""
Debug Selector Inspector
Navigate to HackerNews and Reddit, inspect actual selectors
"""
import asyncio
from playwright.async_api import async_playwright

async def inspect_hackernews():
    """Inspect HackerNews voting element structure"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)  # Use headed mode to see what's happening
    context = await browser.new_context()
    page = await context.new_page()

    try:
        print("\n" + "="*80)
        print("🔍 INSPECTING HACKERNEWS VOTING ELEMENTS")
        print("="*80)

        await page.goto("https://news.ycombinator.com/", wait_until='domcontentloaded')
        await asyncio.sleep(2)

        print("\n1. Finding story rows...")
        stories = await page.query_selector_all('.athing')
        print(f"   Found {len(stories)} stories")

        if stories:
            # Inspect first story's voting area
            print("\n2. Inspecting first story's voting structure...")
            story = stories[0]

            # Get HTML of the story row
            html = await story.inner_html()
            print(f"\n   Story HTML preview: {html[:500]}...")

            # Look for votearrow elements
            votearrows = await story.query_selector_all('.votearrow')
            print(f"\n3. Found {len(votearrows)} votearrow elements in first story")

            if votearrows:
                # Try clicking first votearrow
                print("\n4. Attempting to click first votearrow...")
                await votearrows[0].click(timeout=5000)
                await asyncio.sleep(1)
                print("   ✅ First click succeeded")

                # Now try to find and click again
                print("\n5. Looking for votearrow after first click...")
                votearrows_after = await story.query_selector_all('.votearrow')
                print(f"   Found {len(votearrows_after)} votearrow elements after first click")

                if votearrows_after:
                    print("\n6. Attempting second click...")
                    try:
                        await votearrows_after[0].click(timeout=5000)
                        print("   ✅ Second click succeeded")
                    except Exception as e:
                        print(f"   ❌ Second click failed: {e}")
                        # Get current HTML to see what changed
                        current_html = await votearrows_after[0].outer_html()
                        print(f"   Element after first click: {current_html}")
                else:
                    print("   ❌ No votearrow found after first click")

    finally:
        await context.close()
        await browser.close()

async def inspect_reddit():
    """Inspect Reddit voting element structure"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)  # Headed mode
    context = await browser.new_context()
    page = await context.new_page()

    try:
        print("\n" + "="*80)
        print("🔍 INSPECTING REDDIT VOTING ELEMENTS")
        print("="*80)

        await page.goto("https://reddit.com/", wait_until='domcontentloaded')
        await asyncio.sleep(3)

        print("\n1. Looking for vote containers...")

        # Try multiple selector patterns
        selectors = [
            "button[aria-label*='upvote' i]",
            "[data-testid='vote-arrows-container']",
            "button[aria-label*='Upvote' i]",
            "div[data-testid='post']",
            "button:has-text('Upvote')",
        ]

        for selector in selectors:
            print(f"\n2. Trying selector: {selector}")
            try:
                elements = await page.query_selector_all(selector)
                print(f"   ✅ Found {len(elements)} elements")

                if elements and len(elements) > 0:
                    html = await elements[0].outer_html()
                    print(f"   First element: {html[:300]}...")

            except Exception as e:
                print(f"   ❌ Selector failed: {e}")

        print("\n3. Trying alternate approach - get all buttons...")
        buttons = await page.query_selector_all('button')
        print(f"   Found {len(buttons)} total buttons")

        # Look for buttons with vote-related attributes
        upvote_buttons = []
        for btn in buttons[:20]:  # Check first 20 buttons
            try:
                aria_label = await btn.get_attribute('aria-label')
                title = await btn.get_attribute('title')
                if aria_label and 'vote' in aria_label.lower():
                    upvote_buttons.append(('aria-label', aria_label))
                    print(f"   Found upvote button: aria-label='{aria_label}'")
                if title and 'vote' in title.lower():
                    upvote_buttons.append(('title', title))
                    print(f"   Found vote button: title='{title}'")
            except:
                pass

        if upvote_buttons:
            print(f"\n4. Found {len(upvote_buttons)} potential vote buttons")
            # Try to click the first one
            print("\n5. Attempting to click first vote button...")
            try:
                await buttons[0].click(timeout=5000)
                print("   ✅ Click succeeded")
            except Exception as e:
                print(f"   ❌ Click failed: {e}")

    finally:
        await context.close()
        await browser.close()

async def main():
    print("\n" + "█"*80)
    print("SELECTOR DEBUG TOOL")
    print("Inspecting actual page structures in HEADED mode")
    print("█"*80)

    # Uncomment to debug
    # await inspect_hackernews()
    # await inspect_reddit()

    print("\n⚠️  This tool uses headed mode to debug selectors")
    print("    Run individually to see browser behavior")
    print("\n    To use:")
    print("    1. Uncomment inspect_hackernews() in main()")
    print("    2. Run: python3 debug_selectors.py")
    print("    3. Watch the browser and note what works/fails")

if __name__ == "__main__":
    asyncio.run(main())
