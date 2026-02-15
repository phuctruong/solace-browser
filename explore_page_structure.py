#!/usr/bin/env python3
"""
Deep Page Structure Explorer
Navigate to sites and output full structure for selector discovery
"""
import asyncio
from playwright.async_api import async_playwright

async def explore_hackernews():
    """Explore HackerNews page structure"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        print("\n" + "="*80)
        print("🔍 HACKERNEWS STRUCTURE EXPLORATION")
        print("="*80)

        await page.goto("https://news.ycombinator.com/", wait_until='domcontentloaded')
        await asyncio.sleep(1)

        # Click into first story
        stories = await page.query_selector_all('span.titleline a')
        if stories:
            print(f"\nFound {len(stories)} story titles")
            print(f"Clicking first story...")
            await stories[0].click()
            await asyncio.sleep(2)

            # Now explore the voting area
            print("\nExploring voting area...")

            # Get the votearrow element
            votearrows = await page.query_selector_all('.votearrow')
            print(f"Found {len(votearrows)} votearrow elements")

            if votearrows:
                # Click first votearrow
                print("\nClicking first votearrow...")
                await votearrows[0].click()
                await asyncio.sleep(1)

                # Check votearrows again
                votearrows_after = await page.query_selector_all('.votearrow')
                print(f"After click: {len(votearrows_after)} votearrow elements")

                # Get HTML of the votearrow area
                if votearrows_after:
                    html = await votearrows_after[0].outer_html()
                    print(f"\nFirst votearrow HTML after click:")
                    print(f"{html}")

                # Try to find a toggle action
                print("\nLooking for alternative selectors...")
                selectors = [
                    ".votearrow",
                    "div.votearrow",
                    "a.votearrow",
                    "[class*='vote']",
                ]
                for sel in selectors:
                    count = len(await page.query_selector_all(sel))
                    print(f"  {sel}: {count} elements")

    finally:
        await context.close()
        await browser.close()

async def explore_reddit():
    """Explore Reddit page structure in detail"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        print("\n" + "="*80)
        print("🔍 REDDIT STRUCTURE EXPLORATION")
        print("="*80)

        await page.goto("https://reddit.com/", wait_until='domcontentloaded')
        await asyncio.sleep(3)

        # Check what's on the page
        print("\nExploring Reddit homepage...")

        # Get HTML of first post area
        posts = await page.query_selector_all('[role="article"]')
        print(f"Found {len(posts)} elements with role='article'")

        if posts:
            print(f"\nFirst post structure:")
            html = await posts[0].inner_html()
            print(f"{html[:1000]}...")

        # Look for buttons
        print(f"\nSearching for vote-related buttons...")
        buttons = await page.query_selector_all('button')
        print(f"Found {len(buttons)} total buttons")

        # Check each button for vote-related attributes
        vote_buttons = []
        for i, btn in enumerate(buttons[:30]):
            try:
                aria = await btn.get_attribute('aria-label')
                title = await btn.get_attribute('title')
                data_testid = await btn.get_attribute('data-testid')
                classes = await btn.get_attribute('class')

                is_vote = False
                if aria and any(x in aria.lower() for x in ['vote', 'upvote', 'downvote']):
                    is_vote = True
                if title and any(x in title.lower() for x in ['vote', 'upvote', 'downvote']):
                    is_vote = True

                if is_vote:
                    vote_buttons.append({
                        'index': i,
                        'aria-label': aria,
                        'title': title,
                        'data-testid': data_testid,
                        'class': classes
                    })
                    print(f"\n  Button {i}:")
                    print(f"    aria-label: {aria}")
                    print(f"    title: {title}")
                    print(f"    data-testid: {data_testid}")
                    print(f"    class: {classes}")
            except:
                pass

        if not vote_buttons:
            print(f"\nNo vote buttons found with vote/upvote/downvote in attributes")
            print(f"Trying to find SVG-based vote buttons...")

            # Look for SVGs that might be vote controls
            svgs = await page.query_selector_all('svg')
            print(f"Found {len(svgs)} SVG elements")

            # Try to find parent containers with vote semantics
            print(f"\nLooking for container patterns...")
            selectors_to_try = [
                "[data-testid*='vote']",
                "[class*='vote']",
                "div[class*='Arrow']",
                "button[class*='upvote' i]",
                "button[class*='Arrow' i]",
                "[class*='UpvoteButton']",
            ]

            for sel in selectors_to_try:
                try:
                    count = len(await page.query_selector_all(sel))
                    if count > 0:
                        print(f"  ✅ {sel}: {count} elements found")
                except:
                    pass

    finally:
        await context.close()
        await browser.close()

async def main():
    await explore_hackernews()
    await explore_reddit()

if __name__ == "__main__":
    asyncio.run(main())
