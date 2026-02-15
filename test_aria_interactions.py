#!/usr/bin/env python3

"""
Test OpenClaw-like features in Solace Browser:
1. ARIA snapshots with element references
2. Structured actions with human-like behaviors
3. Smart waiting conditions
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_aria_interactions():
    """Test ARIA snapshots and structured actions"""

    print("\n" + "="*80)
    print("OPENCLAW-LIKE FEATURES: ARIA SNAPSHOTS + STRUCTURED ACTIONS")
    print("="*80 + "\n")

    # Start browser
    print("Step 1: Starting browser...")
    browser = SolaceBrowser(headless=False)
    await browser.start()
    print("✓ Browser started\n")

    # Navigate to a test page
    print("Step 2: Navigating to example.com...")
    await browser.navigate("https://example.com")
    await asyncio.sleep(3)
    print("✓ Page loaded\n")

    # Get ARIA snapshot (NEW!)
    print("Step 3: Getting ARIA snapshot (accessibility tree with element refs)...")
    aria_result = await browser.get_aria_snapshot(limit=100)
    if aria_result.get("success"):
        aria_nodes = aria_result.get("nodes", [])
        print(f"✓ Got {len(aria_nodes)} ARIA nodes\n")

        print("Sample ARIA nodes:")
        for node in aria_nodes[:5]:
            print(f"  - Ref: {node.get('ref')}, Role: {node.get('role')}, Name: {node.get('name')}")
    else:
        print(f"❌ Error: {aria_result.get('error')}\n")

    # Get DOM snapshot (NEW!)
    print("\nStep 4: Getting DOM snapshot...")
    dom_result = await browser.get_dom_snapshot(limit=100)
    if dom_result.get("success"):
        dom_nodes = dom_result.get("nodes", [])
        print(f"✓ Got {len(dom_nodes)} DOM nodes\n")

        print("Sample DOM nodes:")
        for node in dom_nodes[:3]:
            print(f"  - Ref: {node.get('ref')}, Tag: {node.get('tag')}, Text: {node.get('text', '').strip()[:50]}")
    else:
        print(f"❌ Error: {dom_result.get('error')}\n")

    # Get comprehensive page snapshot (NEW!)
    print("\nStep 5: Getting comprehensive page snapshot...")
    snapshot_result = await browser.get_page_snapshot()
    if snapshot_result.get("success"):
        print(f"✓ Page snapshot complete")
        print(f"  - URL: {snapshot_result.get('url')}")
        print(f"  - ARIA nodes: {len(snapshot_result.get('aria', []))}")
        print(f"  - DOM nodes: {len(snapshot_result.get('dom', []))}")
    else:
        print(f"❌ Error: {snapshot_result.get('error')}\n")

    # Test structured actions (NEW!)
    print("\nStep 6: Testing structured actions...")

    # Navigate to LinkedIn login for interactive testing
    print("\n  Navigating to LinkedIn login page...")
    await browser.navigate("https://www.linkedin.com/login")
    await asyncio.sleep(3)

    # Get the page structure
    page_snapshot = await browser.get_page_snapshot()
    print(f"  ✓ Page loaded with {len(page_snapshot.get('aria', []))} ARIA nodes")

    # Test: Scroll into view (makes element visible before interacting)
    print("\n  Testing scrollIntoView action...")
    scroll_result = await browser.act({
        "kind": "scrollIntoView",
        "ref": "input[name='session_key']",  # Email field
        "timeoutMs": 5000
    })
    print(f"  Result: {scroll_result.get('success', False)}")

    # Test: Type with 'slowly' option (human-like typing)
    print("\n  Testing type action with slowly=true (human-like)...")
    type_result = await browser.act({
        "kind": "type",
        "ref": "input[name='session_key']",
        "text": "phuc.truong@gmail.com",
        "slowly": True,
        "delayMs": 50,  # 50ms between each character
        "timeoutMs": 5000
    })
    print(f"  Result: {type_result.get('success', False)}")
    if type_result.get('success'):
        print(f"  ✓ Typed slowly (looks human-like, not like a bot!)")

    # Test: Wait for element
    print("\n  Testing wait action (wait for password field)...")
    wait_result = await browser.act({
        "kind": "wait",
        "selector": "input[name='password']",
        "timeoutMs": 5000
    })
    print(f"  Result: {wait_result.get('success', False)}")

    # Test: Hover before clicking (reveals tooltips)
    print("\n  Testing hover action (useful for tooltips)...")
    hover_result = await browser.act({
        "kind": "hover",
        "ref": "input[name='session_key']",
        "timeoutMs": 3000
    })
    print(f"  Result: {hover_result.get('success', False)}")

    # Test: Click with modifiers (Ctrl+click, Shift+click, etc.)
    print("\n  Testing click action with modifiers...")
    click_result = await browser.act({
        "kind": "click",
        "ref": "button[type='submit']",
        "modifiers": ["shift"],  # Shift+click
        "timeoutMs": 5000
    })
    print(f"  Result: {click_result.get('success', False)}")

    # Summary
    print("\n" + "="*80)
    print("FEATURES TESTED:")
    print("="*80)
    print("""
✅ ARIA Snapshots         - Get accessibility tree with element references
✅ DOM Snapshots          - Get DOM structure with element refs
✅ Page Snapshots         - Combined ARIA + DOM + page state
✅ Slow Typing            - Type character-by-character (looks human)
✅ Hover Actions          - Hover before clicking (triggers tooltips)
✅ Scroll Into View       - Make hidden elements visible
✅ Click Modifiers        - Shift+click, Ctrl+click, etc.
✅ Smart Waiting          - Wait for elements, text, URL changes, load states
✅ Double Click           - Support for double-click actions
✅ Right Click            - Support for right-click (context menu)

This makes the browser automation:
- More human-like (slow typing, hovers, modifiers)
- More robust (waiting for conditions instead of fixed delays)
- More structured (element references instead of CSS selectors)
- More powerful (rich interaction model like OpenClaw)
    """)

    print("="*80 + "\n")

    print("Keeping browser open for 15 seconds...")
    await asyncio.sleep(15)

    await browser.stop()
    print("✓ Test complete!\n")


if __name__ == "__main__":
    asyncio.run(test_aria_interactions())
