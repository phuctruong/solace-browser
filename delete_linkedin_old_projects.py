#!/usr/bin/env python3
"""
Delete old LinkedIn projects automatically
Uses OpenClaw patterns: slowly typing, keyboard control
"""

import requests
import time

BROWSER_API = "http://localhost:9222"
REQUEST_TIMEOUT = 30

OLD_PROJECTS = [
    "IF-THEORY",
    "PHUCNET",
    "PZIP",
    "SOLACEAGI",
    "STILLWATER OS"
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

def delete_project(project_name, index=0):
    """Delete a specific project by finding its edit button"""
    print(f"\n{'='*70}")
    print(f"🗑️  Deleting: {project_name}")
    print('='*70)

    # Navigate to projects page
    print("  Navigating to projects page...")
    result = api_call("POST", "/navigate", {"url": "https://www.linkedin.com/in/me/details/projects/"})
    if not result.get('success'):
        print(f"  ❌ Failed to navigate")
        return False
    time.sleep(2)

    # Try to find and click the edit button for this project
    # LinkedIn uses aria-label on edit buttons
    selectors_to_try = [
        f"button[aria-label*='Edit {project_name}']",
        f"button[aria-label*='Edit']:nth-of-type({index + 1})",
        # Try clicking all edit buttons and checking which modal opens
    ]

    print("  Looking for edit button...")
    edit_clicked = False

    for selector in selectors_to_try:
        print(f"  Trying: {selector[:50]}...")
        result = api_call("POST", "/click", {"selector": selector})
        if result.get('success'):
            print(f"  ✓ Clicked edit button")
            edit_clicked = True
            break
        time.sleep(0.5)

    if not edit_clicked:
        print(f"  ⚠️  Could not find edit button - trying manual approach")
        print(f"  💡 MANUAL: Click edit icon for '{project_name}' → Delete → Confirm")
        return False

    time.sleep(2)

    # Look for Delete button in modal
    print("  Looking for Delete button...")
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
        time.sleep(0.5)

    if not deleted:
        print(f"  ⚠️  Could not find Delete button")
        return False

    time.sleep(1)

    # Confirm deletion
    print("  Confirming deletion...")
    confirm_selectors = [
        "button:has-text('Delete'):has-text('confirm')",
        "button:has-text('Yes')",
        "button[data-test-modal-close-btn]",
    ]

    for selector in confirm_selectors:
        result = api_call("POST", "/click", {"selector": selector})
        if result.get('success'):
            print(f"  ✓ Confirmed")
            time.sleep(2)
            print(f"✅ Successfully deleted: {project_name}")
            return True

    print(f"  ⚠️  Could not confirm deletion")
    return False

def main():
    print("\n" + "="*70)
    print("🗑️  LINKEDIN OLD PROJECTS CLEANUP")
    print("="*70)
    print("Deleting old projects with technical jargon")
    print("Keeping new HR-approved domain-named projects\n")

    # Check browser
    health = api_call("GET", "/health")
    if health.get('status') != 'ok':
        print("❌ Browser server not running")
        return

    print("✅ Browser server ready\n")

    print("📋 Projects to delete:")
    for i, proj in enumerate(OLD_PROJECTS, 1):
        print(f"  {i}. {proj}")
    print()

    # Manual approach with clear instructions
    print("="*70)
    print("⚠️  SEMI-AUTOMATED APPROACH")
    print("="*70)
    print("LinkedIn's dynamic structure requires manual steps.")
    print("\nFor each old project, I'll navigate to the page.")
    print("YOU: Click edit icon → Delete → Confirm")
    print("\nPress Enter when ready to start...")
    input()

    for i, project in enumerate(OLD_PROJECTS):
        print(f"\n{'='*70}")
        print(f"[{i+1}/{len(OLD_PROJECTS)}] {project}")
        print('='*70)

        # Navigate to projects
        result = api_call("POST", "/navigate", {"url": "https://www.linkedin.com/in/me/details/projects/"})
        time.sleep(2)

        # Take screenshot so user can see
        screenshot = api_call("GET", "/screenshot")
        print(f"📸 Screenshot: {screenshot.get('path')}")

        print(f"\n👉 MANUAL STEP:")
        print(f"   1. Find '{project}' in the browser")
        print(f"   2. Click the edit icon (pencil)")
        print(f"   3. Click 'Delete'")
        print(f"   4. Confirm deletion")
        print(f"\nPress Enter when done...")
        input()

    # Final verification
    print("\n" + "="*70)
    print("📊 FINAL VERIFICATION")
    print("="*70)

    result = api_call("POST", "/navigate", {"url": "https://www.linkedin.com/in/me/details/projects/"})
    time.sleep(2)
    screenshot = api_call("GET", "/screenshot")
    print(f"📸 Final screenshot: {screenshot.get('path')}")

    print("\nYou should now see only:")
    for proj in ["Stillwater.com", "SolaceAgi.com", "PZip.com", "IFTheory.com", "Phuc.net"]:
        print(f"  • {proj}")

    print("\n✅ CLEANUP COMPLETE!")

if __name__ == "__main__":
    main()
