#!/usr/bin/env python3

"""
Debug LinkedIn ARIA tree - See what elements we're actually getting
"""

import asyncio
import json
from playwright.async_api import async_playwright
from browser_interactions import format_aria_tree, get_dom_snapshot
from dataclasses import asdict

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            storage_state='artifacts/linkedin_session.json'
        )

        page = await context.new_page()

        print("🌐 Navigating to LinkedIn...")
        await page.goto('https://www.linkedin.com/in/phuctruong/', wait_until='networkidle')

        print("📸 Getting ARIA tree...")
        aria_tree = await format_aria_tree(page, limit=500)

        print(f"\n✅ Found {len(aria_tree)} ARIA nodes\n")

        # Show first 50 nodes
        for i, node in enumerate(aria_tree[:50]):
            node_dict = asdict(node)
            role = node_dict.get('role', '')
            name = node_dict.get('name', '')
            ref = node_dict.get('ref', '')

            if role and name:
                print(f"{ref:6s} | role={role:15s} | name={name}")

        print("\n" + "=" * 80)
        print("🔍 Looking for Edit/Profile related elements...")
        print("=" * 80)

        for node in aria_tree:
            node_dict = asdict(node)
            role = (node_dict.get('role') or '').lower()
            name = (node_dict.get('name') or '').lower()
            ref = node_dict.get('ref')

            if 'edit' in name or 'profile' in name or 'pencil' in name:
                print(f"  {ref:6s} | {role:15s} | {name}")

        print("\n" + "=" * 80)
        print("🔍 Looking for textbox/input elements...")
        print("=" * 80)

        for node in aria_tree:
            node_dict = asdict(node)
            role = (node_dict.get('role') or '').lower()
            name = (node_dict.get('name') or '').lower()
            ref = node_dict.get('ref')

            if 'textbox' in role or 'input' in role:
                print(f"  {ref:6s} | {role:15s} | {name}")

        print("\n💾 Saving full ARIA tree to aria_debug.json...")
        with open('aria_debug.json', 'w') as f:
            json.dump([asdict(node) for node in aria_tree], f, indent=2)

        print("\n✅ Done! Check aria_debug.json for full tree")

        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
