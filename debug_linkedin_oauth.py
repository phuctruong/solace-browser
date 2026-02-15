#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def debug_linkedin_oauth():
    """Debug LinkedIn OAuth buttons"""

    print("\n" + "=" * 80)
    print("DEBUGGING: LinkedIn OAuth Options")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False, debug_ui=False)
    await browser.start()

    print("📌 Navigating to LinkedIn login page...")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)

    print("✓ Page loaded\n")

    # Check for Apple button location
    print("📌 Finding Sign in with Apple button...")
    apple_btn = await browser.current_page.query_selector("button:has-text('Sign in with Apple')")
    if apple_btn:
        print("✓ Found Apple button")
        # Get its parent element to understand the layout
        parent_html = await apple_btn.evaluate("el => el.parentElement.outerHTML")
        print(f"\nParent HTML:\n{parent_html[:500]}\n")

    # Check the full OAuth container
    print("📌 Looking for OAuth container...")
    oauth_html = await browser.current_page.evaluate("""
        () => {
            // Try to find elements containing "Sign in" or "Continue"
            const container = document.querySelector('[data-testid*="sign"], [class*="oauth"], [class*="social"]');
            if (container) {
                return container.outerHTML.substring(0, 1000);
            }

            // Fallback: look for button containers
            const buttons = document.querySelectorAll('button');
            for (let btn of buttons) {
                if (btn.textContent.includes('Apple')) {
                    return btn.parentElement.parentElement.outerHTML.substring(0, 1000);
                }
            }

            return "OAuth container not found";
        }
    """)

    print(f"OAuth container HTML:\n{oauth_html}\n")

    # Check for any elements with "google" in data attributes
    print("📌 Searching for hidden Google elements...")
    google_elements = await browser.current_page.evaluate("""
        () => {
            const elements = [];
            const walker = document.createTreeWalker(
                document.documentElement,
                NodeFilter.SHOW_ELEMENT,
                null,
                false
            );

            let node;
            while (node = walker.nextNode()) {
                const html = node.outerHTML;
                if (html.toLowerCase().includes('google')) {
                    elements.push({
                        tag: node.tagName,
                        text: node.textContent.substring(0, 50),
                        display: window.getComputedStyle(node).display,
                        visibility: window.getComputedStyle(node).visibility
                    });
                }
            }

            return elements.slice(0, 10);  // Limit to first 10
        }
    """)

    print(f"Elements containing 'google':")
    for elem in google_elements:
        print(f"  - Tag: {elem['tag']}, Text: {elem['text']}, Display: {elem['display']}, Visibility: {elem['visibility']}")

    # Check the page title and meta description
    print("\n📌 Page information...")
    title = await browser.current_page.title()
    url = browser.current_page.url
    print(f"Title: {title}")
    print(f"URL: {url}")

    # Try clicking the Apple button to see what happens
    print("\n📌 Checking button structure...")
    buttons_info = await browser.current_page.evaluate("""
        () => {
            const buttons = document.querySelectorAll('button');
            return Array.from(buttons.slice(0, 5)).map(btn => ({
                text: btn.textContent.trim(),
                class: btn.className,
                onclick: btn.onclick ? 'YES' : 'NO',
                datatest: btn.getAttribute('data-test-id')
            }));
        }
    """)

    print("\nFirst 5 buttons:")
    for btn in buttons_info:
        print(f"  - {btn['text']}: onclick={btn['onclick']}, data-test={btn['datatest']}")

    # Take a screenshot to see the current state
    print("\n📌 Taking screenshot...")
    await browser.current_page.screenshot(path="artifacts/linkedin-oauth-debug.png")
    print("✓ Screenshot saved to artifacts/linkedin-oauth-debug.png")

    await browser.stop()
    print("\n✓ Debug complete\n")


if __name__ == "__main__":
    asyncio.run(debug_linkedin_oauth())
