#!/usr/bin/env python3
"""
Automated deletion of old LinkedIn projects
Uses position-based selection to find and delete specific projects
"""

import requests
import time
import json

BROWSER_API = "http://localhost:9222"
REQUEST_TIMEOUT = 30

OLD_PROJECTS = [
    "STILLWATER OS",
    "SOLACEAGI",
    "PZIP",
    "PHUCNET",
    "IF-THEORY"
]

def api_call(method, endpoint, data=None):
    """Make API call to browser server"""
    url = f"{BROWSER_API}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
        else:
            response = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)

        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_project_workflow(project_name):
    """
    Delete a specific project using LinkedIn's UI
    Strategy: Navigate to projects, find project card, edit, delete
    """
    print(f"\n{'='*70}")
    print(f"🗑️  Deleting: {project_name}")
    print('='*70)

    # Step 1: Navigate to projects page
    print("Step 1: Navigate to projects page...")
    result = api_call("POST", "/navigate", {"url": "https://www.linkedin.com/in/me/details/projects/"})
    if not result.get('success'):
        print(f"  ❌ Failed: {result.get('error')}")
        return False
    time.sleep(2)

    # Step 2: Look for project in the HTML
    print(f"Step 2: Searching for '{project_name}'...")
    html_result = api_call("GET", "/html-clean")
    html = html_result.get('html', '')

    if project_name not in html:
        print(f"  ⚠️  Project '{project_name}' not found on page")
        return False

    print(f"  ✓ Found '{project_name}' on page")

    # Step 3: Try different strategies to click the edit button
    print("Step 3: Attempting to click edit button...")

    # Strategy based on ARIA snapshot - LinkedIn uses LINKS not BUTTONS
    selectors = [
        # Strategy A: Exact ARIA label (found in snapshot)
        f"a[aria-label='Edit project {project_name}']",
        # Strategy B: Playwright role + name selector
        f"link[name='Edit project {project_name}']",
        # Strategy C: Link with partial match
        f"a[aria-label*='Edit project {project_name}']",
        # Strategy D: Text-based (most stable)
        f"a:has-text('Edit project {project_name}')",
    ]

    success = False
    for selector in selectors:
        print(f"  Trying selector: {selector[:50]}...")
        result = api_call("POST", "/click", {"selector": selector})

        if result.get('success'):
            print(f"  ✓ Clicked edit button")
            success = True
            break
        else:
            print(f"  ✗ Failed: {result.get('error', 'unknown')[:50]}")

    if not success:
        print(f"  ❌ Could not find edit button for '{project_name}'")
        print(f"  💡 Manual deletion required")
        return False

    time.sleep(1.5)

    # Step 4: Click Delete button in the edit modal
    print("Step 4: Looking for Delete button...")
    delete_selectors = [
        "button:has-text('Delete')",
        "button[aria-label*='Delete']",
        "a:has-text('Delete')",
    ]

    deleted = False
    for selector in delete_selectors:
        result = api_call("POST", "/click", {"selector": selector})
        if result.get('success'):
            print(f"  ✓ Clicked Delete")
            deleted = True
            break

    if not deleted:
        print(f"  ❌ Could not find Delete button")
        return False

    time.sleep(1)

    # Step 5: Confirm deletion
    print("Step 5: Confirming deletion...")
    confirm_selectors = [
        "button:has-text('Delete'):has-text('Confirm')",
        "button:has-text('Yes')",
        "button[aria-label*='confirm']",
    ]

    confirmed = False
    for selector in confirm_selectors:
        result = api_call("POST", "/click", {"selector": selector})
        if result.get('success'):
            print(f"  ✓ Confirmed deletion")
            confirmed = True
            break

    time.sleep(2)

    print(f"✅ Successfully deleted: {project_name}")
    return True

def main():
    print("\n" + "="*70)
    print("🗑️  LINKEDIN PROJECT CLEANUP AUTOMATION")
    print("="*70)
    print("Deleting old projects with technical jargon")
    print("Keeping new HR-approved domain-named projects")
    print()

    # Check browser
    health = api_call("GET", "/health")
    if health.get('status') != 'ok':
        print("❌ Browser server not running")
        print("Start with: python3 persistent_browser_server.py")
        return

    print("✅ Browser server ready\n")

    # Take before screenshot
    print("📸 Taking before screenshot...")
    screenshot = api_call("GET", "/screenshot")
    print(f"   Saved: {screenshot.get('path')}\n")

    # Delete each old project
    deleted_count = 0
    for project_name in OLD_PROJECTS:
        success = delete_project_workflow(project_name)
        if success:
            deleted_count += 1

    # Take after screenshot
    print("\n📸 Taking after screenshot...")
    time.sleep(2)
    api_call("POST", "/navigate", {"url": "https://www.linkedin.com/in/me/details/projects/"})
    time.sleep(2)
    screenshot = api_call("GET", "/screenshot")
    print(f"   Saved: {screenshot.get('path')}\n")

    # Summary
    print("="*70)
    print("📊 CLEANUP SUMMARY")
    print("="*70)
    print(f"Projects deleted: {deleted_count}/{len(OLD_PROJECTS)}")
    print(f"Success rate: {deleted_count/len(OLD_PROJECTS)*100:.0f}%")

    if deleted_count == len(OLD_PROJECTS):
        print("\n✅ All old projects deleted successfully!")
    else:
        print(f"\n⚠️  {len(OLD_PROJECTS) - deleted_count} projects need manual deletion")

    print("\nFinal profile should have only:")
    for proj in ["Stillwater.com", "SolaceAgi.com", "PZip.com", "IFTheory.com", "Phuc.net"]:
        print(f"  • {proj}")

if __name__ == "__main__":
    main()
