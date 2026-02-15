#!/usr/bin/env python3
"""
Check what actually loads on the pages
"""
import asyncio
from playwright.async_api import async_playwright

async def check_page(url: str, name: str):
    """Check what loads at a URL"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        print(f"\n{'='*80}")
        print(f"Checking: {name}")
        print(f"{'='*80}")

        print(f"Navigating to {url}...")
        response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        print(f"Response status: {response.status if response else 'No response'}")

        # Wait a bit for JS to load
        await asyncio.sleep(2)

        # Get current URL (check for redirects)
        current_url = page.url
        print(f"Final URL: {current_url}")

        # Get page title
        title = await page.title()
        print(f"Page title: {title}")

        # Get HTML size
        html = await page.content()
        print(f"HTML size: {len(html)} bytes")

        # Check if page is blank
        if len(html) < 500:
            print(f"\n⚠️  Page seems very small!")
            print(f"HTML content:\n{html}")
        else:
            # Show first 500 chars
            print(f"\nFirst 500 chars of HTML:")
            print(html[:500])
            print(f"...")

        # Check for common blocking messages
        if 'blocked' in html.lower():
            print(f"\n⚠️  Found 'blocked' in HTML")
        if 'bot' in html.lower():
            print(f"\n⚠️  Found 'bot' in HTML")
        if 'javascript' in html.lower():
            print(f"\n⚠️  Found 'javascript' in HTML")
        if 'cloudflare' in html.lower():
            print(f"\n⚠️  Found 'cloudflare' in HTML")

        # Try to extract some content
        print(f"\nLooking for content...")
        text = await page.inner_text('body')
        if text:
            print(f"Body text (first 200 chars): {text[:200]}")
        else:
            print(f"No text found in body")

    finally:
        await context.close()
        await browser.close()

async def main():
    print("\n" + "█"*80)
    print("PAGE LOAD CHECKER")
    print("Check what actually loads at each URL")
    print("█"*80)

    await check_page("https://news.ycombinator.com/", "HackerNews")
    await check_page("https://reddit.com/", "Reddit")

if __name__ == "__main__":
    asyncio.run(main())
