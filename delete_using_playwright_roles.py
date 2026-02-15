#!/usr/bin/env python3
"""
Delete LinkedIn projects using Playwright role selectors
Based on OpenClaw pattern: role + name is most stable
"""

import requests
import time

API = "http://localhost:9222"

OLD_PROJECTS = [
    ("IF-THEORY", "n391"),
    ("PHUCNET", "n403"),
    ("PZIP", "n409"),
    ("SOLACEAGI", "n421"),
    ("STILLWATER OS", "n427")
]

def delete_project_with_role_selector(project_name, aria_ref):
    """Delete using Playwright get_by_role selector"""
    print(f"\n{'='*70}")
    print(f"🗑️  Deleting: {project_name} (ARIA ref: {aria_ref})")
    print('='*70)

    # Navigate to projects
    result = requests.post(f"{API}/navigate",
                          json={"url": "https://www.linkedin.com/in/me/details/projects/"},
                          timeout=30)
    time.sleep(2)

    # Strategy: Use role-based Playwright selector
    # LinkedIn uses role="link" with name="Edit project {NAME}"
    selector = f'role=link[name="Edit project {project_name}"]'

    print(f"Step 1: Clicking edit link with role selector...")
    print(f"   Selector: {selector}")

    result = requests.post(f"{API}/click",
                          json={"selector": selector},
                          timeout=30)

    if not result.json().get('success'):
        # Fallback: Try with regex pattern
        selector = f'role=link[name=/Edit project {project_name}/i]'
        print(f"   Retry with regex: {selector}")
        result = requests.post(f"{API}/click",
                              json={"selector": selector},
                              timeout=30)

    if not result.json().get('success'):
        print(f"  ❌ Failed to click edit link")
        print(f"     Error: {result.json().get('error', 'unknown')}")
        return False

    print(f"  ✓ Clicked edit link")
    time.sleep(1.5)

    # Click Delete button
    print(f"Step 2: Clicking Delete button...")
    delete_selectors = [
        'role=button[name="Delete"]',
        'role=button[name=/delete/i]',
        "button:has-text('Delete')",
    ]

    deleted = False
    for selector in delete_selectors:
        result = requests.post(f"{API}/click",
                              json={"selector": selector},
                              timeout=30)
        if result.json().get('success'):
            print(f"  ✓ Clicked Delete")
            deleted = True
            break

    if not deleted:
        print(f"  ❌ Could not find Delete button")
        return False

    time.sleep(1)

    # Confirm
    print(f"Step 3: Confirming deletion...")
    confirm_selectors = [
        'role=button[name="Delete"]',  # Might be same button
        'role=button[name="Confirm"]',
        'role=button[name="Yes"]',
        "button:has-text('Delete')",
        "button:has-text('Yes')",
    ]

    confirmed = False
    for selector in confirm_selectors:
        result = requests.post(f"{API}/click",
                              json={"selector": selector},
                              timeout=30)
        if result.json().get('success'):
            print(f"  ✓ Confirmed deletion")
            confirmed = True
            break

    if not confirmed:
        print(f"  ⚠️  Confirmation may have failed")

    time.sleep(2)
    print(f"✅ Completed deletion workflow for {project_name}")
    return True

def main():
    print("\n" + "="*70)
    print("🗑️  LINKEDIN PROJECT DELETION - PLAYWRIGHT ROLE SELECTORS")
    print("="*70)
    print("Using OpenClaw pattern: role + name (most stable)")
    print()

    # Check browser
    health = requests.get(f"{API}/health", timeout=10).json()
    if health.get('status') != 'ok':
        print("❌ Browser server not running")
        return

    print("✅ Browser server ready\n")

    deleted_count = 0
    for project_name, aria_ref in OLD_PROJECTS:
        success = delete_project_with_role_selector(project_name, aria_ref)
        if success:
            deleted_count += 1
        time.sleep(1)

    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)
    print(f"Deleted: {deleted_count}/{len(OLD_PROJECTS)}")

    if deleted_count == len(OLD_PROJECTS):
        print("\n✅ All old projects deleted!")
    else:
        print(f"\n⚠️  {len(OLD_PROJECTS) - deleted_count} projects remaining")

if __name__ == "__main__":
    main()
