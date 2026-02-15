#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def debug_linkedin_buttons():
    """Debug script to show all buttons on LinkedIn login page"""

    print("\n" + "=" * 80)
    print("DEBUGGING: LinkedIn Login Page Buttons")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False, debug_ui=False)
    await browser.start()

    print("📌 Navigating to LinkedIn login page...")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)
    await browser.current_page.screenshot(path="artifacts/linkedin-debug.png")
    print("✓ Page loaded\n")

    print("📌 Finding all buttons...")
    buttons = await browser.current_page.query_selector_all("button")
    print(f"\nTotal buttons: {len(buttons)}\n")

    print("ALL BUTTONS:")
    print("-" * 80)

    for i, btn in enumerate(buttons, 1):
        text = await btn.text_content()
        aria_label = await btn.get_attribute('aria-label')
        html_class = await btn.get_attribute('class')
        btn_id = await btn.get_attribute('id')

        # Check if button contains "google" anywhere
        has_google = ('google' in text.lower()) if text else False
        has_google = has_google or (('google' in aria_label.lower()) if aria_label else False)
        has_google = has_google or (('google' in html_class.lower()) if html_class else False)

        google_marker = " [CONTAINS GOOGLE]" if has_google else ""

        print(f"{i:3}. text='{text.strip() if text else '(empty)'}'")
        if aria_label:
            print(f"      aria-label='{aria_label}'")
        if html_class:
            print(f"      class='{html_class}'")
        if btn_id:
            print(f"      id='{btn_id}'")
        print(f"{google_marker}")
        print()

    # Also check for links that might be Google signin
    print("\n" + "=" * 80)
    print("CHECKING FOR GOOGLE LINKS")
    print("=" * 80 + "\n")

    links = await browser.current_page.query_selector_all("a")
    print(f"Total links: {len(links)}\n")

    google_links = []
    for link in links:
        text = await link.text_content()
        aria_label = await link.get_attribute('aria-label')
        href = await link.get_attribute('href')

        if text and 'google' in text.lower():
            google_links.append((text.strip(), aria_label, href))

    if google_links:
        print("Links containing 'google':")
        for text, aria_label, href in google_links:
            print(f"  - {text}")
            print(f"    aria-label: {aria_label}")
            print(f"    href: {href}")
            print()
    else:
        print("No links containing 'google' found")

    # Also look at page HTML structure around "google"
    print("\n" + "=" * 80)
    print("SEARCHING HTML FOR 'GOOGLE'")
    print("=" * 80 + "\n")

    html = await browser.current_page.evaluate("() => document.documentElement.outerHTML")
    if 'google' in html.lower():
        print("✓ HTML contains 'google'")
        # Find the context
        lower_html = html.lower()
        google_pos = lower_html.find('google')
        snippet_start = max(0, google_pos - 150)
        snippet_end = min(len(html), google_pos + 150)
        snippet = html[snippet_start:snippet_end]
        print(f"\nContext around first 'google':\n{snippet}\n")
    else:
        print("✗ HTML does not contain 'google'")

    print("\n" + "=" * 80)
    print("CLEANUP")
    print("=" * 80 + "\n")

    await browser.stop()
    print("✓ Done\n")


if __name__ == "__main__":
    asyncio.run(debug_linkedin_buttons())
