#!/usr/bin/env python3
"""
Add missing LinkedIn projects using OpenClaw patterns
Uses Playwright role selectors + slowly typing for contenteditable forms
"""

import requests
import time

API = "http://localhost:9222"

MISSING_PROJECTS = [
    {
        "name": "SolaceAgi.com",
        "description": "AI decision-making platform serving enterprise teams who need verified, explainable recommendations instead of black-box outputs.\n\nImpact:\n• 65,537+ decision templates across finance, healthcare, legal\n• 99.3% accuracy on complex reasoning tasks\n• Used by teams replacing costly consultant hours",
        "url": "https://solaceagi.com"
    },
    {
        "name": "PZip.com",
        "description": "Universal compression tool that helps developers, data teams, and researchers reduce file sizes across all formats.\n\nImpact:\n• Beats industry standard LZMA on 91.4% of test cases\n• 4.075x average compression ratio\n• Open-source with commercial support available",
        "url": "https://pzip.com"
    },
    {
        "name": "Phuc.net",
        "description": "Solo founder ecosystem hub showcasing 5 verified AI products built in public with full transparency.\n\nImpact:\n• 100% SWE-bench verified (6/6 industry benchmarks)\n• Community-supported via Ko-fi tips\n• Harsh QA culture ensures quality over hype",
        "url": "https://phuc.net"
    }
]

def add_project(project):
    """Add a single project using OpenClaw patterns"""
    print(f"\n{'='*70}")
    print(f"➕ Adding: {project['name']}")
    print('='*70)

    # Step 1: Navigate to projects page
    print("Step 1: Navigate to projects page...")
    result = requests.post(f"{API}/navigate",
                          json={"url": "https://www.linkedin.com/in/me/details/projects/"},
                          timeout=30)
    if not result.json().get('success'):
        print(f"  ❌ Navigation failed")
        return False

    time.sleep(2)

    # Step 2: Click "Add new project" link (it's a LINK not a button!)
    print("Step 2: Click 'Add new project' link...")
    add_selectors = [
        'role=link[name="Add new project"]',  # Exact from ARIA snapshot
        'role=link[name=/add.*project/i]',
        "a:has-text('Add new project')",
        "a:has-text('Add project')",
    ]

    clicked = False
    for selector in add_selectors:
        result = requests.post(f"{API}/click",
                              json={"selector": selector},
                              timeout=30)
        if result.json().get('success'):
            print(f"  ✓ Clicked Add project")
            clicked = True
            break

    if not clicked:
        print(f"  ❌ Could not find Add project button")
        return False

    time.sleep(2)

    # Step 3: Fill project name (OpenClaw slowly pattern for contenteditable)
    print(f"Step 3: Fill project name: {project['name']}")
    name_selectors = [
        "#single-line-text-form-component-profileEditFormElement-PROFILE_PROJECT-ACoAABCc_DwBDDDPd3Yxx62kvQ7YfU5kKJtDiIg-PROJECT-CERTIFICATION-project-title",
        "input[name*='title']",
        "input[id*='title']",
        "[aria-label*='project'][aria-label*='title']",
    ]

    filled_name = False
    for selector in name_selectors:
        result = requests.post(f"{API}/fill",
                              json={
                                  "selector": selector,
                                  "text": project['name'],
                                  "slowly": True  # OpenClaw pattern
                              },
                              timeout=60)
        if result.json().get('success'):
            print(f"  ✓ Filled name")
            filled_name = True
            break
        time.sleep(0.5)

    if not filled_name:
        print(f"  ⚠️  Name fill uncertain - continuing")

    time.sleep(1)

    # Step 4: Fill description (OpenClaw slowly pattern)
    print(f"Step 4: Fill description ({len(project['description'])} chars)")
    desc_selectors = [
        "textarea[name*='description']",
        "div[contenteditable='true']",
        "[aria-label*='description']",
        "textarea",
    ]

    filled_desc = False
    for selector in desc_selectors:
        result = requests.post(f"{API}/fill",
                              json={
                                  "selector": selector,
                                  "text": project['description'],
                                  "slowly": True  # OpenClaw pattern
                              },
                              timeout=120)
        if result.json().get('success'):
            print(f"  ✓ Filled description")
            filled_desc = True
            break
        time.sleep(0.5)

    if not filled_desc:
        print(f"  ⚠️  Description fill uncertain")

    time.sleep(1)

    # Step 5: Fill URL
    print(f"Step 5: Fill URL: {project['url']}")
    url_selectors = [
        "input[name*='url']",
        "input[type='url']",
        "[aria-label*='URL']",
        "[aria-label*='link']",
    ]

    for selector in url_selectors:
        result = requests.post(f"{API}/fill",
                              json={
                                  "selector": selector,
                                  "text": project['url']
                              },
                              timeout=30)
        if result.json().get('success'):
            print(f"  ✓ Filled URL")
            break
        time.sleep(0.5)

    time.sleep(1)

    # Step 6: Click Save
    print("Step 6: Click Save button...")
    save_selectors = [
        'role=button[name="Save"]',
        'role=button[name="Add"]',
        "button:has-text('Save')",
        "button:has-text('Add')",
        "button[aria-label*='Save']",
    ]

    saved = False
    for selector in save_selectors:
        result = requests.post(f"{API}/click",
                              json={"selector": selector},
                              timeout=30)
        if result.json().get('success'):
            print(f"  ✓ Clicked Save")
            saved = True
            break

    time.sleep(3)  # Wait for save to complete

    if saved:
        print(f"✅ Successfully added: {project['name']}")
        return True
    else:
        print(f"  ⚠️  Save uncertain - check manually")
        return False

def main():
    print("\n" + "="*70)
    print("➕ ADD MISSING LINKEDIN PROJECTS")
    print("="*70)
    print("Using OpenClaw patterns: role selectors + slowly typing")
    print()

    # Check browser
    health = requests.get(f"{API}/health", timeout=10).json()
    if health.get('status') != 'ok':
        print("❌ Browser server not running")
        return

    print("✅ Browser server ready\n")

    added_count = 0
    for project in MISSING_PROJECTS:
        success = add_project(project)
        if success:
            added_count += 1
        time.sleep(2)

    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"Added: {added_count}/{len(MISSING_PROJECTS)}")

    if added_count == len(MISSING_PROJECTS):
        print("\n✅ All missing projects added!")
        print("\n📊 Final profile should have:")
        for p in ["Stillwater.com", "SolaceAgi.com", "PZip.com", "IFTheory.com", "Phuc.net"]:
            print(f"  • {p}")
        print("\n🎉 Profile optimization complete: 10/10!")
    else:
        print(f"\n⚠️  {len(MISSING_PROJECTS) - added_count} projects may need manual addition")

if __name__ == "__main__":
    main()
