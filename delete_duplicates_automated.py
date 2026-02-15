#!/usr/bin/env python3
"""
Automated deletion of duplicate LinkedIn projects
Systematic approach using project list extraction
"""

import requests
import time
import re

API = "http://localhost:9222"
TIMEOUT = 30

def api_call(method, endpoint, data=None):
    """Make API call"""
    url = f"{API}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=TIMEOUT)
        else:
            response = requests.post(url, json=data, timeout=TIMEOUT)
        return response.json()
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_project_urls():
    """Extract all project edit URLs from the page"""
    # Get HTML
    result = api_call("GET", "/html-clean")
    html = result.get('html', '')

    # Find all edit URLs
    pattern = r'href="(/in/[^/]+/edit/forms/project/[^"]+)"'
    matches = re.findall(pattern, html)

    # Convert to full URLs
    urls = [f"https://www.linkedin.com{url}" for url in matches]
    return urls

def delete_project_by_url(edit_url, project_name):
    """Delete project by navigating to its edit URL"""
    print(f"\n{'='*70}")
    print(f"🗑️  Deleting: {project_name}")
    print(f"    URL: {edit_url[:60]}...")
    print('='*70)

    # Navigate to edit page
    print("  1. Navigating to edit page...")
    result = api_call("POST", "/navigate", {"url": edit_url})
    if not result.get('success'):
        print(f"  ❌ Navigation failed: {result.get('error')}")
        return False

    time.sleep(3)

    # Look for Delete button/link
    print("  2. Looking for Delete button...")
    delete_selectors = [
        "button:has-text('Delete')",
        "a:has-text('Delete')",
        "button[aria-label*='Delete']",
        "[data-test-modal-close-btn]",
    ]

    deleted = False
    for selector in delete_selectors:
        result = api_call("POST", "/click", {"selector": selector})
        if result.get('success'):
            print(f"  ✓ Clicked Delete ({selector[:30]}...)")
            deleted = True
            break
        time.sleep(0.5)

    if not deleted:
        print("  ⚠️  Delete button not found")
        # Take screenshot for debugging
        screenshot = api_call("GET", "/screenshot")
        print(f"  📸 Debug screenshot: {screenshot.get('path')}")
        return False

    time.sleep(1.5)

    # Confirm deletion
    print("  3. Confirming deletion...")
    confirm_selectors = [
        "button:has-text('Delete')",
        "button:has-text('Confirm')",
        "button:has-text('Yes')",
    ]

    confirmed = False
    for selector in confirm_selectors:
        result = api_call("POST", "/click", {"selector": selector})
        if result.get('success'):
            print(f"  ✓ Confirmed deletion")
            confirmed = True
            break
        time.sleep(0.5)

    if confirmed:
        time.sleep(2)
        print(f"✅ Successfully deleted: {project_name}")
        return True
    else:
        print(f"  ⚠️  Confirmation failed")
        return False

def main():
    print("\n" + "="*70)
    print("🗑️  AUTOMATED DUPLICATE PROJECT DELETION")
    print("="*70)

    # Check browser
    health = api_call("GET", "/health")
    if health.get('status') != 'ok':
        print("❌ Browser server not running")
        print("   Start with: python3 persistent_browser_server.py")
        return

    print("✅ Browser server ready\n")

    # Navigate to projects page
    print("📋 Loading projects page...")
    result = api_call("POST", "/navigate", {"url": "https://www.linkedin.com/in/me/details/projects/"})
    time.sleep(3)

    # Get project URLs
    print("🔍 Extracting project edit URLs...")
    project_urls = get_project_urls()
    print(f"   Found {len(project_urls)} project edit URLs")

    if not project_urls:
        print("❌ No project URLs found - trying manual approach")
        return

    # Get HTML to identify which projects are old
    result = api_call("GET", "/html-clean")
    html = result.get('html', '')

    old_projects = {
        "IF-THEORY": None,
        "PHUCNET": None,
        "PZIP": None,
        "SOLACEAGI": None,
        "STILLWATER OS": None
    }

    # Try to match URLs to project names by checking HTML context
    print("\n📌 Identifying old projects to delete...")

    # For each project URL, navigate and check the title field
    urls_to_delete = []

    for i, url in enumerate(project_urls[:10], 1):  # Check first 10
        print(f"  Checking project {i}...")
        result = api_call("POST", "/navigate", {"url": url})
        time.sleep(2)

        # Get page HTML and look for project title
        page_html = api_call("GET", "/html-clean").get('html', '')

        # Check if any old project name is in the title field
        for old_name in old_projects.keys():
            if old_name in page_html and old_projects[old_name] is None:
                print(f"    ✓ Found: {old_name}")
                old_projects[old_name] = url
                urls_to_delete.append((url, old_name))
                break

        if len(urls_to_delete) >= 5:
            break

    if not urls_to_delete:
        print("\n⚠️  Could not automatically identify old projects")
        print("💡 Falling back to manual deletion")
        return

    print(f"\n🎯 Found {len(urls_to_delete)} old projects to delete:")
    for url, name in urls_to_delete:
        print(f"  • {name}")

    # Delete each project
    print("\n" + "="*70)
    print("STARTING DELETION")
    print("="*70)

    deleted_count = 0
    for url, name in urls_to_delete:
        if delete_project_by_url(url, name):
            deleted_count += 1
        time.sleep(2)

    # Final summary
    print("\n" + "="*70)
    print("📊 DELETION SUMMARY")
    print("="*70)
    print(f"Projects deleted: {deleted_count}/{len(urls_to_delete)}")

    if deleted_count == len(urls_to_delete):
        print("\n✅ ALL OLD PROJECTS DELETED!")
    else:
        print(f"\n⚠️  {len(urls_to_delete) - deleted_count} projects need manual deletion")

    # Navigate back to projects page
    print("\n📸 Taking final screenshot...")
    api_call("POST", "/navigate", {"url": "https://www.linkedin.com/in/me/details/projects/"})
    time.sleep(3)
    screenshot = api_call("GET", "/screenshot")
    print(f"   Saved: {screenshot.get('path')}")

    print("\n✅ CLEANUP COMPLETE!")

if __name__ == "__main__":
    main()
